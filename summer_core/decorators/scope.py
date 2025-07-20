"""
Scope Decorator.

Provides the @Scope decorator for configuring bean scopes.
"""

from typing import Any, Callable, Optional, Type, TypeVar, Union

T = TypeVar('T', bound=type)


def Scope(scope_name: str) -> Callable[[T], T]:
    """
    Decorator to configure the scope of a bean.
    
    This decorator can be used in combination with component decorators
    to specify the scope of a bean.
    
    Args:
        scope_name: The name of the scope (singleton, prototype, request, session, or custom)
        
    Returns:
        The decorator function
        
    Example:
        @Component
        @Scope("prototype")
        class MyService:
            pass
            
        @Service
        @Scope("request")
        class RequestScopedService:
            pass
    """
    def decorator(target_class: T) -> T:
        # Set scope metadata
        target_class._summer_scope = scope_name
        return target_class
    
    return decorator


def get_bean_scope(cls: Type) -> str:
    """
    Get the scope for a bean class.
    
    Args:
        cls: The class to get the scope for
        
    Returns:
        The scope name (defaults to "singleton")
    """
    return getattr(cls, '_summer_scope', 'singleton')