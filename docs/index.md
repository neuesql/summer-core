# Summer Core Framework

[![Release](https://img.shields.io/github/v/release/neuesql/summer-core)](https://img.shields.io/github/v/release/neuesql/summer-core)
[![Build status](https://img.shields.io/github/actions/workflow/status/neuesql/summer-core/main.yml?branch=main)](https://github.com/neuesql/summer-core/actions/workflows/main.yml?query=branch%3Amain)
[![Commit activity](https://img.shields.io/github/commit-activity/m/neuesql/summer-core)](https://img.shields.io/github/commit-activity/m/neuesql/summer-core)
[![License](https://img.shields.io/github/license/neuesql/summer-core)](https://img.shields.io/github/license/neuesql/summer-core)

**Summer Core** is a Python implementation of Spring Framework concepts, bringing enterprise Java patterns to Python for Data and AI applications.

## Key Features

- **Dependency Injection Container**: Manage object lifecycles and dependencies
- **Aspect-Oriented Programming**: Modularize cross-cutting concerns
- **Event System**: Build loosely coupled, event-driven applications
- **Configuration Management**: Configure applications with Python code or external files
- **Data Access Abstraction**: Work with different databases using a unified interface
- **Testing Support**: Easily test your applications with framework support

## Quick Start

```bash
# Install the package
pip install summer-core

# Create a simple application
```

```python
from summer_core.decorators import Component, Service, Autowired
from summer_core.container import ApplicationContext

# Define components
@Service
class UserService:
    def get_user(self, user_id):
        return {"id": user_id, "name": "John Doe"}

@Component
class UserController:
    @Autowired
    def __init__(self, user_service: UserService):
        self.user_service = user_service
    
    def get_user_details(self, user_id):
        return self.user_service.get_user(user_id)

# Create application context
context = ApplicationContext(base_packages=["myapp"])
context.refresh()

# Get controller and use it
controller = context.get_bean("userController")
user = controller.get_user_details(123)
print(user)
```

## Why Summer Core?

Summer Core brings the power and flexibility of Spring Framework to Python, making it easier to build maintainable, testable, and scalable applications. It's particularly well-suited for:

- **Data Processing Applications**: Build robust data pipelines with clear separation of concerns
- **AI/ML Applications**: Structure machine learning applications with dependency injection and AOP
- **Enterprise Applications**: Apply proven enterprise patterns to Python applications

## Getting Started

Check out the [Getting Started](overview/getting-started.md) guide to begin using Summer Core in your projects.

## Contributing

We welcome contributions! See our [contribution guidelines](https://github.com/neuesql/summer-core/blob/main/CONTRIBUTING.md) for details.