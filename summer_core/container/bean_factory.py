"""
Bean Factory - Core container that instantiates and manages beans.

Provides the fundamental functionality for bean creation, dependency resolution,
and lifecycle management within the IoC container.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar

from summer_core.container.bean_definition import BeanDefinition

T = TypeVar('T')


class BeanFactory(ABC):
    """
    The root interface for accessing a Summer IoC container.
    
    This is the central interface for a Spring IoC container and provides
    basic functionality for retrieving beans and checking bean definitions.
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
            BeanCreationError: If the bean could not be created
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
            
        Raises:
            NoSuchBeanDefinitionError: If no bean with the given name exists
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
            
        Raises:
            NoSuchBeanDefinitionError: If no bean with the given name exists
        """
        pass


class DefaultBeanFactory(BeanFactory):
    """
    Default implementation of the BeanFactory interface.
    
    Provides basic bean creation, caching, and dependency resolution
    functionality for the Summer IoC container.
    """

    def __init__(self) -> None:
        """Initialize the bean factory."""
        self._bean_definitions: Dict[str, BeanDefinition] = {}
        self._singleton_objects: Dict[str, Any] = {}
        self._type_to_names: Dict[Type, List[str]] = {}
        self._currently_creating: set = set()

    def register_bean_definition(self, name: str, bean_definition: BeanDefinition) -> None:
        """
        Register a new bean definition with this factory.
        
        Args:
            name: The name of the bean
            bean_definition: The bean definition to register
        """
        self._bean_definitions[name] = bean_definition
        
        # Update type-to-names mapping
        bean_type = bean_definition.bean_type
        if bean_type not in self._type_to_names:
            self._type_to_names[bean_type] = []
        self._type_to_names[bean_type].append(name)

    def get_bean_definition(self, name: str) -> BeanDefinition:
        """
        Get the bean definition for the given bean name.
        
        Args:
            name: The name of the bean
            
        Returns:
            The bean definition
            
        Raises:
            NoSuchBeanDefinitionError: If no bean with the given name exists
        """
        if name not in self._bean_definitions:
            from summer_core.exceptions import NoSuchBeanDefinitionError
            raise NoSuchBeanDefinitionError(f"No bean named '{name}' available")
        return self._bean_definitions[name]

    def get_bean(self, name: str) -> Any:
        """Return an instance of the bean registered under the given name."""
        bean_definition = self.get_bean_definition(name)
        
        if bean_definition.is_singleton():
            # Return cached singleton or create new one
            if name in self._singleton_objects:
                return self._singleton_objects[name]
            
            # Check for circular dependency
            if name in self._currently_creating:
                from summer_core.exceptions import CircularDependencyError
                raise CircularDependencyError(
                    f"Circular dependency detected for bean '{name}'"
                )
            
            try:
                self._currently_creating.add(name)
                bean_instance = self._create_bean(name, bean_definition)
                self._singleton_objects[name] = bean_instance
                return bean_instance
            finally:
                self._currently_creating.discard(name)
        else:
            # Create new prototype instance
            return self._create_bean(name, bean_definition)

    def get_bean_by_type(self, bean_type: Type[T]) -> T:
        """Return the bean instance that uniquely matches the given type."""
        matching_names = self._type_to_names.get(bean_type, [])
        
        if not matching_names:
            from summer_core.exceptions import NoSuchBeanDefinitionError
            raise NoSuchBeanDefinitionError(
                f"No bean of type '{bean_type.__name__}' available"
            )
        
        if len(matching_names) > 1:
            # Check for primary bean
            primary_names = [
                name for name in matching_names 
                if self._bean_definitions[name].primary
            ]
            if len(primary_names) == 1:
                return self.get_bean(primary_names[0])
            
            from summer_core.exceptions import NoUniqueBeanDefinitionError
            raise NoUniqueBeanDefinitionError(
                f"Multiple beans of type '{bean_type.__name__}' available: {matching_names}"
            )
        
        return self.get_bean(matching_names[0])

    def contains_bean(self, name: str) -> bool:
        """Check if this bean factory contains a bean definition with the given name."""
        return name in self._bean_definitions

    def is_singleton(self, name: str) -> bool:
        """Check whether the bean with the given name is a singleton."""
        bean_definition = self.get_bean_definition(name)
        return bean_definition.is_singleton()

    def get_type(self, name: str) -> Optional[Type]:
        """Determine the type of the bean with the given name."""
        if name not in self._bean_definitions:
            return None
        return self._bean_definitions[name].bean_type

    def get_bean_definition_names(self) -> List[str]:
        """Return the names of all beans defined in this factory."""
        return list(self._bean_definitions.keys())

    def _create_bean(self, name: str, bean_definition: BeanDefinition) -> Any:
        """
        Create a bean instance from the given bean definition.
        
        Args:
            name: The name of the bean
            bean_definition: The bean definition
            
        Returns:
            The created bean instance
        """
        try:
            # Create the bean instance
            if bean_definition.factory_method:
                bean_instance = bean_definition.factory_method()
            else:
                # Use constructor with dependency injection
                constructor_args = self._resolve_constructor_dependencies(bean_definition)
                bean_instance = bean_definition.bean_type(*constructor_args)
            
            # Perform dependency injection
            self._inject_dependencies(bean_instance, bean_definition)
            
            # Execute post-construct methods
            self._execute_post_construct_methods(bean_instance, bean_definition)
            
            return bean_instance
            
        except Exception as e:
            from summer_core.exceptions import BeanCreationError
            raise BeanCreationError(f"Error creating bean '{name}': {str(e)}") from e

    def _resolve_constructor_dependencies(self, bean_definition: BeanDefinition) -> List[Any]:
        """Resolve constructor dependencies for a bean."""
        constructor_deps = bean_definition.get_constructor_dependencies()
        resolved_args = []
        
        for dep in constructor_deps:
            if dep.qualifier:
                dependency = self.get_bean(dep.qualifier)
            else:
                dependency = self.get_bean_by_type(dep.dependency_type)
            resolved_args.append(dependency)
        
        return resolved_args

    def _inject_dependencies(self, bean_instance: Any, bean_definition: BeanDefinition) -> None:
        """Inject dependencies into a bean instance."""
        # Setter injection
        for dep in bean_definition.get_setter_dependencies():
            if dep.qualifier:
                dependency = self.get_bean(dep.qualifier)
            else:
                dependency = self.get_bean_by_type(dep.dependency_type)
            
            setter_name = f"set_{dep.name}"
            if hasattr(bean_instance, setter_name):
                getattr(bean_instance, setter_name)(dependency)

        # Field injection
        for dep in bean_definition.get_field_dependencies():
            if dep.qualifier:
                dependency = self.get_bean(dep.qualifier)
            else:
                dependency = self.get_bean_by_type(dep.dependency_type)
            
            setattr(bean_instance, dep.name, dependency)

    def _execute_post_construct_methods(self, bean_instance: Any, bean_definition: BeanDefinition) -> None:
        """Execute post-construct lifecycle methods."""
        for method_name in bean_definition.post_construct_methods:
            if hasattr(bean_instance, method_name):
                method = getattr(bean_instance, method_name)
                method()