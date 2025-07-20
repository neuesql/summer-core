"""
Test lifecycle callback functionality.

Verifies that @PostConstruct and @PreDestroy methods are executed
at the appropriate times during bean lifecycle.
"""

import unittest
import tempfile
import sys
from pathlib import Path


class TestLifecycleCallbacks(unittest.TestCase):
    
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

    def test_post_construct_lifecycle(self):
        """Test that @PostConstruct methods are called after bean creation."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            
            # Create test package structure
            test_package_dir = Path(temp_dir) / "test_lifecycle"
            test_package_dir.mkdir()
            
            # Create __init__.py
            (test_package_dir / "__init__.py").write_text("")
            
            # Create service with lifecycle methods
            lifecycle_content = '''
from summer_core import Service, PostConstruct, PreDestroy

@Service
class LifecycleService:
    def __init__(self):
        self.initialized = False
        self.destroyed = False
        self.init_count = 0
        self.destroy_count = 0
    
    @PostConstruct
    def initialize(self):
        self.initialized = True
        self.init_count += 1
    
    @PreDestroy
    def cleanup(self):
        self.destroyed = True
        self.destroy_count += 1

@Service
class MultipleLifecycleService:
    def __init__(self):
        self.step1_done = False
        self.step2_done = False
        self.cleanup1_done = False
        self.cleanup2_done = False
    
    @PostConstruct
    def init_step1(self):
        self.step1_done = True
    
    @PostConstruct
    def init_step2(self):
        self.step2_done = True
    
    @PreDestroy
    def cleanup_step1(self):
        self.cleanup1_done = True
    
    @PreDestroy
    def cleanup_step2(self):
        self.cleanup2_done = True
'''
            
            (test_package_dir / "services.py").write_text(lifecycle_content)
            
            # Add temp directory to Python path
            sys.path.insert(0, temp_dir)
            
            try:
                from summer_core import DefaultApplicationContext
                
                self.context = DefaultApplicationContext(base_packages=["test_lifecycle"])
                self.context.refresh()
                
                # Get the service - @PostConstruct should have been called
                service = self.context.get_bean("lifecycleService")
                self.assertTrue(service.initialized)
                self.assertEqual(service.init_count, 1)
                self.assertFalse(service.destroyed)
                self.assertEqual(service.destroy_count, 0)
                
                # Test multiple lifecycle methods
                multi_service = self.context.get_bean("multipleLifecycleService")
                self.assertTrue(multi_service.step1_done)
                self.assertTrue(multi_service.step2_done)
                self.assertFalse(multi_service.cleanup1_done)
                self.assertFalse(multi_service.cleanup2_done)
                
                # Close context - @PreDestroy should be called
                self.context.close()
                
                # Check that @PreDestroy methods were called
                self.assertTrue(service.destroyed)
                self.assertEqual(service.destroy_count, 1)
                self.assertTrue(multi_service.cleanup1_done)
                self.assertTrue(multi_service.cleanup2_done)
                
                # Set context to None so tearDown doesn't try to close it again
                self.context = None
                
            finally:
                if temp_dir in sys.path:
                    sys.path.remove(temp_dir)

    def test_lifecycle_with_dependencies(self):
        """Test lifecycle methods work correctly with dependency injection."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            
            test_package_dir = Path(temp_dir) / "test_deps_lifecycle"
            test_package_dir.mkdir()
            
            (test_package_dir / "__init__.py").write_text("")
            
            deps_lifecycle_content = '''
from summer_core import Service, Autowired, PostConstruct, PreDestroy

@Service
class DatabaseService:
    def __init__(self):
        self.connected = False
    
    def connect(self):
        self.connected = True
    
    def disconnect(self):
        self.connected = False

@Service
class UserService:
    @Autowired
    def __init__(self, database_service: DatabaseService):
        self.database_service = database_service
        self.ready = False
    
    @PostConstruct
    def initialize(self):
        # Use injected dependency in post-construct
        self.database_service.connect()
        self.ready = True
    
    @PreDestroy
    def cleanup(self):
        # Clean up using injected dependency
        self.database_service.disconnect()
        self.ready = False
'''
            
            (test_package_dir / "deps_services.py").write_text(deps_lifecycle_content)
            
            sys.path.insert(0, temp_dir)
            
            try:
                from summer_core import DefaultApplicationContext
                
                self.context = DefaultApplicationContext(base_packages=["test_deps_lifecycle"])
                self.context.refresh()
                
                # Get services
                user_service = self.context.get_bean("userService")
                database_service = self.context.get_bean("databaseService")
                
                # Check that dependency injection happened before @PostConstruct
                self.assertIsNotNone(user_service.database_service)
                self.assertIs(user_service.database_service, database_service)
                
                # Check that @PostConstruct was called and used the injected dependency
                self.assertTrue(user_service.ready)
                self.assertTrue(database_service.connected)
                
                # Close context
                self.context.close()
                
                # Check that @PreDestroy was called
                self.assertFalse(user_service.ready)
                self.assertFalse(database_service.connected)
                
                self.context = None
                
            finally:
                if temp_dir in sys.path:
                    sys.path.remove(temp_dir)

    def test_lifecycle_with_configuration_beans(self):
        """Test lifecycle methods work with @Configuration @Bean methods."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            
            test_package_dir = Path(temp_dir) / "test_config_lifecycle"
            test_package_dir.mkdir()
            
            (test_package_dir / "__init__.py").write_text("")
            
            config_lifecycle_content = '''
from summer_core import Configuration, Bean, PostConstruct, PreDestroy

class ConfiguredService:
    def __init__(self, name: str):
        self.name = name
        self.initialized = False
        self.destroyed = False
    
    @PostConstruct
    def init(self):
        self.initialized = True
    
    @PreDestroy
    def cleanup(self):
        self.destroyed = True

@Configuration
class ServiceConfig:
    
    @Bean
    def configured_service(self) -> ConfiguredService:
        return ConfiguredService("test_service")
'''
            
            (test_package_dir / "config_lifecycle.py").write_text(config_lifecycle_content)
            
            sys.path.insert(0, temp_dir)
            
            try:
                from summer_core import DefaultApplicationContext
                
                self.context = DefaultApplicationContext(base_packages=["test_config_lifecycle"])
                self.context.refresh()
                
                # Get the configured service
                service = self.context.get_bean("configured_service")
                
                # Check that @PostConstruct was called
                self.assertEqual(service.name, "test_service")
                self.assertTrue(service.initialized)
                self.assertFalse(service.destroyed)
                
                # Close context
                self.context.close()
                
                # Check that @PreDestroy was called
                self.assertTrue(service.destroyed)
                
                self.context = None
                
            finally:
                if temp_dir in sys.path:
                    sys.path.remove(temp_dir)


if __name__ == '__main__':
    unittest.main()