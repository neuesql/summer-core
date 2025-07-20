"""
Test component scanning functionality.

Verifies that the ComponentScanner can discover and register components
automatically from packages.
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path

class TestComponentScanning(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = None
        self.context = None
    
    def tearDown(self):
        """Clean up after each test method."""
        if self.context:
            self.context.close()
        # Clean up sys.path if we modified it
        if self.temp_dir and self.temp_dir in sys.path:
            sys.path.remove(self.temp_dir)

    def test_component_scanning(self):
        """Test that component scanning discovers and registers components."""
        
        # Create a temporary package for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            
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
                
                # Should find 4 components
                self.assertEqual(len(bean_definitions), 4, f"Expected 4 components, found {len(bean_definitions)}")
                
                # Check component names
                component_names = {bd.bean_name for bd in bean_definitions}
                expected_names = {"testService", "testComponent", "testRepository", "dependentService"}
                self.assertEqual(component_names, expected_names)
                
                # Test with ApplicationContext
                self.context = DefaultApplicationContext(base_packages=["test_components"])
                self.context.refresh()
                
                # Verify beans are registered
                bean_names = self.context.get_bean_definition_names()
                self.assertEqual(len(bean_names), 4)
                
                # Test bean retrieval
                test_service = self.context.get_bean("testService")
                self.assertEqual(test_service.name, "test_service")
                self.assertEqual(test_service.get_data(), "service_data")
                
                test_component = self.context.get_bean("testComponent")
                self.assertEqual(test_component.value, "component_value")
                
                test_repository = self.context.get_bean("testRepository")
                self.assertEqual(test_repository.data, [])
                test_repository.save("test_item")
                self.assertEqual(test_repository.data, ["test_item"])
                
                # Test dependency injection
                dependent_service = self.context.get_bean("dependentService")
                self.assertEqual(dependent_service.name, "dependent_service")
                self.assertIs(dependent_service.test_service, test_service)  # Should be same singleton instance
                
            finally:
                # Clean up
                if temp_dir in sys.path:
                    sys.path.remove(temp_dir)


    def test_component_scanning_with_lifecycle(self):
        """Test component scanning with lifecycle methods."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            
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
                
                self.assertEqual(len(bean_definitions), 1)
                bean_def = bean_definitions[0]
                
                # Check lifecycle methods are detected
                self.assertEqual(len(bean_def.post_construct_methods), 1)
                self.assertIn("init", bean_def.post_construct_methods)
                self.assertEqual(len(bean_def.pre_destroy_methods), 1)
                self.assertIn("cleanup", bean_def.pre_destroy_methods)
                
            finally:
                if temp_dir in sys.path:
                    sys.path.remove(temp_dir)


if __name__ == '__main__':
    unittest.main()