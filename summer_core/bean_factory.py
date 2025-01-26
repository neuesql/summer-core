from abc import ABC, abstractmethod
from typing import Any, Optional

from summer_core.bean_definition import BeanDefinition, BeanScope


class BeanCreationError(Exception):
    """Exception raised when there is an error creating a bean."""

    pass


class BeanNotFoundError(Exception):
    """Exception raised when a requested bean is not found."""

    pass


class CircularDependencyError(Exception):
    """Exception raised when a circular dependency is detected."""

    pass


class BeanFactory(ABC):
    """Abstract base class for bean factories.

    This class defines the core interface for managing beans and their dependencies.
    Concrete implementations should handle bean registration, creation, and dependency resolution.
    """

    @abstractmethod
    def register_bean(self, bean_definition: BeanDefinition) -> None:
        """Register a new bean definition.

        Args:
            bean_definition: The bean definition to register.

        Raises:
            ValueError: If a bean with the same name is already registered.
        """
        pass

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


class DefaultBeanFactory(BeanFactory):
    """Default implementation of BeanFactory.

    This class is responsible for registering bean definitions, creating bean instances,
    and resolving dependencies between beans. It supports both singleton and prototype
    scoped beans.

    Attributes:
        _bean_definitions: Dictionary mapping bean names to their definitions.
        _singleton_instances: Cache of singleton bean instances.
    """

    def __init__(self):
        """Initialize an empty bean factory."""
        self._bean_definitions: dict[str, BeanDefinition] = {}
        self._singleton_instances: dict[str, Any] = {}

    def register_bean(self, bean_definition: BeanDefinition) -> None:
        """Register a new bean definition.

        Args:
            bean_definition: The bean definition to register.

        Raises:
            ValueError: If a bean with the same name is already registered.
        """
        if bean_definition.name in self._bean_definitions:
            raise ValueError(f"Bean with name '{bean_definition.name}' is already registered")
        self._bean_definitions[bean_definition.name] = bean_definition

    def get_bean(self, name: str, creating_stack: Optional[set[str]] = None) -> Any:
        """Get a bean instance by name.

        Args:
            name: The name of the bean to retrieve.
            creating_stack: Set of beans currently being created (for circular dependency detection).

        Returns:
            An instance of the requested bean.

        Raises:
            BeanNotFoundError: If the requested bean is not registered.
            CircularDependencyError: If a circular dependency is detected.
            BeanCreationError: If there is an error creating the bean.
        """
        if name not in self._bean_definitions:
            raise BeanNotFoundError(f"No bean found with name '{name}'")

        bean_def = self._bean_definitions[name]

        # Check for singleton instance
        if bean_def.scope == BeanScope.SINGLETON and name in self._singleton_instances:
            return self._singleton_instances[name]

        # Initialize creating_stack for circular dependency detection
        if creating_stack is None:
            creating_stack = set()

        # Check for circular dependencies
        if name in creating_stack:
            raise CircularDependencyError(f"Circular dependency detected while creating bean '{name}'")

        creating_stack.add(name)

        try:
            # Resolve dependencies
            dependencies = {}
            for dep_name, _ in bean_def.dependencies.items():
                dependencies[dep_name] = self.get_bean(dep_name, creating_stack)

            # Create instance
            instance = bean_def.bean_class(**dependencies)

            # Cache singleton instance
            if bean_def.scope == BeanScope.SINGLETON:
                self._singleton_instances[name] = instance
            else:
                return instance

        except Exception as e:
            raise BeanCreationError(f"Error creating bean '{name}': {e!s}") from e
        finally:
            creating_stack.remove(name)
