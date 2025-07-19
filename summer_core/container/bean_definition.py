"""
Bean Definition - Holds complete metadata about beans.

Contains information about bean scope, dependencies, lifecycle methods,
and other configuration details needed for bean instantiation and management.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type


class BeanScope(Enum):
    """Enumeration of supported bean scopes."""
    SINGLETON = "singleton"
    PROTOTYPE = "prototype"
    REQUEST = "request"
    SESSION = "session"


class InjectionType(Enum):
    """Enumeration of dependency injection types."""
    CONSTRUCTOR = "constructor"
    SETTER = "setter"
    FIELD = "field"


@dataclass
class DependencyDescriptor:
    """Describes a dependency that needs to be injected."""
    name: str
    dependency_type: Type
    required: bool = True
    qualifier: Optional[str] = None
    injection_type: InjectionType = InjectionType.CONSTRUCTOR


@dataclass
class BeanDefinition:
    """
    Holds the configuration metadata for a bean.
    
    This class contains all the information needed to create and manage
    a bean instance including its type, scope, dependencies, and lifecycle methods.
    """
    
    # Basic bean information
    bean_name: str
    bean_type: Type
    scope: BeanScope = BeanScope.SINGLETON
    
    # Bean creation
    factory_method: Optional[Callable] = None
    factory_bean_name: Optional[str] = None
    constructor_args: List[Any] = field(default_factory=list)
    
    # Dependencies
    dependencies: List[DependencyDescriptor] = field(default_factory=list)
    property_values: Dict[str, Any] = field(default_factory=dict)
    
    # Lifecycle
    init_method_name: Optional[str] = None
    destroy_method_name: Optional[str] = None
    post_construct_methods: List[str] = field(default_factory=list)
    pre_destroy_methods: List[str] = field(default_factory=list)
    
    # Configuration
    lazy_init: bool = False
    primary: bool = False
    abstract: bool = False
    parent_name: Optional[str] = None
    
    # Conditional registration
    profiles: Set[str] = field(default_factory=set)
    conditions: List[Callable[[], bool]] = field(default_factory=list)
    
    # Metadata
    description: Optional[str] = None
    source: Optional[str] = None  # Source file or configuration class
    
    def is_singleton(self) -> bool:
        """Check if this bean is a singleton."""
        return self.scope == BeanScope.SINGLETON
    
    def is_prototype(self) -> bool:
        """Check if this bean is a prototype."""
        return self.scope == BeanScope.PROTOTYPE
    
    def has_constructor_args(self) -> bool:
        """Check if this bean has constructor arguments."""
        return len(self.constructor_args) > 0
    
    def has_dependencies(self) -> bool:
        """Check if this bean has dependencies to inject."""
        return len(self.dependencies) > 0
    
    def get_constructor_dependencies(self) -> List[DependencyDescriptor]:
        """Get dependencies that should be injected via constructor."""
        return [dep for dep in self.dependencies 
                if dep.injection_type == InjectionType.CONSTRUCTOR]
    
    def get_setter_dependencies(self) -> List[DependencyDescriptor]:
        """Get dependencies that should be injected via setter methods."""
        return [dep for dep in self.dependencies 
                if dep.injection_type == InjectionType.SETTER]
    
    def get_field_dependencies(self) -> List[DependencyDescriptor]:
        """Get dependencies that should be injected directly into fields."""
        return [dep for dep in self.dependencies 
                if dep.injection_type == InjectionType.FIELD]
    
    def add_dependency(self, dependency: DependencyDescriptor) -> None:
        """Add a dependency to this bean definition."""
        self.dependencies.append(dependency)
    
    def add_post_construct_method(self, method_name: str) -> None:
        """Add a post-construct lifecycle method."""
        if method_name not in self.post_construct_methods:
            self.post_construct_methods.append(method_name)
    
    def add_pre_destroy_method(self, method_name: str) -> None:
        """Add a pre-destroy lifecycle method."""
        if method_name not in self.pre_destroy_methods:
            self.pre_destroy_methods.append(method_name)
    
    def matches_profile(self, active_profiles: Set[str]) -> bool:
        """Check if this bean matches the given active profiles."""
        if not self.profiles:
            return True  # No profile restrictions
        return bool(self.profiles.intersection(active_profiles))
    
    def meets_conditions(self) -> bool:
        """Check if all conditions for this bean are met."""
        return all(condition() for condition in self.conditions)