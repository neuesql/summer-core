"""
Bean Factory - Core container that instantiates and manages beans.

Provides the fundamental functionality for bean creation, dependency resolution,
and lifecycle management within the IoC container.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar

from summer_core.container.bean_definition import BeanDefinition, BeanScope
from summer_core.container.scope import get_scope_registry

T = TypeVar('T')


class BeanPostProcessor(ABC):
    """
    Factory hook that allows for custom modification of new bean instances.
    
    Bean post processors operate on bean instances after they have been created
    and configured, allowing for custom initialization logic and proxy creation.
    """
    
    @abstractmethod
    def post_process_before_initialization(self, bean: Any, bean_name: str) -> Any:
        """
        Apply this processor to the given new bean instance before any bean
        initialization callbacks.
        
        Args:
            bean: The new bean instance
            bean_name: The name of the bean
            
        Returns:
            The bean instance to use (either the original or a wrapped one)
        """
        pass
    
    @abstractmethod
    def post_process_after_initialization(self, bean: Any, bean_name: str) -> Any:
        """
        Apply this processor to the given new bean instance after any bean
        initialization callbacks.
        
        Args:
            bean: The new bean instance
            bean_name: The name of the bean
            
        Returns:
            The bean instance to use (either the original or a wrapped one)
        """
        pass


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
        self._dependency_resolver = None
        self._scope_registry = get_scope_registry()
        self._bean_post_processors: List[BeanPostProcessor] = []

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
            raise NoSuchBeanDefinitionError(name)
        return self._bean_definitions[name]

    def get_bean(self, name: str) -> Any:
        """Return an instance of the bean registered under the given name."""
        bean_definition = self.get_bean_definition(name)
        
        # Get the appropriate scope
        scope_name = bean_definition.scope.value
        scope = self._scope_registry.get_scope(scope_name)
        
        if not scope:
            from summer_core.exceptions import BeanCreationError
            raise BeanCreationError(name, f"Unknown scope: {scope_name}")
        
        # Use scope to get/create bean instance
        def object_factory():
            # Check for circular dependency
            if name in self._currently_creating:
                from summer_core.exceptions import CircularDependencyError
                # Build dependency chain for better error reporting
                creating_list = list(self._currently_creating) + [name]
                dependency_path = " -> ".join(creating_list)
                raise CircularDependencyError(dependency_path, creating_list)
            
            try:
                self._currently_creating.add(name)
                bean_instance = self._create_bean(name, bean_definition)
                
                # Register destruction callback if bean has pre-destroy methods
                if bean_definition.pre_destroy_methods:
                    def destruction_callback():
                        self._execute_pre_destroy_methods(bean_instance, bean_definition)
                    scope.register_destruction_callback(name, destruction_callback)
                
                return bean_instance
            finally:
                self._currently_creating.discard(name)
        
        return scope.get(name, object_factory)

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
    
    def add_bean_post_processor(self, processor: BeanPostProcessor) -> None:
        """
        Add a BeanPostProcessor that will get applied to beans created by this factory.
        
        Args:
            processor: The bean post processor to add
        """
        self._bean_post_processors.append(processor)
    
    def get_bean_post_processors(self) -> List[BeanPostProcessor]:
        """
        Return the list of BeanPostProcessors that will get applied to beans
        created with this factory.
        
        Returns:
            List of bean post processors
        """
        return self._bean_post_processors.copy()

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
                # Resolve dependencies for factory method
                factory_args = self._resolve_constructor_dependencies(bean_definition)
                bean_instance = bean_definition.factory_method(*factory_args)
            else:
                # Use constructor with dependency injection
                constructor_args = self._resolve_constructor_dependencies(bean_definition)
                bean_instance = bean_definition.bean_type(*constructor_args)
            
            # Perform dependency injection
            self._inject_dependencies(bean_instance, bean_definition)
            
            # Apply bean post processors before initialization
            bean_instance = self._apply_bean_post_processors_before_initialization(bean_instance, name)
            
            # Execute post-construct methods
            self._execute_post_construct_methods(bean_instance, bean_definition)
            
            # Apply bean post processors after initialization
            bean_instance = self._apply_bean_post_processors_after_initialization(bean_instance, name)
            
            return bean_instance
            
        except Exception as e:
            from summer_core.exceptions import BeanCreationError
            raise BeanCreationError(name, str(e), e) from e

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

    def _execute_pre_destroy_methods(self, bean_instance: Any, bean_definition: BeanDefinition) -> None:
        """Execute pre-destroy lifecycle methods."""
        for method_name in bean_definition.pre_destroy_methods:
            if hasattr(bean_instance, method_name):
                method = getattr(bean_instance, method_name)
                try:
                    method()
                except Exception as e:
                    # Log the error but don't fail the destruction process
                    print(f"Warning: Error executing pre-destroy method {method_name}: {e}")

    def destroy_singletons(self) -> None:
        """Destroy all singleton beans and execute their pre-destroy methods."""
        # Use scope registry to destroy all scoped beans
        self._scope_registry.destroy_all_scopes()
        
        # Clear the singleton cache (for backward compatibility)
        self._singleton_objects.clear()

    def set_dependency_resolver(self, dependency_resolver) -> None:
        """
        Set the dependency resolver for this bean factory.
        
        Args:
            dependency_resolver: The dependency resolver to use
        """
        self._dependency_resolver = dependency_resolver
    
    def register_scope(self, scope_name: str, scope) -> None:
        """
        Register a custom scope implementation.
        
        Args:
            scope_name: The name of the scope
            scope: The scope implementation
        """
        self._scope_registry.register_scope(scope_name, scope)
    
    def get_registered_scope_names(self) -> list:
        """
        Get the names of all registered scopes.
        
        Returns:
            A list of scope names
        """
        return self._scope_registry.get_registered_scope_names()

    def validate_dependencies(self) -> None:
        """
        Validate all bean dependencies for circular dependencies.
        
        Raises:
            CircularDependencyError: If circular dependencies are detected
        """
        if self._dependency_resolver:
            self._dependency_resolver.validate_all_dependencies()
        else:
            # Fallback validation without dependency resolver
            self._validate_dependencies_fallback()

    def _validate_dependencies_fallback(self) -> None:
        """
        Fallback dependency validation without dependency resolver.
        
        Raises:
            CircularDependencyError: If circular dependencies are detected
        """
        # Simple circular dependency detection using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(bean_name: str) -> Optional[List[str]]:
            if bean_name in rec_stack:
                return [bean_name]
            if bean_name in visited:
                return None
            
            visited.add(bean_name)
            rec_stack.add(bean_name)
            
            if bean_name in self._bean_definitions:
                bean_def = self._bean_definitions[bean_name]
                for dep in bean_def.dependencies:
                    dep_name = dep.qualifier
                    if not dep_name:
                        # Find bean name by type
                        for name, definition in self._bean_definitions.items():
                            if definition.bean_type == dep.dependency_type:
                                dep_name = name
                                break
                    
                    if dep_name:
                        cycle = has_cycle(dep_name)
                        if cycle:
                            if bean_name in cycle:
                                # Complete the cycle
                                cycle_start = cycle.index(bean_name)
                                return cycle[cycle_start:] + [bean_name]
                            else:
                                cycle.append(bean_name)
                                return cycle
            
            rec_stack.remove(bean_name)
            return None
        
        for bean_name in self._bean_definitions.keys():
            if bean_name not in visited:
                cycle = has_cycle(bean_name)
                if cycle:
                    cycle_path = " -> ".join(cycle)
                    from summer_core.exceptions import CircularDependencyError
                    raise CircularDependencyError(cycle_path, cycle)
    
    def _apply_bean_post_processors_before_initialization(self, bean: Any, bean_name: str) -> Any:
        """
        Apply all registered BeanPostProcessors before initialization.
        
        Args:
            bean: The bean instance
            bean_name: The name of the bean
            
        Returns:
            The processed bean instance
        """
        result = bean
        for processor in self._bean_post_processors:
            result = processor.post_process_before_initialization(result, bean_name)
        return result
    
    def _apply_bean_post_processors_after_initialization(self, bean: Any, bean_name: str) -> Any:
        """
        Apply all registered BeanPostProcessors after initialization.
        
        Args:
            bean: The bean instance
            bean_name: The name of the bean
            
        Returns:
            The processed bean instance
        """
        result = bean
        for processor in self._bean_post_processors:
            result = processor.post_process_after_initialization(result, bean_name)
        return result