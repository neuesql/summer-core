"""
Dependency Injection Decorators.

Provides decorators for automatic dependency injection including @Autowired,
@Bean, @Value, and @Qualifier.
"""

from typing import Any, Callable, Optional, Type, TypeVar, Union, get_type_hints
from functools import wraps
import inspect

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


def Autowired(target: Optional[Union[Callable, Type]] = None, *, required: bool = True) -> Any:
    """
    Decorator for automatic dependency injection.
    
    Can be used on constructors, methods, or fields to automatically inject
    dependencies from the application context.
    
    Args:
        target: The target to decorate (constructor, method, or field)
        required: Whether the dependency is required (default: True)
        
    Returns:
        The decorated target with autowiring metadata
        
    Example:
        class UserService:
            @Autowired
            def __init__(self, user_repository: UserRepository):
                self.user_repository = user_repository
                
            @Autowired
            def set_email_service(self, email_service: EmailService):
                self.email_service = email_service
    """
    def decorator(func_or_class: Union[Callable, Type]) -> Union[Callable, Type]:
        if inspect.isclass(func_or_class):
            # Decorating a class - mark constructor for autowiring
            if hasattr(func_or_class, '__init__'):
                func_or_class.__init__ = _mark_for_autowiring(func_or_class.__init__, required)
            func_or_class._summer_autowired_constructor = True
        else:
            # Decorating a method or function
            func_or_class = _mark_for_autowiring(func_or_class, required)
        
        return func_or_class
    
    if target is None:
        # Called with arguments: @Autowired(required=False)
        return decorator
    else:
        # Called without arguments: @Autowired
        return decorator(target)


def _mark_for_autowiring(func: Callable, required: bool) -> Callable:
    """Mark a function for autowiring and extract dependency information."""
    func._summer_autowired = True
    func._summer_required = required
    
    # Extract type hints for dependency resolution
    type_hints = get_type_hints(func)
    sig = inspect.signature(func)
    
    dependencies = []
    for param_name, param in sig.parameters.items():
        if param_name == 'self':
            continue
            
        param_type = type_hints.get(param_name, param.annotation)
        if param_type != inspect.Parameter.empty:
            dependencies.append({
                'name': param_name,
                'type': param_type,
                'required': required and param.default == inspect.Parameter.empty
            })
    
    func._summer_dependencies = dependencies
    return func


def Bean(func: Optional[F] = None, *, name: Optional[str] = None, scope: str = "singleton") -> Union[F, Callable[[F], F]]:
    """
    Decorator to mark a method as a bean factory method.
    
    Methods annotated with @Bean are used to create and configure beans
    that will be managed by the Spring container.
    
    Args:
        func: The method to decorate (when used without parentheses)
        name: Optional custom name for the bean (defaults to method name)
        scope: Bean scope (singleton, prototype, request, session)
        
    Returns:
        The decorated method with bean metadata
        
    Example:
        @Configuration
        class AppConfig:
            @Bean
            def database_service(self) -> DatabaseService:
                return DatabaseService("postgresql://localhost/mydb")
                
            @Bean(name="customCache", scope="prototype")
            def cache_service(self) -> CacheService:
                return CacheService()
    """
    def decorator(method: F) -> F:
        method._summer_bean_method = True
        method._summer_bean_name = name or method.__name__
        method._summer_bean_scope = scope
        
        # Extract return type for bean registration
        type_hints = get_type_hints(method)
        return_type = type_hints.get('return', None)
        method._summer_bean_type = return_type
        
        # Extract dependencies from method parameters
        sig = inspect.signature(method)
        dependencies = []
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
                
            param_type = type_hints.get(param_name, param.annotation)
            if param_type != inspect.Parameter.empty:
                dependencies.append({
                    'name': param_name,
                    'type': param_type,
                    'required': param.default == inspect.Parameter.empty
                })
        
        method._summer_bean_dependencies = dependencies
        return method
    
    if func is None:
        return decorator
    else:
        return decorator(func)


def Value(expression: str, *, default: Any = None) -> Any:
    """
    Decorator for injecting values from configuration properties.
    
    Injects values from application properties, environment variables,
    or other configuration sources.
    
    Args:
        expression: The property expression (e.g., "${app.name}")
        default: Default value if property is not found
        
    Returns:
        A property placeholder that will be resolved at runtime
        
    Example:
        class DatabaseConfig:
            @Value("${database.url}")
            def set_database_url(self, url: str):
                self.database_url = url
                
            @Value("${database.pool.size:10}")  # Default value of 10
            def set_pool_size(self, size: int):
                self.pool_size = size
    """
    def decorator(func: Callable) -> Callable:
        func._summer_value_injection = True
        func._summer_value_expression = expression
        func._summer_value_default = default
        return func
    
    return decorator


def Qualifier(name: str) -> Callable:
    """
    Decorator to specify which bean to inject when multiple candidates exist.
    
    Used in conjunction with @Autowired to disambiguate between multiple
    beans of the same type.
    
    Args:
        name: The name of the specific bean to inject
        
    Returns:
        A decorator that marks the parameter with qualifier information
        
    Example:
        class OrderService:
            @Autowired
            def __init__(self, 
                        @Qualifier("primaryDatabase") db: DatabaseService,
                        @Qualifier("cacheDatabase") cache_db: DatabaseService):
                self.db = db
                self.cache_db = cache_db
    """
    def decorator(func: Callable) -> Callable:
        if not hasattr(func, '_summer_qualifiers'):
            func._summer_qualifiers = {}
        
        # This is a simplified implementation
        # In a full implementation, we'd need to track parameter positions
        func._summer_qualifiers['default'] = name
        return func
    
    return decorator


def PostConstruct(func: F) -> F:
    """
    Decorator to mark a method as a post-construct lifecycle callback.
    
    Methods annotated with @PostConstruct are called after dependency
    injection is complete and before the bean is put into service.
    
    Args:
        func: The method to mark as post-construct
        
    Returns:
        The decorated method
        
    Example:
        @Component
        class DatabaseService:
            @PostConstruct
            def initialize_connection_pool(self):
                # Initialize resources after all dependencies are injected
                self.connection_pool = create_pool()
    """
    func._summer_post_construct = True
    return func


def PreDestroy(func: F) -> F:
    """
    Decorator to mark a method as a pre-destroy lifecycle callback.
    
    Methods annotated with @PreDestroy are called before the bean
    is destroyed by the container.
    
    Args:
        func: The method to mark as pre-destroy
        
    Returns:
        The decorated method
        
    Example:
        @Component
        class DatabaseService:
            @PreDestroy
            def cleanup_resources(self):
                # Clean up resources before bean destruction
                if self.connection_pool:
                    self.connection_pool.close()
    """
    func._summer_pre_destroy = True
    return func


def is_autowired(func: Callable) -> bool:
    """
    Check if a function is marked for autowiring.
    
    Args:
        func: The function to check
        
    Returns:
        True if the function is marked for autowiring
    """
    return hasattr(func, '_summer_autowired') and func._summer_autowired


def is_bean_method(func: Callable) -> bool:
    """
    Check if a method is marked as a bean factory method.
    
    Args:
        func: The method to check
        
    Returns:
        True if the method is a bean factory method
    """
    return hasattr(func, '_summer_bean_method') and func._summer_bean_method


def get_bean_name(func: Callable) -> Optional[str]:
    """
    Get the bean name for a bean factory method.
    
    Args:
        func: The method to get the bean name for
        
    Returns:
        The bean name, or None if not a bean method
    """
    if is_bean_method(func):
        return getattr(func, '_summer_bean_name', None)
    return None