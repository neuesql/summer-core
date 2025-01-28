from abc import ABC, abstractmethod

from summer_core.bean_definition import BeanDefinition


class BeanDefRegisterMixin(ABC):
    """Abstract base class for bean definition registration.

    This mixin class defines the interface for registering bean definitions in a container.
    It provides a standardized way to register beans with their metadata, ensuring consistent
    bean registration across different implementations.

    The mixin pattern allows this functionality to be combined with other interfaces
    while maintaining separation of concerns.

    Example:
        class MyBeanContainer(BeanDefRegisterMixin):
            def register_bean_definition(self, bean_definition: BeanDefinition) -> None:
                # Implementation of bean registration
                pass
    """

    @abstractmethod
    def register_bean_definition(self, bean_definition: BeanDefinition) -> None:
        """Register a new bean definition.

        Args:
            bean_definition: The bean definition to register, containing the bean's
                           metadata such as name, class type, scope, and dependencies.

        Raises:
            DuplicateBeanError: If a bean with the same name is already registered.
        """
        pass
