import unittest

from summer_core.abs_bean_factory import AbstractBeanFactory
from summer_core.bean_definition import BeanDefinition, BeanScope
from summer_core.bean_exceptions import (
    BeanCreationError,
    BeanNotFoundError,
    DuplicateBeanError,
)


class TestBeanFactory(unittest.TestCase):
    def setUp(self):
        """Set up a new BeanFactory instance for each test."""
        self.bean_factory = AbstractBeanFactory()

    def test_register_bean(self):
        """Test registering a bean definition."""

        class TestBean:
            pass

        bean_def = BeanDefinition("test_bean", TestBean)
        self.bean_factory.register_bean_definition(bean_def)

        self.assertIn("test_bean", self.bean_factory._bean_definitions)

    def test_register_duplicate_bean(self):
        """Test registering a bean with a duplicate name raises DuplicateBeanError."""

        class TestBean:
            pass

        bean_def = BeanDefinition("test_bean", TestBean)
        self.bean_factory.register_bean_definition(bean_def)

        with self.assertRaises(DuplicateBeanError):
            self.bean_factory.register_bean_definition(bean_def)

    def test_get_nonexistent_bean(self):
        """Test getting a non-existent bean raises BeanNotFoundError."""
        with self.assertRaises(BeanNotFoundError):
            self.bean_factory.get_bean("nonexistent")

    def test_get_bean_definition(self):
        """Test getting a bean definition."""

        class TestBean:
            pass

        bean_def = BeanDefinition("test_bean", TestBean)
        self.bean_factory.register_bean_definition(bean_def)

        retrieved_def = self.bean_factory.get_bean_definition("test_bean")
        self.assertEqual(retrieved_def, bean_def)

    def test_get_nonexistent_bean_definition(self):
        """Test getting a non-existent bean definition raises BeanNotFoundError."""
        with self.assertRaises(BeanNotFoundError):
            self.bean_factory.get_bean_definition("nonexistent")

    def test_get_bean_names(self):
        """Test getting all registered bean names."""

        class Bean1:
            pass

        class Bean2:
            pass

        bean1_def = BeanDefinition("bean1", Bean1)
        bean2_def = BeanDefinition("bean2", Bean2)

        self.bean_factory.register_bean_definition(bean1_def)
        self.bean_factory.register_bean_definition(bean2_def)

        bean_names = self.bean_factory.get_bean_names()
        self.assertEqual(set(bean_names), {"bean1", "bean2"})

    def test_get_bean_names_empty(self):
        """Test getting bean names when no beans are registered."""
        bean_names = self.bean_factory.get_bean_names()
        self.assertEqual(bean_names, [])

    def test_get_singleton_bean(self):
        """Test getting a singleton bean returns the same instance."""

        class TestBean:
            pass

        bean_def = BeanDefinition("test_bean", TestBean)
        self.bean_factory.register_bean_definition(bean_def)

        instance1 = self.bean_factory.get_bean("test_bean")
        instance2 = self.bean_factory.get_bean("test_bean")

        self.assertIs(instance1, instance2)

    def test_get_prototype_bean(self):
        """Test getting a prototype bean returns different instances."""

        class TestBean:
            pass

        bean_def = BeanDefinition("test_bean", TestBean, scope=BeanScope.PROTOTYPE)
        self.bean_factory.register_bean_definition(bean_def)

        instance1 = self.bean_factory.get_bean("test_bean")
        instance2 = self.bean_factory.get_bean("test_bean")

        self.assertIsNot(instance1, instance2)

    def test_dependency_injection(self):
        """Test dependency injection between beans."""

        class DependencyBean:
            pass

        class TestBean:
            def __init__(self, dependency: DependencyBean):
                self.dependency = dependency

        dep_def = BeanDefinition("dependency", DependencyBean)
        self.bean_factory.register_bean_definition(dep_def)

        bean_def = BeanDefinition("test_bean", TestBean, dependencies={"dependency": DependencyBean})
        self.bean_factory.register_bean_definition(bean_def)

        instance = self.bean_factory.get_bean("test_bean")
        self.assertIsInstance(instance.dependency, DependencyBean)

    def test_missing_dependency(self):
        """Test error handling when a dependency is missing."""

        class BeanA:
            pass

        class BeanB:
            def __init__(self, bean_a: BeanA):
                self.bean_a = bean_a

        bean_a_def = BeanDefinition("bean_a", BeanA, dependencies={"bean_b": BeanB})
        bean_b_def = BeanDefinition("bean_b", BeanB, dependencies={"bean_a": BeanA})

        self.bean_factory.register_bean_definition(bean_a_def)
        self.bean_factory.register_bean_definition(bean_b_def)

        with self.assertRaises(BeanCreationError):
            self.bean_factory.get_bean("bean_a")

    def test_bean_creation_error(self):
        """Test bean creation error handling."""

        class FailingBean:
            def __init__(self):
                raise ValueError("Initialization failed")

        bean_def = BeanDefinition("failing_bean", FailingBean)
        self.bean_factory.register_bean_definition(bean_def)

        with self.assertRaises(BeanCreationError):
            self.bean_factory.get_bean("failing_bean")
