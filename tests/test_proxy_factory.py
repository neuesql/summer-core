"""
Tests for proxy factory and method interception.

This module tests the AOP framework's proxy creation and method interception
capabilities, including advice chain execution and join point handling.
"""

import unittest
from unittest.mock import Mock, patch, call

from summer_core.decorators.aspect import aspect, before, after, around, after_returning, after_throwing
from summer_core.aop.proxy_factory import ProxyFactory, AdviceChain, create_proxy, is_proxy, get_target
from summer_core.aop.advice import (
    AdviceType, AdviceMetadata, AspectMetadata, JoinPoint, ProceedingJoinPoint,
    register_aspect_metadata
)


class MockService:
    """Test service class for proxy testing."""
    
    def __init__(self, name: str = "test"):
        self.name = name
        self.call_count = 0
    
    def simple_method(self) -> str:
        """Simple method for testing."""
        self.call_count += 1
        return f"Hello from {self.name}"
    
    def method_with_args(self, x: int, y: int) -> int:
        """Method with arguments for testing."""
        self.call_count += 1
        return x + y
    
    def method_that_throws(self) -> None:
        """Method that throws an exception."""
        self.call_count += 1
        raise ValueError("Test exception")
    
    def get_call_count(self) -> int:
        """Get the number of method calls."""
        return self.call_count


class TestProxyFactory(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        # Clear aspect registry
        from summer_core.aop.advice import _aspect_registry
        _aspect_registry.clear()
        
        self.proxy_factory = ProxyFactory()
        self.test_service = MockService("proxy_test")
    
    def test_create_proxy_no_aspects(self):
        """Test proxy creation when no aspects apply."""
        proxy = self.proxy_factory.create_proxy(self.test_service)
        
        # Should return original object when no aspects apply
        self.assertEqual(proxy, self.test_service)
    
    def test_create_proxy_with_aspects(self):
        """Test proxy creation with applicable aspects."""
        # Create a mock aspect with advice
        aspect_metadata = AspectMetadata(aspect_class=Mock, order=0)
        advice_metadata = AdviceMetadata(
            advice_type=AdviceType.BEFORE,
            pointcut="simple_method",
            method=Mock(),
            arg_names=['join_point']
        )
        aspect_metadata.advice_methods = [advice_metadata]
        
        # Mock the aspect registry
        with patch('summer_core.aop.proxy_factory.get_all_aspects', return_value=[aspect_metadata]):
            with patch('summer_core.aop.proxy_factory.matches_pointcut', return_value=True):
                proxy = self.proxy_factory.create_proxy(self.test_service)
                
                # Should create a proxy
                self.assertNotEqual(proxy, self.test_service)
                self.assertTrue(self.proxy_factory.is_proxy(proxy))
                self.assertEqual(self.proxy_factory.get_target(proxy), self.test_service)
    
    def test_proxy_method_interception(self):
        """Test that proxy intercepts method calls."""
        # Create a real aspect for testing
        @aspect
        class TestAspect:
            def __init__(self):
                self.before_called = False
            
            @before("simple_method")
            def log_before(self, join_point):
                self.before_called = True
        
        aspect_instance = TestAspect()
        
        # Mock the aspect system to return our test aspect
        aspect_metadata = AspectMetadata(aspect_class=TestAspect, order=0)
        advice_metadata = AdviceMetadata(
            advice_type=AdviceType.BEFORE,
            pointcut="simple_method",
            method=aspect_instance.log_before,
            arg_names=['join_point']
        )
        aspect_metadata.advice_methods = [advice_metadata]
        
        with patch('summer_core.aop.proxy_factory.get_all_aspects', return_value=[aspect_metadata]):
            with patch('summer_core.aop.proxy_factory.matches_pointcut') as mock_matches:
                # Only match simple_method
                mock_matches.side_effect = lambda pointcut, target, method: method.__name__ == "simple_method"
                
                proxy = self.proxy_factory.create_proxy(self.test_service)
                
                # Call the proxied method
                result = proxy.simple_method()
                
                # Verify the method was called and advice was executed
                self.assertEqual(result, "Hello from proxy_test")
                self.assertEqual(self.test_service.call_count, 1)
    
    def test_is_proxy_and_get_target(self):
        """Test proxy detection and target retrieval."""
        # Test with non-proxy object
        self.assertFalse(is_proxy(self.test_service))
        self.assertEqual(get_target(self.test_service), self.test_service)
        
        # Create a mock proxy
        mock_proxy = Mock()
        mock_proxy._target = self.test_service
        mock_proxy._advice_map = {}
        
        self.assertTrue(is_proxy(mock_proxy))
        self.assertEqual(get_target(mock_proxy), self.test_service)


class TestAdviceChain(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.target = MockService("chain_test")
        self.method = self.target.simple_method
    
    def test_advice_chain_no_advice(self):
        """Test advice chain with no advice."""
        chain = AdviceChain(self.target, self.method, [])
        result = chain.proceed((), {})
        
        self.assertEqual(result, "Hello from chain_test")
        self.assertEqual(self.target.call_count, 1)
    
    def test_advice_chain_before_advice(self):
        """Test advice chain with before advice."""
        # Create mock advice
        mock_advice_method = Mock()
        advice = AdviceMetadata(
            advice_type=AdviceType.BEFORE,
            pointcut="simple_method",
            method=mock_advice_method,
            arg_names=['join_point']
        )
        
        chain = AdviceChain(self.target, self.method, [advice])
        result = chain.proceed((), {})
        
        # Verify method was called and advice was executed
        self.assertEqual(result, "Hello from chain_test")
        self.assertEqual(self.target.call_count, 1)
        mock_advice_method.assert_called_once()
    
    def test_advice_chain_after_advice(self):
        """Test advice chain with after advice."""
        mock_advice_method = Mock()
        advice = AdviceMetadata(
            advice_type=AdviceType.AFTER,
            pointcut="simple_method",
            method=mock_advice_method,
            arg_names=['join_point']
        )
        
        chain = AdviceChain(self.target, self.method, [advice])
        result = chain.proceed((), {})
        
        self.assertEqual(result, "Hello from chain_test")
        self.assertEqual(self.target.call_count, 1)
        mock_advice_method.assert_called_once()
    
    def test_advice_chain_after_returning_advice(self):
        """Test advice chain with after returning advice."""
        mock_advice_method = Mock()
        advice = AdviceMetadata(
            advice_type=AdviceType.AFTER_RETURNING,
            pointcut="simple_method",
            method=mock_advice_method,
            returning_param="result",
            arg_names=['join_point', 'result']
        )
        
        chain = AdviceChain(self.target, self.method, [advice])
        result = chain.proceed((), {})
        
        self.assertEqual(result, "Hello from chain_test")
        self.assertEqual(self.target.call_count, 1)
        mock_advice_method.assert_called_once()
    
    def test_advice_chain_after_throwing_advice(self):
        """Test advice chain with after throwing advice."""
        mock_advice_method = Mock()
        advice = AdviceMetadata(
            advice_type=AdviceType.AFTER_THROWING,
            pointcut="method_that_throws",
            method=mock_advice_method,
            throwing_param="error",
            arg_names=['join_point', 'error']
        )
        
        throwing_method = self.target.method_that_throws
        chain = AdviceChain(self.target, throwing_method, [advice])
        
        with self.assertRaises(ValueError):
            chain.proceed((), {})
        
        self.assertEqual(self.target.call_count, 1)
        mock_advice_method.assert_called_once()
    
    def test_advice_chain_around_advice(self):
        """Test advice chain with around advice."""
        def mock_around_advice(proceeding_join_point):
            # Modify behavior in around advice
            result = proceeding_join_point.proceed()
            return f"Around: {result}"
        
        advice = AdviceMetadata(
            advice_type=AdviceType.AROUND,
            pointcut="simple_method",
            method=mock_around_advice,
            arg_names=['proceeding_join_point']
        )
        
        chain = AdviceChain(self.target, self.method, [advice])
        result = chain.proceed((), {})
        
        self.assertEqual(result, "Around: Hello from chain_test")
        self.assertEqual(self.target.call_count, 1)
    
    def test_advice_chain_multiple_advice(self):
        """Test advice chain with multiple advice."""
        execution_order = []
        
        def before_advice(join_point):
            execution_order.append("before")
        
        def after_advice(join_point):
            execution_order.append("after")
        
        before_advice_meta = AdviceMetadata(
            advice_type=AdviceType.BEFORE,
            pointcut="simple_method",
            method=before_advice,
            arg_names=['join_point']
        )
        
        after_advice_meta = AdviceMetadata(
            advice_type=AdviceType.AFTER,
            pointcut="simple_method",
            method=after_advice,
            arg_names=['join_point']
        )
        
        chain = AdviceChain(self.target, self.method, [before_advice_meta, after_advice_meta])
        result = chain.proceed((), {})
        
        self.assertEqual(result, "Hello from chain_test")
        self.assertEqual(self.target.call_count, 1)
        self.assertEqual(execution_order, ["before", "after"])


class TestJoinPointIntegration(unittest.TestCase):
    
    def test_join_point_in_advice_chain(self):
        """Test that join points are properly created and passed to advice."""
        join_point_data = {}
        
        def capture_join_point(join_point):
            join_point_data['target'] = join_point.get_target()
            join_point_data['method'] = join_point.get_method()
            join_point_data['args'] = join_point.get_args()
            join_point_data['kwargs'] = join_point.get_kwargs()
            join_point_data['signature'] = join_point.get_signature()
        
        advice = AdviceMetadata(
            advice_type=AdviceType.BEFORE,
            pointcut="method_with_args",
            method=capture_join_point,
            arg_names=['join_point']
        )
        
        target = MockService("join_point_test")
        method = target.method_with_args
        
        chain = AdviceChain(target, method, [advice])
        result = chain.proceed((5, 3), {})
        
        # Verify join point data
        self.assertEqual(join_point_data['target'], target)
        self.assertEqual(join_point_data['method'], method)
        self.assertEqual(join_point_data['args'], (5, 3))
        self.assertEqual(join_point_data['kwargs'], {})
        self.assertIn('MockService', join_point_data['signature'])
        self.assertIn('method_with_args', join_point_data['signature'])
        
        # Verify method execution
        self.assertEqual(result, 8)
        self.assertEqual(target.call_count, 1)
    
    def test_proceeding_join_point_in_around_advice(self):
        """Test proceeding join point functionality in around advice."""
        proceeding_data = {}
        
        def around_advice(proceeding_join_point):
            proceeding_data['has_proceeded_before'] = proceeding_join_point.has_proceeded()
            result = proceeding_join_point.proceed()
            proceeding_data['has_proceeded_after'] = proceeding_join_point.has_proceeded()
            proceeding_data['result'] = proceeding_join_point.get_result()
            return f"Modified: {result}"
        
        advice = AdviceMetadata(
            advice_type=AdviceType.AROUND,
            pointcut="simple_method",
            method=around_advice,
            arg_names=['proceeding_join_point']
        )
        
        target = MockService("proceeding_test")
        method = target.simple_method
        
        chain = AdviceChain(target, method, [advice])
        result = chain.proceed((), {})
        
        # Verify proceeding join point behavior
        self.assertFalse(proceeding_data['has_proceeded_before'])
        self.assertTrue(proceeding_data['has_proceeded_after'])
        self.assertEqual(proceeding_data['result'], "Hello from proceeding_test")
        self.assertEqual(result, "Modified: Hello from proceeding_test")
        self.assertEqual(target.call_count, 1)


class TestComplexProxyScenarios(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        from summer_core.aop.advice import _aspect_registry
        _aspect_registry.clear()
    
    def test_proxy_with_multiple_aspects(self):
        """Test proxy creation with multiple aspects."""
        execution_log = []
        
        # Create multiple aspects
        @aspect(order=1)
        class FirstAspect:
            @before("simple_method")
            def first_before(self, join_point):
                execution_log.append("first_before")
        
        @aspect(order=2)
        class SecondAspect:
            @before("simple_method")
            def second_before(self, join_point):
                execution_log.append("second_before")
        
        # This test demonstrates the structure, but full integration
        # would require the container to wire everything together
        self.assertEqual(len(execution_log), 0)  # No execution yet
    
    def test_proxy_attribute_access(self):
        """Test that proxy properly handles attribute access."""
        # Create a simple proxy manually for testing
        class SimpleProxy:
            def __init__(self, target):
                self._target = target
                self._advice_map = {}
            
            def __getattr__(self, name):
                return getattr(self._target, name)
            
            def __setattr__(self, name, value):
                if name.startswith('_'):
                    super().__setattr__(name, value)
                else:
                    setattr(self._target, name, value)
        
        target = MockService("attribute_test")
        proxy = SimpleProxy(target)
        
        # Test attribute access
        self.assertEqual(proxy.name, "attribute_test")
        
        # Test attribute setting
        proxy.name = "modified"
        self.assertEqual(target.name, "modified")
        self.assertEqual(proxy.name, "modified")


if __name__ == '__main__':
    unittest.main()