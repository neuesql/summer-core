"""
Component Registration Decorators.

Provides decorators for automatic bean registration including @Component,
@Service, @Repository, and @Configuration.
"""

from typing import Any, Callable, Optional, Type, TypeVar, Union
from functools import wraps

T = TypeVar('T', bound=type)


def Component(cls: Optional[T] = None, *, name: Optional[str] = None, scope: str = "singleton") -> Union[T, Callable[[T], T]]:
    """
    Decorator to mark a class as a Spring component for automatic detection.
    
    Classes annotated with @Component are automatically registered as beans
    in the application context during component scanning.
    
    Args:
        cls: The class to decorate (when used without parentheses)
        name: Optional custom name for the bean (defaults to lowercase class name)
        scope: Bean scope (singleton, prototype, request, session)
        
    Returns:
        The decorated class with component metadata
        
    Example:
        @Component
        class MyService:
            pass
            
        @Component(name="customService", scope="prototype")
        class AnotherService:
            pass
    """
    def decorator(target_class: T) -> T:
        # Set component metadata
        target_class._summer_component = True
        target_class._summer_component_type = "component"
        target_class._summer_bean_name = name or _generate_bean_name(target_class)
        target_class._summer_scope = scope
        
        return target_class
    
    if cls is None:
        # Called with arguments: @Component(name="...", scope="...")
        return decorator
    else:
        # Called without arguments: @Component
        return decorator(cls)


def Service(cls: Optional[T] = None, *, name: Optional[str] = None, scope: str = "singleton") -> Union[T, Callable[[T], T]]:
    """
    Decorator to mark a class as a service component.
    
    @Service is a specialization of @Component for service layer classes.
    It indicates that the class holds business logic.
    
    Args:
        cls: The class to decorate (when used without parentheses)
        name: Optional custom name for the bean (defaults to lowercase class name)
        scope: Bean scope (singleton, prototype, request, session)
        
    Returns:
        The decorated class with service metadata
        
    Example:
        @Service
        class UserService:
            def create_user(self, user_data):
                # Business logic here
                pass
    """
    def decorator(target_class: T) -> T:
        # Set service metadata
        target_class._summer_component = True
        target_class._summer_component_type = "service"
        target_class._summer_bean_name = name or _generate_bean_name(target_class)
        target_class._summer_scope = scope
        
        return target_class
    
    if cls is None:
        return decorator
    else:
        return decorator(cls)


def Repository(cls: Optional[T] = None, *, name: Optional[str] = None, scope: str = "singleton") -> Union[T, Callable[[T], T]]:
    """
    Decorator to mark a class as a repository component.
    
    @Repository is a specialization of @Component for data access layer classes.
    It indicates that the class encapsulates storage, retrieval, and search behavior.
    
    Args:
        cls: The class to decorate (when used without parentheses)
        name: Optional custom name for the bean (defaults to lowercase class name)
        scope: Bean scope (singleton, prototype, request, session)
        
    Returns:
        The decorated class with repository metadata
        
    Example:
        @Repository
        class UserRepository:
            def find_by_email(self, email: str):
                # Data access logic here
                pass
    """
    def decorator(target_class: T) -> T:
        # Set repository metadata
        target_class._summer_component = True
        target_class._summer_component_type = "repository"
        target_class._summer_bean_name = name or _generate_bean_name(target_class)
        target_class._summer_scope = scope
        
        return target_class
    
    if cls is None:
        return decorator
    else:
        return decorator(cls)


def Configuration(cls: Optional[T] = None, *, name: Optional[str] = None) -> Union[T, Callable[[T], T]]:
    """
    Decorator to mark a class as a configuration class.
    
    @Configuration classes contain @Bean methods that define beans to be
    managed by the Spring container. This is equivalent to XML configuration.
    
    Args:
        cls: The class to decorate (when used without parentheses)
        name: Optional custom name for the configuration class
        
    Returns:
        The decorated class with configuration metadata
        
    Example:
        @Configuration
        class AppConfig:
            @Bean
            def database_service(self) -> DatabaseService:
                return DatabaseService("postgresql://...")
    """
    def decorator(target_class: T) -> T:
        # Set configuration metadata
        target_class._summer_configuration = True
        target_class._summer_bean_name = name or _generate_bean_name(target_class)
        target_class._summer_bean_methods = []
        
        # Scan for @Bean methods
        for attr_name in dir(target_class):
            attr = getattr(target_class, attr_name)
            if hasattr(attr, '_summer_bean_method'):
                target_class._summer_bean_methods.append(attr_name)
        
        return target_class
    
    if cls is None:
        return decorator
    else:
        return decorator(cls)


def _generate_bean_name(cls: Type) -> str:
    """
    Generate a default bean name from the class name.
    
    Converts CamelCase class names to camelCase bean names.
    
    Args:
        cls: The class to generate a name for
        
    Returns:
        The generated bean name
    """
    class_name = cls.__name__
    if len(class_name) == 1:
        return class_name.lower()
    return class_name[0].lower() + class_name[1:]


def is_component(cls: Type) -> bool:
    """
    Check if a class is marked as a component.
    
    Args:
        cls: The class to check
        
    Returns:
        True if the class is a component
    """
    return hasattr(cls, '_summer_component') and cls._summer_component


def get_component_name(cls: Type) -> Optional[str]:
    """
    Get the component name for a class.
    
    Args:
        cls: The class to get the name for
        
    Returns:
        The component name, or None if not a component
    """
    if is_component(cls):
        return getattr(cls, '_summer_bean_name', None)
    return None


def get_component_scope(cls: Type) -> str:
    """
    Get the component scope for a class.
    
    Args:
        cls: The class to get the scope for
        
    Returns:
        The component scope (defaults to "singleton")
    """
    if is_component(cls):
        return getattr(cls, '_summer_scope', 'singleton')
    return 'singleton'