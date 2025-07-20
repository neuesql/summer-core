"""
Integration test for the complete Summer Framework functionality.

Tests the full integration of components, configuration, dependency injection,
and lifecycle management working together.
"""

import unittest
import tempfile
import sys
from pathlib import Path


class TestFrameworkIntegration(unittest.TestCase):
    
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

    def test_full_framework_integration(self):
        """Test complete framework integration with all features."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            
            # Create test package structure
            test_package_dir = Path(temp_dir) / "integration_test"
            test_package_dir.mkdir()
            
            # Create __init__.py
            (test_package_dir / "__init__.py").write_text("")
            
            # Create a complete application with all features
            app_content = '''
from summer_core import Service, Repository, Configuration, Bean, Autowired
from summer_core.decorators.autowired import PostConstruct, PreDestroy

# Repository layer
@Repository
class UserRepository:
    def __init__(self):
        self.users = {}
        self.connected = False
    
    @PostConstruct
    def connect(self):
        self.connected = True
        print("UserRepository connected")
    
    @PreDestroy
    def disconnect(self):
        self.connected = False
        print("UserRepository disconnected")
    
    def save(self, user_id: str, user_data: dict):
        self.users[user_id] = user_data
        return user_data
    
    def find_by_id(self, user_id: str):
        return self.users.get(user_id)

# Service layer
@Service
class UserService:
    @Autowired
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        self.initialized = False
    
    @PostConstruct
    def initialize(self):
        self.initialized = True
        print("UserService initialized")
    
    @PreDestroy
    def cleanup(self):
        self.initialized = False
        print("UserService cleaned up")
    
    def create_user(self, user_id: str, name: str, email: str):
        user_data = {"name": name, "email": email}
        return self.user_repository.save(user_id, user_data)
    
    def get_user(self, user_id: str):
        return self.user_repository.find_by_id(user_id)

# Configuration beans
class EmailService:
    def __init__(self, smtp_host: str, smtp_port: int):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.connected = False
    
    @PostConstruct
    def connect(self):
        self.connected = True
        print(f"EmailService connected to {self.smtp_host}:{self.smtp_port}")
    
    @PreDestroy
    def disconnect(self):
        self.connected = False
        print("EmailService disconnected")
    
    def send_email(self, to: str, subject: str, body: str):
        return f"Email sent to {to}: {subject}"

class NotificationService:
    def __init__(self, email_service: EmailService, user_service: UserService):
        self.email_service = email_service
        self.user_service = user_service
    
    def send_welcome_email(self, user_id: str):
        user = self.user_service.get_user(user_id)
        if user:
            return self.email_service.send_email(
                user["email"], 
                "Welcome!", 
                f"Welcome {user['name']}!"
            )
        return None

@Configuration
class AppConfig:
    
    @Bean
    def email_service(self) -> EmailService:
        return EmailService("smtp.example.com", 587)
    
    @Bean
    def notification_service(self, email_service: EmailService, user_service: UserService) -> NotificationService:
        return NotificationService(email_service, user_service)
'''
            
            (test_package_dir / "app.py").write_text(app_content)
            
            # Add temp directory to Python path
            sys.path.insert(0, temp_dir)
            
            try:
                from summer_core import DefaultApplicationContext
                
                # Create and start the application context
                self.context = DefaultApplicationContext(base_packages=["integration_test"])
                self.context.refresh()
                
                # Verify all beans are registered
                bean_names = set(self.context.get_bean_definition_names())
                expected_beans = {
                    "userRepository", "userService", 
                    "email_service", "notification_service"
                }
                self.assertTrue(expected_beans.issubset(bean_names))
                
                # Test component beans
                user_repository = self.context.get_bean("userRepository")
                user_service = self.context.get_bean("userService")
                
                # Verify dependency injection
                self.assertIs(user_service.user_repository, user_repository)
                
                # Verify @PostConstruct was called
                self.assertTrue(user_repository.connected)
                self.assertTrue(user_service.initialized)
                
                # Test configuration beans
                email_service = self.context.get_bean("email_service")
                notification_service = self.context.get_bean("notification_service")
                
                # Verify configuration bean properties
                self.assertEqual(email_service.smtp_host, "smtp.example.com")
                self.assertEqual(email_service.smtp_port, 587)
                self.assertTrue(email_service.connected)
                
                # Verify configuration bean dependencies
                self.assertIs(notification_service.email_service, email_service)
                self.assertIs(notification_service.user_service, user_service)
                
                # Test business logic
                user_data = user_service.create_user("123", "John Doe", "john@example.com")
                self.assertEqual(user_data["name"], "John Doe")
                self.assertEqual(user_data["email"], "john@example.com")
                
                retrieved_user = user_service.get_user("123")
                self.assertEqual(retrieved_user, user_data)
                
                # Test cross-layer functionality
                welcome_message = notification_service.send_welcome_email("123")
                self.assertEqual(welcome_message, "Email sent to john@example.com: Welcome!")
                
                # Test singleton behavior
                user_service2 = self.context.get_bean("userService")
                self.assertIs(user_service, user_service2)
                
                # Close context and verify @PreDestroy is called
                self.context.close()
                
                # Verify @PreDestroy was called
                self.assertFalse(user_repository.connected)
                self.assertFalse(user_service.initialized)
                self.assertFalse(email_service.connected)
                
                self.context = None
                
            finally:
                if temp_dir in sys.path:
                    sys.path.remove(temp_dir)


if __name__ == '__main__':
    unittest.main()