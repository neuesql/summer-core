"""
Unit tests for basic project structure and core interfaces.

Verifies that the fundamental components of the Summer framework
are properly set up and can be imported and used.
"""

import unittest
from summer_core import (
    ApplicationContext, 
    DefaultApplicationContext,
    Component, 
    Service, 
    Repository, 
    Configuration,
    Autowired, 
    Bean, 
    Value, 
    Qualifier
)
from summer_core.container.bean_definition import BeanDefinition, BeanScope
from summer_core.exceptions import (
    SummerFrameworkError,
    BeanCreationError,
    NoSuchBeanDefinitionError
)


class TestBasicFramework(unittest.TestCase):
    """Test basic framework functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.context = None
    
    def tearDown(self):
        """Clean up after each test method."""
        if self.context:
            self.context.close()
    
    def test_imports(self):
        """Test that all core components can be imported."""
        # If we got here, imports worked (they're at module level)
        self.assertTrue(True)
    
    def test_component_decorators(self):
        """Test that component decorators work correctly."""
        @Component
        class TestComponent:
            pass
        
        @Service
        class TestService:
            pass
        
        @Repository
        class TestRepository:
            pass
        
        @Configuration
        class TestConfiguration:
            pass
        
        # Check that decorators add the expected metadata
        self.assertTrue(hasattr(TestComponent, '_summer_component'))
        self.assertTrue(TestComponent._summer_component)
        self.assertEqual(TestComponent._summer_component_type, "component")
        
        self.assertTrue(hasattr(TestService, '_summer_component'))
        self.assertEqual(TestService._summer_component_type, "service")
        
        self.assertTrue(hasattr(TestRepository, '_summer_component'))
        self.assertEqual(TestRepository._summer_component_type, "repository")
        
        self.assertTrue(hasattr(TestConfiguration, '_summer_configuration'))
        self.assertTrue(TestConfiguration._summer_configuration)
    
    def test_bean_definition(self):
        """Test BeanDefinition functionality."""
        class TestClass:
            pass
        
        bean_def = BeanDefinition(
            bean_name="testBean",
            bean_type=TestClass,
            scope=BeanScope.SINGLETON
        )
        
        self.assertEqual(bean_def.bean_name, "testBean")
        self.assertEqual(bean_def.bean_type, TestClass)
        self.assertTrue(bean_def.is_singleton())
        self.assertFalse(bean_def.is_prototype())
    
    def test_application_context_basic(self):
        """Test basic ApplicationContext functionality."""
        context = DefaultApplicationContext()
        
        # Test initial state
        self.assertFalse(context.is_active())
        self.assertEqual(len(context.get_bean_definition_names()), 0)
        
        # Test that we can refresh the context
        context.refresh()
        self.assertTrue(context.is_active())
        
        # Test that we can close the context
        context.close()
        self.assertFalse(context.is_active())
    
    def test_bean_factory_registration(self):
        """Test bean registration and retrieval."""
        class TestService:
            def __init__(self):
                self.name = "test_service"
        
        self.context = DefaultApplicationContext()
        self.context.refresh()
        
        # Create and register a bean definition
        bean_def = BeanDefinition(
            bean_name="testService",
            bean_type=TestService,
            scope=BeanScope.SINGLETON
        )
        
        self.context.register_bean_definition("testService", bean_def)
        
        # Test bean retrieval
        self.assertTrue(self.context.contains_bean("testService"))
        self.assertTrue(self.context.is_singleton("testService"))
        
        bean_instance = self.context.get_bean("testService")
        self.assertIsInstance(bean_instance, TestService)
        self.assertEqual(bean_instance.name, "test_service")
        
        # Test singleton behavior
        bean_instance2 = self.context.get_bean("testService")
        self.assertIs(bean_instance, bean_instance2)
    
    def test_exceptions(self):
        """Test that framework exceptions work correctly."""
        self.context = DefaultApplicationContext()
        self.context.refresh()
        
        # Test NoSuchBeanDefinitionError
        with self.assertRaises(NoSuchBeanDefinitionError) as cm:
            self.context.get_bean("nonexistent")
        
        self.assertIn("nonexistent", str(cm.exception))
        
        # Test that we can create other exception types
        bean_error = BeanCreationError("testBean", "Test error message")
        self.assertIn("testBean", str(bean_error))
        self.assertIn("Test error message", str(bean_error))
    
    def test_decorators(self):
        """Test that decorators add proper metadata."""
        class TestService:
            @Autowired
            def __init__(self, dependency: str):
                self.dependency = dependency
        
        # Check that the constructor is marked for autowiring
        self.assertTrue(hasattr(TestService.__init__, '_summer_autowired'))
        self.assertTrue(TestService.__init__._summer_autowired)
        
        @Configuration
        class TestConfig:
            @Bean
            def test_service(self) -> str:
                return "test_service_instance"
        
        # Check that the method is marked as a bean factory method
        self.assertTrue(hasattr(TestConfig.test_service, '_summer_bean_method'))
        self.assertTrue(TestConfig.test_service._summer_bean_method)
        self.assertEqual(TestConfig.test_service._summer_bean_name, "test_service")


if __name__ == '__main__':
    unittest.main()