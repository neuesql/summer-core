"""
Manual test for basic project structure and core interfaces.

Verifies that the fundamental components of the Summer framework
are properly set up and can be imported and used.
"""

def test_imports():
    """Test that all core components can be imported."""
    try:
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
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_component_decorators():
    """Test that component decorators work correctly."""
    try:
        from summer_core import Component, Service, Repository, Configuration
        
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
        
        print("✓ Component decorators working correctly")
        return True
    except Exception as e:
        print(f"✗ Component decorators failed: {e}")
        return False


def test_bean_definition():
    """Test BeanDefinition functionality."""
    try:
        from summer_core.container.bean_definition import BeanDefinition, BeanScope
        
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
        
        print("✓ BeanDefinition working correctly")
        return True
    except Exception as e:
        print(f"✗ BeanDefinition failed: {e}")
        return False


def test_application_context_basic():
    """Test basic ApplicationContext functionality."""
    try:
        from summer_core import DefaultApplicationContext
        
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
        
        print("✓ ApplicationContext basic functionality working")
        return True
    except Exception as e:
        print(f"✗ ApplicationContext failed: {e}")
        return False


def test_bean_factory_registration():
    """Test bean registration and retrieval."""
    try:
        from summer_core import DefaultApplicationContext
        from summer_core.container.bean_definition import BeanDefinition, BeanScope
        
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
        
        print("✓ Bean factory registration and retrieval working")
        return True
    except Exception as e:
        print(f"✗ Bean factory failed: {e}")
        return False


def test_exceptions():
    """Test that framework exceptions work correctly."""
    try:
        from summer_core import DefaultApplicationContext
        from summer_core.exceptions import NoSuchBeanDefinitionError, BeanCreationError
        
        context = DefaultApplicationContext()
        context.refresh()
        
        # Test NoSuchBeanDefinitionError
        try:
            context.get_bean("nonexistent")
            print("✗ Expected NoSuchBeanDefinitionError was not raised")
            return False
        except NoSuchBeanDefinitionError as e:
            assert "nonexistent" in str(e)
        
        # Test that we can create other exception types
        bean_error = BeanCreationError("testBean", "Test error message")
        assert "testBean" in str(bean_error)
        assert "Test error message" in str(bean_error)
        
        print("✓ Framework exceptions working correctly")
        return True
    except Exception as e:
        print(f"✗ Exception handling failed: {e}")
        return False


def test_decorators():
    """Test that decorators add proper metadata."""
    try:
        from summer_core import Autowired, Bean, Configuration
        
        class TestService:
            @Autowired
            def __init__(self, dependency: str):
                self.dependency = dependency
        
        # Check that the constructor is marked for autowiring
        assert hasattr(TestService.__init__, '_summer_autowired')
        assert TestService.__init__._summer_autowired is True
        
        @Configuration
        class TestConfig:
            @Bean
            def test_service(self) -> str:
                return "test_service_instance"
        
        # Check that the method is marked as a bean factory method
        assert hasattr(TestConfig.test_service, '_summer_bean_method')
        assert TestConfig.test_service._summer_bean_method is True
        assert TestConfig.test_service._summer_bean_name == "test_service"
        
        print("✓ Decorators working correctly")
        return True
    except Exception as e:
        print(f"✗ Decorators failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Running Summer Core Framework Tests...")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_component_decorators,
        test_bean_definition,
        test_application_context_basic,
        test_bean_factory_registration,
        test_exceptions,
        test_decorators
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Tests completed: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Task 1 completed successfully.")
        return True
    else:
        print("❌ Some tests failed.")
        return False


if __name__ == "__main__":
    main()