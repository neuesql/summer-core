from abc import ABC, abstractmethod
from typing import Any, Optional, TypeVar

T = TypeVar("T")


class BeanFactory(ABC):
    """Abstract base class for bean factories.

    This class defines the core interface for managing beans and their dependencies.
    Concrete implementations should handle bean registration, creation, and dependency resolution.
    """

    @abstractmethod
    def contains_bean(self, name: str) -> bool:
        """
        Check if this bean factory contains a bean definition with the given name.

        Args:
            name: The name of the bean to query

        Returns:
            True if a bean with the given name is present
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

    @abstractmethod
    def get_bean_of_type(self, required_type: type[T]) -> T:
        """
        Return the bean instance that uniquely matches the given object type.

        Args:
            required_type: Type the bean must match

        Returns:
            An instance of the single bean matching the required type

        Raises:
            NoSuchBeanDefinitionException: If no bean of the given type was found
            BeansException: If the bean could not be created
        """
        pass

    @abstractmethod
    def get_type(self, name: str) -> Optional[type]:
        """
        Determine the type of the bean with the given name.

        Args:
            name: The name of the bean to query

        Returns:
            The type of the bean, or None if not determinable

        Raises:
            NoSuchBeanDefinitionException: If there is no bean with the given name
        """
        pass

    @abstractmethod
    def is_prototype(self, name: str) -> bool:
        """
        Is this bean a prototype?

        Args:
            name: The name of the bean to query

        Returns:
            True if this bean will always deliver independent instances

        Raises:
            NoSuchBeanDefinitionException: If there is no bean with the given name
        """
        pass

    @abstractmethod
    def is_singleton(self, name: str) -> bool:
        """
        Is this bean a shared singleton?

        Args:
            name: The name of the bean to query

        Returns:
            True if this bean corresponds to a singleton instance

        Raises:
            NoSuchBeanDefinitionException: If there is no bean with the given name
        """
        pass

    @abstractmethod
    def is_type_match(self, name: str, type_to_match: type[Any]) -> bool:
        """
        Check whether the bean with the given name matches the specified type.

        Args:
            name: The name of the bean to query
            type_to_match: The type to match against

        Returns:
            True if the bean type matches

        Raises:
            NoSuchBeanDefinitionException: If there is no bean with the given name
        """
        pass
