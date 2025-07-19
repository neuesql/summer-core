"""
Summer Framework Exception Hierarchy.

Defines all framework-specific exceptions with detailed error messages
and resolution suggestions.
"""


class SummerFrameworkError(Exception):
    """Base exception for all Summer framework errors."""
    
    def __init__(self, message: str, cause: Exception = None):
        """
        Initialize the framework error.
        
        Args:
            message: The error message
            cause: The underlying cause of the error
        """
        super().__init__(message)
        self.cause = cause


class BeanCreationError(SummerFrameworkError):
    """Raised when bean creation fails."""
    
    def __init__(self, bean_name: str, message: str, cause: Exception = None):
        """
        Initialize the bean creation error.
        
        Args:
            bean_name: The name of the bean that failed to create
            message: The error message
            cause: The underlying cause of the error
        """
        full_message = f"Error creating bean '{bean_name}': {message}"
        super().__init__(full_message, cause)
        self.bean_name = bean_name


class CircularDependencyError(SummerFrameworkError):
    """Raised when circular dependencies are detected."""
    
    def __init__(self, dependency_path: str):
        """
        Initialize the circular dependency error.
        
        Args:
            dependency_path: The circular dependency path
        """
        message = (
            f"Circular dependency detected: {dependency_path}. "
            "Consider using setter injection or @Lazy annotation to break the cycle."
        )
        super().__init__(message)
        self.dependency_path = dependency_path


class NoSuchBeanDefinitionError(SummerFrameworkError):
    """Raised when a requested bean is not found."""
    
    def __init__(self, bean_identifier: str, available_beans: list = None):
        """
        Initialize the no such bean definition error.
        
        Args:
            bean_identifier: The name or type of the bean that was not found
            available_beans: List of available bean names for suggestions
        """
        message = f"No bean definition found for '{bean_identifier}'"
        
        if available_beans:
            message += f". Available beans: {', '.join(available_beans)}"
        
        super().__init__(message)
        self.bean_identifier = bean_identifier
        self.available_beans = available_beans or []


class NoUniqueBeanDefinitionError(SummerFrameworkError):
    """Raised when multiple beans of the same type exist without a primary designation."""
    
    def __init__(self, bean_type: str, matching_beans: list):
        """
        Initialize the no unique bean definition error.
        
        Args:
            bean_type: The type that has multiple matching beans
            matching_beans: List of matching bean names
        """
        message = (
            f"Multiple beans of type '{bean_type}' found: {', '.join(matching_beans)}. "
            "Consider marking one as @Primary or use @Qualifier to specify which one to inject."
        )
        super().__init__(message)
        self.bean_type = bean_type
        self.matching_beans = matching_beans


class ConfigurationError(SummerFrameworkError):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str, config_source: str = None):
        """
        Initialize the configuration error.
        
        Args:
            message: The error message
            config_source: The source of the invalid configuration
        """
        full_message = message
        if config_source:
            full_message = f"Configuration error in '{config_source}': {message}"
        
        super().__init__(full_message)
        self.config_source = config_source


class TransactionError(SummerFrameworkError):
    """Raised when transaction-related errors occur."""
    
    def __init__(self, message: str, cause: Exception = None):
        """
        Initialize the transaction error.
        
        Args:
            message: The error message
            cause: The underlying cause of the error
        """
        super().__init__(message, cause)


class AspectError(SummerFrameworkError):
    """Raised when AOP-related errors occur."""
    
    def __init__(self, message: str, aspect_name: str = None, cause: Exception = None):
        """
        Initialize the aspect error.
        
        Args:
            message: The error message
            aspect_name: The name of the aspect that caused the error
            cause: The underlying cause of the error
        """
        full_message = message
        if aspect_name:
            full_message = f"Aspect error in '{aspect_name}': {message}"
        
        super().__init__(full_message, cause)
        self.aspect_name = aspect_name