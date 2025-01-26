import unittest

from summer_core.bean_definition import BeanDefinition, BeanScope
from summer_core.bean_factory import BeanCreationError, BeanNotFoundError, CircularDependencyError, DefaultBeanFactory


class TestBeanFactory(unittest.TestCase):
    def setUp(self):
        """Set up a new BeanFactory instance for each test."""
        self.bean_factory = DefaultBeanFactory()

    def test_register_bean(self):
        """Test registering a bean definition."""

        class TestBean:
            pass

        bean_def = BeanDefinition("test_bean", TestBean)
        self.bean_factory.register_bean(bean_def)

        self.assertIn("test_bean", self.bean_factory._bean_definitions)

    def test_register_duplicate_bean(self):
        """Test registering a bean with a duplicate name raises ValueError."""

        class TestBean:
            pass

        bean_def = BeanDefinition("test_bean", TestBean)
        self.bean_factory.register_bean(bean_def)

        with self.assertRaises(ValueError):
            self.bean_factory.register_bean(bean_def)

    def test_get_nonexistent_bean(self):
        """Test getting a non-existent bean raises BeanNotFoundError."""
        with self.assertRaises(BeanNotFoundError):
            self.bean_factory.get_bean("nonexistent")

    def test_get_singleton_bean(self):
        """Test getting a singleton bean returns the same instance."""

        class TestBean:
            pass

        bean_def = BeanDefinition("test_bean", TestBean)
        self.bean_factory.register_bean(bean_def)

        instance1 = self.bean_factory.get_bean("test_bean")
        instance2 = self.bean_factory.get_bean("test_bean")

        self.assertIs(instance1, instance2)

    def test_get_prototype_bean(self):
        """Test getting a prototype bean returns different instances."""

        class TestBean:
            pass

        bean_def = BeanDefinition("test_bean", TestBean, scope=BeanScope.PROTOTYPE)
        self.bean_factory.register_bean(bean_def)

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
        self.bean_factory.register_bean(dep_def)

        bean_def = BeanDefinition("test_bean", TestBean, dependencies={"dependency": DependencyBean})
        self.bean_factory.register_bean(bean_def)

        instance = self.bean_factory.get_bean("test_bean")
        self.assertIsInstance(instance.dependency, DependencyBean)

    def test_circular_dependency(self):
        """Test circular dependency detection."""

        class BeanA:
            def __init__(self, bean_b: "BeanB"):
                self.bean_b = bean_b

        class BeanB:
            def __init__(self, bean_a: BeanA):
                self.bean_a = bean_a

        bean_a_def = BeanDefinition("bean_a", BeanA, dependencies={"bean_b": BeanB})
        bean_b_def = BeanDefinition("bean_b", BeanB, dependencies={"bean_a": BeanA})

        self.bean_factory.register_bean(bean_a_def)
        self.bean_factory.register_bean(bean_b_def)

        with self.assertRaises(CircularDependencyError):
            self.bean_factory.get_bean("bean_a")

    def test_bean_creation_error(self):
        """Test bean creation error handling."""

        class FailingBean:
            def __init__(self):
                raise ValueError("Initialization failed")

        bean_def = BeanDefinition("failing_bean", FailingBean)
        self.bean_factory.register_bean(bean_def)

        with self.assertRaises(BeanCreationError):
            self.bean_factory.get_bean("failing_bean")
