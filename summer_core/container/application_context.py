"""
Application Context - Central interface for accessing the Summer IoC container.

Provides methods for retrieving beans by name and type, manages bean scopes,
handles bean lifecycle callbacks, and publishes application events.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar

T = TypeVar('T')


class ApplicationContext(ABC):
    """
    Central interface for providing configuration information to an application.
    
    This interface extends BeanFactory and provides additional functionality
    for enterprise applications including event publishing, resource loading,
    and environment management.
    """

    @abstractmethod
    def get_bean(self, name: str) -> Any:
        """
        Return an instance of the bean registered under the given name.
        
        Args:
            name: The name of the bean to retrieve
            
        Returns:
            The bean instance
            
        Raises:
            NoSuchBeanDefinitionError: If no bean with the given name exists
        """
        pass

    @abstractmethod
    def get_bean_by_type(self, bean_type: Type[T]) -> T:
        """
        Return the bean instance that uniquely matches the given type.
        
        Args:
            bean_type: The type of the bean to retrieve
            
        Returns:
            The bean instance of the specified type
            
        Raises:
            NoSuchBeanDefinitionError: If no bean of the given type exists
            NoUniqueBeanDefinitionError: If more than one bean of the given type exists
        """
        pass

    @abstractmethod
    def get_beans_by_type(self, bean_type: Type[T]) -> Dict[str, T]:
        """
        Return all beans of the given type.
        
        Args:
            bean_type: The type of beans to retrieve
            
        Returns:
            A dictionary mapping bean names to bean instances
        """
        pass

    @abstractmethod
    def contains_bean(self, name: str) -> bool:
        """
        Check if this bean factory contains a bean definition with the given name.
        
        Args:
            name: The name of the bean to look for
            
        Returns:
            True if a bean with the given name is defined
        """
        pass

    @abstractmethod
    def is_singleton(self, name: str) -> bool:
        """
        Check whether the bean with the given name is a singleton.
        
        Args:
            name: The name of the bean to query
            
        Returns:
            True if the bean is a singleton
        """
        pass

    @abstractmethod
    def get_type(self, name: str) -> Optional[Type]:
        """
        Determine the type of the bean with the given name.
        
        Args:
            name: The name of the bean to query
            
        Returns:
            The type of the bean, or None if not determinable
        """
        pass

    @abstractmethod
    def get_bean_definition_names(self) -> List[str]:
        """
        Return the names of all beans defined in this factory.
        
        Returns:
            A list of all bean names
        """
        pass

    @abstractmethod
    def refresh(self) -> None:
        """
        Load or refresh the persistent representation of the configuration.
        
        This method will destroy already created singletons if it fails,
        to avoid dangling resources.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Close this application context, destroying all beans in its bean factory.
        """
        pass

    @abstractmethod
    def is_active(self) -> bool:
        """
        Determine whether this application context is active.
        
        Returns:
            True if the context is active and has not been closed
        """
        pass

class DefaultApplicationContext(ApplicationContext):
    """
    Default implementation of the ApplicationContext interface.
    
    Provides a complete IoC container with bean lifecycle management,
    event publishing, and resource loading capabilities.
    """

    def __init__(self, base_packages: Optional[List[str]] = None) -> None:
        """
        Initialize the application context.
        
        Args:
            base_packages: List of packages to scan for components
        """
        from summer_core.container.bean_factory import DefaultBeanFactory
        
        self._bean_factory = DefaultBeanFactory()
        self._active = False
        self._closed = False
        self._base_packages = base_packages or []

    def get_bean(self, name: str) -> Any:
        """Return an instance of the bean registered under the given name."""
        self._check_active()
        return self._bean_factory.get_bean(name)

    def get_bean_by_type(self, bean_type: Type[T]) -> T:
        """Return the bean instance that uniquely matches the given type."""
        self._check_active()
        return self._bean_factory.get_bean_by_type(bean_type)

    def get_beans_by_type(self, bean_type: Type[T]) -> Dict[str, T]:
        """Return all beans of the given type."""
        self._check_active()
        result = {}
        for name in self._bean_factory.get_bean_definition_names():
            bean_def = self._bean_factory.get_bean_definition(name)
            if bean_def.bean_type == bean_type or issubclass(bean_def.bean_type, bean_type):
                result[name] = self._bean_factory.get_bean(name)
        return result

    def contains_bean(self, name: str) -> bool:
        """Check if this bean factory contains a bean definition with the given name."""
        return self._bean_factory.contains_bean(name)

    def is_singleton(self, name: str) -> bool:
        """Check whether the bean with the given name is a singleton."""
        return self._bean_factory.is_singleton(name)

    def get_type(self, name: str) -> Optional[Type]:
        """Determine the type of the bean with the given name."""
        return self._bean_factory.get_type(name)

    def get_bean_definition_names(self) -> List[str]:
        """Return the names of all beans defined in this factory."""
        return self._bean_factory.get_bean_definition_names()

    def refresh(self) -> None:
        """Load or refresh the persistent representation of the configuration."""
        if self._closed:
            raise RuntimeError("ApplicationContext has been closed")
        
        try:
            # Perform component scanning if base packages are configured
            if hasattr(self, '_base_packages') and self._base_packages:
                self._perform_component_scanning()
            
            self._active = True
        except Exception as e:
            self._active = False
            raise RuntimeError(f"Failed to refresh ApplicationContext: {str(e)}") from e

    def close(self) -> None:
        """Close this application context, destroying all beans in its bean factory."""
        if not self._closed:
            self._active = False
            self._closed = True
            # Execute pre-destroy methods on all singleton beans
            self._destroy_beans()

    def is_active(self) -> bool:
        """Determine whether this application context is active."""
        return self._active and not self._closed

    def register_bean_definition(self, name: str, bean_definition: 'BeanDefinition') -> None:
        """
        Register a bean definition with this context.
        
        Args:
            name: The name of the bean
            bean_definition: The bean definition to register
        """
        self._bean_factory.register_bean_definition(name, bean_definition)

    def _perform_component_scanning(self) -> None:
        """Perform component scanning and register discovered beans."""
        from summer_core.container.component_scanner import ComponentScanner
        from summer_core.container.configuration_processor import ConfigurationClassProcessor
        
        # Scan for components
        scanner = ComponentScanner()
        component_bean_definitions = scanner.scan_packages(self._base_packages)
        
        for bean_def in component_bean_definitions:
            self.register_bean_definition(bean_def.bean_name, bean_def)
        
        # Process configuration classes
        config_processor = ConfigurationClassProcessor()
        config_bean_definitions = config_processor.process_configuration_classes(self._base_packages)
        
        for bean_def in config_bean_definitions:
            self.register_bean_definition(bean_def.bean_name, bean_def)

    def _destroy_beans(self) -> None:
        """Execute pre-destroy methods on all singleton beans."""
        self._bean_factory.destroy_singletons()

    def _check_active(self) -> None:
        """Check if the context is active and raise an error if not."""
        if self._closed:
            raise RuntimeError("ApplicationContext has been closed")
        if not self._active:
            raise RuntimeError("ApplicationContext is not active - call refresh() first")