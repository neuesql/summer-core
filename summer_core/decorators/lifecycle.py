"""
Lifecycle Decorators - Bean lifecycle management decorators.

This module provides decorators for managing bean lifecycle callbacks
including post-construction initialization and pre-destruction cleanup.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar

F = TypeVar('F', bound=Callable[..., Any])


def PostConstruct(func: F) -> F:
    """
    Decorator to mark a method as a post-construct callback.
    
    Methods decorated with @PostConstruct will be called after
    dependency injection is complete and before the bean is
    made available for use.
    
    Args:
        func: The method to mark as post-construct
        
    Returns:
        The decorated method
        
    Example:
        @Component
        class DatabaseService:
            @PostConstruct
            def initialize_connection(self):
                # Setup database connection
                pass
    """
    if not hasattr(func, '__self__'):
        # Store metadata on the function for later processing
        func._summer_post_construct = True
    return func


def PreDestroy(func: F) -> F:
    """
    Decorator to mark a method as a pre-destroy callback.
    
    Methods decorated with @PreDestroy will be called before
    the bean is destroyed, allowing for cleanup of resources.
    
    Args:
        func: The method to mark as pre-destroy
        
    Returns:
        The decorated method
        
    Example:
        @Component
        class DatabaseService:
            @PreDestroy
            def cleanup_connection(self):
                # Close database connection
                pass
    """
    if not hasattr(func, '__self__'):
        # Store metadata on the function for later processing
        func._summer_pre_destroy = True
    return func


class InitializingBean(ABC):
    """
    Interface to be implemented by beans that need to react once all their
    properties have been set by the container.
    
    This provides an alternative to using the @PostConstruct decorator
    for initialization logic.
    """
    
    @abstractmethod
    def after_properties_set(self) -> None:
        """
        Invoked by the containing BeanFactory after it has set all bean properties
        and satisfied BeanFactoryAware, ApplicationContextAware etc.
        
        This method allows the bean instance to perform validation of its overall
        configuration and final initialization when all bean properties have been set.
        """
        pass


class DisposableBean(ABC):
    """
    Interface to be implemented by beans that want to release resources on destruction.
    
    This provides an alternative to using the @PreDestroy decorator
    for cleanup logic.
    """
    
    @abstractmethod
    def destroy(self) -> None:
        """
        Invoked by the containing BeanFactory on destruction of a bean.
        
        This method allows the bean instance to perform cleanup of resources
        before the bean is destroyed.
        """
        pass


def get_post_construct_methods(bean_class: type) -> list[str]:
    """
    Get all post-construct methods from a bean class.
    
    This includes both methods decorated with @PostConstruct and
    the after_properties_set method if the class implements InitializingBean.
    
    Args:
        bean_class: The bean class to inspect
        
    Returns:
        List of method names that should be called after construction
    """
    methods = []
    
    # Check for @PostConstruct decorated methods
    for attr_name in dir(bean_class):
        attr = getattr(bean_class, attr_name)
        if callable(attr) and hasattr(attr, '_summer_post_construct'):
            methods.append(attr_name)
    
    # Check for InitializingBean interface
    if issubclass(bean_class, InitializingBean):
        methods.append('after_properties_set')
    
    return methods


def get_pre_destroy_methods(bean_class: type) -> list[str]:
    """
    Get all pre-destroy methods from a bean class.
    
    This includes both methods decorated with @PreDestroy and
    the destroy method if the class implements DisposableBean.
    
    Args:
        bean_class: The bean class to inspect
        
    Returns:
        List of method names that should be called before destruction
    """
    methods = []
    
    # Check for @PreDestroy decorated methods
    for attr_name in dir(bean_class):
        attr = getattr(bean_class, attr_name)
        if callable(attr) and hasattr(attr, '_summer_pre_destroy'):
            methods.append(attr_name)
    
    # Check for DisposableBean interface
    if issubclass(bean_class, DisposableBean):
        methods.append('destroy')
    
    return methods