import unittest

from summer_core.bean_definition import BeanDefinition, BeanScope


class TestBeanDefinition(unittest.TestCase):
    def test_init_with_defaults(self):
        """Test BeanDefinition initialization with default values."""

        class TestBean:
            pass

        bean_def = BeanDefinition("test_bean", TestBean)

        self.assertEqual(bean_def.name, "test_bean")
        self.assertEqual(bean_def.bean_class, TestBean)
        self.assertEqual(bean_def.scope, BeanScope.SINGLETON)
        self.assertEqual(bean_def.dependencies, {})

    def test_init_with_custom_values(self):
        """Test BeanDefinition initialization with custom values."""

        class TestBean:
            pass

        class DependencyBean:
            pass

        dependencies = {"dep1": DependencyBean}
        bean_def = BeanDefinition(
            name="test_bean", bean_class=TestBean, scope=BeanScope.PROTOTYPE, dependencies=dependencies
        )

        self.assertEqual(bean_def.name, "test_bean")
        self.assertEqual(bean_def.bean_class, TestBean)
        self.assertEqual(bean_def.scope, BeanScope.PROTOTYPE)
        self.assertEqual(bean_def.dependencies, dependencies)
