import inspect
from dataclasses import dataclass
from typing import Callable, Any

from pyee import EventEmitter

from .middleware import MiddlewareConsumer
from ..ioc import PestyContainer
from ..utils import Utils
from ...common.decorator.injectable import Injectable


@dataclass
class MiddlewareDict:
    path: str
    middleware: Callable


class ModuleCompiler:
    module: Any
    middlewares: list[MiddlewareDict]

    def __init__(self, module: Callable):
        self.module = module
        self.container = PestyContainer()
        self.module_resolved = {}
        self.hooks = {}
        self.middlewares = []
        self.ee = EventEmitter()
        self.middleware_consumer = MiddlewareConsumer(self)

    def extract_hook_in_module(self, hook, module):
        if hasattr(module, hook) and inspect.ismethod(getattr(module, hook)):
            hook__ = getattr(module, hook)
            hooks = []
            if hook in self.hooks.keys():
                hooks = self.hooks[hook]
            hooks.append(hook__)
            self.hooks[hook] = hooks

    def extract_hooks_in_module(self, module):
        self.extract_hook_in_module("on_startup", module)
        self.extract_hook_in_module("on_shutdown", module)

    @classmethod
    def update_module_import(cls, module):
        setattr(module, 'imports', [im for im in (module.imports or []) if im is not None])

    async def register_and_resolve_provider(self, module, init=False):
        self.update_module_import(module)
        await self.resolve_providers_of_module(module)
        ins_m = module()
        self.module_resolved[module.__name__] = ins_m
        self.extract_hooks_in_module(ins_m)
        imports = getattr(module, 'imports')
        global_module = []
        if init:
            old_global_module = [m for m in imports if
                                 hasattr(m, "is_global__") and m.is_global__]
            for index, gb_module in enumerate(old_global_module):
                m = self.modify_module_imports(gb_module, old_global_module[0:index + 1])
                await self.register_and_resolve_provider(m)
                global_module.append(m)

        for module_import in [m for m in imports if
                              m not in global_module and m.__name__ not in self.module_resolved.keys()]:
            m = self.modify_module_imports(module_import, global_module)
            await self.register_and_resolve_provider(m)
            instance = m()
            self.module_resolved[m.__name__] = instance
            self.extract_hooks_in_module(instance)

    def modify_module_imports(self, module, global_modules):
        self.update_module_import(module)
        filtered_global_modules = [m for m in global_modules if m != module]
        module_imports: list = (module.imports or [])
        module_imports_with_global = filtered_global_modules + module_imports
        setattr(module, 'imports', module_imports_with_global)
        setattr(module, 'container__', self.container)
        return module

    async def recreate_async_provider(self, module):
        if hasattr(module, 'token__'):
            token = module.token__
            if hasattr(module, 'use_value__'):
                value = module.use_value__
                setattr(module, "providers", [Injectable(token)(lambda: value)] + module.providers)
            if hasattr(module, 'use_factory__'):
                use_factory = module.use_factory__
                inject = []
                if hasattr(module, 'provider_inject__'):
                    inject = self.filter_async_provider_inject(module.imports, module.provider_inject__)
                value = await self.resolve_use_factory(use_factory=use_factory, inject=inject)
                setattr(module, "providers", [Injectable(token)(lambda: value)] + module.providers)
                return

    @classmethod
    def extract_provider(cls, module):
        return [p for p in module.providers if hasattr(p, 'injectable__')]

    def filter_async_provider_inject(self, modules: list, inject: list):
        providers = []
        for module in modules:
            providers = providers + self.extract_provider(module)
        return [p for p in inject if p in providers]

    async def resolve_use_factory(self, use_factory, inject=None):
        if inject is None:
            inject = []
        factory_signature = inspect.signature(use_factory).parameters
        factory_dependencies = {}
        for param_name, param in factory_signature.items():
            if param.annotation in inject:
                dep_value = self.container.instances.get(param.annotation)
                factory_dependencies[param_name] = dep_value
        if inspect.iscoroutinefunction(use_factory):
            return await use_factory(**factory_dependencies)
        return use_factory(**factory_dependencies)

    async def resolve_providers_of_module(self, module):
        await self.resolve_controllers_of_module(module)
        self.extract_middleware_of_module(module)
        await self.recreate_async_provider(module)
        providers = self.extract_provider(module)
        for p in providers:
            is_middleware = hasattr(p, 'middleware__')
            if inspect.isclass(p):
                instance = self.container.resolve(p, module)
                self.put_module_provider_instance(module, p, instance, is_middleware=is_middleware)
            else:
                token = p.token__
                instance = self.container.resolve_method(p, token=token)
                self.put_module_provider_instance(module, token, instance, is_middleware=is_middleware)

    async def resolve_controllers_of_module(self, module):
        controllers = [ctrl for ctrl in module.controllers if hasattr(ctrl, 'controller__')]
        for ctrl in controllers:
            if inspect.isclass(ctrl):
                self.container.resolve(ctrl, module)
            else:
                token = ctrl.token__
                self.container.resolve_method(ctrl, token=token)

    @classmethod
    def put_module_provider_instance(cls, module, token, instance, is_middleware=False):
        if is_middleware:
            cls.put_module_element(module, 'middleware_instances__', token, instance)
        else:
            cls.put_module_element(module, 'provider_instances__', token, instance)

    @classmethod
    def put_module_element(cls, module, element_type, key, value):
        instances__ = {}
        if hasattr(module, element_type):
            instances__ = getattr(module, element_type)
        instances__[key] = value
        setattr(module, element_type, instances__)

    # MIDDLEWARE
    @classmethod
    def get_middleware_of_handler(cls, handler, path='path__'):
        path = getattr(handler, path) or ''
        if hasattr(handler, 'middleware__'):
            return path, getattr(handler, 'middleware__') or []
        return path, []

    def apply_middleware_to_path(self, path, middlewares: list):
        transformed_middleware = []
        for m in middlewares:
            if inspect.isclass(m):
                instance = m()
                middleware = getattr(instance, 'use')
                transformed_middleware.append(MiddlewareDict(path=path, middleware=middleware))
            elif inspect.isfunction(m) or inspect.ismethod(m):
                transformed_middleware.append(MiddlewareDict(path=path, middleware=m))

        self.middlewares += transformed_middleware
        return transformed_middleware

    def apply_middleware_to_ctrl(self, ctrl, middlewares=None):
        if middlewares is None:
            middlewares = []
        applied_middlewares = []
        ctrl_path, ctrl_middleware = self.get_middleware_of_handler(ctrl, path='path')
        applied_middlewares += self.apply_middleware_to_path(ctrl_path, middlewares + ctrl_middleware)
        methods = inspect.getmembers(ctrl, predicate=Utils.is_handler)
        for name, value in methods:
            method_path, method_middleware = self.get_middleware_of_handler(value)
            applied_middlewares += self.apply_middleware_to_path(ctrl_path + method_path
                                                                 , method_middleware)
        return applied_middlewares

    def extract_middleware_of_module(self, module):
        module_middlewares: list[MiddlewareDict] = []
        middlewares: list = [p for p in getattr(module, 'providers') if hasattr(p, 'middleware__')]
        controllers = [ctrl for ctrl in module.controllers if hasattr(ctrl, 'controller__')]
        for ctrl in controllers:
            module_middlewares += self.apply_middleware_to_ctrl(ctrl, middlewares)
        setattr(module, 'middlewares__', module_middlewares)

        if hasattr(module, 'pesty_module__') and getattr(module, 'pesty_module__'):
            if hasattr(module, 'configure'):
                c = self.middleware_consumer
                module_instance = module()
                module_instance.configure(c)

    # COMPILE
    async def compile(self):
        await self.register_and_resolve_provider(self.module, init=True)
        return self.module
