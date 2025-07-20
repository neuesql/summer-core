"""
Test lifecycle interface functionality.

Verifies that InitializingBean and DisposableBean interfaces work correctly
and are properly integrated with the container lifecycle.
"""

import unittest
import tempfile
import sys
from pathlib import Path


class TestLifecycleInterfaces(unittest.TestCase):
    
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

    def test_initializing_bean_interface(self):
        """Test that InitializingBean interface methods are called."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            
            # Create test package structure
            test_package_dir = Path(temp_dir) / "test_initializing"
            test_package_dir.mkdir()
            
            # Create __init__.py
            (test_package_dir / "__init__.py").write_text("")
            
            # Create service implementing InitializingBean
            initializing_content = '''
from summer_core import Service, InitializingBean

@Service
class InitializingService(InitializingBean):
    def __init__(self):
        self.initialized = False
        self.init_count = 0
    
    def after_properties_set(self):
        self.initialized = True
        self.init_count += 1
    
    def get_status(self):
        return f"Initialized: {self.initialized}, Count: {self.init_count}"
'''
            
            (test_package_dir / "services.py").write_text(initializing_content)
            
            # Add temp directory to Python path
            sys.path.insert(0, temp_dir)
            
            try:
                from summer_core import DefaultApplicationContext
                
                self.context = DefaultApplicationContext(base_packages=["test_initializing"])
                self.context.refresh()
                
                # Get the service - after_properties_set should have been called
                service = self.context.get_bean("initializingService")
                self.assertTrue(service.initialized)
                self.assertEqual(service.init_count, 1)
                
            finally:
                if temp_dir in sys.path:
                    sys.path.remove(temp_dir)

    def test_disposable_bean_interface(self):
        """Test that DisposableBean interface methods are called."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            
            # Create test package structure
            test_package_dir = Path(temp_dir) / "test_disposable"
            test_package_dir.mkdir()
            
            # Create __init__.py
            (test_package_dir / "__init__.py").write_text("")
            
            # Create service implementing DisposableBean
            disposable_content = '''
from summer_core import Service, DisposableBean

@Service
class DisposableService(DisposableBean):
    def __init__(self):
        self.destroyed = False
        self.destroy_count = 0
    
    def destroy(self):
        self.destroyed = True
        self.destroy_count += 1
    
    def get_status(self):
        return f"Destroyed: {self.destroyed}, Count: {self.destroy_count}"
'''
            
            (test_package_dir / "services.py").write_text(disposable_content)
            
            # Add temp directory to Python path
            sys.path.insert(0, temp_dir)
            
            try:
                from summer_core import DefaultApplicationContext
                
                self.context = DefaultApplicationContext(base_packages=["test_disposable"])
                self.context.refresh()
                
                # Get the service
                service = self.context.get_bean("disposableService")
                self.assertFalse(service.destroyed)
                self.assertEqual(service.destroy_count, 0)
                
                # Close context - destroy should be called
                self.context.close()
                
                # Check that destroy method was called
                self.assertTrue(service.destroyed)
                self.assertEqual(service.destroy_count, 1)
                
                # Set context to None so tearDown doesn't try to close it again
                self.context = None
                
            finally:
                if temp_dir in sys.path:
                    sys.path.remove(temp_dir)

    def test_both_interfaces_combined(self):
        """Test service implementing both InitializingBean and DisposableBean."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            
            # Create test package structure
            test_package_dir = Path(temp_dir) / "test_combined"
            test_package_dir.mkdir()
            
            # Create __init__.py
            (test_package_dir / "__init__.py").write_text("")
            
            # Create service implementing both interfaces
            combined_content = '''
from summer_core import Service, InitializingBean, DisposableBean

@Service
class CombinedService(InitializingBean, DisposableBean):
    def __init__(self):
        self.initialized = False
        self.destroyed = False
        self.init_count = 0
        self.destroy_count = 0
    
    def after_properties_set(self):
        self.initialized = True
        self.init_count += 1
    
    def destroy(self):
        self.destroyed = True
        self.destroy_count += 1
    
    def get_status(self):
        return f"Init: {self.initialized}({self.init_count}), Destroy: {self.destroyed}({self.destroy_count})"
'''
            
            (test_package_dir / "services.py").write_text(combined_content)
            
            # Add temp directory to Python path
            sys.path.insert(0, temp_dir)
            
            try:
                from summer_core import DefaultApplicationContext
                
                self.context = DefaultApplicationContext(base_packages=["test_combined"])
                self.context.refresh()
                
                # Get the service
                service = self.context.get_bean("combinedService")
                
                # Check initialization
                self.assertTrue(service.initialized)
                self.assertEqual(service.init_count, 1)
                self.assertFalse(service.destroyed)
                self.assertEqual(service.destroy_count, 0)
                
                # Close context
                self.context.close()
                
                # Check destruction
                self.assertTrue(service.destroyed)
                self.assertEqual(service.destroy_count, 1)
                
                self.context = None
                
            finally:
                if temp_dir in sys.path:
                    sys.path.remove(temp_dir)

    def test_interfaces_with_decorators(self):
        """Test that interfaces work alongside @PostConstruct and @PreDestroy decorators."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            
            # Create test package structure
            test_package_dir = Path(temp_dir) / "test_mixed"
            test_package_dir.mkdir()
            
            # Create __init__.py
            (test_package_dir / "__init__.py").write_text("")
            
            # Create service with both interfaces and decorators
            mixed_content = '''
from summer_core import Service, InitializingBean, DisposableBean, PostConstruct, PreDestroy

@Service
class MixedLifecycleService(InitializingBean, DisposableBean):
    def __init__(self):
        self.post_construct_called = False
        self.after_properties_set_called = False
        self.pre_destroy_called = False
        self.destroy_called = False
        self.call_order = []
    
    @PostConstruct
    def post_construct_method(self):
        self.post_construct_called = True
        self.call_order.append("post_construct")
    
    def after_properties_set(self):
        self.after_properties_set_called = True
        self.call_order.append("after_properties_set")
    
    @PreDestroy
    def pre_destroy_method(self):
        self.pre_destroy_called = True
        self.call_order.append("pre_destroy")
    
    def destroy(self):
        self.destroy_called = True
        self.call_order.append("destroy")
'''
            
            (test_package_dir / "services.py").write_text(mixed_content)
            
            # Add temp directory to Python path
            sys.path.insert(0, temp_dir)
            
            try:
                from summer_core import DefaultApplicationContext
                
                self.context = DefaultApplicationContext(base_packages=["test_mixed"])
                self.context.refresh()
                
                # Get the service
                service = self.context.get_bean("mixedLifecycleService")
                
                # Check that both initialization methods were called
                self.assertTrue(service.post_construct_called)
                self.assertTrue(service.after_properties_set_called)
                self.assertFalse(service.pre_destroy_called)
                self.assertFalse(service.destroy_called)
                
                # Verify both initialization methods were called
                self.assertIn("post_construct", service.call_order)
                self.assertIn("after_properties_set", service.call_order)
                
                # Close context
                self.context.close()
                
                # Check that both destruction methods were called
                self.assertTrue(service.pre_destroy_called)
                self.assertTrue(service.destroy_called)
                self.assertIn("pre_destroy", service.call_order)
                self.assertIn("destroy", service.call_order)
                
                self.context = None
                
            finally:
                if temp_dir in sys.path:
                    sys.path.remove(temp_dir)

    def test_interface_with_dependencies(self):
        """Test that interface methods can use injected dependencies."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            
            # Create test package structure
            test_package_dir = Path(temp_dir) / "test_deps_interface"
            test_package_dir.mkdir()
            
            # Create __init__.py
            (test_package_dir / "__init__.py").write_text("")
            
            # Create services with dependency injection
            deps_interface_content = '''
from summer_core import Service, Autowired, InitializingBean, DisposableBean

@Service
class ConfigService:
    def __init__(self):
        self.config_loaded = False
    
    def load_config(self):
        self.config_loaded = True
        return {"database_url": "test://localhost"}
    
    def unload_config(self):
        self.config_loaded = False

@Service
class DatabaseService(InitializingBean, DisposableBean):
    @Autowired
    def __init__(self, config_service: ConfigService):
        self.config_service = config_service
        self.connected = False
        self.config = None
    
    def after_properties_set(self):
        # Use injected dependency in initialization
        self.config = self.config_service.load_config()
        self.connected = True
    
    def destroy(self):
        # Use injected dependency in cleanup
        self.config_service.unload_config()
        self.connected = False
        self.config = None
'''
            
            (test_package_dir / "services.py").write_text(deps_interface_content)
            
            # Add temp directory to Python path
            sys.path.insert(0, temp_dir)
            
            try:
                from summer_core import DefaultApplicationContext
                
                self.context = DefaultApplicationContext(base_packages=["test_deps_interface"])
                self.context.refresh()
                
                # Get services
                database_service = self.context.get_bean("databaseService")
                config_service = self.context.get_bean("configService")
                
                # Check that dependency injection happened before after_properties_set
                self.assertIsNotNone(database_service.config_service)
                self.assertIs(database_service.config_service, config_service)
                
                # Check that after_properties_set used the injected dependency
                self.assertTrue(database_service.connected)
                self.assertIsNotNone(database_service.config)
                self.assertTrue(config_service.config_loaded)
                
                # Close context
                self.context.close()
                
                # Check that destroy method used the injected dependency
                self.assertFalse(database_service.connected)
                self.assertIsNone(database_service.config)
                self.assertFalse(config_service.config_loaded)
                
                self.context = None
                
            finally:
                if temp_dir in sys.path:
                    sys.path.remove(temp_dir)


if __name__ == '__main__':
    unittest.main()