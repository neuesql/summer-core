"""
Test configuration class processing functionality.

Verifies that the ConfigurationClassProcessor can discover and process
@Configuration classes and their @Bean methods.
"""

import unittest
import tempfile
import sys
from pathlib import Path


class TestConfigurationProcessing(unittest.TestCase):
    
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

    def test_configuration_class_processing(self):
        """Test that @Configuration classes and @Bean methods are processed correctly."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            
            # Create test package structure
            test_package_dir = Path(temp_dir) / "test_config"
            test_package_dir.mkdir()
            
            # Create __init__.py
            (test_package_dir / "__init__.py").write_text("")
            
            # Create configuration class
            config_content = '''
from summer_core import Configuration, Bean

class DatabaseService:
    def __init__(self, url: str):
        self.url = url
        self.connected = False
    
    def connect(self):
        self.connected = True
        return f"Connected to {self.url}"

class CacheService:
    def __init__(self, size: int = 100):
        self.size = size
        self.cache = {}
    
    def get(self, key):
        return self.cache.get(key)
    
    def put(self, key, value):
        self.cache[key] = value

@Configuration
class AppConfig:
    
    @Bean
    def database_service(self) -> DatabaseService:
        return DatabaseService("postgresql://localhost:5432/testdb")
    
    @Bean(name="cache", scope="singleton")
    def cache_service(self) -> CacheService:
        return CacheService(size=200)
    
    @Bean
    def dependent_service(self, database_service: DatabaseService) -> str:
        return f"Service using {database_service.url}"
'''
            
            (test_package_dir / "config.py").write_text(config_content)
            
            # Add temp directory to Python path
            sys.path.insert(0, temp_dir)
            
            try:
                from summer_core import DefaultApplicationContext
                from summer_core.container.configuration_processor import ConfigurationClassProcessor
                
                # Test ConfigurationClassProcessor directly
                processor = ConfigurationClassProcessor()
                bean_definitions = processor.process_configuration_classes(["test_config"])
                
                # Should find 3 bean definitions
                self.assertEqual(len(bean_definitions), 3)
                
                # Check bean names
                bean_names = {bd.bean_name for bd in bean_definitions}
                expected_names = {"database_service", "cache", "dependent_service"}
                self.assertEqual(bean_names, expected_names)
                
                # Check that factory methods are set
                for bean_def in bean_definitions:
                    self.assertIsNotNone(bean_def.factory_method)
                    self.assertIsNotNone(bean_def.factory_bean_name)
                
                # Test with ApplicationContext
                self.context = DefaultApplicationContext(base_packages=["test_config"])
                self.context.refresh()
                
                # Verify beans are registered and can be retrieved
                database_service = self.context.get_bean("database_service")
                self.assertEqual(database_service.url, "postgresql://localhost:5432/testdb")
                self.assertFalse(database_service.connected)
                
                cache_service = self.context.get_bean("cache")
                self.assertEqual(cache_service.size, 200)
                self.assertEqual(cache_service.cache, {})
                
                dependent_service = self.context.get_bean("dependent_service")
                self.assertEqual(dependent_service, "Service using postgresql://localhost:5432/testdb")
                
                # Test singleton behavior
                database_service2 = self.context.get_bean("database_service")
                self.assertIs(database_service, database_service2)
                
            finally:
                if temp_dir in sys.path:
                    sys.path.remove(temp_dir)

    def test_configuration_with_dependencies(self):
        """Test @Bean methods with dependencies."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            
            test_package_dir = Path(temp_dir) / "test_deps"
            test_package_dir.mkdir()
            
            (test_package_dir / "__init__.py").write_text("")
            
            deps_config_content = '''
from summer_core import Configuration, Bean

class Repository:
    def __init__(self, name: str):
        self.name = name

class Service:
    def __init__(self, repository: Repository):
        self.repository = repository

@Configuration
class DepsConfig:
    
    @Bean
    def user_repository(self) -> Repository:
        return Repository("UserRepository")
    
    @Bean
    def user_service(self, user_repository: Repository) -> Service:
        return Service(user_repository)
'''
            
            (test_package_dir / "deps_config.py").write_text(deps_config_content)
            
            sys.path.insert(0, temp_dir)
            
            try:
                from summer_core import DefaultApplicationContext
                
                self.context = DefaultApplicationContext(base_packages=["test_deps"])
                self.context.refresh()
                
                # Test that dependencies are properly injected
                user_service = self.context.get_bean("user_service")
                user_repository = self.context.get_bean("user_repository")
                
                self.assertIsNotNone(user_service.repository)
                self.assertEqual(user_service.repository.name, "UserRepository")
                self.assertIs(user_service.repository, user_repository)
                
            finally:
                if temp_dir in sys.path:
                    sys.path.remove(temp_dir)

    def test_mixed_component_and_configuration(self):
        """Test that both @Component and @Configuration work together."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            
            test_package_dir = Path(temp_dir) / "test_mixed"
            test_package_dir.mkdir()
            
            (test_package_dir / "__init__.py").write_text("")
            
            mixed_content = '''
from summer_core import Configuration, Bean, Service, Autowired

@Service
class ComponentService:
    def __init__(self):
        self.name = "component_service"

class ConfigBean:
    def __init__(self, value: str):
        self.value = value

@Configuration
class MixedConfig:
    
    @Bean
    def config_bean(self) -> ConfigBean:
        return ConfigBean("from_config")
    
    @Bean
    def mixed_service(self, component_service: ComponentService, config_bean: ConfigBean) -> str:
        return f"{component_service.name} + {config_bean.value}"
'''
            
            (test_package_dir / "mixed.py").write_text(mixed_content)
            
            sys.path.insert(0, temp_dir)
            
            try:
                from summer_core import DefaultApplicationContext
                
                self.context = DefaultApplicationContext(base_packages=["test_mixed"])
                self.context.refresh()
                
                # Should have both component and configuration beans
                component_service = self.context.get_bean("componentService")
                config_bean = self.context.get_bean("config_bean")
                mixed_service = self.context.get_bean("mixed_service")
                
                self.assertEqual(component_service.name, "component_service")
                self.assertEqual(config_bean.value, "from_config")
                self.assertEqual(mixed_service, "component_service + from_config")
                
            finally:
                if temp_dir in sys.path:
                    sys.path.remove(temp_dir)


if __name__ == '__main__':
    unittest.main()