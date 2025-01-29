from typing import Any, Optional

from summer_core.bean_definition import BeanDefinition, BeanScope
from summer_core.bean_exceptions import (
    BeanCreationError,
    BeanNotFoundError,
    DuplicateBeanError,
)
from summer_core.interface_bean_def_register import BeanDefRegisterMixin
from summer_core.interface_bean_factory import BeanFactory, T


class AbstractBeanFactory(BeanFactory, BeanDefRegisterMixin):
    """Default implementation of BeanFactory.

    This class is responsible for registering bean definitions, creating bean instances,
    and resolving dependencies between beans. It supports both singleton and prototype
    scoped beans.

    Attributes:
        _bean_definitions: Dictionary mapping bean names to their definitions.
        _singleton_instances: Cache of singleton bean instances.
    """

    def get_bean_of_type(self, required_type: type[T]) -> T:
        """Return the bean instance that uniquely matches the given object type.

        Args:
            required_type: Type the bean must match.

        Returns:
            An instance of the single bean matching the required type.

        Raises:
            BeanNotFoundError: If no bean of the given type was found.
            BeanCreationError: If the bean could not be created.
        """
        matching_beans = []
        for name in self._bean_definitions:
            if self.is_type_match(name, required_type):
                matching_beans.append(name)

        if not matching_beans:
            raise BeanNotFoundError(f"No bean found of type {required_type.__name__}")
        if len(matching_beans) > 1:
            raise BeanCreationError(f"Found {len(matching_beans)} beans of type {required_type.__name__}, expected one")

        return self.get_bean(matching_beans[0])

    def is_type_match(self, name: str, type_to_match: type[Any]) -> bool:
        """Check whether the bean with the given name matches the specified type.

        Args:
            name: The name of the bean to query.
            type_to_match: The type to match against.

        Returns:
            True if the bean type matches.

        Raises:
            BeanNotFoundError: If there is no bean with the given name.
        """
        bean_type = self.get_type(name)
        if bean_type is None:
            return False
        return issubclass(bean_type, type_to_match)

    def get_type(self, name: str) -> Optional[type]:
        """Determine the type of the bean with the given name.

        Args:
            name: The name of the bean to query.

        Returns:
            The type of the bean, or None if not determinable.

        Raises:
            BeanNotFoundError: If there is no bean with the given name.
        """
        if not self.contains_bean(name):
            raise BeanNotFoundError(f"No bean found with name '{name}'")
        return self._bean_definitions[name].bean_class

    def __init__(self):
        """Initialize an empty bean factory."""
        self._bean_definitions: dict[str, BeanDefinition] = {}
        self._singleton_instances: dict[str, Any] = {}

    def register_bean_definition(self, bean_definition: BeanDefinition) -> None:
        """Register a new bean definition.

        Args:
            bean_definition: The bean definition to register.

        Raises:
            DuplicateBeanError: If a bean with the same name is already registered.
        """
        if bean_definition.name in self._bean_definitions:
            raise DuplicateBeanError(f"Bean with name '{bean_definition.name}' is already registered")
        self._bean_definitions[bean_definition.name] = bean_definition

    def get_bean(self, name: str) -> Any:
        """Get a bean instance by name.

        Args:
            name: The name of the bean to retrieve.

        Returns:
            An instance of the requested bean.

        Raises:
            BeanNotFoundError: If the requested bean is not registered.
            BeanCreationError: If there is an error creating the bean.
        """
        if name not in self._bean_definitions:
            raise BeanNotFoundError(f"No bean found with name '{name}'")

        bean_def = self._bean_definitions[name]

        # Check for singleton instance
        if bean_def.scope == BeanScope.SINGLETON and name in self._singleton_instances:
            return self._singleton_instances[name]

        instance = self.create_bean(name, bean_def)
        return instance

    def create_bean(self, name: str, bean_def: BeanDefinition) -> Any:
        """Create a new bean instance.

        Args:
            name: The name of the bean to create.
            bean_def: The bean definition.

        Returns:
            A new instance of the bean.

        Raises:
            BeanCreationError: If there is an error creating the bean or resolving its dependencies.
        """
        instance: Any = None
        try:
            # Resolve dependencies
            dependencies = {}
            for dep_name, _ in bean_def.dependencies.items():
                try:
                    dependencies[dep_name] = self.get_bean(dep_name)
                except BeanNotFoundError as e:
                    raise BeanCreationError(f"Required dependency '{dep_name}' for bean '{name}' not found") from e

            # Create instance
            instance = bean_def.bean_class(**dependencies)

            # Cache singleton instance
            if bean_def.scope == BeanScope.SINGLETON:
                self._singleton_instances[name] = instance

        except Exception as e:
            raise BeanCreationError(f"Error creating bean '{name}': {e!s}") from e

        return instance

    def contains_bean(self, name: str) -> bool:
        """Check if a bean with the given name exists.

        Args:
            name: The name of the bean to check.

        Returns:
            True if the bean exists, False otherwise.
        """
        return name in self._bean_definitions

    def get_bean_definition(self, name: str) -> BeanDefinition:
        """Get the bean definition for the given name.

        Args:
            name: The name of the bean definition to retrieve.

        Returns:
            The bean definition.

        Raises:
            BeanNotFoundError: If no bean definition is found with the given name.
        """
        if not self.contains_bean(name):
            raise BeanNotFoundError(f"No bean definition found with name '{name}'")
        return self._bean_definitions[name]

    def is_singleton(self, name: str) -> bool:
        """Check if the bean with the given name is a singleton.

        Args:
            name: The name of the bean to check.

        Returns:
            True if the bean is a singleton, False otherwise.

        Raises:
            BeanNotFoundError: If no bean is found with the given name.
        """
        bean_def = self.get_bean_definition(name)
        return bean_def.scope == BeanScope.SINGLETON

    def is_prototype(self, name: str) -> bool:
        """Check if the bean with the given name is a prototype.

        Args:
            name: The name of the bean to check.

        Returns:
            True if the bean is a prototype, False otherwise.

        Raises:
            BeanNotFoundError: If no bean is found with the given name.
        """
        bean_def = self.get_bean_definition(name)
        return bean_def.scope == BeanScope.PROTOTYPE

    def get_bean_names(self) -> list[str]:
        """Get all registered bean names.

        Returns:
            A list of registered bean names.
        """
        return list(self._bean_definitions.keys())
