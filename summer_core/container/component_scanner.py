"""
Component Scanner - Discovers and registers components automatically.

Scans packages for classes decorated with @Component, @Service, @Repository
and automatically registers them as bean definitions in the application context.
"""

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import List, Set, Type, Optional, Dict, Any

from summer_core.container.bean_definition import BeanDefinition, BeanScope, DependencyDescriptor, InjectionType
from summer_core.decorators.component import is_component, get_component_name, get_component_scope
from summer_core.decorators.autowired import is_autowired, PostConstruct, PreDestroy


class ComponentScanner:
    """
    Scans packages for Spring components and registers them automatically.
    
    Discovers classes annotated with @Component, @Service, @Repository and
    creates appropriate bean definitions for registration with the container.
    """

    def __init__(self) -> None:
        """Initialize the component scanner."""
        self._scanned_packages: Set[str] = set()
        self._discovered_components: Dict[str, Type] = {}

    def scan_packages(self, base_packages: List[str]) -> List[BeanDefinition]:
        """
        Scan the specified packages for components.
        
        Args:
            base_packages: List of package names to scan
            
        Returns:
            List of bean definitions for discovered components
        """
        bean_definitions = []
        
        for package_name in base_packages:
            if package_name not in self._scanned_packages:
                components = self._scan_package(package_name)
                for component_class in components:
                    bean_def = self._create_bean_definition(component_class)
                    if bean_def:
                        bean_definitions.append(bean_def)
                self._scanned_packages.add(package_name)
        
        return bean_definitions

    def _scan_package(self, package_name: str) -> List[Type]:
        """
        Scan a single package for component classes.
        
        Args:
            package_name: The package to scan
            
        Returns:
            List of component classes found in the package
        """
        components = []
        
        try:
            # Import the package
            package = importlib.import_module(package_name)
            
            # Get the package path
            if hasattr(package, '__path__'):
                package_path = package.__path__
            else:
                # Single module, not a package
                return self._scan_module(package)
            
            # Walk through all modules in the package
            for importer, modname, ispkg in pkgutil.walk_packages(
                package_path, 
                prefix=package_name + "."
            ):
                try:
                    module = importlib.import_module(modname)
                    components.extend(self._scan_module(module))
                except ImportError as e:
                    # Skip modules that can't be imported
                    print(f"Warning: Could not import module {modname}: {e}")
                    continue
                    
        except ImportError as e:
            print(f"Warning: Could not import package {package_name}: {e}")
        
        return components

    def _scan_module(self, module) -> List[Type]:
        """
        Scan a single module for component classes.
        
        Args:
            module: The module to scan
            
        Returns:
            List of component classes found in the module
        """
        components = []
        
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Only consider classes defined in this module
            if obj.__module__ == module.__name__ and is_component(obj):
                components.append(obj)
                self._discovered_components[get_component_name(obj)] = obj
        
        return components

    def _create_bean_definition(self, component_class: Type) -> Optional[BeanDefinition]:
        """
        Create a bean definition from a component class.
        
        Args:
            component_class: The component class to create a definition for
            
        Returns:
            Bean definition for the component, or None if creation fails
        """
        try:
            bean_name = get_component_name(component_class)
            scope_str = get_component_scope(component_class)
            
            # Convert scope string to enum
            scope = BeanScope.SINGLETON
            if scope_str == "prototype":
                scope = BeanScope.PROTOTYPE
            elif scope_str == "request":
                scope = BeanScope.REQUEST
            elif scope_str == "session":
                scope = BeanScope.SESSION
            
            # Create bean definition
            bean_def = BeanDefinition(
                bean_name=bean_name,
                bean_type=component_class,
                scope=scope,
                source=f"{component_class.__module__}.{component_class.__name__}"
            )
            
            # Process constructor dependencies
            self._process_constructor_dependencies(component_class, bean_def)
            
            # Process lifecycle methods
            self._process_lifecycle_methods(component_class, bean_def)
            
            return bean_def
            
        except Exception as e:
            print(f"Warning: Could not create bean definition for {component_class}: {e}")
            return None

    def _process_constructor_dependencies(self, component_class: Type, bean_def: BeanDefinition) -> None:
        """
        Process constructor dependencies for autowiring.
        
        Args:
            component_class: The component class
            bean_def: The bean definition to update
        """
        constructor = getattr(component_class, '__init__', None)
        if not constructor:
            return
        
        # Check if constructor is marked for autowiring
        if hasattr(constructor, '_summer_autowired') and constructor._summer_autowired:
            dependencies = getattr(constructor, '_summer_dependencies', [])
            
            for dep_info in dependencies:
                dependency = DependencyDescriptor(
                    name=dep_info['name'],
                    dependency_type=dep_info['type'],
                    required=dep_info['required'],
                    injection_type=InjectionType.CONSTRUCTOR
                )
                bean_def.add_dependency(dependency)
        else:
            # Check if class is marked for autowiring (class-level @Autowired)
            if hasattr(component_class, '_summer_autowired_constructor'):
                # Extract type hints from constructor
                import typing
                type_hints = typing.get_type_hints(constructor)
                sig = inspect.signature(constructor)
                
                for param_name, param in sig.parameters.items():
                    if param_name == 'self':
                        continue
                    
                    param_type = type_hints.get(param_name, param.annotation)
                    if param_type != inspect.Parameter.empty:
                        dependency = DependencyDescriptor(
                            name=param_name,
                            dependency_type=param_type,
                            required=param.default == inspect.Parameter.empty,
                            injection_type=InjectionType.CONSTRUCTOR
                        )
                        bean_def.add_dependency(dependency)

    def _process_lifecycle_methods(self, component_class: Type, bean_def: BeanDefinition) -> None:
        """
        Process lifecycle methods (@PostConstruct, @PreDestroy).
        
        Args:
            component_class: The component class
            bean_def: The bean definition to update
        """
        for name, method in inspect.getmembers(component_class, inspect.isfunction):
            if hasattr(method, '_summer_post_construct') and method._summer_post_construct:
                bean_def.add_post_construct_method(name)
            elif hasattr(method, '_summer_pre_destroy') and method._summer_pre_destroy:
                bean_def.add_pre_destroy_method(name)

    def get_discovered_components(self) -> Dict[str, Type]:
        """
        Get all discovered components.
        
        Returns:
            Dictionary mapping component names to component classes
        """
        return self._discovered_components.copy()

    def clear_cache(self) -> None:
        """Clear the scanner cache."""
        self._scanned_packages.clear()
        self._discovered_components.clear()