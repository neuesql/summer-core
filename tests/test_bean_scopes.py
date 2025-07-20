"""
Tests for bean scope functionality.

Tests singleton, prototype, request, and session scopes,
as well as custom scope extension mechanism.
"""

import unittest
import threading
import time
from typing import Any, Callable, Optional

from summer_core.container.application_context import DefaultApplicationContext
from summer_core.container.bean_definition import BeanDefinition, BeanScope
from summer_core.container.scope import (
    Scope, SingletonScope, PrototypeScope, RequestScope, SessionScope, 
    ScopeRegistry, get_scope_registry
)
from summer_core.decorators import Component, Service, Scope as ScopeDecorator


class TestSingletonScope(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.scope = SingletonScope()
        self.call_count = 0
    
    def tearDown(self):
        """Clean up after each test method."""
        if hasattr(self.scope, 'destroy'):
            self.scope.destroy()
    
    def test_singleton_returns_same_instance(self):
        """Test that singleton scope returns the same instance."""
        def factory():
            self.call_count += 1
            return f"instance_{self.call_count}"
        
        # Get instance twice
        instance1 = self.scope.get("test_bean", factory)
        instance2 = self.scope.get("test_bean", factory)
        
        # Should be the same instance
        self.assertEqual(instance1, instance2)
        self.assertEqual(instance1, "instance_1")
        self.assertEqual(self.call_count, 1)
    
    def test_singleton_different_beans(self):
        """Test that different beans get different instances."""
        def factory1():
            return "bean1_instance"
        
        def factory2():
            return "bean2_instance"
        
        instance1 = self.scope.get("bean1", factory1)
        instance2 = self.scope.get("bean2", factory2)
        
        self.assertNotEqual(instance1, instance2)
        self.assertEqual(instance1, "bean1_instance")
        self.assertEqual(instance2, "bean2_instance")
    
    def test_singleton_destruction_callback(self):
        """Test that destruction callbacks are executed."""
        callback_executed = False
        
        def destruction_callback():
            nonlocal callback_executed
            callback_executed = True
        
        def factory():
            return "test_instance"
        
        # Get instance and register callback
        instance = self.scope.get("test_bean", factory)
        self.scope.register_destruction_callback("test_bean", destruction_callback)
        
        # Remove bean
        removed = self.scope.remove("test_bean")
        
        self.assertEqual(removed, instance)
        self.assertTrue(callback_executed)
    
    def test_singleton_conversation_id(self):
        """Test that singleton scope has no conversation ID."""
        self.assertIsNone(self.scope.get_conversation_id())


class TestPrototypeScope(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.scope = PrototypeScope()
        self.call_count = 0
    
    def test_prototype_returns_new_instance(self):
        """Test that prototype scope returns new instances."""
        def factory():
            self.call_count += 1
            return f"instance_{self.call_count}"
        
        # Get instance twice
        instance1 = self.scope.get("test_bean", factory)
        instance2 = self.scope.get("test_bean", factory)
        
        # Should be different instances
        self.assertNotEqual(instance1, instance2)
        self.assertEqual(instance1, "instance_1")
        self.assertEqual(instance2, "instance_2")
        self.assertEqual(self.call_count, 2)
    
    def test_prototype_remove_returns_none(self):
        """Test that removing prototype beans returns None."""
        def factory():
            return "test_instance"
        
        # Get instance
        instance = self.scope.get("test_bean", factory)
        
        # Remove should return None (not stored)
        removed = self.scope.remove("test_bean")
        self.assertIsNone(removed)
    
    def test_prototype_destruction_callback_registration(self):
        """Test that destruction callbacks can be registered for prototype beans."""
        def destruction_callback():
            pass
        
        # Should not raise an error
        self.scope.register_destruction_callback("test_bean", destruction_callback)
    
    def test_prototype_conversation_id(self):
        """Test that prototype scope has no conversation ID."""
        self.assertIsNone(self.scope.get_conversation_id())


class TestRequestScope(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.scope = RequestScope()
        self.call_count = 0
    
    def test_request_scope_same_thread(self):
        """Test that request scope returns same instance within same thread."""
        def factory():
            self.call_count += 1
            return f"instance_{self.call_count}"
        
        # Get instance twice in same thread
        instance1 = self.scope.get("test_bean", factory)
        instance2 = self.scope.get("test_bean", factory)
        
        # Should be the same instance
        self.assertEqual(instance1, instance2)
        self.assertEqual(instance1, "instance_1")
        self.assertEqual(self.call_count, 1)
    
    def test_request_scope_different_threads(self):
        """Test that request scope returns different instances in different threads."""
        results = {}
        call_counts = {}
        
        def factory():
            thread_id = threading.current_thread().ident
            if thread_id not in call_counts:
                call_counts[thread_id] = 0
            call_counts[thread_id] += 1
            return f"instance_{thread_id}_{call_counts[thread_id]}"
        
        def thread_worker(thread_name):
            instance1 = self.scope.get("test_bean", factory)
            instance2 = self.scope.get("test_bean", factory)
            results[thread_name] = (instance1, instance2)
        
        # Create and start threads
        thread1 = threading.Thread(target=thread_worker, args=("thread1",))
        thread2 = threading.Thread(target=thread_worker, args=("thread2",))
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Each thread should have same instances within thread, different between threads
        self.assertEqual(results["thread1"][0], results["thread1"][1])
        self.assertEqual(results["thread2"][0], results["thread2"][1])
        self.assertNotEqual(results["thread1"][0], results["thread2"][0])
    
    def test_request_scope_destruction_callback(self):
        """Test that destruction callbacks work for request scope."""
        callback_executed = False
        
        def destruction_callback():
            nonlocal callback_executed
            callback_executed = True
        
        def factory():
            return "test_instance"
        
        # Get instance and register callback
        instance = self.scope.get("test_bean", factory)
        self.scope.register_destruction_callback("test_bean", destruction_callback)
        
        # Remove bean
        removed = self.scope.remove("test_bean")
        
        self.assertEqual(removed, instance)
        self.assertTrue(callback_executed)
    
    def test_request_scope_conversation_id(self):
        """Test that request scope returns thread ID as conversation ID."""
        conversation_id = self.scope.get_conversation_id()
        self.assertIsNotNone(conversation_id)
        self.assertEqual(conversation_id, str(threading.current_thread().ident))
    
    def test_request_scope_destroy_request(self):
        """Test that destroy_request cleans up current thread's beans."""
        callback_executed = False
        
        def destruction_callback():
            nonlocal callback_executed
            callback_executed = True
        
        def factory():
            return "test_instance"
        
        # Get instance and register callback
        instance = self.scope.get("test_bean", factory)
        self.scope.register_destruction_callback("test_bean", destruction_callback)
        
        # Destroy request
        self.scope.destroy_request()
        
        self.assertTrue(callback_executed)


class TestSessionScope(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.scope = SessionScope()
        self.call_count = 0
    
    def test_session_scope_same_session(self):
        """Test that session scope returns same instance within same session."""
        def factory():
            self.call_count += 1
            return f"instance_{self.call_count}"
        
        # Set session ID
        self.scope.set_current_session_id("session1")
        
        # Get instance twice in same session
        instance1 = self.scope.get("test_bean", factory)
        instance2 = self.scope.get("test_bean", factory)
        
        # Should be the same instance
        self.assertEqual(instance1, instance2)
        self.assertEqual(instance1, "instance_1")
        self.assertEqual(self.call_count, 1)
    
    def test_session_scope_different_sessions(self):
        """Test that session scope returns different instances in different sessions."""
        def factory():
            self.call_count += 1
            return f"instance_{self.call_count}"
        
        # Get instance in session1
        self.scope.set_current_session_id("session1")
        instance1 = self.scope.get("test_bean", factory)
        
        # Get instance in session2
        self.scope.set_current_session_id("session2")
        instance2 = self.scope.get("test_bean", factory)
        
        # Should be different instances
        self.assertNotEqual(instance1, instance2)
        self.assertEqual(instance1, "instance_1")
        self.assertEqual(instance2, "instance_2")
        self.assertEqual(self.call_count, 2)
    
    def test_session_scope_no_session_id(self):
        """Test that session scope raises error when no session ID is set."""
        def factory():
            return "test_instance"
        
        # Should raise error when no session ID
        with self.assertRaises(RuntimeError) as cm:
            self.scope.get("test_bean", factory)
        
        self.assertIn("No session ID available", str(cm.exception))
    
    def test_session_scope_destruction_callback(self):
        """Test that destruction callbacks work for session scope."""
        callback_executed = False
        
        def destruction_callback():
            nonlocal callback_executed
            callback_executed = True
        
        def factory():
            return "test_instance"
        
        # Set session ID
        self.scope.set_current_session_id("session1")
        
        # Get instance and register callback
        instance = self.scope.get("test_bean", factory)
        self.scope.register_destruction_callback("test_bean", destruction_callback)
        
        # Remove bean
        removed = self.scope.remove("test_bean")
        
        self.assertEqual(removed, instance)
        self.assertTrue(callback_executed)
    
    def test_session_scope_conversation_id(self):
        """Test that session scope returns session ID as conversation ID."""
        self.scope.set_current_session_id("session1")
        conversation_id = self.scope.get_conversation_id()
        self.assertEqual(conversation_id, "session1")
    
    def test_session_scope_destroy_session(self):
        """Test that destroy_session cleans up session's beans."""
        callback_executed = False
        
        def destruction_callback():
            nonlocal callback_executed
            callback_executed = True
        
        def factory():
            return "test_instance"
        
        # Set session ID and get instance
        self.scope.set_current_session_id("session1")
        instance = self.scope.get("test_bean", factory)
        self.scope.register_destruction_callback("test_bean", destruction_callback)
        
        # Destroy session
        self.scope.destroy_session("session1")
        
        self.assertTrue(callback_executed)


class CustomTestScope(Scope):
    """Custom scope implementation for testing."""
    
    def __init__(self):
        self.objects = {}
        self.callbacks = {}
        self.prefix = "custom_"
    
    def get(self, name: str, object_factory: Callable[[], Any]) -> Any:
        key = self.prefix + name
        if key not in self.objects:
            self.objects[key] = object_factory()
        return self.objects[key]
    
    def remove(self, name: str) -> Optional[Any]:
        key = self.prefix + name
        obj = self.objects.pop(key, None)
        callback = self.callbacks.pop(key, None)
        if callback:
            callback()
        return obj
    
    def register_destruction_callback(self, name: str, callback: Callable[[], None]) -> None:
        key = self.prefix + name
        self.callbacks[key] = callback
    
    def get_conversation_id(self) -> Optional[str]:
        return "custom_conversation"


class TestScopeRegistry(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.registry = ScopeRegistry()
    
    def test_built_in_scopes_registered(self):
        """Test that built-in scopes are registered by default."""
        scope_names = self.registry.get_registered_scope_names()
        
        self.assertIn("singleton", scope_names)
        self.assertIn("prototype", scope_names)
        self.assertIn("request", scope_names)
        self.assertIn("session", scope_names)
    
    def test_get_built_in_scopes(self):
        """Test that built-in scopes can be retrieved."""
        singleton_scope = self.registry.get_scope("singleton")
        prototype_scope = self.registry.get_scope("prototype")
        request_scope = self.registry.get_scope("request")
        session_scope = self.registry.get_scope("session")
        
        self.assertIsInstance(singleton_scope, SingletonScope)
        self.assertIsInstance(prototype_scope, PrototypeScope)
        self.assertIsInstance(request_scope, RequestScope)
        self.assertIsInstance(session_scope, SessionScope)
    
    def test_register_custom_scope(self):
        """Test that custom scopes can be registered."""
        custom_scope = CustomTestScope()
        self.registry.register_scope("custom", custom_scope)
        
        retrieved_scope = self.registry.get_scope("custom")
        self.assertEqual(retrieved_scope, custom_scope)
        
        scope_names = self.registry.get_registered_scope_names()
        self.assertIn("custom", scope_names)
    
    def test_get_nonexistent_scope(self):
        """Test that getting nonexistent scope returns None."""
        scope = self.registry.get_scope("nonexistent")
        self.assertIsNone(scope)


class TestBeanScopeIntegration(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.context = None
    
    def tearDown(self):
        """Clean up after each test method."""
        if self.context:
            self.context.close()
    
    def test_singleton_bean_in_context(self):
        """Test that singleton beans work correctly in application context."""
        @Component
        class SingletonService:
            def __init__(self):
                self.created_at = time.time()
        
        self.context = DefaultApplicationContext()
        
        # Register bean definition
        bean_def = BeanDefinition(
            bean_name="singletonService",
            bean_type=SingletonService,
            scope=BeanScope.SINGLETON
        )
        self.context.register_bean_definition("singletonService", bean_def)
        self.context.refresh()
        
        # Get bean twice
        service1 = self.context.get_bean("singletonService")
        service2 = self.context.get_bean("singletonService")
        
        # Should be the same instance
        self.assertIs(service1, service2)
        self.assertEqual(service1.created_at, service2.created_at)
    
    def test_prototype_bean_in_context(self):
        """Test that prototype beans work correctly in application context."""
        @Component
        class PrototypeService:
            def __init__(self):
                self.created_at = time.time()
        
        self.context = DefaultApplicationContext()
        
        # Register bean definition
        bean_def = BeanDefinition(
            bean_name="prototypeService",
            bean_type=PrototypeService,
            scope=BeanScope.PROTOTYPE
        )
        self.context.register_bean_definition("prototypeService", bean_def)
        self.context.refresh()
        
        # Get bean twice
        service1 = self.context.get_bean("prototypeService")
        time.sleep(0.001)  # Ensure different timestamps
        service2 = self.context.get_bean("prototypeService")
        
        # Should be different instances
        self.assertIsNot(service1, service2)
        self.assertNotEqual(service1.created_at, service2.created_at)
    
    def test_custom_scope_in_context(self):
        """Test that custom scopes work correctly in application context."""
        @Component
        class CustomScopedService:
            def __init__(self):
                self.value = "custom_service"
        
        self.context = DefaultApplicationContext()
        
        # Register custom scope
        custom_scope = CustomTestScope()
        self.context.register_scope("custom", custom_scope)
        
        # Register bean definition with custom scope
        bean_def = BeanDefinition(
            bean_name="customScopedService",
            bean_type=CustomScopedService,
            scope=BeanScope.SINGLETON  # We'll override this
        )
        bean_def.scope = type('CustomScope', (), {'value': 'custom'})()
        self.context.register_bean_definition("customScopedService", bean_def)
        self.context.refresh()
        
        # Get bean
        service = self.context.get_bean("customScopedService")
        self.assertIsInstance(service, CustomScopedService)
        self.assertEqual(service.value, "custom_service")
    
    def test_scope_decorator(self):
        """Test that @Scope decorator works correctly."""
        @Component
        @ScopeDecorator("prototype")
        class DecoratedService:
            def __init__(self):
                self.created_at = time.time()
        
        # Check that scope metadata is set
        self.assertEqual(getattr(DecoratedService, '_summer_scope'), "prototype")


if __name__ == '__main__':
    unittest.main()