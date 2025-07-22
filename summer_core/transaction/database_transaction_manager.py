"""
Database Transaction Manager Implementation.

This module provides a concrete implementation of the PlatformTransactionManager
interface for database transactions, supporting various database backends.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

from summer_core.exceptions import TransactionError
from summer_core.transaction.transaction_manager import (
    DEFAULT_TRANSACTION_DEFINITION,
    Isolation,
    PlatformTransactionManager,
    Propagation,
    TransactionDefinition,
    TransactionStatus,
    TransactionSynchronizationManager,
)


class DatabaseTransactionStatus(TransactionStatus):
    """
    Database-specific transaction status.
    
    Extends the base TransactionStatus with database-specific functionality.
    """
    
    def __init__(self,
                 transaction_manager: 'AbstractDatabaseTransactionManager',
                 connection: Any = None,
                 transaction_object: Any = None,
                 new_transaction: bool = True,
                 rollback_only: bool = False,
                 completed: bool = False,
                 savepoint_name: Optional[str] = None):
        """
        Initialize a new database transaction status.
        
        Args:
            transaction_manager: The transaction manager that created this status
            connection: The database connection
            transaction_object: The underlying transaction object
            new_transaction: Whether this is a new transaction
            rollback_only: Whether this transaction is marked for rollback only
            completed: Whether this transaction has been completed
            savepoint_name: The name of the savepoint (for nested transactions)
        """
        super().__init__(
            transaction_manager=transaction_manager,
            transaction_object=transaction_object,
            new_transaction=new_transaction,
            rollback_only=rollback_only,
            completed=completed
        )
        self._connection = connection
        self._savepoint_name = savepoint_name
    
    @property
    def connection(self) -> Any:
        """Get the database connection."""
        return self._connection
    
    @property
    def savepoint_name(self) -> Optional[str]:
        """Get the savepoint name for nested transactions."""
        return self._savepoint_name
    
    def flush(self) -> None:
        """
        Flush the underlying session to the database.
        
        This is used primarily with ORM sessions that buffer changes.
        """
        if hasattr(self._connection, 'flush'):
            self._connection.flush()


class AbstractDatabaseTransactionManager(PlatformTransactionManager, ABC):
    """
    Abstract base class for database transaction managers.
    
    This class provides common functionality for database transaction managers,
    with concrete implementations handling specific database backends.
    """
    
    def __init__(self):
        """Initialize the database transaction manager."""
        self._transaction_counter = 0
    
    def get_transaction(self, definition: Optional[TransactionDefinition] = None) -> DatabaseTransactionStatus:
        """
        Begin a new transaction according to the specified definition.
        
        Args:
            definition: The transaction definition, or None for default settings
            
        Returns:
            A transaction status object representing the new transaction
            
        Raises:
            TransactionError: If transaction creation fails
        """
        definition = definition or DEFAULT_TRANSACTION_DEFINITION
        
        try:
            # Check if there's an existing transaction
            if TransactionSynchronizationManager.is_transaction_active():
                # Handle according to propagation behavior
                return self._handle_existing_transaction(definition)
            else:
                # Create a new transaction
                return self._begin_new_transaction(definition)
        except Exception as e:
            raise TransactionError(f"Could not create transaction: {str(e)}", e)
    
    def commit(self, status: TransactionStatus) -> None:
        """
        Commit the given transaction.
        
        Args:
            status: The transaction status object returned by get_transaction
            
        Raises:
            TransactionError: If the commit fails
        """
        if status.is_completed():
            raise TransactionError("Transaction is already completed")
        
        try:
            db_status = self._cast_status(status)
            
            # Trigger synchronization callbacks
            if db_status.is_new_transaction():
                TransactionSynchronizationManager.trigger_before_commit(
                    self._is_read_only_transaction(db_status)
                )
            
            # Perform the actual commit if this is a new transaction
            if db_status.is_new_transaction():
                if db_status.is_rollback_only():
                    self._do_rollback(db_status)
                else:
                    self._do_commit(db_status)
                
                # Trigger after-commit callbacks
                TransactionSynchronizationManager.trigger_after_commit()
            
            # Mark as completed
            db_status._completed = True
            
            # Clean up if this was the outermost transaction
            if db_status.is_new_transaction():
                self._cleanup_after_completion(db_status)
        except Exception as e:
            raise TransactionError(f"Could not commit transaction: {str(e)}", e)
    
    def rollback(self, status: TransactionStatus) -> None:
        """
        Roll back the given transaction.
        
        Args:
            status: The transaction status object returned by get_transaction
            
        Raises:
            TransactionError: If the rollback fails
        """
        if status.is_completed():
            raise TransactionError("Transaction is already completed")
        
        try:
            db_status = self._cast_status(status)
            
            # Perform the actual rollback if this is a new transaction
            if db_status.is_new_transaction():
                self._do_rollback(db_status)
            elif db_status.savepoint_name:
                # Rollback to savepoint for nested transactions
                self._do_rollback_to_savepoint(db_status)
            
            # Mark as completed
            db_status._completed = True
            
            # Clean up if this was the outermost transaction
            if db_status.is_new_transaction():
                self._cleanup_after_completion(db_status)
        except Exception as e:
            raise TransactionError(f"Could not rollback transaction: {str(e)}", e)
    
    def _cast_status(self, status: TransactionStatus) -> DatabaseTransactionStatus:
        """
        Cast the transaction status to DatabaseTransactionStatus.
        
        Args:
            status: The transaction status to cast
            
        Returns:
            The status as DatabaseTransactionStatus
            
        Raises:
            TransactionError: If the status is not a DatabaseTransactionStatus
        """
        if not isinstance(status, DatabaseTransactionStatus):
            raise TransactionError(
                f"Expected DatabaseTransactionStatus but got {type(status).__name__}"
            )
        return status
    
    def _handle_existing_transaction(self, definition: TransactionDefinition) -> DatabaseTransactionStatus:
        """
        Handle an existing transaction according to the propagation behavior.
        
        Args:
            definition: The transaction definition
            
        Returns:
            A transaction status object
            
        Raises:
            TransactionError: If the propagation behavior is not supported
        """
        propagation = definition.get_propagation()
        
        if propagation == Propagation.REQUIRED:
            # Participate in existing transaction
            return self._participate_in_existing_transaction(definition)
        elif propagation == Propagation.REQUIRES_NEW:
            # Suspend current transaction and create a new one
            return self._suspend_and_create_new_transaction(definition)
        elif propagation == Propagation.NESTED:
            # Create a savepoint in the current transaction
            return self._create_nested_transaction(definition)
        elif propagation == Propagation.SUPPORTS:
            # Participate in existing transaction
            return self._participate_in_existing_transaction(definition)
        elif propagation == Propagation.NOT_SUPPORTED:
            # Suspend current transaction and execute non-transactionally
            return self._suspend_current_transaction(definition)
        elif propagation == Propagation.NEVER:
            # Existing transaction is not allowed
            raise TransactionError(
                "Existing transaction found for transaction marked with propagation 'NEVER'"
            )
        elif propagation == Propagation.MANDATORY:
            # Existing transaction is required
            return self._participate_in_existing_transaction(definition)
        else:
            raise TransactionError(f"Unknown transaction propagation: {propagation}")
    
    @abstractmethod
    def _begin_new_transaction(self, definition: TransactionDefinition) -> DatabaseTransactionStatus:
        """
        Begin a new transaction.
        
        Args:
            definition: The transaction definition
            
        Returns:
            A transaction status object representing the new transaction
        """
        pass
    
    @abstractmethod
    def _participate_in_existing_transaction(self, definition: TransactionDefinition) -> DatabaseTransactionStatus:
        """
        Participate in an existing transaction.
        
        Args:
            definition: The transaction definition
            
        Returns:
            A transaction status object
        """
        pass
    
    @abstractmethod
    def _suspend_and_create_new_transaction(self, definition: TransactionDefinition) -> DatabaseTransactionStatus:
        """
        Suspend the current transaction and create a new one.
        
        Args:
            definition: The transaction definition
            
        Returns:
            A transaction status object representing the new transaction
        """
        pass
    
    @abstractmethod
    def _suspend_current_transaction(self, definition: TransactionDefinition) -> DatabaseTransactionStatus:
        """
        Suspend the current transaction.
        
        Args:
            definition: The transaction definition
            
        Returns:
            A transaction status object
        """
        pass
    
    @abstractmethod
    def _create_nested_transaction(self, definition: TransactionDefinition) -> DatabaseTransactionStatus:
        """
        Create a nested transaction (savepoint).
        
        Args:
            definition: The transaction definition
            
        Returns:
            A transaction status object representing the nested transaction
        """
        pass
    
    @abstractmethod
    def _do_commit(self, status: DatabaseTransactionStatus) -> None:
        """
        Perform the actual commit.
        
        Args:
            status: The transaction status
        """
        pass
    
    @abstractmethod
    def _do_rollback(self, status: DatabaseTransactionStatus) -> None:
        """
        Perform the actual rollback.
        
        Args:
            status: The transaction status
        """
        pass
    
    @abstractmethod
    def _do_rollback_to_savepoint(self, status: DatabaseTransactionStatus) -> None:
        """
        Rollback to a savepoint.
        
        Args:
            status: The transaction status with savepoint information
        """
        pass
    
    @abstractmethod
    def _cleanup_after_completion(self, status: DatabaseTransactionStatus) -> None:
        """
        Clean up after transaction completion.
        
        Args:
            status: The transaction status
        """
        pass
    
    def _is_read_only_transaction(self, status: DatabaseTransactionStatus) -> bool:
        """
        Check if the transaction is read-only.
        
        Args:
            status: The transaction status
            
        Returns:
            True if the transaction is read-only, False otherwise
        """
        # Default implementation - can be overridden by subclasses
        return False
    
    def _generate_savepoint_name(self) -> str:
        """
        Generate a unique savepoint name.
        
        Returns:
            A unique savepoint name
        """
        self._transaction_counter += 1
        return f"SAVEPOINT_{self._transaction_counter}"


class SQLAlchemyTransactionManager(AbstractDatabaseTransactionManager):
    """
    Transaction manager implementation for SQLAlchemy.
    
    This class provides transaction management for SQLAlchemy sessions.
    """
    
    def __init__(self, session_factory):
        """
        Initialize the SQLAlchemy transaction manager.
        
        Args:
            session_factory: A callable that returns a new SQLAlchemy session
        """
        super().__init__()
        self._session_factory = session_factory
        self._suspended_resources: Dict[str, Any] = {}
    
    def _begin_new_transaction(self, definition: TransactionDefinition) -> DatabaseTransactionStatus:
        """
        Begin a new SQLAlchemy transaction.
        
        Args:
            definition: The transaction definition
            
        Returns:
            A transaction status object representing the new transaction
        """
        # Get a new session
        session = self._session_factory()
        
        # Begin a transaction with the appropriate isolation level
        transaction = session.begin(
            subtransactions=False,
            isolation_level=self._convert_isolation_level(definition.get_isolation())
        )
        
        # Set read-only mode if specified
        if definition.is_read_only():
            # SQLAlchemy doesn't have a direct read-only mode, but we can track it
            session.info['read_only'] = True
        
        # Register the session with the synchronization manager
        TransactionSynchronizationManager.bind_resource('sqlalchemy_session', session)
        TransactionSynchronizationManager.set_transaction_active(True)
        TransactionSynchronizationManager.set_current_transaction(transaction)
        
        return DatabaseTransactionStatus(
            transaction_manager=self,
            connection=session,
            transaction_object=transaction,
            new_transaction=True
        )
    
    def _participate_in_existing_transaction(self, definition: TransactionDefinition) -> DatabaseTransactionStatus:
        """
        Participate in an existing SQLAlchemy transaction.
        
        Args:
            definition: The transaction definition
            
        Returns:
            A transaction status object
        """
        # Get the existing session
        session = TransactionSynchronizationManager.get_resource('sqlalchemy_session')
        if not session:
            raise TransactionError("No existing SQLAlchemy session found")
        
        # Get the existing transaction
        transaction = TransactionSynchronizationManager.get_current_transaction()
        
        # Create a new status that participates in the existing transaction
        return DatabaseTransactionStatus(
            transaction_manager=self,
            connection=session,
            transaction_object=transaction,
            new_transaction=False
        )
    
    def _suspend_and_create_new_transaction(self, definition: TransactionDefinition) -> DatabaseTransactionStatus:
        """
        Suspend the current SQLAlchemy transaction and create a new one.
        
        Args:
            definition: The transaction definition
            
        Returns:
            A transaction status object representing the new transaction
        """
        # Suspend the current resources
        self._suspended_resources = {
            'session': TransactionSynchronizationManager.unbind_resource('sqlalchemy_session'),
            'transaction': TransactionSynchronizationManager.get_current_transaction()
        }
        
        # Create a new transaction
        return self._begin_new_transaction(definition)
    
    def _suspend_current_transaction(self, definition: TransactionDefinition) -> DatabaseTransactionStatus:
        """
        Suspend the current SQLAlchemy transaction.
        
        Args:
            definition: The transaction definition
            
        Returns:
            A transaction status object
        """
        # Suspend the current resources
        self._suspended_resources = {
            'session': TransactionSynchronizationManager.unbind_resource('sqlalchemy_session'),
            'transaction': TransactionSynchronizationManager.get_current_transaction()
        }
        
        # Return a non-transactional status
        return DatabaseTransactionStatus(
            transaction_manager=self,
            connection=None,
            transaction_object=None,
            new_transaction=False
        )
    
    def _create_nested_transaction(self, definition: TransactionDefinition) -> DatabaseTransactionStatus:
        """
        Create a nested SQLAlchemy transaction (savepoint).
        
        Args:
            definition: The transaction definition
            
        Returns:
            A transaction status object representing the nested transaction
        """
        # Get the existing session
        session = TransactionSynchronizationManager.get_resource('sqlalchemy_session')
        if not session:
            raise TransactionError("No existing SQLAlchemy session found")
        
        # Create a savepoint
        savepoint_name = self._generate_savepoint_name()
        session.begin_nested()  # SQLAlchemy handles savepoint naming internally
        
        return DatabaseTransactionStatus(
            transaction_manager=self,
            connection=session,
            transaction_object=session.get_transaction(),
            new_transaction=False,
            savepoint_name=savepoint_name
        )
    
    def _do_commit(self, status: DatabaseTransactionStatus) -> None:
        """
        Commit the SQLAlchemy transaction.
        
        Args:
            status: The transaction status
        """
        if status.connection:
            status.connection.commit()
    
    def _do_rollback(self, status: DatabaseTransactionStatus) -> None:
        """
        Roll back the SQLAlchemy transaction.
        
        Args:
            status: The transaction status
        """
        if status.connection:
            status.connection.rollback()
    
    def _do_rollback_to_savepoint(self, status: DatabaseTransactionStatus) -> None:
        """
        Roll back to a SQLAlchemy savepoint.
        
        Args:
            status: The transaction status with savepoint information
        """
        if status.connection and status.savepoint_name:
            # SQLAlchemy handles savepoint rollback through the nested transaction
            status.transaction_object.rollback()
    
    def _cleanup_after_completion(self, status: DatabaseTransactionStatus) -> None:
        """
        Clean up after SQLAlchemy transaction completion.
        
        Args:
            status: The transaction status
        """
        # Unbind the session
        TransactionSynchronizationManager.unbind_resource('sqlalchemy_session')
        TransactionSynchronizationManager.set_transaction_active(False)
        TransactionSynchronizationManager.set_current_transaction(None)
        
        # Close the session if it was created for this transaction
        if status.is_new_transaction() and status.connection:
            status.connection.close()
        
        # Restore suspended resources if any
        if self._suspended_resources:
            if 'session' in self._suspended_resources and self._suspended_resources['session']:
                TransactionSynchronizationManager.bind_resource(
                    'sqlalchemy_session', 
                    self._suspended_resources['session']
                )
            if 'transaction' in self._suspended_resources and self._suspended_resources['transaction']:
                TransactionSynchronizationManager.set_current_transaction(
                    self._suspended_resources['transaction']
                )
                TransactionSynchronizationManager.set_transaction_active(True)
            
            self._suspended_resources = {}
    
    def _is_read_only_transaction(self, status: DatabaseTransactionStatus) -> bool:
        """
        Check if the SQLAlchemy transaction is read-only.
        
        Args:
            status: The transaction status
            
        Returns:
            True if the transaction is read-only, False otherwise
        """
        if status.connection and hasattr(status.connection, 'info'):
            return status.connection.info.get('read_only', False)
        return False
    
    def _convert_isolation_level(self, isolation: Isolation) -> Optional[str]:
        """
        Convert the framework isolation level to SQLAlchemy isolation level.
        
        Args:
            isolation: The framework isolation level
            
        Returns:
            The SQLAlchemy isolation level string, or None for default
        """
        if isolation == Isolation.DEFAULT:
            return None
        elif isolation == Isolation.READ_UNCOMMITTED:
            return "READ UNCOMMITTED"
        elif isolation == Isolation.READ_COMMITTED:
            return "READ COMMITTED"
        elif isolation == Isolation.REPEATABLE_READ:
            return "REPEATABLE READ"
        elif isolation == Isolation.SERIALIZABLE:
            return "SERIALIZABLE"
        else:
            return None


class JDBCLikeTransactionManager(AbstractDatabaseTransactionManager):
    """
    Transaction manager implementation for JDBC-like connections.
    
    This class provides transaction management for database connections
    that follow the JDBC-like API (e.g., psycopg2, sqlite3).
    """
    
    def __init__(self, connection_factory):
        """
        Initialize the JDBC-like transaction manager.
        
        Args:
            connection_factory: A callable that returns a new database connection
        """
        super().__init__()
        self._connection_factory = connection_factory
        self._suspended_resources: Dict[str, Any] = {}
    
    def _begin_new_transaction(self, definition: TransactionDefinition) -> DatabaseTransactionStatus:
        """
        Begin a new JDBC-like transaction.
        
        Args:
            definition: The transaction definition
            
        Returns:
            A transaction status object representing the new transaction
        """
        # Get a new connection
        connection = self._connection_factory()
        
        # Set isolation level if specified
        if definition.get_isolation() != Isolation.DEFAULT:
            self._set_isolation_level(connection, definition.get_isolation())
        
        # Begin transaction (disable autocommit)
        connection.autocommit = False
        
        # Register the connection with the synchronization manager
        TransactionSynchronizationManager.bind_resource('jdbc_connection', connection)
        TransactionSynchronizationManager.set_transaction_active(True)
        TransactionSynchronizationManager.set_current_transaction(connection)
        
        return DatabaseTransactionStatus(
            transaction_manager=self,
            connection=connection,
            transaction_object=connection,
            new_transaction=True
        )
    
    def _participate_in_existing_transaction(self, definition: TransactionDefinition) -> DatabaseTransactionStatus:
        """
        Participate in an existing JDBC-like transaction.
        
        Args:
            definition: The transaction definition
            
        Returns:
            A transaction status object
        """
        # Get the existing connection
        connection = TransactionSynchronizationManager.get_resource('jdbc_connection')
        if not connection:
            raise TransactionError("No existing JDBC-like connection found")
        
        # Create a new status that participates in the existing transaction
        return DatabaseTransactionStatus(
            transaction_manager=self,
            connection=connection,
            transaction_object=connection,
            new_transaction=False
        )
    
    def _suspend_and_create_new_transaction(self, definition: TransactionDefinition) -> DatabaseTransactionStatus:
        """
        Suspend the current JDBC-like transaction and create a new one.
        
        Args:
            definition: The transaction definition
            
        Returns:
            A transaction status object representing the new transaction
        """
        # Suspend the current resources
        self._suspended_resources = {
            'connection': TransactionSynchronizationManager.unbind_resource('jdbc_connection'),
            'transaction': TransactionSynchronizationManager.get_current_transaction()
        }
        
        # Create a new transaction
        return self._begin_new_transaction(definition)
    
    def _suspend_current_transaction(self, definition: TransactionDefinition) -> DatabaseTransactionStatus:
        """
        Suspend the current JDBC-like transaction.
        
        Args:
            definition: The transaction definition
            
        Returns:
            A transaction status object
        """
        # Suspend the current resources
        self._suspended_resources = {
            'connection': TransactionSynchronizationManager.unbind_resource('jdbc_connection'),
            'transaction': TransactionSynchronizationManager.get_current_transaction()
        }
        
        # Return a non-transactional status
        return DatabaseTransactionStatus(
            transaction_manager=self,
            connection=None,
            transaction_object=None,
            new_transaction=False
        )
    
    def _create_nested_transaction(self, definition: TransactionDefinition) -> DatabaseTransactionStatus:
        """
        Create a nested JDBC-like transaction (savepoint).
        
        Args:
            definition: The transaction definition
            
        Returns:
            A transaction status object representing the nested transaction
        """
        # Get the existing connection
        connection = TransactionSynchronizationManager.get_resource('jdbc_connection')
        if not connection:
            raise TransactionError("No existing JDBC-like connection found")
        
        # Create a savepoint
        savepoint_name = self._generate_savepoint_name()
        cursor = connection.cursor()
        cursor.execute(f"SAVEPOINT {savepoint_name}")
        
        return DatabaseTransactionStatus(
            transaction_manager=self,
            connection=connection,
            transaction_object=connection,
            new_transaction=False,
            savepoint_name=savepoint_name
        )
    
    def _do_commit(self, status: DatabaseTransactionStatus) -> None:
        """
        Commit the JDBC-like transaction.
        
        Args:
            status: The transaction status
        """
        if status.connection:
            status.connection.commit()
    
    def _do_rollback(self, status: DatabaseTransactionStatus) -> None:
        """
        Roll back the JDBC-like transaction.
        
        Args:
            status: The transaction status
        """
        if status.connection:
            status.connection.rollback()
    
    def _do_rollback_to_savepoint(self, status: DatabaseTransactionStatus) -> None:
        """
        Roll back to a JDBC-like savepoint.
        
        Args:
            status: The transaction status with savepoint information
        """
        if status.connection and status.savepoint_name:
            cursor = status.connection.cursor()
            cursor.execute(f"ROLLBACK TO SAVEPOINT {status.savepoint_name}")
    
    def _cleanup_after_completion(self, status: DatabaseTransactionStatus) -> None:
        """
        Clean up after JDBC-like transaction completion.
        
        Args:
            status: The transaction status
        """
        # Unbind the connection
        TransactionSynchronizationManager.unbind_resource('jdbc_connection')
        TransactionSynchronizationManager.set_transaction_active(False)
        TransactionSynchronizationManager.set_current_transaction(None)
        
        # Close the connection if it was created for this transaction
        if status.is_new_transaction() and status.connection:
            status.connection.close()
        
        # Restore suspended resources if any
        if self._suspended_resources:
            if 'connection' in self._suspended_resources and self._suspended_resources['connection']:
                TransactionSynchronizationManager.bind_resource(
                    'jdbc_connection', 
                    self._suspended_resources['connection']
                )
            if 'transaction' in self._suspended_resources and self._suspended_resources['transaction']:
                TransactionSynchronizationManager.set_current_transaction(
                    self._suspended_resources['transaction']
                )
                TransactionSynchronizationManager.set_transaction_active(True)
            
            self._suspended_resources = {}
    
    def _set_isolation_level(self, connection: Any, isolation: Isolation) -> None:
        """
        Set the isolation level on the connection.
        
        Args:
            connection: The database connection
            isolation: The isolation level to set
        """
        cursor = connection.cursor()
        
        if isolation == Isolation.READ_UNCOMMITTED:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
        elif isolation == Isolation.READ_COMMITTED:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
        elif isolation == Isolation.REPEATABLE_READ:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        elif isolation == Isolation.SERIALIZABLE:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")