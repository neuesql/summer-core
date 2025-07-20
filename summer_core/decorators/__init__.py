"""
Framework Decorators.

This module provides all the Spring-style decorators for component registration,
dependency injection, aspect-oriented programming, and transaction management.
"""

from summer_core.decorators.component import Component, Service, Repository, Configuration
from summer_core.decorators.autowired import Autowired, Bean, Value, Qualifier
from summer_core.decorators.lifecycle import PostConstruct, PreDestroy, InitializingBean, DisposableBean

__all__ = [
    "Component",
    "Service",
    "Repository", 
    "Configuration",
    "Autowired",
    "Bean",
    "Value",
    "Qualifier",
    "PostConstruct",
    "PreDestroy",
    "InitializingBean",
    "DisposableBean",
]