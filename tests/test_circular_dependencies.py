"""
Tests for circular dependency detection and resolution.

This module tests various circular dependency scenarios and ensures
proper error reporting and detection mechanisms.
"""

import unittest
import tempfile
import sys
import os
from typing import Optional

from summer_core.container.application_context import DefaultApplicationContext
from summer_core.container.bean_factory import DefaultBeanFactory
from summer_core.container.bean_definition import BeanDefinition, DependencyDescriptor, BeanScope
from summer_core.container.dependency_resolver import DependencyResolver
from summer_core.decorators.component import Component, Service
from summer_core.decorators.autowired import Autowired
from summer_core.exceptions import CircularDependencyError, BeanCreationError


class TestCircularDependencyDetection(unittest.TestCase):
    """Test circular dependency detection mechanisms."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.bean_factory = DefaultBeanFactory()
        self.dependency_resolver = DependencyResolver(self.bean_factory)
        self.bean_factory.set_dependency_resolver(self.dependency_resolver)
        self.context = None

    def tearDown(self):
        """Clean up after each test method."""
        if self.context:
            self.context.close()

    def test_simple_circular_dependency_detection(self):
        """Test detection of simple A -> B -> A circular dependency."""
        # Create bean definitions with circular dependency
        bean_a_def = BeanDefinition(
            bean_name="beanA",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("b_dependency", object, qualifier="beanB")]
        )
        bean_b_def = BeanDefinition(
            bean_name="beanB",
            bean_type=object,
            scope=BeanScope.SINGLETON, 
            dependencies=[DependencyDescriptor("a_dependency", object, qualifier="beanA")]
        )
        
        self.bean_factory.register_bean_definition("beanA", bean_a_def)
        self.bean_factory.register_bean_definition("beanB", bean_b_def)
        
        # Validate dependencies should detect circular dependency
        with self.assertRaises(CircularDependencyError) as cm:
            self.bean_factory.validate_dependencies()
        
        error_message = str(cm.exception)
        self.assertIn("Circular dependency detected", error_message)
        self.assertTrue("beanA" in error_message and "beanB" in error_message)

    def test_complex_circular_dependency_detection(self):
        """Test detection of complex A -> B -> C -> A circular dependency."""
        # Create bean definitions with complex circular dependency
        bean_a_def = BeanDefinition(
            bean_name="beanA",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("b_dependency", object, qualifier="beanB")]
        )
        bean_b_def = BeanDefinition(
            bean_name="beanB",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("c_dependency", object, qualifier="beanC")]
        )
        bean_c_def = BeanDefinition(
            bean_name="beanC",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("a_dependency", object, qualifier="beanA")]
        )
        
        self.bean_factory.register_bean_definition("beanA", bean_a_def)
        self.bean_factory.register_bean_definition("beanB", bean_b_def)
        self.bean_factory.register_bean_definition("beanC", bean_c_def)
        
        # Validate dependencies should detect circular dependency
        with self.assertRaises(CircularDependencyError) as cm:
            self.bean_factory.validate_dependencies()
        
        error_message = str(cm.exception)
        self.assertIn("Circular dependency detected", error_message)

    def test_self_circular_dependency_detection(self):
        """Test detection of self-referencing circular dependency."""
        # Create bean definition that depends on itself
        bean_def = BeanDefinition(
            bean_name="selfBean",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("self_dependency", object, qualifier="selfBean")]
        )
        
        self.bean_factory.register_bean_definition("selfBean", bean_def)
        
        # Validate dependencies should detect self-circular dependency
        with self.assertRaises(CircularDependencyError) as cm:
            self.bean_factory.validate_dependencies()
        
        error_message = str(cm.exception)
        self.assertIn("Circular dependency detected", error_message)
        self.assertIn("selfBean", error_message)

    def test_no_circular_dependency_valid_case(self):
        """Test that valid dependency chains don't trigger false positives."""
        # Create valid dependency chain A -> B -> C (no cycle)
        bean_a_def = BeanDefinition(
            bean_name="beanA",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("b_dependency", object, qualifier="beanB")]
        )
        bean_b_def = BeanDefinition(
            bean_name="beanB",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("c_dependency", object, qualifier="beanC")]
        )
        bean_c_def = BeanDefinition(
            bean_name="beanC",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[]  # No dependencies
        )
        
        self.bean_factory.register_bean_definition("beanA", bean_a_def)
        self.bean_factory.register_bean_definition("beanB", bean_b_def)
        self.bean_factory.register_bean_definition("beanC", bean_c_def)
        
        # Validate dependencies should not raise any errors
        try:
            self.bean_factory.validate_dependencies()
        except CircularDependencyError:
            self.fail("validate_dependencies() raised CircularDependencyError unexpectedly")

    def test_circular_dependency_during_bean_creation(self):
        """Test circular dependency detection during actual bean creation."""
        # Create test classes with circular dependencies
        class ServiceA:
            def __init__(self, service_b):
                self.service_b = service_b

        class ServiceB:
            def __init__(self, service_a):
                self.service_a = service_a

        # Create bean definitions
        bean_a_def = BeanDefinition(
            bean_name="serviceA",
            bean_type=ServiceA,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("service_b", ServiceB, qualifier="serviceB")]
        )
        bean_b_def = BeanDefinition(
            bean_name="serviceB",
            bean_type=ServiceB,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("service_a", ServiceA, qualifier="serviceA")]
        )
        
        self.bean_factory.register_bean_definition("serviceA", bean_a_def)
        self.bean_factory.register_bean_definition("serviceB", bean_b_def)
        
        # Attempting to get bean should raise BeanCreationError with CircularDependencyError as cause
        with self.assertRaises((CircularDependencyError, BeanCreationError)) as cm:
            self.bean_factory.get_bean("serviceA")
        
        error_message = str(cm.exception)
        self.assertIn("serviceA", error_message)
        self.assertIn("serviceB", error_message)
        self.assertIn("Circular dependency detected", error_message)

    def test_multiple_circular_dependencies_detection(self):
        """Test detection of multiple separate circular dependency cycles."""
        # Create two separate circular dependency cycles
        # Cycle 1: A -> B -> A
        bean_a_def = BeanDefinition(
            bean_name="beanA",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("b_dependency", object, qualifier="beanB")]
        )
        bean_b_def = BeanDefinition(
            bean_name="beanB",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("a_dependency", object, qualifier="beanA")]
        )
        
        # Cycle 2: C -> D -> C
        bean_c_def = BeanDefinition(
            bean_name="beanC",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("d_dependency", object, qualifier="beanD")]
        )
        bean_d_def = BeanDefinition(
            bean_name="beanD",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("c_dependency", object, qualifier="beanC")]
        )
        
        self.bean_factory.register_bean_definition("beanA", bean_a_def)
        self.bean_factory.register_bean_definition("beanB", bean_b_def)
        self.bean_factory.register_bean_definition("beanC", bean_c_def)
        self.bean_factory.register_bean_definition("beanD", bean_d_def)
        
        # Build dependency graph first
        for bean_name, bean_definition in self.bean_factory._bean_definitions.items():
            self.dependency_resolver._build_dependency_graph(bean_name, bean_definition)
        
        # Should detect circular dependencies
        cycles = self.dependency_resolver.detect_circular_dependencies()
        self.assertGreater(len(cycles), 0, "Should detect at least one circular dependency")


class TestCircularDependencyWithDecorators(unittest.TestCase):
    """Test circular dependency detection with decorator-based configuration."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = self.temp_dir.name
        sys.path.insert(0, self.temp_path)
        self.context = None

    def tearDown(self):
        """Clean up after each test method."""
        if self.context:
            self.context.close()
        sys.path.remove(self.temp_path)
        self.temp_dir.cleanup()

    def test_circular_dependency_with_component_decorators(self):
        """Test circular dependency detection with @Component decorators."""
        # Create test module with circular dependencies
        test_module_content = '''
from summer_core.decorators.component import Component, Service
from summer_core.decorators.autowired import Autowired

@Service
class UserService:
    @Autowired
    def __init__(self, order_service):
        self.order_service = order_service

@Service  
class OrderService:
    @Autowired
    def __init__(self, user_service):
        self.user_service = user_service
'''
        
        # Write test module
        test_module_path = os.path.join(self.temp_path, "circular_test_module.py")
        with open(test_module_path, 'w') as f:
            f.write(test_module_content)
        
        # Create application context and scan for components
        self.context = DefaultApplicationContext(base_packages=["circular_test_module"])
        
        # Context refresh should succeed, but bean creation should detect circular dependency
        self.context.refresh()
        
        # Try to get a bean to trigger circular dependency detection
        with self.assertRaises((CircularDependencyError, BeanCreationError)):
            self.context.get_bean('userService')

    def test_circular_dependency_error_message_quality(self):
        """Test that circular dependency error messages are informative."""
        # Create simple circular dependency
        class ServiceA:
            pass

        class ServiceB:
            pass

        bean_a_def = BeanDefinition(
            bean_name="serviceA",
            bean_type=ServiceA,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("service_b", ServiceB, qualifier="serviceB")]
        )
        bean_b_def = BeanDefinition(
            bean_name="serviceB",
            bean_type=ServiceB,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("service_a", ServiceA, qualifier="serviceA")]
        )
        
        bean_factory = DefaultBeanFactory()
        bean_factory.register_bean_definition("serviceA", bean_a_def)
        bean_factory.register_bean_definition("serviceB", bean_b_def)
        
        with self.assertRaises((CircularDependencyError, BeanCreationError)) as cm:
            bean_factory.get_bean("serviceA")
        
        error_message = str(cm.exception)
        
        # Check that error message contains helpful information
        self.assertIn("Circular dependency detected", error_message)
        self.assertIn("serviceA", error_message)
        self.assertIn("serviceB", error_message)
        self.assertIn("->", error_message)  # Should show dependency chain

    def test_dependency_chain_reporting(self):
        """Test that dependency chains are properly reported."""
        dependency_resolver = DependencyResolver(DefaultBeanFactory())
        
        # Create a dependency chain A -> B -> C
        bean_a_def = BeanDefinition(
            bean_name="beanA",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("b_dependency", object, qualifier="beanB")]
        )
        bean_b_def = BeanDefinition(
            bean_name="beanB",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("c_dependency", object, qualifier="beanC")]
        )
        bean_c_def = BeanDefinition(
            bean_name="beanC",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[]
        )
        
        dependency_resolver._bean_factory.register_bean_definition("beanA", bean_a_def)
        dependency_resolver._bean_factory.register_bean_definition("beanB", bean_b_def)
        dependency_resolver._bean_factory.register_bean_definition("beanC", bean_c_def)
        
        # Get dependency chain
        chain = dependency_resolver.get_dependency_chain("beanA")
        
        # Chain should include all dependencies in correct order
        self.assertIn("beanA", chain)
        self.assertIn("beanB", chain)
        self.assertIn("beanC", chain)
        
        # beanC should come before beanB, and beanB before beanA (dependency order)
        c_index = chain.index("beanC")
        b_index = chain.index("beanB")
        a_index = chain.index("beanA")
        
        self.assertLess(c_index, b_index)
        self.assertLess(b_index, a_index)


class TestCircularDependencyEdgeCases(unittest.TestCase):
    """Test edge cases for circular dependency detection."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.bean_factory = DefaultBeanFactory()
        self.dependency_resolver = DependencyResolver(self.bean_factory)
        self.bean_factory.set_dependency_resolver(self.dependency_resolver)

    def test_deep_circular_dependency_chain(self):
        """Test detection of deep circular dependency chains (A->B->C->D->E->A)."""
        # Create a deep circular dependency chain
        bean_names = ["beanA", "beanB", "beanC", "beanD", "beanE"]
        
        for i, bean_name in enumerate(bean_names):
            next_bean = bean_names[(i + 1) % len(bean_names)]  # Circular reference
            bean_def = BeanDefinition(
                bean_name=bean_name,
                bean_type=object,
                scope=BeanScope.SINGLETON,
                dependencies=[DependencyDescriptor("next_dependency", object, qualifier=next_bean)]
            )
            self.bean_factory.register_bean_definition(bean_name, bean_def)
        
        # Should detect circular dependency
        with self.assertRaises(CircularDependencyError) as cm:
            self.bean_factory.validate_dependencies()
        
        error_message = str(cm.exception)
        self.assertIn("Circular dependency detected", error_message)
        # Should contain at least some of the beans in the cycle
        self.assertTrue(any(bean_name in error_message for bean_name in bean_names))

    def test_mixed_circular_and_valid_dependencies(self):
        """Test scenario with both circular and valid dependencies."""
        # Valid chain: validA -> validB -> validC
        valid_a_def = BeanDefinition(
            bean_name="validA",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("valid_b", object, qualifier="validB")]
        )
        valid_b_def = BeanDefinition(
            bean_name="validB",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("valid_c", object, qualifier="validC")]
        )
        valid_c_def = BeanDefinition(
            bean_name="validC",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[]
        )
        
        # Circular chain: circularA -> circularB -> circularA
        circular_a_def = BeanDefinition(
            bean_name="circularA",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("circular_b", object, qualifier="circularB")]
        )
        circular_b_def = BeanDefinition(
            bean_name="circularB",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("circular_a", object, qualifier="circularA")]
        )
        
        # Register all beans
        self.bean_factory.register_bean_definition("validA", valid_a_def)
        self.bean_factory.register_bean_definition("validB", valid_b_def)
        self.bean_factory.register_bean_definition("validC", valid_c_def)
        self.bean_factory.register_bean_definition("circularA", circular_a_def)
        self.bean_factory.register_bean_definition("circularB", circular_b_def)
        
        # Should detect circular dependency
        with self.assertRaises(CircularDependencyError) as cm:
            self.bean_factory.validate_dependencies()
        
        error_message = str(cm.exception)
        self.assertIn("Circular dependency detected", error_message)
        # Should mention the circular beans, not the valid ones
        self.assertTrue("circularA" in error_message or "circularB" in error_message)

    def test_circular_dependency_with_optional_dependencies(self):
        """Test circular dependency detection with optional dependencies."""
        class ServiceA:
            def __init__(self, service_b=None):
                self.service_b = service_b

        class ServiceB:
            def __init__(self, service_a):
                self.service_a = service_a

        # ServiceA has optional dependency on ServiceB
        # ServiceB has required dependency on ServiceA
        bean_a_def = BeanDefinition(
            bean_name="serviceA",
            bean_type=ServiceA,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("service_b", ServiceB, qualifier="serviceB", required=False)]
        )
        bean_b_def = BeanDefinition(
            bean_name="serviceB",
            bean_type=ServiceB,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("service_a", ServiceA, qualifier="serviceA", required=True)]
        )
        
        self.bean_factory.register_bean_definition("serviceA", bean_a_def)
        self.bean_factory.register_bean_definition("serviceB", bean_b_def)
        
        # Should still detect circular dependency even with optional dependency
        with self.assertRaises(CircularDependencyError):
            self.bean_factory.validate_dependencies()

    def test_multiple_separate_circular_cycles(self):
        """Test detection when multiple separate circular cycles exist."""
        # Cycle 1: A1 -> B1 -> A1
        bean_a1_def = BeanDefinition(
            bean_name="beanA1",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("b1_dependency", object, qualifier="beanB1")]
        )
        bean_b1_def = BeanDefinition(
            bean_name="beanB1",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("a1_dependency", object, qualifier="beanA1")]
        )
        
        # Cycle 2: A2 -> B2 -> C2 -> A2
        bean_a2_def = BeanDefinition(
            bean_name="beanA2",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("b2_dependency", object, qualifier="beanB2")]
        )
        bean_b2_def = BeanDefinition(
            bean_name="beanB2",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("c2_dependency", object, qualifier="beanC2")]
        )
        bean_c2_def = BeanDefinition(
            bean_name="beanC2",
            bean_type=object,
            scope=BeanScope.SINGLETON,
            dependencies=[DependencyDescriptor("a2_dependency", object, qualifier="beanA2")]
        )
        
        # Register all beans
        self.bean_factory.register_bean_definition("beanA1", bean_a1_def)
        self.bean_factory.register_bean_definition("beanB1", bean_b1_def)
        self.bean_factory.register_bean_definition("beanA2", bean_a2_def)
        self.bean_factory.register_bean_definition("beanB2", bean_b2_def)
        self.bean_factory.register_bean_definition("beanC2", bean_c2_def)
        
        # Should detect at least one circular dependency
        with self.assertRaises(CircularDependencyError):
            self.bean_factory.validate_dependencies()
        
        # Test that we can detect multiple cycles
        cycles = self.dependency_resolver.detect_circular_dependencies()
        self.assertGreaterEqual(len(cycles), 1, "Should detect at least one circular dependency")

    def test_circular_dependency_detection_performance(self):
        """Test that circular dependency detection performs well with many beans."""
        import time
        
        # Create a large number of beans with valid dependencies
        num_beans = 100
        for i in range(num_beans):
            bean_name = f"bean{i}"
            dependencies = []
            
            # Each bean depends on the next one (except the last)
            if i < num_beans - 1:
                next_bean = f"bean{i+1}"
                dependencies.append(DependencyDescriptor("next_dep", object, qualifier=next_bean))
            
            bean_def = BeanDefinition(
                bean_name=bean_name,
                bean_type=object,
                scope=BeanScope.SINGLETON,
                dependencies=dependencies
            )
            self.bean_factory.register_bean_definition(bean_name, bean_def)
        
        # Add one circular dependency at the end
        last_bean_def = self.bean_factory.get_bean_definition(f"bean{num_beans-1}")
        last_bean_def.dependencies.append(DependencyDescriptor("circular_dep", object, qualifier="bean0"))
        
        # Measure time for circular dependency detection
        start_time = time.time()
        
        with self.assertRaises(CircularDependencyError):
            self.bean_factory.validate_dependencies()
        
        end_time = time.time()
        detection_time = end_time - start_time
        
        # Should complete in reasonable time (less than 1 second for 100 beans)
        self.assertLess(detection_time, 1.0, f"Circular dependency detection took too long: {detection_time:.3f}s")


if __name__ == '__main__':
    unittest.main()