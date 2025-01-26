from abc import ABC, abstractmethod
from typing import Any


class BeanFactory(ABC):
    """Abstract base class for bean factories.

    This class defines the core interface for managing beans and their dependencies.
    Concrete implementations should handle bean registration, creation, and dependency resolution.
    """

    @abstractmethod
    def get_bean(self, name: str) -> Any:
        """Get a bean instance by name.

        Args:
            name: The name of the bean to retrieve.

        Returns:
            An instance of the requested bean.

        Raises:
            BeanNotFoundError: If the requested bean is not registered.
            CircularDependencyError: If a circular dependency is detected.
            BeanCreationError: If there is an error creating the bean.
        """
        pass
