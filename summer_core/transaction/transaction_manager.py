"""
Transaction Manager Interface and Implementations.

This module provides the core interfaces and implementations for transaction management.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, Optional, TypeVar, cast

from summer_core.exceptions import TransactionException


class TransactionStatus:
    """
    Represents the status of a transaction.
    
    This class provides information about the current transaction state
    and allows for controlling the transaction (commit/rollback).
    """
    
    def __init__(self, 
                 transaction_manager: 'PlatformTransactionManager',
                 transaction_object: Any = None,
                 new_transaction: bool = True,
                 rollback_only: bool = False,
                 completed: bool = False):
        """
        Initialize a new transaction status.
        
        Args:
            transaction_manager: The transaction manager that created this status
            transaction_object: The underlying transaction object (implementation-specific)
            new_transaction: Whether this is a new transaction
            rollback_only: Whether this transaction is marked for rollback only
            completed: Whether this transaction has been completed
        """
        self._transaction_manager = transaction_manager
        self._transaction_object = transaction_object
        self._new_transaction = new_transaction
        self._rollback_only = rollback_only
        self._completed = completed
        
    @property
    def transaction_object(self) -> Any:
        """Get the underlying transaction object."""
        return self._transaction_object
    
    def is_new_transaction(self) -> bool:
        """Check if this is a new transaction."""
        return self._new_transaction
    
    def is_completed(self) -> bool:
        """Check if this transaction has been completed."""
        return self._completed
    
    def is_rollback_only(self) -> bool:
        """Check if this transaction is marked for rollback only."""
        return self._rollback_only
    
    def set_rollback_only(self) -> None:
        """Mark this transaction for rollback only."""
        self._rollback_only = True
    
    def flush(self) -> None:
        """
        Flush the underlying session to the database.
        
        This is a no-op in the base implementation and should be
        overridden by specific transaction manager implementations.
        """
        pass


class PlatformTransactionManager(ABC):
    """
    Interface for transaction management.
    
    This is the central interface for transaction management in the framework.
    Concrete implementations handle specific transaction technologies.
    """
    
    @abstractmethod
    def get_transaction(self, definition: Optional['TransactionDefinition'] = None) -> TransactionStatus:
        """
        Begin a new transaction according to the specified definition.
        
        Args:
            definition: The transaction definition, or None for default settings
            
        Returns:
            A transaction status object representing the new transaction
            
        Raises:
            TransactionException: If transaction creation fails
        """
        pass
    
    @abstractmethod
    def commit(self, status: TransactionStatus) -> None:
        """
        Commit the given transaction.
        
        Args:
            status: The transaction status object returned by get_transaction
            
        Raises:
            TransactionException: If the commit fails
        """
        pass
    
    @abstractmethod
    def rollback(self, status: TransactionStatus) -> None:
        """
        Roll back the given transaction.
        
        Args:
            status: The transaction status object returned by get_transaction
            
        Raises:
            TransactionException: If the rollback fails
        """
        pass


class Propagation(Enum):
    """
    Transaction propagation behaviors.
    
    These values determine how transactions relate to existing transactions.
    """
    
    # Support a current transaction, create a new one if none exists
    REQUIRED = auto()
    
    # Create a new transaction, suspending the current transaction if one exists
    REQUIRES_NEW = auto()
    
    # Support a current transaction, execute non-transactionally if none exists
    SUPPORTS = auto()
    
    # Execute non-transactionally, throw an exception if a transaction exists
    NOT_SUPPORTED = auto()
    
    # Execute in a transaction, throw an exception if a transaction exists
    NEVER = auto()
    
    # Support a current transaction, throw an exception if none exists
    MANDATORY = auto()
    
    # Execute within a nested transaction if a current transaction exists
    NESTED = auto()


class Isolation(Enum):
    """
    Transaction isolation levels.
    
    These values determine the isolation level of the transaction.
    """
    
    # Use the default isolation level of the underlying datastore
    DEFAULT = auto()
    
    # A constant indicating that dirty reads, non-repeatable reads and phantom reads can occur
    READ_UNCOMMITTED = auto()
    
    # A constant indicating that dirty reads are prevented; non-repeatable reads and phantom reads can occur
    READ_COMMITTED = auto()
    
    # A constant indicating that dirty reads and non-repeatable reads are prevented; phantom reads can occur
    REPEATABLE_READ = auto()
    
    # A constant indicating that dirty reads, non-repeatable reads and phantom reads are prevented
    SERIALIZABLE = auto()


@dataclass
class TransactionDefinition:
    """
    Definition of transaction attributes.
    
    This class encapsulates the settings for a transaction.
    """
    
    # Default values
    propagation: Propagation = Propagation.REQUIRED
    isolation: Isolation = Isolation.DEFAULT
    timeout: int = -1  # -1 means no timeout
    read_only: bool = False
    name: Optional[str] = None
    
    def is_read_only(self) -> bool:
        """Check if this transaction is read-only."""
        return self.read_only
    
    def get_timeout(self) -> int:
        """Get the transaction timeout in seconds."""
        return self.timeout
    
    def get_isolation(self) -> Isolation:
        """Get the transaction isolation level."""
        return self.isolation
    
    def get_propagation(self) -> Propagation:
        """Get the transaction propagation behavior."""
        return self.propagation
    
    def get_name(self) -> Optional[str]:
        """Get the transaction name."""
        return self.name


# Default transaction definition with standard settings
DEFAULT_TRANSACTION_DEFINITION = TransactionDefinition()


class TransactionSynchronization(ABC):
    """
    Interface for transaction synchronization callbacks.
    
    This allows for executing custom code at various points in the
    transaction lifecycle.
    """
    
    @abstractmethod
    def before_commit(self, read_only: bool) -> None:
        """
        Called before transaction commit.
        
        Args:
            read_only: Whether the transaction is read-only
        """
        pass
    
    @abstractmethod
    def before_completion(self) -> None:
        """Called before transaction completion (before commit or rollback)."""
        pass
    
    @abstractmethod
    def after_commit(self) -> None:
        """Called after transaction commit."""
        pass
    
    @abstractmethod
    def after_completion(self, status: int) -> None:
        """
        Called after transaction completion (after commit or rollback).
        
        Args:
            status: The completion status (committed, rolled back, etc.)
        """
        pass


class TransactionSynchronizationManager:
    """
    Manages resources and synchronizations per transaction.
    
    This is a static utility class that provides methods for managing
    transaction-bound resources and synchronizations.
    """
    
    # Thread-local storage for transaction resources and synchronizations
    _resources: Dict[str, Any] = {}
    _synchronizations: list[TransactionSynchronization] = []
    _current_transaction: Optional[Any] = None
    _transaction_active: bool = False
    
    @classmethod
    def bind_resource(cls, key: str, value: Any) -> None:
        """
        Bind a resource to the current transaction.
        
        Args:
            key: The resource key
            value: The resource value
        """
        cls._resources[key] = value
    
    @classmethod
    def unbind_resource(cls, key: str) -> Any:
        """
        Unbind a resource from the current transaction.
        
        Args:
            key: The resource key
            
        Returns:
            The previously bound resource value
        """
        return cls._resources.pop(key, None)
    
    @classmethod
    def get_resource(cls, key: str) -> Optional[Any]:
        """
        Get a resource bound to the current transaction.
        
        Args:
            key: The resource key
            
        Returns:
            The bound resource value, or None if not found
        """
        return cls._resources.get(key)
    
    @classmethod
    def has_resource(cls, key: str) -> bool:
        """
        Check if a resource is bound to the current transaction.
        
        Args:
            key: The resource key
            
        Returns:
            True if the resource is bound, False otherwise
        """
        return key in cls._resources
    
    @classmethod
    def register_synchronization(cls, synchronization: TransactionSynchronization) -> None:
        """
        Register a transaction synchronization.
        
        Args:
            synchronization: The synchronization to register
        """
        cls._synchronizations.append(synchronization)
    
    @classmethod
    def clear(cls) -> None:
        """Clear all resources and synchronizations."""
        cls._resources.clear()
        cls._synchronizations.clear()
        cls._current_transaction = None
        cls._transaction_active = False
    
    @classmethod
    def is_transaction_active(cls) -> bool:
        """Check if a transaction is currently active."""
        return cls._transaction_active
    
    @classmethod
    def set_transaction_active(cls, active: bool) -> None:
        """
        Set whether a transaction is currently active.
        
        Args:
            active: Whether a transaction is active
        """
        cls._transaction_active = active
    
    @classmethod
    def set_current_transaction(cls, transaction: Any) -> None:
        """
        Set the current transaction object.
        
        Args:
            transaction: The current transaction object
        """
        cls._current_transaction = transaction
    
    @classmethod
    def get_current_transaction(cls) -> Optional[Any]:
        """
        Get the current transaction object.
        
        Returns:
            The current transaction object, or None if not set
        """
        return cls._current_transaction
    
    @classmethod
    def trigger_before_commit(cls, read_only: bool) -> None:
        """
        Trigger beforeCommit callbacks on registered synchronizations.
        
        Args:
            read_only: Whether the transaction is read-only
        """
        for synchronization in cls._synchronizations:
            synchronization.before_commit(read_only)
    
    @classmethod
    def trigger_before_completion(cls) -> None:
        """Trigger beforeCompletion callbacks on registered synchronizations."""
        for synchronization in cls._synchronizations:
            synchronization.before_completion()
    
    @classmethod
    def trigger_after_commit(cls) -> None:
        """Trigger afterCommit callbacks on registered synchronizations."""
        for synchronization in cls._synchronizations:
            synchronization.after_commit()
    
    @classmethod
    def trigger_after_completion(cls, status: int) -> None:
        """
        Trigger afterCompletion callbacks on registered synchronizations.
        
        Args:
            status: The completion status
        """
        for synchronization in cls._synchronizations:
            synchronization.after_completion(status)


# Type variable for the return type of the transactional function
T = TypeVar('T')


class TransactionTemplate:
    """
    Template for executing code within a transaction.
    
    This class provides a way to execute code within a transaction
    programmatically, similar to the @transactional decorator but
    for use in code.
    """
    
    def __init__(self, 
                 transaction_manager: PlatformTransactionManager,
                 definition: Optional[TransactionDefinition] = None):
        """
        Initialize a new transaction template.
        
        Args:
            transaction_manager: The transaction manager to use
            definition: The transaction definition, or None for default settings
        """
        self.transaction_manager = transaction_manager
        self.definition = definition or DEFAULT_TRANSACTION_DEFINITION
    
    def execute(self, callback: Callable[[], T]) -> T:
        """
        Execute the given callback within a transaction.
        
        Args:
            callback: The callback to execute
            
        Returns:
            The result of the callback
            
        Raises:
            TransactionException: If the transaction fails
        """
        status = self.transaction_manager.get_transaction(self.definition)
        
        try:
            result = callback()
            
            if status.is_rollback_only():
                self.transaction_manager.rollback(status)
            else:
                self.transaction_manager.commit(status)
                
            return result
        except Exception as e:
            # Roll back on exception
            self.transaction_manager.rollback(status)
            
            # Re-raise the exception
            raise TransactionException(f"Transaction callback failed: {str(e)}") from e