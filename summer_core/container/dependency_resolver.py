"""
Dependency Resolver - Handles complex dependency resolution scenarios.

Provides advanced dependency resolution including circular dependency detection,
optional dependencies, and collection injection.
"""

from typing import Any, Dict, List, Set, Type, Optional
from collections import defaultdict, deque

from summer_core.container.bean_definition import BeanDefinition, DependencyDescriptor


class DependencyGraph:
    """
    Represents the dependency graph between beans.
    
    Used for circular dependency detection and resolution ordering.
    """

    def __init__(self) -> None:
        """Initialize the dependency graph."""
        self._graph: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_graph: Dict[str, Set[str]] = defaultdict(set)

    def add_dependency(self, bean_name: str, dependency_name: str) -> None:
        """
        Add a dependency relationship.
        
        Args:
            bean_name: The name of the bean that has the dependency
            dependency_name: The name of the bean that is depended upon
        """
        self._graph[bean_name].add(dependency_name)
        self._reverse_graph[dependency_name].add(bean_name)

    def has_circular_dependency(self, bean_name: str) -> bool:
        """
        Check if there's a circular dependency involving the given bean.
        
        Args:
            bean_name: The name of the bean to check
            
        Returns:
            True if a circular dependency exists
        """
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self._graph[node]:
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        return has_cycle(bean_name)

    def get_circular_dependency_path(self, bean_name: str) -> Optional[List[str]]:
        """
        Get the circular dependency path if one exists.
        
        Args:
            bean_name: The name of the bean to check
            
        Returns:
            The circular dependency path, or None if no cycle exists
        """
        visited = set()
        rec_stack = set()
        path = []
        
        def find_cycle(node: str) -> Optional[List[str]]:
            if node in rec_stack:
                # Found cycle, return path from cycle start
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]
            
            if node in visited:
                return None
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self._graph[node]:
                result = find_cycle(neighbor)
                if result:
                    return result
            
            rec_stack.remove(node)
            path.pop()
            return None
        
        return find_cycle(bean_name)

    def find_all_cycles(self) -> List[List[str]]:
        """
        Find all circular dependency cycles in the graph.
        
        Returns:
            List of cycles, each represented as a list of bean names
        """
        visited = set()
        cycles = []
        
        # Create a copy of keys to avoid dictionary changed size during iteration
        nodes = list(self._graph.keys())
        
        for node in nodes:
            if node not in visited:
                cycle = self.get_circular_dependency_path(node)
                if cycle:
                    cycles.append(cycle)
                    visited.update(cycle)
        
        return cycles

    def get_creation_order(self) -> List[str]:
        """
        Get the order in which beans should be created to satisfy dependencies.
        
        Returns:
            List of bean names in dependency order
        """
        in_degree = defaultdict(int)
        all_nodes = set(self._graph.keys()) | set(self._reverse_graph.keys())
        
        # Calculate in-degrees
        for node in all_nodes:
            in_degree[node] = len(self._reverse_graph[node])
        
        # Topological sort using Kahn's algorithm
        queue = deque([node for node in all_nodes if in_degree[node] == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            for neighbor in self._graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result


class DependencyResolver:
    """
    Handles complex dependency resolution scenarios.
    
    Provides functionality for resolving dependencies, detecting circular
    dependencies, and managing optional dependencies.
    """

    def __init__(self, bean_factory) -> None:
        """
        Initialize the dependency resolver.
        
        Args:
            bean_factory: The bean factory to use for bean resolution
        """
        self._bean_factory = bean_factory
        self._dependency_graph = DependencyGraph()
        self._dependency_chains: Dict[str, List[str]] = {}

    def resolve_dependencies(self, bean_name: str, bean_definition: BeanDefinition) -> Dict[str, Any]:
        """
        Resolve all dependencies for a given bean.
        
        Args:
            bean_name: The name of the bean
            bean_definition: The bean definition
            
        Returns:
            Dictionary mapping dependency names to resolved instances
            
        Raises:
            CircularDependencyError: If circular dependencies are detected
            NoSuchBeanDefinitionError: If required dependencies cannot be found
        """
        resolved_dependencies = {}
        
        # Build dependency graph
        self._build_dependency_graph(bean_name, bean_definition)
        
        # Check for circular dependencies
        if self._dependency_graph.has_circular_dependency(bean_name):
            cycle_path = self._dependency_graph.get_circular_dependency_path(bean_name)
            from summer_core.exceptions import CircularDependencyError
            raise CircularDependencyError(
                f"Circular dependency detected: {' -> '.join(cycle_path)}"
            )
        
        # Resolve each dependency
        for dependency in bean_definition.dependencies:
            try:
                resolved_instance = self._resolve_single_dependency(dependency)
                resolved_dependencies[dependency.name] = resolved_instance
            except Exception as e:
                if dependency.required:
                    raise
                # Optional dependency that couldn't be resolved
                resolved_dependencies[dependency.name] = None
        
        return resolved_dependencies

    def _build_dependency_graph(self, bean_name: str, bean_definition: BeanDefinition) -> None:
        """Build the dependency graph for the given bean."""
        for dependency in bean_definition.dependencies:
            if dependency.qualifier:
                dep_name = dependency.qualifier
            else:
                # Find bean name by type
                dep_name = self._find_bean_name_by_type(dependency.dependency_type)
            
            if dep_name:
                self._dependency_graph.add_dependency(bean_name, dep_name)

    def _resolve_single_dependency(self, dependency: DependencyDescriptor) -> Any:
        """
        Resolve a single dependency.
        
        Args:
            dependency: The dependency descriptor
            
        Returns:
            The resolved dependency instance
        """
        if dependency.qualifier:
            # Resolve by name
            return self._bean_factory.get_bean(dependency.qualifier)
        else:
            # Resolve by type
            return self._bean_factory.get_bean_by_type(dependency.dependency_type)

    def _find_bean_name_by_type(self, bean_type: Type) -> Optional[str]:
        """
        Find a bean name by its type.
        
        Args:
            bean_type: The type to search for
            
        Returns:
            The bean name, or None if not found
        """
        for name, definition in self._bean_factory._bean_definitions.items():
            if definition.bean_type == bean_type:
                return name
        return None

    def get_beans_by_type(self, bean_type: Type) -> Dict[str, Any]:
        """
        Get all beans of a specific type.
        
        Args:
            bean_type: The type to search for
            
        Returns:
            Dictionary mapping bean names to instances
        """
        result = {}
        for name, definition in self._bean_factory._bean_definitions.items():
            if definition.bean_type == bean_type or issubclass(definition.bean_type, bean_type):
                result[name] = self._bean_factory.get_bean(name)
        return result

    def resolve_collection_dependency(self, element_type: Type) -> List[Any]:
        """
        Resolve a collection dependency (all beans of a given type).
        
        Args:
            element_type: The type of elements in the collection
            
        Returns:
            List of all beans of the specified type
        """
        beans_by_type = self.get_beans_by_type(element_type)
        return list(beans_by_type.values())

    def can_resolve_dependency(self, dependency: DependencyDescriptor) -> bool:
        """
        Check if a dependency can be resolved.
        
        Args:
            dependency: The dependency descriptor
            
        Returns:
            True if the dependency can be resolved
        """
        try:
            if dependency.qualifier:
                return self._bean_factory.contains_bean(dependency.qualifier)
            else:
                # Check if any bean of the required type exists
                return self._find_bean_name_by_type(dependency.dependency_type) is not None
        except Exception:
            return False

    def detect_circular_dependencies(self) -> List[List[str]]:
        """
        Detect all circular dependencies in the current bean definitions.
        
        Returns:
            List of circular dependency cycles, each represented as a list of bean names
        """
        return self._dependency_graph.find_all_cycles()

    def get_dependency_chain(self, bean_name: str) -> List[str]:
        """
        Get the dependency chain for a given bean in creation order.
        
        Args:
            bean_name: The name of the bean
            
        Returns:
            List of bean names in dependency creation order
        """
        if bean_name in self._dependency_chains:
            return self._dependency_chains[bean_name]
        
        # Build dependency chain using topological sort
        visited = set()
        temp_visited = set()
        chain = []
        
        def visit(node: str):
            if node in temp_visited:
                # Circular dependency detected
                return
            if node in visited:
                return
            
            temp_visited.add(node)
            
            # Visit dependencies first
            if node in self._bean_factory._bean_definitions:
                bean_def = self._bean_factory._bean_definitions[node]
                for dep in bean_def.dependencies:
                    dep_name = dep.qualifier or self._find_bean_name_by_type(dep.dependency_type)
                    if dep_name:
                        visit(dep_name)
            
            temp_visited.remove(node)
            visited.add(node)
            chain.append(node)
        
        visit(bean_name)
        self._dependency_chains[bean_name] = chain
        return chain

    def validate_all_dependencies(self) -> None:
        """
        Validate all bean dependencies for circular dependencies.
        
        Raises:
            CircularDependencyError: If circular dependencies are detected
        """
        # Build dependency graph for all beans
        for bean_name, bean_definition in self._bean_factory._bean_definitions.items():
            self._build_dependency_graph(bean_name, bean_definition)
        
        # Check for circular dependencies
        cycles = self.detect_circular_dependencies()
        if cycles:
            # Report the first cycle found
            cycle = cycles[0]
            cycle_path = " -> ".join(cycle)
            from summer_core.exceptions import CircularDependencyError
            raise CircularDependencyError(cycle_path, cycle)