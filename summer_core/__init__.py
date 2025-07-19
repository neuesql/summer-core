"""
Summer Core - A Python framework inspired by Spring Framework.

Provides enterprise-grade infrastructure for building scalable, maintainable Python applications
with features including dependency injection, aspect-oriented programming, declarative transaction
management, and enterprise integration capabilities.
"""

from summer_core.container.application_context import ApplicationContext, DefaultApplicationContext
from summer_core.decorators.component import Component, Service, Repository, Configuration
from summer_core.decorators.autowired import Autowired, Bean, Value, Qualifier

__version__ = "0.0.1"
__all__ = [
    "ApplicationContext",
    "DefaultApplicationContext",
    "Component",
    "Service", 
    "Repository",
    "Configuration",
    "Autowired",
    "Bean",
    "Value",
    "Qualifier",
]