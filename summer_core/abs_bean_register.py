from abc import ABC, abstractmethod

from summer_core.bean_definition import BeanDefinition


class BeanRegisterMixin(ABC):
    """Abstract base class for bean registration."""

    @abstractmethod
    def register_bean_definition(self, bean_definition: BeanDefinition) -> None:
        """Register a new bean definition.

        Args:
            bean_definition: The bean definition to register.

        Raises:
            DuplicateBeanError: If a bean with the same name is already registered.
        """
        pass
