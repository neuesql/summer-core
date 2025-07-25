"""
IoC Container Implementation.

This module provides the core Inversion of Control container functionality
including bean factory, application context, and dependency resolution.
"""

from summer_core.container.application_context import ApplicationContext
from summer_core.container.bean_factory import BeanFactory
from summer_core.container.bean_definition import BeanDefinition
from summer_core.container.scope import Scope, SingletonScope, PrototypeScope, RequestScope, SessionScope, ScopeRegistry

__all__ = [
    "ApplicationContext",
    "BeanFactory", 
    "BeanDefinition",
    "Scope",
    "SingletonScope",
    "PrototypeScope", 
    "RequestScope",
    "SessionScope",
    "ScopeRegistry",
]