"""
Test basic project structure and core interfaces.

Verifies that the fundamental components of the Summer framework
are properly set up and can be imported and used.
"""

import pytest
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


def test_imports():
    """Test that all core components can be imported."""
    # This test passes if imports work without errors
    assert ApplicationContext is not None
    assert DefaultApplicationContext is not None
    assert Component is not None
    assert Service is not None
    assert Repository is not None
    assert Configuration is not None
    assert Autowired is not None
    assert Bean is not None
    assert Value is not None
    assert Qualifier is not None


def test_component_decorators():
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
    assert hasattr(TestComponent, '_summer_component')
    assert TestComponent._summer_component is True
    assert TestComponent._summer_component_type == "component"
    
    assert hasattr(TestService, '_summer_component')
    assert TestService._summer_component_type == "service"
    
    assert hasattr(TestRepository, '_summer_component')
    assert TestRepository._summer_component_type == "repository"
    
    assert hasattr(TestConfiguration, '_summer_configuration')
    assert TestConfiguration._summer_configuration is True


def test_bean_definition():
    """Test BeanDefinition functionality."""
    
    class TestClass:
        pass
    
    bean_def = BeanDefinition(
        bean_name="testBean",
        bean_type=TestClass,
        scope=BeanScope.SINGLETON
    )
    
    assert bean_def.bean_name == "testBean"
    assert bean_def.bean_type == TestClass
    assert bean_def.is_singleton() is True
    assert bean_def.is_prototype() is False


def test_application_context_basic():
    """Test basic ApplicationContext functionality."""
    
    context = DefaultApplicationContext()
    
    # Test initial state
    assert context.is_active() is False
    assert len(context.get_bean_definition_names()) == 0
    
    # Test that we can refresh the context
    context.refresh()
    assert context.is_active() is True
    
    # Test that we can close the context
    context.close()
    assert context.is_active() is False


def test_bean_factory_registration():
    """Test bean registration and retrieval."""
    
    class TestService:
        def __init__(self):
            self.name = "test_service"
    
    context = DefaultApplicationContext()
    context.refresh()
    
    # Create and register a bean definition
    bean_def = BeanDefinition(
        bean_name="testService",
        bean_type=TestService,
        scope=BeanScope.SINGLETON
    )
    
    context.register_bean_definition("testService", bean_def)
    
    # Test bean retrieval
    assert context.contains_bean("testService") is True
    assert context.is_singleton("testService") is True
    
    bean_instance = context.get_bean("testService")
    assert isinstance(bean_instance, TestService)
    assert bean_instance.name == "test_service"
    
    # Test singleton behavior
    bean_instance2 = context.get_bean("testService")
    assert bean_instance is bean_instance2


def test_exceptions():
    """Test that framework exceptions work correctly."""
    
    context = DefaultApplicationContext()
    context.refresh()
    
    # Test NoSuchBeanDefinitionError
    with pytest.raises(NoSuchBeanDefinitionError) as exc_info:
        context.get_bean("nonexistent")
    
    assert "nonexistent" in str(exc_info.value)
    
    # Test that we can create other exception types
    bean_error = BeanCreationError("testBean", "Test error message")
    assert "testBean" in str(bean_error)
    assert "Test error message" in str(bean_error)


def test_autowired_decorator():
    """Test that @Autowired decorator adds metadata."""
    
    class TestService:
        @Autowired
        def __init__(self, dependency: str):
            self.dependency = dependency
    
    # Check that the constructor is marked for autowiring
    assert hasattr(TestService.__init__, '_summer_autowired')
    assert TestService.__init__._summer_autowired is True


def test_bean_decorator():
    """Test that @Bean decorator adds metadata."""
    
    @Configuration
    class TestConfig:
        @Bean
        def test_service(self) -> str:
            return "test_service_instance"
    
    # Check that the method is marked as a bean factory method
    assert hasattr(TestConfig.test_service, '_summer_bean_method')
    assert TestConfig.test_service._summer_bean_method is True
    assert TestConfig.test_service._summer_bean_name == "test_service"


if __name__ == "__main__":
    pytest.main([__file__])