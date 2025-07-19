"""
Test configuration class processing functionality.

Verifies that @Configuration classes and @Bean methods are processed correctly
and integrated with the application context.
"""

import unittest
import tempfile
import sys
from pathlib import Path


class TestConfigurationProcessing(unittest.TestCase):
    """Test cases for configuration class processing functionality."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dirs = []
        self.context = None

    def tearDown(self):
        """Clean up after each test method."""
        if self.context:
            self.context.close()
        
        # Clean up sys.path
        for temp_dir in self.temp_dirs:
            if temp_dir in sys.path:
                sys.path.remove(temp_dir)

    def test_configuration_class_discovery(self):
        """Test that @Configuration classes are discovered and processed."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dirs.append(temp_dir)
            
            # Create test package structure
            test_package_dir = Path(temp_dir) / "config_test"
            test_package_dir.mkdir()
            
            (test_package_dir / "__init__.py").write_text("")
            
            # Create configuration class
            config_content = '''
from summer_core import Configuration, Bean

@Configuration
class AppConfig:
    @Bean
    def message_service(self) -> str:
        return "Hello from MessageService"
    
    @Bean
    def number_service(self) -> int:
        return 42
'''
            
            (test_package_dir / "config.py").write_text(config_content)
            
            sys.path.insert(0, temp_dir)
            
            from summer_core import DefaultApplicationContext
            
            # Test with ApplicationContext (which includes configuration processing)
            self.context = DefaultApplicationContext(base_packages=["config_test"])
            self.context.refresh()
            
            # Should find configuration class + 2 @Bean methods = 3 total
            bean_names = set(self.context.get_bean_definition_names())
            expected_names = {"appConfig", "message_service", "number_service"}
            self.assertEqual(bean_names, expected_names)
            
            # Test that @Bean methods work
            message_service = self.context.get_bean("message_service")
            self.assertEqual(message_service, "Hello from MessageService")
            
            number_service = self.context.get_bean("number_service")
            self.assertEqual(number_service, 42)

    def test_configuration_integration_with_context(self):
        """Test that configuration processing integrates with ApplicationContext."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dirs.append(temp_dir)
            
            test_package_dir = Path(temp_dir) / "integration_config"
            test_package_dir.mkdir()
            
            (test_package_dir / "__init__.py").write_text("")
            
            config_content = '''
from summer_core import Configuration, Bean

class DatabaseService:
    def __init__(self, url: str):
        self.url = url
    
    def connect(self):
        return f"Connected to {self.url}"

@Configuration
class DatabaseConfig:
    @Bean
    def database_service(self) -> DatabaseService:
        return DatabaseService("postgresql://localhost:5432/testdb")
    
    @Bean
    def connection_pool_size(self) -> int:
        return 10
'''
            
            (test_package_dir / "database_config.py").write_text(config_content)
            
            sys.path.insert(0, temp_dir)
            
            from summer_core import DefaultApplicationContext
            
            # Test with ApplicationContext
            self.context = DefaultApplicationContext(base_packages=["integration_config"])
            self.context.refresh()
            
            # Verify beans are registered
            bean_names = self.context.get_bean_definition_names()
            self.assertIn("databaseConfig", bean_names)
            self.assertIn("database_service", bean_names)
            self.assertIn("connection_pool_size", bean_names)
            
            # Test bean retrieval and functionality
            database_service = self.context.get_bean("database_service")
            self.assertIsNotNone(database_service)
            self.assertEqual(database_service.url, "postgresql://localhost:5432/testdb")
            self.assertEqual(database_service.connect(), "Connected to postgresql://localhost:5432/testdb")
            
            pool_size = self.context.get_bean("connection_pool_size")
            self.assertEqual(pool_size, 10)

    def test_bean_method_dependencies(self):
        """Test that @Bean methods can have dependencies injected."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dirs.append(temp_dir)
            
            test_package_dir = Path(temp_dir) / "dependency_config"
            test_package_dir.mkdir()
            
            (test_package_dir / "__init__.py").write_text("")
            
            config_content = '''
from summer_core import Configuration, Bean, Service

@Service
class LoggingService:
    def __init__(self):
        self.logs = []
    
    def log(self, message: str):
        self.logs.append(message)
        return f"Logged: {message}"

class EmailService:
    def __init__(self, logger):
        self.logger = logger
    
    def send_email(self, message: str):
        self.logger.log(f"Sending email: {message}")
        return f"Email sent: {message}"

@Configuration
class ServiceConfig:
    @Bean
    def email_service(self, logging_service: LoggingService) -> EmailService:
        return EmailService(logging_service)
'''
            
            (test_package_dir / "service_config.py").write_text(config_content)
            
            sys.path.insert(0, temp_dir)
            
            from summer_core import DefaultApplicationContext
            
            self.context = DefaultApplicationContext(base_packages=["dependency_config"])
            self.context.refresh()
            
            # Test dependency injection in @Bean methods
            email_service = self.context.get_bean("email_service")
            logging_service = self.context.get_bean("loggingService")
            
            self.assertIsNotNone(email_service)
            self.assertIsNotNone(logging_service)
            self.assertIs(email_service.logger, logging_service)  # Should be same instance
            
            # Test functionality
            result = email_service.send_email("Test message")
            self.assertEqual(result, "Email sent: Test message")
            self.assertIn("Sending email: Test message", logging_service.logs)

    def test_configuration_with_custom_bean_names(self):
        """Test @Bean methods with custom names and scopes."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dirs.append(temp_dir)
            
            test_package_dir = Path(temp_dir) / "custom_config"
            test_package_dir.mkdir()
            
            (test_package_dir / "__init__.py").write_text("")
            
            config_content = '''
from summer_core import Configuration, Bean

class CacheService:
    def __init__(self, name: str):
        self.name = name
        self.data = {}
    
    def get(self, key: str):
        return self.data.get(key)
    
    def put(self, key: str, value):
        self.data[key] = value

@Configuration
class CacheConfig:
    @Bean(name="primaryCache", scope="singleton")
    def primary_cache_service(self) -> CacheService:
        return CacheService("primary")
    
    @Bean(name="secondaryCache", scope="prototype")
    def secondary_cache_service(self) -> CacheService:
        return CacheService("secondary")
'''
            
            (test_package_dir / "cache_config.py").write_text(config_content)
            
            sys.path.insert(0, temp_dir)
            
            from summer_core import DefaultApplicationContext
            
            self.context = DefaultApplicationContext(base_packages=["custom_config"])
            self.context.refresh()
            
            # Test custom bean names
            self.assertTrue(self.context.contains_bean("primaryCache"))
            self.assertTrue(self.context.contains_bean("secondaryCache"))
            
            primary_cache = self.context.get_bean("primaryCache")
            self.assertEqual(primary_cache.name, "primary")
            
            secondary_cache = self.context.get_bean("secondaryCache")
            self.assertEqual(secondary_cache.name, "secondary")
            
            # Test singleton vs prototype behavior
            primary_cache2 = self.context.get_bean("primaryCache")
            self.assertIs(primary_cache, primary_cache2)  # Singleton
            
            secondary_cache2 = self.context.get_bean("secondaryCache")
            self.assertIsNot(secondary_cache, secondary_cache2)  # Prototype

    def test_mixed_components_and_configuration(self):
        """Test that regular components and configuration classes work together."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dirs.append(temp_dir)
            
            test_package_dir = Path(temp_dir) / "mixed_config"
            test_package_dir.mkdir()
            
            (test_package_dir / "__init__.py").write_text("")
            
            mixed_content = '''
from summer_core import Configuration, Bean, Service, Repository, Autowired

@Repository
class UserRepository:
    def __init__(self):
        self.users = ["alice", "bob"]
    
    def find_all(self):
        return self.users

@Service
class UserService:
    @Autowired
    def __init__(self, user_repository: UserRepository):
        self.repository = user_repository
    
    def get_user_count(self):
        return len(self.repository.find_all())

class NotificationService:
    def __init__(self, prefix: str):
        self.prefix = prefix
    
    def notify(self, message: str):
        return f"{self.prefix}: {message}"

@Configuration
class AppConfig:
    @Bean
    def notification_service(self, user_service: UserService) -> NotificationService:
        user_count = user_service.get_user_count()
        return NotificationService(f"[{user_count} users]")
'''
            
            (test_package_dir / "mixed.py").write_text(mixed_content)
            
            sys.path.insert(0, temp_dir)
            
            from summer_core import DefaultApplicationContext
            
            self.context = DefaultApplicationContext(base_packages=["mixed_config"])
            self.context.refresh()
            
            # Test that all beans are registered
            bean_names = set(self.context.get_bean_definition_names())
            expected_names = {"userRepository", "userService", "appConfig", "notification_service"}
            self.assertTrue(expected_names.issubset(bean_names))
            
            # Test integration between components and configuration
            notification_service = self.context.get_bean("notification_service")
            user_service = self.context.get_bean("userService")
            user_repository = self.context.get_bean("userRepository")
            
            # Verify dependency injection worked correctly
            self.assertIs(user_service.repository, user_repository)
            
            # Test functionality
            result = notification_service.notify("Hello World")
            self.assertEqual(result, "[2 users]: Hello World")

    def test_configuration_class_as_bean(self):
        """Test that configuration classes themselves are registered as beans."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dirs.append(temp_dir)
            
            test_package_dir = Path(temp_dir) / "config_bean_test"
            test_package_dir.mkdir()
            
            (test_package_dir / "__init__.py").write_text("")
            
            config_content = '''
from summer_core import Configuration, Bean

@Configuration
class MyConfig:
    def __init__(self):
        self.config_name = "MyConfig"
    
    @Bean
    def simple_string(self) -> str:
        return f"Created by {self.config_name}"
'''
            
            (test_package_dir / "my_config.py").write_text(config_content)
            
            sys.path.insert(0, temp_dir)
            
            from summer_core import DefaultApplicationContext
            
            self.context = DefaultApplicationContext(base_packages=["config_bean_test"])
            self.context.refresh()
            
            # Test that configuration class is registered as a bean
            self.assertTrue(self.context.contains_bean("myConfig"))
            
            config_instance = self.context.get_bean("myConfig")
            self.assertIsNotNone(config_instance)
            self.assertEqual(config_instance.config_name, "MyConfig")
            
            # Test that @Bean method uses the config instance
            simple_string = self.context.get_bean("simple_string")
            self.assertEqual(simple_string, "Created by MyConfig")


if __name__ == '__main__':
    unittest.main()