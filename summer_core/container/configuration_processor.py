"""
Configuration Class Processor - Processes @Configuration classes and @Bean methods.

Handles the processing of configuration classes decorated with @Configuration
and their @Bean factory methods to register beans in the application context.
"""

import inspect
import importlib
import pkgutil
from typing import List, Dict, Any, Type, Optional, Set

from summer_core.container.bean_definition import BeanDefinition, BeanScope, DependencyDescriptor, InjectionType
from summer_core.decorators.autowired import is_bean_method, get_bean_name
from summer_core.decorators.component import is_component


class ConfigurationClassProcessor:
    """
    Processes @Configuration classes and their @Bean methods.
    
    Discovers configuration classes and processes their @Bean methods to
    create bean definitions that can be registered with the container.
    """

    def __init__(self) -> None:
        """Initialize the configuration processor."""
        self._processed_configurations: Set[Type] = set()
        self._configuration_instances: Dict[Type, Any] = {}

    def process_configuration_classes(self, base_packages: List[str]) -> List[BeanDefinition]:
        """
        Process all configuration classes in the specified packages.
        
        Args:
            base_packages: List of package names to scan for configuration classes
            
        Returns:
            List of bean definitions from @Bean methods
        """
        bean_definitions = []
        
        for package_name in base_packages:
            config_classes = self._discover_configuration_classes(package_name)
            for config_class in config_classes:
                if config_class not in self._processed_configurations:
                    bean_defs = self._process_configuration_class(config_class)
                    bean_definitions.extend(bean_defs)
                    self._processed_configurations.add(config_class)
        
        return bean_definitions

    def process_configuration_class(self, config_class: Type) -> List[BeanDefinition]:
        """
        Process a single configuration class.
        
        Args:
            config_class: The configuration class to process
            
        Returns:
            List of bean definitions from @Bean methods
        """
        if config_class in self._processed_configurations:
            return []
        
        bean_definitions = self._process_configuration_class(config_class)
        self._processed_configurations.add(config_class)
        return bean_definitions

    def _discover_configuration_classes(self, package_name: str) -> List[Type]:
        """
        Discover configuration classes in a package.
        
        Args:
            package_name: The package to scan
            
        Returns:
            List of configuration classes found
        """
        config_classes = []
        
        try:
            # Import the package
            package = importlib.import_module(package_name)
            
            # Get the package path
            if hasattr(package, '__path__'):
                package_path = package.__path__
            else:
                # Single module, not a package
                return self._scan_module_for_configurations(package)
            
            # Walk through all modules in the package
            for importer, modname, ispkg in pkgutil.walk_packages(
                package_path, 
                prefix=package_name + "."
            ):
                try:
                    module = importlib.import_module(modname)
                    config_classes.extend(self._scan_module_for_configurations(module))
                except ImportError as e:
                    print(f"Warning: Could not import module {modname}: {e}")
                    continue
                    
        except ImportError as e:
            print(f"Warning: Could not import package {package_name}: {e}")
        
        return config_classes

    def _scan_module_for_configurations(self, module) -> List[Type]:
        """
        Scan a module for configuration classes.
        
        Args:
            module: The module to scan
            
        Returns:
            List of configuration classes found
        """
        config_classes = []
        
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Only consider classes defined in this module
            if (obj.__module__ == module.__name__ and 
                hasattr(obj, '_summer_configuration') and 
                obj._summer_configuration):
                config_classes.append(obj)
        
        return config_classes

    def _process_configuration_class(self, config_class: Type) -> List[BeanDefinition]:
        """
        Process a single configuration class and its @Bean methods.
        
        Args:
            config_class: The configuration class to process
            
        Returns:
            List of bean definitions from @Bean methods
        """
        bean_definitions = []
        
        try:
            # Create an instance of the configuration class
            config_instance = config_class()
            self._configuration_instances[config_class] = config_instance
            
            # Process all @Bean methods
            for method_name, method in inspect.getmembers(config_instance, inspect.ismethod):
                if is_bean_method(method):
                    bean_def = self._create_bean_definition_from_method(
                        config_instance, method, method_name
                    )
                    if bean_def:
                        bean_definitions.append(bean_def)
            
        except Exception as e:
            print(f"Warning: Could not process configuration class {config_class}: {e}")
        
        return bean_definitions

    def _create_bean_definition_from_method(
        self, 
        config_instance: Any, 
        method: Any, 
        method_name: str
    ) -> Optional[BeanDefinition]:
        """
        Create a bean definition from a @Bean method.
        
        Args:
            config_instance: The configuration class instance
            method: The @Bean method
            method_name: The name of the method
            
        Returns:
            Bean definition for the @Bean method, or None if creation fails
        """
        try:
            # Get bean metadata from the method
            bean_name = getattr(method, '_summer_bean_name', method_name)
            bean_scope_str = getattr(method, '_summer_bean_scope', 'singleton')
            bean_type = getattr(method, '_summer_bean_type', None)
            
            # Convert scope string to enum
            scope = BeanScope.SINGLETON
            if bean_scope_str == "prototype":
                scope = BeanScope.PROTOTYPE
            elif bean_scope_str == "request":
                scope = BeanScope.REQUEST
            elif bean_scope_str == "session":
                scope = BeanScope.SESSION
            
            # If no return type annotation, try to infer from method execution
            if bean_type is None:
                # This is risky - we're calling the method to determine type
                # In a production system, we'd want better type inference
                try:
                    sample_instance = method()
                    bean_type = type(sample_instance)
                except Exception:
                    # Fall back to object type
                    bean_type = object
            
            # Create factory method that calls the configuration method with resolved dependencies
            def factory_method(*args):
                return method(*args)
            
            # Create bean definition
            bean_def = BeanDefinition(
                bean_name=bean_name,
                bean_type=bean_type,
                scope=scope,
                factory_method=factory_method,
                factory_bean_name=f"{config_instance.__class__.__name__}#{method_name}",
                source=f"{config_instance.__class__.__module__}.{config_instance.__class__.__name__}.{method_name}"
            )
            
            # Process method dependencies
            self._process_bean_method_dependencies(method, bean_def)
            
            # Process lifecycle methods on the bean type
            self._process_bean_type_lifecycle_methods(bean_type, bean_def)
            
            return bean_def
            
        except Exception as e:
            print(f"Warning: Could not create bean definition for method {method_name}: {e}")
            return None

    def _process_bean_method_dependencies(self, method: Any, bean_def: BeanDefinition) -> None:
        """
        Process dependencies for a @Bean method.
        
        Args:
            method: The @Bean method
            bean_def: The bean definition to update
        """
        # Get dependencies from method metadata
        dependencies = getattr(method, '_summer_bean_dependencies', [])
        
        for dep_info in dependencies:
            dependency = DependencyDescriptor(
                name=dep_info['name'],
                dependency_type=dep_info['type'],
                required=dep_info['required'],
                injection_type=InjectionType.CONSTRUCTOR  # Bean method parameters are like constructor args
            )
            bean_def.add_dependency(dependency)

    def get_configuration_instance(self, config_class: Type) -> Optional[Any]:
        """
        Get the instance of a processed configuration class.
        
        Args:
            config_class: The configuration class
            
        Returns:
            The configuration instance, or None if not processed
        """
        return self._configuration_instances.get(config_class)

    def _process_bean_type_lifecycle_methods(self, bean_type: Type, bean_def: BeanDefinition) -> None:
        """
        Process lifecycle methods on the bean type.
        
        Args:
            bean_type: The bean type to scan for lifecycle methods
            bean_def: The bean definition to update
        """
        for name, method in inspect.getmembers(bean_type, inspect.isfunction):
            if hasattr(method, '_summer_post_construct') and method._summer_post_construct:
                bean_def.add_post_construct_method(name)
            elif hasattr(method, '_summer_pre_destroy') and method._summer_pre_destroy:
                bean_def.add_pre_destroy_method(name)

    def clear_cache(self) -> None:
        """Clear the processor cache."""
        self._processed_configurations.clear()
        self._configuration_instances.clear()