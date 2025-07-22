"""
Tests for the @transactional decorator.

This module tests the declarative transaction management functionality.
"""
import unittest
from unittest.mock import MagicMock, patch, call

from summer_core.decorators.transactional import (
    transactional,
    Transactional,
    TransactionalConfig,
    TransactionalInterceptor,
    is_transactional,
    get_transactional_config,
    get_transactional_interceptor,
)
from summer_core.exceptions import TransactionException
from summer_core.transaction.transaction_manager import (
    Isolation,
    PlatformTransactionManager,
    Propagation,
    TransactionDefinition,
    TransactionStatus,
    TransactionTemplate,
)


class TestTransactionalConfig(unittest.TestCase):
    """Test the TransactionalConfig class."""
    
    def test_default_config(self):
        """Test creating a config with default values."""
        config = TransactionalConfig()
        
        self.assertEqual(config.propagation, Propagation.REQUIRED)
        self.assertEqual(config.isolation, Isolation.DEFAULT)
        self.assertEqual(config.timeout, -1)
        self.assertFalse(config.read_only)
        self.assertEqual(config.rollback_for, [Exception])
        self.assertEqual(config.no_rollback_for, [])
        self.assertIsNone(config.transaction_manager)
    
    def test_custom_config(self):
        """Test creating a config with custom values."""
        config = TransactionalConfig(
            propagation=Propagation.REQUIRES_NEW,
            isolation=Isolation.SERIALIZABLE,
            timeout=30,
            read_only=True,
            rollback_for=[ValueError, RuntimeError],
            no_rollback_for=[KeyError],
            transaction_manager="customTxManager"
        )
        
        self.assertEqual(config.propagation, Propagation.REQUIRES_NEW)
        self.assertEqual(config.isolation, Isolation.SERIALIZABLE)
        self.assertEqual(config.timeout, 30)
        self.assertTrue(config.read_only)
        self.assertEqual(config.rollback_for, [ValueError, RuntimeError])
        self.assertEqual(config.no_rollback_for, [KeyError])
        self.assertEqual(config.transaction_manager, "customTxManager")
    
    def test_should_rollback_on_exception(self):
        """Test rollback decision logic."""
        config = TransactionalConfig(
            rollback_for=[ValueError, RuntimeError],
            no_rollback_for=[KeyError]
        )
        
        # Should rollback for specified exceptions
        self.assertTrue(config.should_rollback_on(ValueError("test")))
        self.assertTrue(config.should_rollback_on(RuntimeError("test")))
        
        # Should NOT rollback for no_rollback_for exceptions (takes precedence)
        self.assertFalse(config.should_rollback_on(KeyError("test")))
        
        # Should rollback for other exceptions (default behavior)
        self.assertTrue(config.should_rollback_on(TypeError("test")))
    
    def test_should_rollback_no_rollback_precedence(self):
        """Test that no_rollback_for takes precedence over rollback_for."""
        config = TransactionalConfig(
            rollback_for=[Exception],  # Would normally rollback for all
            no_rollback_for=[ValueError]  # But not for ValueError
        )
        
        # Should NOT rollback for ValueError despite being in rollback_for
        self.assertFalse(config.should_rollback_on(ValueError("test")))
        
        # Should rollback for other exceptions
        self.assertTrue(config.should_rollback_on(RuntimeError("test")))
    
    def test_to_transaction_definition(self):
        """Test converting config to TransactionDefinition."""
        config = TransactionalConfig(
            propagation=Propagation.NESTED,
            isolation=Isolation.READ_COMMITTED,
            timeout=60,
            read_only=True
        )
        
        definition = config.to_transaction_definition()
        
        self.assertEqual(definition.propagation, Propagation.NESTED)
        self.assertEqual(definition.isolation, Isolation.READ_COMMITTED)
        self.assertEqual(definition.timeout, 60)
        self.assertTrue(definition.read_only)


class TestTransactionalInterceptor(unittest.TestCase):
    """Test the TransactionalInterceptor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = TransactionalConfig()
        self.mock_transaction_manager = MagicMock(spec=PlatformTransactionManager)
        self.interceptor = TransactionalInterceptor(self.config, self.mock_transaction_manager)
    
    def test_get_transaction_manager_with_instance(self):
        """Test getting transaction manager when instance is provided."""
        # Get transaction manager
        tx_manager = self.interceptor.get_transaction_manager()
        
        # Verify it returns the provided instance
        self.assertEqual(tx_manager, self.mock_transaction_manager)
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_get_transaction_manager_from_sync_manager(self, mock_sync_manager):
        """Test getting transaction manager from synchronization manager."""
        # Create interceptor without transaction manager instance
        interceptor = TransactionalInterceptor(self.config)
        
        # Set up mock synchronization manager
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        # Get transaction manager
        tx_manager = interceptor.get_transaction_manager()
        
        # Verify correct calls
        mock_sync_manager.get_resource.assert_called_once_with('transaction_manager')
        self.assertEqual(tx_manager, self.mock_transaction_manager)
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_get_transaction_manager_no_manager(self, mock_sync_manager):
        """Test error when no transaction manager is available."""
        # Create interceptor without transaction manager instance
        interceptor = TransactionalInterceptor(self.config)
        
        mock_sync_manager.get_resource.return_value = None
        
        with self.assertRaises(TransactionException) as context:
            interceptor.get_transaction_manager()
        
        self.assertIn("No transaction manager available", str(context.exception))
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_invoke_successful(self, mock_sync_manager):
        """Test successful method invocation."""
        # Set up mocks
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        # Set up transaction status
        mock_status = MagicMock(spec=TransactionStatus)
        mock_status.is_rollback_only.return_value = False
        self.mock_transaction_manager.get_transaction.return_value = mock_status
        
        # Create test method
        def test_method(arg1, arg2, kwarg1=None):
            return f"called with {arg1}, {arg2}, {kwarg1}"
        
        # Invoke method
        result = self.interceptor.invoke(test_method, ("a", "b"), {"kwarg1": "c"})
        
        # Verify transaction manager was called correctly
        self.mock_transaction_manager.get_transaction.assert_called_once()
        self.mock_transaction_manager.commit.assert_called_once_with(mock_status)
        self.mock_transaction_manager.rollback.assert_not_called()
        
        # Verify synchronization manager was called
        mock_sync_manager.set_transaction_active.assert_has_calls([call(True), call(False)])
        mock_sync_manager.set_current_transaction.assert_has_calls([call(mock_status.transaction_object), call(None)])
        
        # Verify result
        self.assertEqual(result, "called with a, b, c")
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_invoke_with_exception(self, mock_sync_manager):
        """Test method invocation with exception."""
        # Set up mocks
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        # Set up transaction status
        mock_status = MagicMock(spec=TransactionStatus)
        mock_status.is_rollback_only.return_value = False
        self.mock_transaction_manager.get_transaction.return_value = mock_status
        
        # Create test method
        def test_method():
            raise ValueError("Test error")
        
        # Invoke method and verify exception is wrapped
        with self.assertRaises(TransactionException) as context:
            self.interceptor.invoke(test_method, (), {})
        
        # Verify transaction was rolled back
        self.mock_transaction_manager.get_transaction.assert_called_once()
        self.mock_transaction_manager.rollback.assert_called_once_with(mock_status)
        self.mock_transaction_manager.commit.assert_not_called()
        
        # Verify synchronization manager cleanup
        mock_sync_manager.set_transaction_active.assert_has_calls([call(True), call(False)])
        mock_sync_manager.set_current_transaction.assert_has_calls([call(mock_status.transaction_object), call(None)])
        
        self.assertIn("Transactional method execution failed", str(context.exception))


class TestTransactionalDecorator(unittest.TestCase):
    """Test the @transactional decorator."""
    
    def test_decorator_with_defaults(self):
        """Test decorator with default parameters."""
        @transactional()
        def test_method():
            return "result"
        
        # Verify metadata is attached
        self.assertTrue(is_transactional(test_method))
        config = get_transactional_config(test_method)
        self.assertIsNotNone(config)
        self.assertEqual(config.propagation, Propagation.REQUIRED)
        self.assertEqual(config.isolation, Isolation.DEFAULT)
        
        interceptor = get_transactional_interceptor(test_method)
        self.assertIsNotNone(interceptor)
        self.assertEqual(interceptor.config, config)
    
    def test_decorator_with_custom_parameters(self):
        """Test decorator with custom parameters."""
        @transactional(
            propagation=Propagation.REQUIRES_NEW,
            isolation=Isolation.SERIALIZABLE,
            timeout=30,
            read_only=True,
            rollback_for=[ValueError],
            no_rollback_for=[KeyError],
            transaction_manager="customTxManager"
        )
        def test_method():
            return "result"
        
        # Verify metadata is attached with correct values
        self.assertTrue(is_transactional(test_method))
        config = get_transactional_config(test_method)
        self.assertIsNotNone(config)
        self.assertEqual(config.propagation, Propagation.REQUIRES_NEW)
        self.assertEqual(config.isolation, Isolation.SERIALIZABLE)
        self.assertEqual(config.timeout, 30)
        self.assertTrue(config.read_only)
        self.assertEqual(config.rollback_for, [ValueError])
        self.assertEqual(config.no_rollback_for, [KeyError])
        self.assertEqual(config.transaction_manager, "customTxManager")
    
    def test_transactional_alias(self):
        """Test that Transactional is an alias for transactional."""
        self.assertEqual(Transactional, transactional)
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_decorated_method_execution(self, mock_sync_manager):
        """Test execution of a decorated method."""
        # Set up mock synchronization manager
        mock_transaction_manager = MagicMock(spec=PlatformTransactionManager)
        mock_sync_manager.get_resource.return_value = mock_transaction_manager
        
        # Set up mock transaction status
        mock_status = MagicMock(spec=TransactionStatus)
        mock_status.is_rollback_only.return_value = False
        mock_transaction_manager.get_transaction.return_value = mock_status
        
        @transactional()
        def test_method(arg1, arg2):
            return f"called with {arg1}, {arg2}"
        
        # Call the decorated method
        result = test_method("a", "b")
        
        # Verify transaction manager was used
        mock_transaction_manager.get_transaction.assert_called_once()
        mock_transaction_manager.commit.assert_called_once_with(mock_status)
        mock_transaction_manager.rollback.assert_not_called()
        
        # Verify result
        self.assertEqual(result, "called with a, b")
    
    def test_non_transactional_method(self):
        """Test utility functions with non-transactional method."""
        def regular_method():
            return "result"
        
        self.assertFalse(is_transactional(regular_method))
        self.assertIsNone(get_transactional_config(regular_method))
        self.assertIsNone(get_transactional_interceptor(regular_method))
    
    def test_async_method_decoration(self):
        """Test decorating async methods."""
        @transactional()
        async def async_test_method():
            return "async_result"
        
        # Verify metadata is attached
        self.assertTrue(is_transactional(async_test_method))
        config = get_transactional_config(async_test_method)
        self.assertIsNotNone(config)
        
        # Verify it's still a coroutine function
        import inspect
        self.assertTrue(inspect.iscoroutinefunction(async_test_method))


class TestTransactionalIntegration(unittest.TestCase):
    """Integration tests for transactional functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_transaction_manager = MagicMock(spec=PlatformTransactionManager)
        self.mock_status = MagicMock(spec=TransactionStatus)
        self.mock_transaction_manager.get_transaction.return_value = self.mock_status
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_successful_transaction_flow(self, mock_sync_manager):
        """Test complete successful transaction flow."""
        # Set up mock synchronization manager
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        # Set up transaction status
        self.mock_status.is_rollback_only.return_value = False
        
        @transactional()
        def business_method():
            return "business_result"
        
        # Execute the method
        result = business_method()
        
        # Verify transaction manager was called
        self.mock_transaction_manager.get_transaction.assert_called_once()
        self.mock_transaction_manager.commit.assert_called_once_with(self.mock_status)
        self.mock_transaction_manager.rollback.assert_not_called()
        
        # Verify result
        self.assertEqual(result, "business_result")
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_rollback_on_exception(self, mock_sync_manager):
        """Test transaction rollback on exception."""
        # Set up mock synchronization manager
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        @transactional()
        def failing_method():
            raise ValueError("Business logic error")
        
        # Execute the method and expect exception
        with self.assertRaises(TransactionException):
            failing_method()
        
        # Verify transaction manager was called
        self.mock_transaction_manager.get_transaction.assert_called_once()
        self.mock_transaction_manager.rollback.assert_called_once_with(self.mock_status)
        self.mock_transaction_manager.commit.assert_not_called()
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_custom_rollback_rules(self, mock_sync_manager):
        """Test custom rollback rules."""
        # Set up mock synchronization manager
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        # Set up transaction status
        self.mock_status.is_rollback_only.return_value = False
        
        @transactional(no_rollback_for=[ValueError])
        def method_with_custom_rules():
            raise ValueError("Should not rollback")
        
        # Execute the method
        with self.assertRaises(TransactionException):
            method_with_custom_rules()
        
        # Verify transaction was committed (not rolled back) for ValueError
        self.mock_transaction_manager.get_transaction.assert_called_once()
        self.mock_transaction_manager.commit.assert_called_once_with(self.mock_status)
        self.mock_transaction_manager.rollback.assert_not_called()
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_propagation_behavior(self, mock_sync_manager):
        """Test different propagation behaviors."""
        # Set up mock synchronization manager
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        # Set up transaction status
        self.mock_status.is_rollback_only.return_value = False
        
        @transactional(propagation=Propagation.REQUIRES_NEW)
        def requires_new_method():
            return "result"
        
        # Execute the method
        result = requires_new_method()
        
        # Verify transaction definition was created with correct propagation
        self.mock_transaction_manager.get_transaction.assert_called_once()
        call_args = self.mock_transaction_manager.get_transaction.call_args
        definition = call_args[0][0] if call_args[0] else call_args[1]['definition']
        self.assertEqual(definition.propagation, Propagation.REQUIRES_NEW)
        
        # Verify transaction was committed
        self.mock_transaction_manager.commit.assert_called_once_with(self.mock_status)
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_isolation_level(self, mock_sync_manager):
        """Test isolation level configuration."""
        # Set up mock synchronization manager
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        @transactional(isolation=Isolation.SERIALIZABLE)
        def serializable_method():
            return "result"
        
        # Execute the method
        result = serializable_method()
        
        # Verify transaction definition was created with correct isolation
        self.mock_transaction_manager.get_transaction.assert_called_once()
        call_args = self.mock_transaction_manager.get_transaction.call_args
        definition = call_args[0][0] if call_args[0] else call_args[1]['definition']
        self.assertEqual(definition.isolation, Isolation.SERIALIZABLE)
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_timeout_configuration(self, mock_sync_manager):
        """Test timeout configuration."""
        # Set up mock synchronization manager
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        @transactional(timeout=30)
        def timed_method():
            return "result"
        
        # Execute the method
        result = timed_method()
        
        # Verify transaction definition was created with correct timeout
        self.mock_transaction_manager.get_transaction.assert_called_once()
        call_args = self.mock_transaction_manager.get_transaction.call_args
        definition = call_args[0][0] if call_args[0] else call_args[1]['definition']
        self.assertEqual(definition.timeout, 30)
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_read_only_transaction(self, mock_sync_manager):
        """Test read-only transaction configuration."""
        # Set up mock synchronization manager
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        @transactional(read_only=True)
        def read_only_method():
            return "result"
        
        # Execute the method
        result = read_only_method()
        
        # Verify transaction definition was created with read-only flag
        self.mock_transaction_manager.get_transaction.assert_called_once()
        call_args = self.mock_transaction_manager.get_transaction.call_args
        definition = call_args[0][0] if call_args[0] else call_args[1]['definition']
        self.assertTrue(definition.read_only)


class TestTransactionalPropagationBehavior(unittest.TestCase):
    """Test transaction propagation behaviors in detail."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_transaction_manager = MagicMock(spec=PlatformTransactionManager)
        self.mock_status = MagicMock(spec=TransactionStatus)
        self.mock_transaction_manager.get_transaction.return_value = self.mock_status
        self.mock_status.is_rollback_only.return_value = False
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_propagation_required(self, mock_sync_manager):
        """Test REQUIRED propagation behavior."""
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        @transactional(propagation=Propagation.REQUIRED)
        def required_method():
            return "required_result"
        
        result = required_method()
        
        # Verify transaction definition has REQUIRED propagation
        call_args = self.mock_transaction_manager.get_transaction.call_args
        definition = call_args[0][0]
        self.assertEqual(definition.propagation, Propagation.REQUIRED)
        self.assertEqual(result, "required_result")
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_propagation_requires_new(self, mock_sync_manager):
        """Test REQUIRES_NEW propagation behavior."""
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        @transactional(propagation=Propagation.REQUIRES_NEW)
        def requires_new_method():
            return "new_transaction_result"
        
        result = requires_new_method()
        
        # Verify transaction definition has REQUIRES_NEW propagation
        call_args = self.mock_transaction_manager.get_transaction.call_args
        definition = call_args[0][0]
        self.assertEqual(definition.propagation, Propagation.REQUIRES_NEW)
        self.assertEqual(result, "new_transaction_result")
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_propagation_supports(self, mock_sync_manager):
        """Test SUPPORTS propagation behavior."""
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        @transactional(propagation=Propagation.SUPPORTS)
        def supports_method():
            return "supports_result"
        
        result = supports_method()
        
        # Verify transaction definition has SUPPORTS propagation
        call_args = self.mock_transaction_manager.get_transaction.call_args
        definition = call_args[0][0]
        self.assertEqual(definition.propagation, Propagation.SUPPORTS)
        self.assertEqual(result, "supports_result")
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_propagation_nested(self, mock_sync_manager):
        """Test NESTED propagation behavior."""
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        @transactional(propagation=Propagation.NESTED)
        def nested_method():
            return "nested_result"
        
        result = nested_method()
        
        # Verify transaction definition has NESTED propagation
        call_args = self.mock_transaction_manager.get_transaction.call_args
        definition = call_args[0][0]
        self.assertEqual(definition.propagation, Propagation.NESTED)
        self.assertEqual(result, "nested_result")


class TestTransactionalIsolationLevels(unittest.TestCase):
    """Test transaction isolation levels in detail."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_transaction_manager = MagicMock(spec=PlatformTransactionManager)
        self.mock_status = MagicMock(spec=TransactionStatus)
        self.mock_transaction_manager.get_transaction.return_value = self.mock_status
        self.mock_status.is_rollback_only.return_value = False
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_isolation_read_uncommitted(self, mock_sync_manager):
        """Test READ_UNCOMMITTED isolation level."""
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        @transactional(isolation=Isolation.READ_UNCOMMITTED)
        def read_uncommitted_method():
            return "read_uncommitted_result"
        
        result = read_uncommitted_method()
        
        # Verify transaction definition has READ_UNCOMMITTED isolation
        call_args = self.mock_transaction_manager.get_transaction.call_args
        definition = call_args[0][0]
        self.assertEqual(definition.isolation, Isolation.READ_UNCOMMITTED)
        self.assertEqual(result, "read_uncommitted_result")
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_isolation_read_committed(self, mock_sync_manager):
        """Test READ_COMMITTED isolation level."""
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        @transactional(isolation=Isolation.READ_COMMITTED)
        def read_committed_method():
            return "read_committed_result"
        
        result = read_committed_method()
        
        # Verify transaction definition has READ_COMMITTED isolation
        call_args = self.mock_transaction_manager.get_transaction.call_args
        definition = call_args[0][0]
        self.assertEqual(definition.isolation, Isolation.READ_COMMITTED)
        self.assertEqual(result, "read_committed_result")
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_isolation_repeatable_read(self, mock_sync_manager):
        """Test REPEATABLE_READ isolation level."""
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        @transactional(isolation=Isolation.REPEATABLE_READ)
        def repeatable_read_method():
            return "repeatable_read_result"
        
        result = repeatable_read_method()
        
        # Verify transaction definition has REPEATABLE_READ isolation
        call_args = self.mock_transaction_manager.get_transaction.call_args
        definition = call_args[0][0]
        self.assertEqual(definition.isolation, Isolation.REPEATABLE_READ)
        self.assertEqual(result, "repeatable_read_result")
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_isolation_serializable(self, mock_sync_manager):
        """Test SERIALIZABLE isolation level."""
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        @transactional(isolation=Isolation.SERIALIZABLE)
        def serializable_method():
            return "serializable_result"
        
        result = serializable_method()
        
        # Verify transaction definition has SERIALIZABLE isolation
        call_args = self.mock_transaction_manager.get_transaction.call_args
        definition = call_args[0][0]
        self.assertEqual(definition.isolation, Isolation.SERIALIZABLE)
        self.assertEqual(result, "serializable_result")


class TestTransactionalTimeoutAndReadOnly(unittest.TestCase):
    """Test transaction timeout and read-only configurations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_transaction_manager = MagicMock(spec=PlatformTransactionManager)
        self.mock_status = MagicMock(spec=TransactionStatus)
        self.mock_transaction_manager.get_transaction.return_value = self.mock_status
        self.mock_status.is_rollback_only.return_value = False
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_timeout_configuration_values(self, mock_sync_manager):
        """Test various timeout values."""
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        # Test different timeout values
        timeout_values = [10, 30, 60, 120, 300]
        
        for timeout in timeout_values:
            with self.subTest(timeout=timeout):
                @transactional(timeout=timeout)
                def timed_method():
                    return f"timeout_{timeout}_result"
                
                result = timed_method()
                
                # Verify transaction definition has correct timeout
                call_args = self.mock_transaction_manager.get_transaction.call_args
                definition = call_args[0][0]
                self.assertEqual(definition.timeout, timeout)
                self.assertEqual(result, f"timeout_{timeout}_result")
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_read_only_true_and_false(self, mock_sync_manager):
        """Test read-only configuration."""
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        # Test read-only = True
        @transactional(read_only=True)
        def read_only_method():
            return "read_only_result"
        
        result = read_only_method()
        
        call_args = self.mock_transaction_manager.get_transaction.call_args
        definition = call_args[0][0]
        self.assertTrue(definition.read_only)
        self.assertEqual(result, "read_only_result")
        
        # Reset mock
        self.mock_transaction_manager.reset_mock()
        
        # Test read-only = False
        @transactional(read_only=False)
        def read_write_method():
            return "read_write_result"
        
        result = read_write_method()
        
        call_args = self.mock_transaction_manager.get_transaction.call_args
        definition = call_args[0][0]
        self.assertFalse(definition.read_only)
        self.assertEqual(result, "read_write_result")


class TestTransactionalRollbackRules(unittest.TestCase):
    """Test detailed rollback rule scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_transaction_manager = MagicMock(spec=PlatformTransactionManager)
        self.mock_status = MagicMock(spec=TransactionStatus)
        self.mock_transaction_manager.get_transaction.return_value = self.mock_status
        self.mock_status.is_rollback_only.return_value = False
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_rollback_for_specific_exceptions(self, mock_sync_manager):
        """Test rollback for specific exception types."""
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        @transactional(rollback_for=[ValueError, TypeError])
        def specific_rollback_method(exception_type):
            if exception_type == "value":
                raise ValueError("Value error")
            elif exception_type == "type":
                raise TypeError("Type error")
            elif exception_type == "runtime":
                raise RuntimeError("Runtime error")
            return "success"
        
        # Test ValueError - should rollback
        with self.assertRaises(TransactionException):
            specific_rollback_method("value")
        self.mock_transaction_manager.rollback.assert_called_once()
        self.mock_transaction_manager.commit.assert_not_called()
        
        # Reset mock
        self.mock_transaction_manager.reset_mock()
        
        # Test TypeError - should rollback
        with self.assertRaises(TransactionException):
            specific_rollback_method("type")
        self.mock_transaction_manager.rollback.assert_called_once()
        self.mock_transaction_manager.commit.assert_not_called()
        
        # Reset mock
        self.mock_transaction_manager.reset_mock()
        
        # Test RuntimeError - should also rollback (default behavior)
        with self.assertRaises(TransactionException):
            specific_rollback_method("runtime")
        self.mock_transaction_manager.rollback.assert_called_once()
        self.mock_transaction_manager.commit.assert_not_called()
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_no_rollback_for_specific_exceptions(self, mock_sync_manager):
        """Test no rollback for specific exception types."""
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        @transactional(no_rollback_for=[ValueError])
        def no_rollback_method(exception_type):
            if exception_type == "value":
                raise ValueError("Value error - should not rollback")
            elif exception_type == "runtime":
                raise RuntimeError("Runtime error - should rollback")
            return "success"
        
        # Test ValueError - should NOT rollback
        with self.assertRaises(TransactionException):
            no_rollback_method("value")
        self.mock_transaction_manager.commit.assert_called_once()
        self.mock_transaction_manager.rollback.assert_not_called()
        
        # Reset mock
        self.mock_transaction_manager.reset_mock()
        
        # Test RuntimeError - should rollback
        with self.assertRaises(TransactionException):
            no_rollback_method("runtime")
        self.mock_transaction_manager.rollback.assert_called_once()
        self.mock_transaction_manager.commit.assert_not_called()
    
    @patch('summer_core.decorators.transactional.TransactionSynchronizationManager')
    def test_complex_rollback_rules(self, mock_sync_manager):
        """Test complex rollback rule combinations."""
        mock_sync_manager.get_resource.return_value = self.mock_transaction_manager
        
        @transactional(
            rollback_for=[Exception],  # Rollback for all exceptions
            no_rollback_for=[ValueError, KeyError]  # Except these specific ones
        )
        def complex_rollback_method(exception_type):
            if exception_type == "value":
                raise ValueError("Should not rollback")
            elif exception_type == "key":
                raise KeyError("Should not rollback")
            elif exception_type == "runtime":
                raise RuntimeError("Should rollback")
            return "success"
        
        # Test ValueError - should NOT rollback (no_rollback_for takes precedence)
        with self.assertRaises(TransactionException):
            complex_rollback_method("value")
        self.mock_transaction_manager.commit.assert_called_once()
        self.mock_transaction_manager.rollback.assert_not_called()
        
        # Reset mock
        self.mock_transaction_manager.reset_mock()
        
        # Test KeyError - should NOT rollback
        with self.assertRaises(TransactionException):
            complex_rollback_method("key")
        self.mock_transaction_manager.commit.assert_called_once()
        self.mock_transaction_manager.rollback.assert_not_called()
        
        # Reset mock
        self.mock_transaction_manager.reset_mock()
        
        # Test RuntimeError - should rollback
        with self.assertRaises(TransactionException):
            complex_rollback_method("runtime")
        self.mock_transaction_manager.rollback.assert_called_once()
        self.mock_transaction_manager.commit.assert_not_called()


if __name__ == '__main__':
    unittest.main()