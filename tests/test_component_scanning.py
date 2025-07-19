"""
Test component scanning functionality.

Verifies that the ComponentScanner can discover and register components
automatically from packages.
"""

import tempfile
import os
import sys
from pathlib import Path

def test_component_scanning():
    """Test that component scanning discovers and registers components."""
    
    # Create a temporary package for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test package structure
        test_package_dir = Path(temp_dir) / "test_components"
        test_package_dir.mkdir()
        
        # Create __init__.py
        (test_package_dir / "__init__.py").write_text("")
        
        # Create test components
        test_service_content = '''
from summer_core import Service, Component, Repository, Autowired

@Service
class TestService:
    def __init__(self):
        self.name = "test_service"
    
    def get_data(self):
        return "service_data"

@Component
class TestComponent:
    def __init__(self):
        self.value = "component_value"

@Repository  
class TestRepository:
    def __init__(self):
        self.data = []
    
    def save(self, item):
        self.data.append(item)
        return item

@Service
class DependentService:
    @Autowired
    def __init__(self, test_service: TestService):
        self.test_service = test_service
        self.name = "dependent_service"
'''
        
        (test_package_dir / "services.py").write_text(test_service_content)
        
        # Add temp directory to Python path
        sys.path.insert(0, temp_dir)
        
        try:
            from summer_core import DefaultApplicationContext
            from summer_core.container.component_scanner import ComponentScanner
            
            # Test ComponentScanner directly
            scanner = ComponentScanner()
            bean_definitions = scanner.scan_packages(["test_components"])
            
            print(f"Found {len(bean_definitions)} components:")
            for bean_def in bean_definitions:
                print(f"  - {bean_def.bean_name} ({bean_def.bean_type.__name__})")
            
            # Should find 4 components
            assert len(bean_definitions) == 4, f"Expected 4 components, found {len(bean_definitions)}"
            
            # Check component names
            component_names = {bd.bean_name for bd in bean_definitions}
            expected_names = {"testService", "testComponent", "testRepository", "dependentService"}
            assert component_names == expected_names, f"Expected {expected_names}, got {component_names}"
            
            # Test with ApplicationContext
            context = DefaultApplicationContext(base_packages=["test_components"])
            context.refresh()
            
            # Verify beans are registered
            bean_names = context.get_bean_definition_names()
            print(f"Registered beans: {bean_names}")
            assert len(bean_names) == 4, f"Expected 4 registered beans, got {len(bean_names)}"
            
            # Test bean retrieval
            test_service = context.get_bean("testService")
            assert test_service.name == "test_service"
            assert test_service.get_data() == "service_data"
            
            test_component = context.get_bean("testComponent")
            assert test_component.value == "component_value"
            
            test_repository = context.get_bean("testRepository")
            assert test_repository.data == []
            test_repository.save("test_item")
            assert test_repository.data == ["test_item"]
            
            # Test dependency injection
            dependent_service = context.get_bean("dependentService")
            assert dependent_service.name == "dependent_service"
            assert dependent_service.test_service is test_service  # Should be same singleton instance
            
            print("✓ Component scanning working correctly")
            return True
            
        except Exception as e:
            print(f"✗ Component scanning failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Clean up
            sys.path.remove(temp_dir)


def test_component_scanning_with_lifecycle():
    """Test component scanning with lifecycle methods."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_package_dir = Path(temp_dir) / "lifecycle_components"
        test_package_dir.mkdir()
        
        (test_package_dir / "__init__.py").write_text("")
        
        lifecycle_content = '''
from summer_core import Service
from summer_core.decorators.autowired import PostConstruct, PreDestroy

@Service
class LifecycleService:
    def __init__(self):
        self.initialized = False
        self.destroyed = False
    
    @PostConstruct
    def init(self):
        self.initialized = True
    
    @PreDestroy
    def cleanup(self):
        self.destroyed = True
'''
        
        (test_package_dir / "lifecycle.py").write_text(lifecycle_content)
        
        sys.path.insert(0, temp_dir)
        
        try:
            from summer_core.container.component_scanner import ComponentScanner
            
            scanner = ComponentScanner()
            bean_definitions = scanner.scan_packages(["lifecycle_components"])
            
            assert len(bean_definitions) == 1
            bean_def = bean_definitions[0]
            
            # Check lifecycle methods are detected
            assert len(bean_def.post_construct_methods) == 1
            assert "init" in bean_def.post_construct_methods
            assert len(bean_def.pre_destroy_methods) == 1
            assert "cleanup" in bean_def.pre_destroy_methods
            
            print("✓ Lifecycle method detection working correctly")
            return True
            
        except Exception as e:
            print(f"✗ Lifecycle method detection failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            sys.path.remove(temp_dir)


def main():
    """Run component scanning tests."""
    print("Running Component Scanning Tests...")
    print("=" * 50)
    
    tests = [
        test_component_scanning,
        test_component_scanning_with_lifecycle
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
        print("🎉 All component scanning tests passed!")
        return True
    else:
        print("❌ Some tests failed.")
        return False


if __name__ == "__main__":
    main()