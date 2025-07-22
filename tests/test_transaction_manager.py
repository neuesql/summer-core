"""
Tests for the transaction management system.

This module tests the transaction manager interfaces and implementations.
"""
import unittest
from unittest.mock import MagicMock, patch

from summer_core.exceptions import TransactionException
from summer_core.transaction import (
    DEFAULT_TRANSACTION_DEFINITION,
    Isolation,
    JDBCLikeTransactionManager,
    PlatformTransactionManager,
    Propagation,
    SQLAlchemyTransactionManager,
    TransactionDefinition,
    TransactionStatus,
    TransactionSynchronizationManager,
    TransactionTemplate,
)


class TestTransactionStatus(unittest.TestCase):
    """Test the TransactionStatus class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.transaction_manager = MagicMock(spec=PlatformTransactionManager)
        self.transaction_object = MagicMock()
    
    def test_transaction_status_creation(self):
        """Test creating a transaction status."""
        status = TransactionStatus(
            transaction_manager=self.transaction_manager,
            transaction_object=self.transaction_object,
            new_transaction=True
        )
        
        self.assertEqual(status.transaction_object, self.transaction_object)
        self.assertTrue(status.is_new_transaction())
        self.assertFalse(status.is_completed())
        self.assertFalse(status.is_rollback_only())
    
    def test_set_rollback_only(self):
        """Test setting rollback only flag."""
        status = TransactionStatus(
            transaction_manager=self.transaction_manager,
            transaction_object=self.transaction_object
        )
        
        self.assertFalse(status.is_rollback_only())
        status.set_rollback_only()
        self.assertTrue(status.is_rollback_only())


class TestTransactionDefinition(unittest.TestCase):
    """Test the TransactionDefinition class."""
    
    def test_default_transaction_definition(self):
        """Test the default transaction definition."""
        definition = DEFAULT_TRANSACTION_DEFINITION
        
        self.assertEqual(definition.get_propagation(), Propagation.REQUIRED)
        self.assertEqual(definition.get_isolation(), Isolation.DEFAULT)
        self.assertEqual(definition.get_timeout(), -1)
        self.assertFalse(definition.is_read_only())
        self.assertIsNone(definition.get_name())
    
    def test_custom_transaction_definition(self):
        """Test creating a custom transaction definition."""
        definition = TransactionDefinition(
            propagation=Propagation.REQUIRES_NEW,
            isolation=Isolation.SERIALIZABLE,
            timeout=30,
            read_only=True,
            name="test-transaction"
        )
        
        self.assertEqual(definition.get_propagation(), Propagation.REQUIRES_NEW)
        self.assertEqual(definition.get_isolation(), Isolation.SERIALIZABLE)
        self.assertEqual(definition.get_timeout(), 30)
        self.assertTrue(definition.is_read_only())
        self.assertEqual(definition.get_name(), "test-transaction")


class TestTransactionSynchronizationManager(unittest.TestCase):
    """Test the TransactionSynchronizationManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        TransactionSynchronizationManager.clear()
    
    def tearDown(self):
        """Clean up after tests."""
        TransactionSynchronizationManager.clear()
    
    def test_resource_binding(self):
        """Test binding and retrieving resources."""
        # Bind a resource
        TransactionSynchronizationManager.bind_resource("test-key", "test-value")
        
        # Check if resource exists
        self.assertTrue(TransactionSynchronizationManager.has_resource("test-key"))
        
        # Get the resource
        value = TransactionSynchronizationManager.get_resource("test-key")
        self.assertEqual(value, "test-value")
        
        # Unbind the resource
        unbound_value = TransactionSynchronizationManager.unbind_resource("test-key")
        self.assertEqual(unbound_value, "test-value")
        
        # Check that resource is gone
        self.assertFalse(TransactionSynchronizationManager.has_resource("test-key"))
    
    def test_transaction_active_flag(self):
        """Test setting and checking transaction active flag."""
        self.assertFalse(TransactionSynchronizationManager.is_transaction_active())
        
        TransactionSynchronizationManager.set_transaction_active(True)
        self.assertTrue(TransactionSynchronizationManager.is_transaction_active())
        
        TransactionSynchronizationManager.set_transaction_active(False)
        self.assertFalse(TransactionSynchronizationManager.is_transaction_active())
    
    def test_current_transaction(self):
        """Test setting and getting current transaction."""
        transaction = MagicMock()
        
        self.assertIsNone(TransactionSynchronizationManager.get_current_transaction())
        
        TransactionSynchronizationManager.set_current_transaction(transaction)
        self.assertEqual(TransactionSynchronizationManager.get_current_transaction(), transaction)
        
        TransactionSynchronizationManager.set_current_transaction(None)
        self.assertIsNone(TransactionSynchronizationManager.get_current_transaction())


class TestSQLAlchemyTransactionManager(unittest.TestCase):
    """Test the SQLAlchemyTransactionManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock session factory
        self.session = MagicMock()
        self.transaction = MagicMock()
        self.session.begin.return_value = self.transaction
        self.session_factory = MagicMock(return_value=self.session)
        
        # Create transaction manager
        self.transaction_manager = SQLAlchemyTransactionManager(self.session_factory)
        
        # Clear synchronization manager
        TransactionSynchronizationManager.clear()
    
    def tearDown(self):
        """Clean up after tests."""
        TransactionSynchronizationManager.clear()
    
    def test_begin_transaction(self):
        """Test beginning a new transaction."""
        # Begin a new transaction
        status = self.transaction_manager.get_transaction()
        
        # Verify session factory was called
        self.session_factory.assert_called_once()
        
        # Verify session.begin was called
        self.session.begin.assert_called_once()
        
        # Verify transaction status
        self.assertEqual(status.connection, self.session)
        self.assertEqual(status.transaction_object, self.transaction)
        self.assertTrue(status.is_new_transaction())
        self.assertFalse(status.is_completed())
        
        # Verify synchronization manager state
        self.assertTrue(TransactionSynchronizationManager.is_transaction_active())
        self.assertEqual(
            TransactionSynchronizationManager.get_resource('sqlalchemy_session'),
            self.session
        )
        self.assertEqual(
            TransactionSynchronizationManager.get_current_transaction(),
            self.transaction
        )
    
    def test_commit_transaction(self):
        """Test committing a transaction."""
        # Begin a new transaction
        status = self.transaction_manager.get_transaction()
        
        # Commit the transaction
        self.transaction_manager.commit(status)
        
        # Verify session.commit was called
        self.session.commit.assert_called_once()
        
        # Verify transaction status
        self.assertTrue(status.is_completed())
        
        # Verify synchronization manager state
        self.assertFalse(TransactionSynchronizationManager.is_transaction_active())
        self.assertIsNone(TransactionSynchronizationManager.get_current_transaction())
        self.assertFalse(TransactionSynchronizationManager.has_resource('sqlalchemy_session'))
    
    def test_rollback_transaction(self):
        """Test rolling back a transaction."""
        # Begin a new transaction
        status = self.transaction_manager.get_transaction()
        
        # Roll back the transaction
        self.transaction_manager.rollback(status)
        
        # Verify session.rollback was called
        self.session.rollback.assert_called_once()
        
        # Verify transaction status
        self.assertTrue(status.is_completed())
        
        # Verify synchronization manager state
        self.assertFalse(TransactionSynchronizationManager.is_transaction_active())
        self.assertIsNone(TransactionSynchronizationManager.get_current_transaction())
        self.assertFalse(TransactionSynchronizationManager.has_resource('sqlalchemy_session'))
    
    def test_nested_transaction(self):
        """Test creating a nested transaction."""
        # Begin a new transaction
        self.transaction_manager.get_transaction()
        
        # Create a nested transaction
        nested_def = TransactionDefinition(propagation=Propagation.NESTED)
        status = self.transaction_manager.get_transaction(nested_def)
        
        # Verify session.begin_nested was called
        self.session.begin_nested.assert_called_once()
        
        # Verify transaction status
        self.assertFalse(status.is_new_transaction())
        self.assertIsNotNone(status.savepoint_name)
    
    def test_requires_new_transaction(self):
        """Test creating a new transaction with REQUIRES_NEW."""
        # Begin a new transaction
        self.transaction_manager.get_transaction()
        
        # Create a new transaction with REQUIRES_NEW
        new_session = MagicMock()
        new_transaction = MagicMock()
        new_session.begin.return_value = new_transaction
        self.session_factory.return_value = new_session
        
        requires_new_def = TransactionDefinition(propagation=Propagation.REQUIRES_NEW)
        status = self.transaction_manager.get_transaction(requires_new_def)
        
        # Verify session factory was called again
        self.assertEqual(self.session_factory.call_count, 2)
        
        # Verify transaction status
        self.assertEqual(status.connection, new_session)
        self.assertEqual(status.transaction_object, new_transaction)
        self.assertTrue(status.is_new_transaction())
    
    def test_commit_error(self):
        """Test error handling during commit."""
        # Begin a new transaction
        status = self.transaction_manager.get_transaction()
        
        # Make commit throw an exception
        self.session.commit.side_effect = Exception("Commit failed")
        
        # Verify exception is wrapped
        with self.assertRaises(TransactionException) as context:
            self.transaction_manager.commit(status)
        
        self.assertIn("Could not commit transaction", str(context.exception))


class TestJDBCLikeTransactionManager(unittest.TestCase):
    """Test the JDBCLikeTransactionManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock connection factory
        self.connection = MagicMock()
        self.cursor = MagicMock()
        self.connection.cursor.return_value = self.cursor
        self.connection_factory = MagicMock(return_value=self.connection)
        
        # Create transaction manager
        self.transaction_manager = JDBCLikeTransactionManager(self.connection_factory)
        
        # Clear synchronization manager
        TransactionSynchronizationManager.clear()
    
    def tearDown(self):
        """Clean up after tests."""
        TransactionSynchronizationManager.clear()
    
    def test_begin_transaction(self):
        """Test beginning a new transaction."""
        # Begin a new transaction
        status = self.transaction_manager.get_transaction()
        
        # Verify connection factory was called
        self.connection_factory.assert_called_once()
        
        # Verify autocommit was disabled
        self.assertFalse(self.connection.autocommit)
        
        # Verify transaction status
        self.assertEqual(status.connection, self.connection)
        self.assertEqual(status.transaction_object, self.connection)
        self.assertTrue(status.is_new_transaction())
        self.assertFalse(status.is_completed())
        
        # Verify synchronization manager state
        self.assertTrue(TransactionSynchronizationManager.is_transaction_active())
        self.assertEqual(
            TransactionSynchronizationManager.get_resource('jdbc_connection'),
            self.connection
        )
        self.assertEqual(
            TransactionSynchronizationManager.get_current_transaction(),
            self.connection
        )
    
    def test_commit_transaction(self):
        """Test committing a transaction."""
        # Begin a new transaction
        status = self.transaction_manager.get_transaction()
        
        # Commit the transaction
        self.transaction_manager.commit(status)
        
        # Verify connection.commit was called
        self.connection.commit.assert_called_once()
        
        # Verify transaction status
        self.assertTrue(status.is_completed())
        
        # Verify synchronization manager state
        self.assertFalse(TransactionSynchronizationManager.is_transaction_active())
        self.assertIsNone(TransactionSynchronizationManager.get_current_transaction())
        self.assertFalse(TransactionSynchronizationManager.has_resource('jdbc_connection'))
    
    def test_rollback_transaction(self):
        """Test rolling back a transaction."""
        # Begin a new transaction
        status = self.transaction_manager.get_transaction()
        
        # Roll back the transaction
        self.transaction_manager.rollback(status)
        
        # Verify connection.rollback was called
        self.connection.rollback.assert_called_once()
        
        # Verify transaction status
        self.assertTrue(status.is_completed())
        
        # Verify synchronization manager state
        self.assertFalse(TransactionSynchronizationManager.is_transaction_active())
        self.assertIsNone(TransactionSynchronizationManager.get_current_transaction())
        self.assertFalse(TransactionSynchronizationManager.has_resource('jdbc_connection'))
    
    def test_nested_transaction(self):
        """Test creating a nested transaction."""
        # Begin a new transaction
        self.transaction_manager.get_transaction()
        
        # Create a nested transaction
        nested_def = TransactionDefinition(propagation=Propagation.NESTED)
        status = self.transaction_manager.get_transaction(nested_def)
        
        # Verify savepoint was created
        self.cursor.execute.assert_called_once()
        self.assertIn("SAVEPOINT", self.cursor.execute.call_args[0][0])
        
        # Verify transaction status
        self.assertFalse(status.is_new_transaction())
        self.assertIsNotNone(status.savepoint_name)
    
    def test_isolation_level_setting(self):
        """Test setting isolation level."""
        # Begin a new transaction with specific isolation
        isolation_def = TransactionDefinition(isolation=Isolation.SERIALIZABLE)
        self.transaction_manager.get_transaction(isolation_def)
        
        # Verify isolation level was set
        self.cursor.execute.assert_called_once()
        self.assertIn("ISOLATION LEVEL SERIALIZABLE", self.cursor.execute.call_args[0][0])


class TestTransactionTemplate(unittest.TestCase):
    """Test the TransactionTemplate class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.transaction_manager = MagicMock(spec=PlatformTransactionManager)
        self.status = MagicMock(spec=TransactionStatus)
        self.transaction_manager.get_transaction.return_value = self.status
        
        self.template = TransactionTemplate(self.transaction_manager)
    
    def test_successful_execution(self):
        """Test successful execution of a callback."""
        # Set up status
        self.status.is_rollback_only.return_value = False
        
        # Define callback
        callback = MagicMock(return_value="result")
        
        # Execute template
        result = self.template.execute(callback)
        
        # Verify callback was called
        callback.assert_called_once()
        
        # Verify transaction was committed
        self.transaction_manager.commit.assert_called_once_with(self.status)
        self.transaction_manager.rollback.assert_not_called()
        
        # Verify result
        self.assertEqual(result, "result")
    
    def test_rollback_only_execution(self):
        """Test execution with rollback-only flag."""
        # Set up status
        self.status.is_rollback_only.return_value = True
        
        # Define callback
        callback = MagicMock(return_value="result")
        
        # Execute template
        result = self.template.execute(callback)
        
        # Verify callback was called
        callback.assert_called_once()
        
        # Verify transaction was rolled back
        self.transaction_manager.rollback.assert_called_once_with(self.status)
        self.transaction_manager.commit.assert_not_called()
        
        # Verify result
        self.assertEqual(result, "result")
    
    def test_exception_handling(self):
        """Test handling exceptions in callback."""
        # Define callback that raises an exception
        callback = MagicMock(side_effect=ValueError("Test error"))
        
        # Execute template and verify exception is wrapped
        with self.assertRaises(TransactionException) as context:
            self.template.execute(callback)
        
        # Verify callback was called
        callback.assert_called_once()
        
        # Verify transaction was rolled back
        self.transaction_manager.rollback.assert_called_once_with(self.status)
        self.transaction_manager.commit.assert_not_called()
        
        # Verify exception message
        self.assertIn("Transaction callback failed", str(context.exception))


if __name__ == '__main__':
    unittest.main()