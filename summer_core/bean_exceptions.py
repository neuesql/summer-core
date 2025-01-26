class BeanFactoryError(Exception):
    """Base exception for all bean factory related errors."""


class BeanDefinitionError(BeanFactoryError):
    """Base exception for bean definition related errors."""


class BeanCreationError(BeanFactoryError):
    """Exception raised when there is an error creating a bean."""


class BeanNotFoundError(BeanFactoryError):
    """Exception raised when a requested bean is not found."""


class CircularDependencyError(BeanCreationError):
    """Exception raised when a circular dependency is detected."""


class DuplicateBeanError(BeanDefinitionError):
    """Exception raised when attempting to register a bean with a duplicate name."""


class DependencyNotFoundError(BeanCreationError):
    """Exception raised when a required dependency cannot be found."""
