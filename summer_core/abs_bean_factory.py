from typing import Any

from summer_core.bean_definition import BeanDefinition, BeanScope
from summer_core.bean_exceptions import (
    BeanCreationError,
    BeanNotFoundError,
    DuplicateBeanError,
)
from summer_core.interface_bean_def_register import BeanDefRegisterMixin
from summer_core.interface_bean_factory import BeanFactory


class AbstractBeanFactory(BeanFactory, BeanDefRegisterMixin):
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
