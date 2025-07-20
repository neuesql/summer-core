#!/usr/bin/env python3
"""
Demonstration of circular dependency detection in Summer Core framework.

This script shows how the framework detects and reports circular dependencies
with detailed error messages and dependency chains.
"""

from summer_core.container.bean_factory import DefaultBeanFactory
from summer_core.container.bean_definition import BeanDefinition, DependencyDescriptor, BeanScope
from summer_core.container.dependency_resolver import DependencyResolver
from summer_core.exceptions import CircularDependencyError


def demo_simple_circular_dependency():
    """Demonstrate detection of simple A -> B -> A circular dependency."""
    print("=== Simple Circular Dependency Demo ===")
    
    # Create bean factory with dependency resolver
    bean_factory = DefaultBeanFactory()
    dependency_resolver = DependencyResolver(bean_factory)
    bean_factory.set_dependency_resolver(dependency_resolver)
    
    # Create bean definitions with circular dependency
    bean_a_def = BeanDefinition(
        bean_name="serviceA",
        bean_type=object,
        scope=BeanScope.SINGLETON,
        dependencies=[DependencyDescriptor("service_b", object, qualifier="serviceB")]
    )
    bean_b_def = BeanDefinition(
        bean_name="serviceB",
        bean_type=object,
        scope=BeanScope.SINGLETON,
        dependencies=[DependencyDescriptor("service_a", object, qualifier="serviceA")]
    )
    
    bean_factory.register_bean_definition("serviceA", bean_a_def)
    bean_factory.register_bean_definition("serviceB", bean_b_def)
    
    try:
        bean_factory.validate_dependencies()
        print("❌ Expected circular dependency error, but none was raised!")
    except CircularDependencyError as e:
        print(f"✅ Circular dependency detected: {e}")
        print(f"   Cycle beans: {e.cycle_beans}")
    
    print()


def demo_complex_circular_dependency():
    """Demonstrate detection of complex A -> B -> C -> D -> A circular dependency."""
    print("=== Complex Circular Dependency Demo ===")
    
    # Create bean factory with dependency resolver
    bean_factory = DefaultBeanFactory()
    dependency_resolver = DependencyResolver(bean_factory)
    bean_factory.set_dependency_resolver(dependency_resolver)
    
    # Create complex circular dependency chain
    bean_names = ["userService", "orderService", "paymentService", "notificationService"]
    
    for i, bean_name in enumerate(bean_names):
        next_bean = bean_names[(i + 1) % len(bean_names)]  # Circular reference
        bean_def = BeanDefinition(
            bean_name=bean_name,
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("next_service", object, qualifier=next_bean)]
        )
        bean_factory.register_bean_definition(bean_name, bean_def)
    
    try:
        bean_factory.validate_dependencies()
        print("❌ Expected circular dependency error, but none was raised!")
    except CircularDependencyError as e:
        print(f"✅ Complex circular dependency detected: {e}")
        print(f"   Cycle beans: {e.cycle_beans}")
    
    print()


def demo_valid_dependency_chain():
    """Demonstrate that valid dependency chains don't trigger false positives."""
    print("=== Valid Dependency Chain Demo ===")
    
    # Create bean factory with dependency resolver
    bean_factory = DefaultBeanFactory()
    dependency_resolver = DependencyResolver(bean_factory)
    bean_factory.set_dependency_resolver(dependency_resolver)
    
    # Create valid dependency chain: A -> B -> C -> D (no cycle)
    bean_a_def = BeanDefinition(
        bean_name="controllerA",
        bean_type=object,
        scope=BeanScope.SINGLETON,
        dependencies=[DependencyDescriptor("service_b", object, qualifier="serviceB")]
    )
    bean_b_def = BeanDefinition(
        bean_name="serviceB",
        bean_type=object,
        scope=BeanScope.SINGLETON,
        dependencies=[DependencyDescriptor("repository_c", object, qualifier="repositoryC")]
    )
    bean_c_def = BeanDefinition(
        bean_name="repositoryC",
        bean_type=object,
        scope=BeanScope.SINGLETON,
        dependencies=[DependencyDescriptor("database_d", object, qualifier="databaseD")]
    )
    bean_d_def = BeanDefinition(
        bean_name="databaseD",
        bean_type=object,
        scope=BeanScope.SINGLETON,
        dependencies=[]  # No dependencies
    )
    
    bean_factory.register_bean_definition("controllerA", bean_a_def)
    bean_factory.register_bean_definition("serviceB", bean_b_def)
    bean_factory.register_bean_definition("repositoryC", bean_c_def)
    bean_factory.register_bean_definition("databaseD", bean_d_def)
    
    try:
        bean_factory.validate_dependencies()
        print("✅ Valid dependency chain validated successfully - no circular dependencies found")
        
        # Show dependency chain
        chain = dependency_resolver.get_dependency_chain("controllerA")
        print(f"   Dependency creation order: {' -> '.join(chain)}")
    except CircularDependencyError as e:
        print(f"❌ Unexpected circular dependency error: {e}")
    
    print()


def demo_multiple_cycles():
    """Demonstrate detection of multiple separate circular dependency cycles."""
    print("=== Multiple Circular Cycles Demo ===")
    
    # Create bean factory with dependency resolver
    bean_factory = DefaultBeanFactory()
    dependency_resolver = DependencyResolver(bean_factory)
    bean_factory.set_dependency_resolver(dependency_resolver)
    
    # Cycle 1: A1 -> B1 -> A1
    bean_a1_def = BeanDefinition(
        bean_name="serviceA1",
        bean_type=object,
        scope=BeanScope.SINGLETON,
        dependencies=[DependencyDescriptor("service_b1", object, qualifier="serviceB1")]
    )
    bean_b1_def = BeanDefinition(
        bean_name="serviceB1",
        bean_type=object,
        scope=BeanScope.SINGLETON,
        dependencies=[DependencyDescriptor("service_a1", object, qualifier="serviceA1")]
    )
    
    # Cycle 2: A2 -> B2 -> C2 -> A2
    bean_a2_def = BeanDefinition(
        bean_name="serviceA2",
        bean_type=object,
        scope=BeanScope.SINGLETON,
        dependencies=[DependencyDescriptor("service_b2", object, qualifier="serviceB2")]
    )
    bean_b2_def = BeanDefinition(
        bean_name="serviceB2",
        bean_type=object,
        scope=BeanScope.SINGLETON,
        dependencies=[DependencyDescriptor("service_c2", object, qualifier="serviceC2")]
    )
    bean_c2_def = BeanDefinition(
        bean_name="serviceC2",
        bean_type=object,
        scope=BeanScope.SINGLETON,
        dependencies=[DependencyDescriptor("service_a2", object, qualifier="serviceA2")]
    )
    
    # Register all beans
    bean_factory.register_bean_definition("serviceA1", bean_a1_def)
    bean_factory.register_bean_definition("serviceB1", bean_b1_def)
    bean_factory.register_bean_definition("serviceA2", bean_a2_def)
    bean_factory.register_bean_definition("serviceB2", bean_b2_def)
    bean_factory.register_bean_definition("serviceC2", bean_c2_def)
    
    try:
        bean_factory.validate_dependencies()
        print("❌ Expected circular dependency error, but none was raised!")
    except CircularDependencyError as e:
        print(f"✅ Multiple cycles detected (showing first): {e}")
        
        # Show all detected cycles
        cycles = dependency_resolver.detect_circular_dependencies()
        print(f"   Total cycles found: {len(cycles)}")
        for i, cycle in enumerate(cycles, 1):
            print(f"   Cycle {i}: {' -> '.join(cycle)}")
    
    print()


def main():
    """Run all circular dependency detection demonstrations."""
    print("Summer Core Framework - Circular Dependency Detection Demo")
    print("=" * 60)
    print()
    
    demo_simple_circular_dependency()
    demo_complex_circular_dependency()
    demo_valid_dependency_chain()
    demo_multiple_cycles()
    
    print("Demo completed! The framework successfully detects circular dependencies")
    print("and provides detailed error messages with dependency chains.")


if __name__ == "__main__":
    main()