# Testing Unit Patterns

## Core Testing Framework
- **Always use Python's built-in `unittest` library** instead of pytest or other testing frameworks
- Use `unittest.TestCase` as the base class for all test classes
- Use `unittest.main()` to run tests when script is executed directly
- Follow unittest naming conventions: test methods must start with `test_`

## Test Structure Patterns

### Basic Test Class Structure
```python
import unittest
from summer_core import Component, Service, ApplicationContext

class TestComponentScanning(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.context = None
    
    def tearDown(self):
        """Clean up after each test method."""
        if self.context:
            self.context.close()
    
    def test_component_discovery(self):
        """Test that components are discovered correctly."""
        # Test implementation
        self.assertTrue(condition)
        self.assertEqual(expected, actual)
        self.assertIsNotNone(value)

if __name__ == '__main__':
    unittest.main()
```

### Assertion Patterns
- Use `self.assertEqual(expected, actual)` for equality checks
- Use `self.assertTrue(condition)` and `self.assertFalse(condition)` for boolean checks
- Use `self.assertIsNone(value)` and `self.assertIsNotNone(value)` for None checks
- Use `self.assertIn(item, container)` for membership tests
- Use `self.assertRaises(ExceptionType)` for exception testing
- Use `self.assertIsInstance(obj, type)` for type checking

### Test Organization
- Group related tests in the same test class
- Use descriptive test method names that explain what is being tested
- Use setUp() and tearDown() methods for test fixtures
- Create separate test files for different modules/components

### Spring Framework Testing Patterns
```python
class TestSpringContainer(unittest.TestCase):
    
    def setUp(self):
        """Set up application context for testing."""
        self.context = DefaultApplicationContext(base_packages=["test_package"])
        self.context.refresh()
    
    def tearDown(self):
        """Clean up application context."""
        if self.context:
            self.context.close()
    
    def test_bean_registration(self):
        """Test that beans are registered correctly."""
        self.assertTrue(self.context.contains_bean("testService"))
        bean = self.context.get_bean("testService")
        self.assertIsNotNone(bean)
        self.assertIsInstance(bean, TestService)
    
    def test_dependency_injection(self):
        """Test that dependencies are injected correctly."""
        service = self.context.get_bean("dependentService")
        self.assertIsNotNone(service.dependency)
        self.assertIsInstance(service.dependency, TestService)
```

### Temporary Test Resources
- Use `tempfile.TemporaryDirectory()` for creating temporary test packages
- Clean up temporary resources in tearDown() or using context managers
- Add temporary paths to sys.path for testing, remove in cleanup

### Error Testing Patterns
```python
def test_exception_handling(self):
    """Test that appropriate exceptions are raised."""
    with self.assertRaises(NoSuchBeanDefinitionError):
        self.context.get_bean("nonexistent")
    
    with self.assertRaises(BeanCreationError) as cm:
        # Code that should raise BeanCreationError
        pass
    
    self.assertIn("expected error message", str(cm.exception))
```