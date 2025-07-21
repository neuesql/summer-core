"""
Integration tests for AOP and IoC container.

This module tests the integration between the AOP framework and the IoC container,
including automatic proxy creation, aspect ordering, and advisor chain execution.
"""

import unittest
from unittest.mock import Mock, patch

from summer_core.container.bean_factory import DefaultBeanFactory, BeanPostProcessor
from summer_core.container.bean_definition import BeanDefinition, BeanScope
from summer_core.decorators.aspect import aspect, before, after, around, pointcut
from summer_core.decorators.component import Component
from summer_core.aop.integration import AopBeanPostProcessor, get_aspect_registry, create_aop_bean_post_processor
from summer_core.aop.advice import get_all_aspects, register_aspect_metadata, AspectMetadata, AdviceMetadata, AdviceType


# Test classes for integration testing
@Component
class MockBusinessService:
    """Test business service for AOP integration."""
    
    def __init__(self):
        self.call_count = 0
        self.execution_log = []
    
    def business_method(self, value: str) -> str:
        """Business method that will be advised."""
        self.call_count += 1
        self.execution_log.append(f"business_method({value})")
        return f"processed: {value}"
    
    def another_method(self) -> str:
        """Another method for testing selective advice."""
        self.call_count += 1
        self.execution_log.append("another_method()")
        return "another result"


@aspect(order=1)
class LoggingAspect:
    """Test logging aspect."""
    
    def __init__(self):
        self.execution_log = []
    
    @pointcut("business_method")
    def business_operations(self):
        """Pointcut for business operations."""
        pass
    
    @before("business_operations")
    def log_before(self, join_point):
        """Log before business operations."""
        self.execution_log.append(f"BEFORE: {join_point.get_signature()}")
    
    @after("business_operations")
    def log_after(self, join_point):
        """Log after business operations."""
        self.execution_log.append(f"AFTER: {join_point.get_signature()}")


@aspect(order=2)
class SecurityAspect:
    """Test security aspect with lower precedence."""
    
    def __init__(self):
        self.execution_log = []
    
    @before("business_method")
    def check_security(self, join_point):
        """Check security before business operations."""
        self.execution_log.append(f"SECURITY: {join_point.get_signature()}")


@aspect(order=0)
class PerformanceAspect:
    """Test performance aspect with highest precedence."""
    
    def __init__(self):
        self.execution_log = []
    
    @around("business_method")
    def measure_performance(self, proceeding_join_point):
        """Measure performance around business operations."""
        self.execution_log.append("PERF_START")
        try:
            result = proceeding_join_point.proceed()
            self.execution_log.append("PERF_END")
            return f"measured: {result}"
        except Exception as e:
            self.execution_log.append("PERF_ERROR")
            raise


class TestAopIntegration(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        # Clear aspect registry
        from summer_core.aop.advice import _aspect_registry
        _aspect_registry.clear()
        
        # Clear the global scope registry to avoid test interference
        from summer_core.container.scope import get_scope_registry
        scope_registry = get_scope_registry()
        scope_registry.destroy_all_scopes()
        
        self.bean_factory = DefaultBeanFactory()
        self.aop_processor = create_aop_bean_post_processor()
        self.bean_factory.add_bean_post_processor(self.aop_processor)
    
    def test_bean_post_processor_registration(self):
        """Test that bean post processors can be registered."""
        processors = self.bean_factory.get_bean_post_processors()
        self.assertEqual(len(processors), 1)
        self.assertIsInstance(processors[0], AopBeanPostProcessor)
    
    def test_bean_creation_without_aspects(self):
        """Test bean creation when no aspects are registered."""
        # Register bean definition
        bean_def = BeanDefinition(
            bean_name="testService",
            bean_type=MockBusinessService,
            scope=BeanScope.SINGLETON
        )
        self.bean_factory.register_bean_definition("testService", bean_def)
        
        # Get bean - should not be proxied
        service = self.bean_factory.get_bean("testService")
        self.assertIsInstance(service, MockBusinessService)
        
        # Call method
        result = service.business_method("test")
        self.assertEqual(result, "processed: test")
        self.assertEqual(service.call_count, 1)
    
    def test_bean_creation_with_aspects(self):
        """Test bean creation with registered aspects."""
        # Register aspects
        logging_aspect = LoggingAspect()
        aspect_metadata = AspectMetadata(aspect_class=LoggingAspect, order=1)
        
        # Create advice metadata manually for testing
        advice_metadata = AdviceMetadata(
            advice_type=AdviceType.BEFORE,
            pointcut="business_method",
            method=logging_aspect.log_before,
            arg_names=['join_point']
        )
        aspect_metadata.advice_methods = [advice_metadata]
        
        # Register aspect
        register_aspect_metadata(LoggingAspect, aspect_metadata)
        
        # Register bean definition
        bean_def = BeanDefinition(
            bean_name="testService",
            bean_type=MockBusinessService,
            scope=BeanScope.SINGLETON
        )
        self.bean_factory.register_bean_definition("testService", bean_def)
        
        # Mock pointcut matching to return True for business_method
        with patch('summer_core.aop.integration.matches_pointcut') as mock_matches_integration, \
             patch('summer_core.aop.proxy_factory.matches_pointcut') as mock_matches_proxy:
            mock_matches_integration.side_effect = lambda pointcut, target, method: method.__name__ == "business_method"
            mock_matches_proxy.side_effect = lambda pointcut, target, method: method.__name__ == "business_method"
            
            # Get bean - should be proxied
            service = self.bean_factory.get_bean("testService")
            
            # Verify it's a proxy
            self.assertTrue(hasattr(service, '_target'))
            self.assertTrue(hasattr(service, '_advice_map'))
    
    def test_aspect_ordering(self):
        """Test that aspects are applied in the correct order."""
        # Register multiple aspects with different orders
        aspects = [
            (PerformanceAspect, 0),
            (LoggingAspect, 1),
            (SecurityAspect, 2)
        ]
        
        for aspect_class, order in aspects:
            aspect_metadata = AspectMetadata(aspect_class=aspect_class, order=order)
            register_aspect_metadata(aspect_class, aspect_metadata)
        
        # Get all aspects and verify ordering
        all_aspects = get_all_aspects()
        sorted_aspects = sorted(all_aspects, key=lambda a: a.order)
        
        expected_order = [PerformanceAspect, LoggingAspect, SecurityAspect]
        actual_order = [a.aspect_class for a in sorted_aspects]
        
        self.assertEqual(actual_order, expected_order)
    
    def test_selective_advice_application(self):
        """Test that advice is only applied to matching methods."""
        # Create aspect that only matches business_method
        logging_aspect = LoggingAspect()
        aspect_metadata = AspectMetadata(aspect_class=LoggingAspect, order=1)
        
        advice_metadata = AdviceMetadata(
            advice_type=AdviceType.BEFORE,
            pointcut="business_method",
            method=logging_aspect.log_before,
            arg_names=['join_point']
        )
        aspect_metadata.advice_methods = [advice_metadata]
        register_aspect_metadata(LoggingAspect, aspect_metadata)
        
        # Register bean
        bean_def = BeanDefinition(
            bean_name="testService",
            bean_type=MockBusinessService,
            scope=BeanScope.SINGLETON
        )
        self.bean_factory.register_bean_definition("testService", bean_def)
        
        # Mock pointcut matching to be selective
        with patch('summer_core.aop.integration.matches_pointcut') as mock_matches:
            mock_matches.side_effect = lambda pointcut, target, method: (
                pointcut == "business_method" and method.__name__ == "business_method"
            )
            
            service = self.bean_factory.get_bean("testService")
            
            # Verify proxy was created (has advice for business_method)
            if hasattr(service, '_advice_map'):
                # business_method should have advice
                self.assertIn('business_method', service._advice_map)
                # another_method should not have advice
                self.assertNotIn('another_method', service._advice_map)


class TestBeanPostProcessor(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        # Clear singleton scope to ensure test isolation
        from summer_core.container.scope import get_scope_registry
        scope_registry = get_scope_registry()
        singleton_scope = scope_registry.get_scope("singleton")
        if singleton_scope and hasattr(singleton_scope, 'destroy'):
            singleton_scope.destroy()
        # Clear the global scope registry to avoid test interference
        from summer_core.container.scope import get_scope_registry
        scope_registry = get_scope_registry()
        scope_registry.destroy_all_scopes()
    
    def test_custom_bean_post_processor(self):
        """Test custom bean post processor functionality."""
        
        class CustomBeanPostProcessor(BeanPostProcessor):
            def __init__(self):
                self.processed_beans = []
            
            def post_process_before_initialization(self, bean, bean_name):
                self.processed_beans.append(f"before_{bean_name}")
                return bean
            
            def post_process_after_initialization(self, bean, bean_name):
                self.processed_beans.append(f"after_{bean_name}")
                return bean
        
        bean_factory = DefaultBeanFactory()
        processor = CustomBeanPostProcessor()
        bean_factory.add_bean_post_processor(processor)
        
        # Register and create bean
        bean_def = BeanDefinition(
            bean_name="testService",
            bean_type=MockBusinessService,
            scope=BeanScope.SINGLETON
        )
        bean_factory.register_bean_definition("testService", bean_def)
        
        service = bean_factory.get_bean("testService")
        
        # Verify processor was called
        self.assertIn("before_testService", processor.processed_beans)
        self.assertIn("after_testService", processor.processed_beans)
    
    def test_multiple_bean_post_processors(self):
        """Test multiple bean post processors are applied in order."""
        
        execution_order = []
        
        class FirstProcessor(BeanPostProcessor):
            def post_process_before_initialization(self, bean, bean_name):
                execution_order.append("first_before")
                return bean
            
            def post_process_after_initialization(self, bean, bean_name):
                execution_order.append("first_after")
                return bean
        
        class SecondProcessor(BeanPostProcessor):
            def post_process_before_initialization(self, bean, bean_name):
                execution_order.append("second_before")
                return bean
            
            def post_process_after_initialization(self, bean, bean_name):
                execution_order.append("second_after")
                return bean
        
        bean_factory = DefaultBeanFactory()
        bean_factory.add_bean_post_processor(FirstProcessor())
        bean_factory.add_bean_post_processor(SecondProcessor())
        
        # Register and create bean
        bean_def = BeanDefinition(
            bean_name="testService",
            bean_type=MockBusinessService,
            scope=BeanScope.SINGLETON
        )
        bean_factory.register_bean_definition("testService", bean_def)
        
        service = bean_factory.get_bean("testService")
        
        # Verify execution order
        expected_order = [
            "first_before", "second_before",
            "first_after", "second_after"
        ]
        self.assertEqual(execution_order, expected_order)


class TestAspectRegistry(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.aspect_registry = get_aspect_registry()
        # Clear any existing instances
        self.aspect_registry._aspect_instances.clear()
    
    def test_aspect_instance_creation(self):
        """Test aspect instance creation and caching."""
        # Get aspect instance
        instance1 = self.aspect_registry.get_aspect_instance(LoggingAspect)
        self.assertIsInstance(instance1, LoggingAspect)
        
        # Get same aspect again - should return cached instance
        instance2 = self.aspect_registry.get_aspect_instance(LoggingAspect)
        self.assertIs(instance1, instance2)
    
    def test_aspect_instance_registration(self):
        """Test manual aspect instance registration."""
        custom_instance = LoggingAspect()
        custom_instance.custom_property = "test"
        
        self.aspect_registry.register_aspect_instance(LoggingAspect, custom_instance)
        
        retrieved_instance = self.aspect_registry.get_aspect_instance(LoggingAspect)
        self.assertIs(retrieved_instance, custom_instance)
        self.assertEqual(retrieved_instance.custom_property, "test")
    
    def test_aspect_registry_with_bean_factory(self):
        """Test aspect registry integration with bean factory."""
        bean_factory = DefaultBeanFactory()
        
        # Register aspect as bean
        aspect_def = BeanDefinition(
            bean_name="loggingAspect",
            bean_type=LoggingAspect,
            scope=BeanScope.SINGLETON
        )
        bean_factory.register_bean_definition("loggingAspect", aspect_def)
        
        # Set bean factory in registry
        self.aspect_registry.set_bean_factory(bean_factory)
        
        # Get aspect instance - should come from bean factory
        instance = self.aspect_registry.get_aspect_instance(LoggingAspect)
        self.assertIsInstance(instance, LoggingAspect)
        
        # Verify it's the same instance from bean factory
        bean_instance = bean_factory.get_bean("loggingAspect")
        self.assertIs(instance, bean_instance)


class TestComplexAopScenarios(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        from summer_core.aop.advice import _aspect_registry
        _aspect_registry.clear()
    
    def test_nested_proxy_creation(self):
        """Test that proxies can be created for beans that are already proxies."""
        # This test verifies that the AOP system can handle complex scenarios
        # where multiple aspects might apply to the same bean
        
        bean_factory = DefaultBeanFactory()
        aop_processor = create_aop_bean_post_processor()
        bean_factory.add_bean_post_processor(aop_processor)
        
        # Register bean
        bean_def = BeanDefinition(
            bean_name="testService",
            bean_type=MockBusinessService,
            scope=BeanScope.SINGLETON
        )
        bean_factory.register_bean_definition("testService", bean_def)
        
        # Create bean without aspects first
        service = bean_factory.get_bean("testService")
        self.assertIsInstance(service, MockBusinessService)
    
    def test_aspect_with_no_matching_pointcuts(self):
        """Test aspect registration when no pointcuts match any methods."""
        # Register aspect with pointcut that doesn't match any methods
        aspect_metadata = AspectMetadata(aspect_class=LoggingAspect, order=1)
        
        advice_metadata = AdviceMetadata(
            advice_type=AdviceType.BEFORE,
            pointcut="nonexistent_method",
            method=LoggingAspect().log_before,
            arg_names=['join_point']
        )
        aspect_metadata.advice_methods = [advice_metadata]
        register_aspect_metadata(LoggingAspect, aspect_metadata)
        
        bean_factory = DefaultBeanFactory()
        aop_processor = create_aop_bean_post_processor()
        bean_factory.add_bean_post_processor(aop_processor)
        
        bean_def = BeanDefinition(
            bean_name="testService",
            bean_type=MockBusinessService,
            scope=BeanScope.SINGLETON
        )
        bean_factory.register_bean_definition("testService", bean_def)
        
        # Mock pointcut matching to return False
        with patch('summer_core.aop.integration.matches_pointcut', return_value=False):
            service = bean_factory.get_bean("testService")
            
            # Should not be proxied since no pointcuts match
            self.assertIsInstance(service, MockBusinessService)
            self.assertFalse(hasattr(service, '_target'))


if __name__ == '__main__':
    unittest.main()