# Overview

Nestipy is a Python framework built on top of Litestar or FastAPI hat follows the modular architecture of NestJS. It is designed to help structure your APIs  in an intuitive, easy to understand, and enjoyable way.

With Nestipy, you can build scalable and maintainable APIs with ease. The framework supports dependency injection, type annotations, decorators, and code generation, making it easy to write clean and testable code.

This framework is not a direct port of NestJS to Python but rather a re-imagining of the framework specifically for Python developers, including data scientists, data analysts, and data engineers. It aims to assist them in building better and faster APIs for their data applications.

Nestipy support <b>Graphql</b> by using strawberry.

## Key Features
### Modular Architecture

Nestipy follows the modular architecture of NestJS, which allows for easy separation of concerns and code organization. Each module contains a collection of related controllers, services, and providers.

### Dependency Injection
Nestipy supports dependency injection, which makes it easy to manage dependencies and write testable code. You can easily inject services and providers into your controllers using decorators.

### Decorators

Nestipy makes extensive use of decorators to define routes, middleware, and other application components. This helps keep the code concise and easy to read.

### Type Annotations

Nestipy leverages Python's type annotations to provide better tooling and help prevent errors. You can annotate your controllers, services, and providers with types to make your code more robust.

### Dynamic module

Nestipy includes a dynamic module option that allow to create dynamic module that can access IOC container.


### Code Generation

Nestipy includes a code generation tool that can create boilerplate code for modules, controllers, and other components. This saves you time and helps you focus on writing the code that matters.


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Credits

[NestJS](https://nestjs.com/), a framework for building Node.js applications.

[Litestar](https://litestar.dev/), a framework for effortlessly build performant APIs.

[FastAPI](https://fastapi.tiangolo.com/), a framework for building Python applications.