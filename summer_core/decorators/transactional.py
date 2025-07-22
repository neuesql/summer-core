"""
Transactional Decorator Implementation.

This module provides the @transactional decorator for declarative transaction management.
"""
import functools
import inspect
from typing import Any, Callable, List, Optional, Type, TypeVar, Union

from summer_core.exceptions import TransactionException
from summer_core.transaction.transaction_manager import (
    DEFAULT_TRANSACTION_DEFINITION,
    Isolation,
    PlatformTransactionManager,
    Propagation,
    TransactionDefinition,
    TransactionSynchronizationManager,
    TransactionTemplate,
)

# Type variable for the decorated function
F = TypeVar('F', bound=Callable[..., Any])


class TransactionalConfig:
    """
    Configuration for transactional behavior.
    
    This class holds all the configuration options for the @transactional decorator.
    """
    
    def __init__(self,
                 propagation: Propagation = Propagation.REQUIRED,
                 isolation: Isolation = Isolation.DEFAULT,
                 timeout: int = -1,
                 read_only: bool = False,
                 rollback_for: Optional[List[Type[Exception]]] = None,
                 no_rollback_for: Optional[List[Type[Exception]]] = None,
                 transaction_manager: Optional[str] = None):
        """
        Initialize transactional configuration.
        
        Args:
            propagation: Transaction propagation behavior
            isolation: Transaction isolation level
            timeout: Transaction timeout in seconds (-1 for no timeout)
            read_only: Whether the transaction is read-only
            rollback_for: Exception types that should trigger rollback
            no_rollback_for: Exception types that should NOT trigger rollback
            transaction_manager: Name of the transaction manager bean to use
        """
        self.propagation = propagation
        self.isolation = isolation
        self.timeout = timeout
        self.read_only = read_only
        self.rollback_for = rollback_for or [Exception]
        self.no_rollback_for = no_rollback_for or []
        self.transaction_manager = transaction_manager
    
    def should_rollback_on(self, exception: Exception) -> bool:
        """
        Determine if the transaction should be rolled back for the given exception.
        
        Args:
            exception: The exception that occurred
            
        Returns:
            True if the transaction should be rolled back, False otherwise
        """
        # Check no_rollback_for first (takes precedence)
        for no_rollback_type in self.no_rollback_for:
            if isinstance(exception, no_rollback_type):
                return False
        
        # Check rollback_for
        for rollback_type in self.rollback_for:
            if isinstance(exception, rollback_type):
                return True
        
        # Default: rollback for all exceptions
        return True
    
    def to_transaction_definition(self) -> TransactionDefinition:
        """
        Convert this configuration to a TransactionDefinition.
        
        Returns:
            A TransactionDefinition with the same settings
        """
        return TransactionDefinition(
            propagation=self.propagation,
            isolation=self.isolation,
            timeout=self.timeout,
            read_only=self.read_only
        )


class TransactionalInterceptor:
    """
    Interceptor that handles transactional method execution.
    
    This class implements the actual transaction management logic
    for methods decorated with @transactional.
    """
    
    def __init__(self, config: TransactionalConfig, transaction_manager: Optional[PlatformTransactionManager] = None):
        """
        Initialize the transactional interceptor.
        
        Args:
            config: The transactional configuration
            transaction_manager: Optional transaction manager to use (for testing)
        """
        self.config = config
        self._transaction_manager: Optional[PlatformTransactionManager] = transaction_manager
    
    def get_transaction_manager(self) -> PlatformTransactionManager:
        """
        Get the transaction manager to use.
        
        Returns:
            The transaction manager instance
            
        Raises:
            TransactionException: If no transaction manager is available
        """
        if self._transaction_manager is None:
            # Try to get transaction manager from synchronization manager
            tx_manager = TransactionSynchronizationManager.get_resource('transaction_manager')
            if tx_manager:
                self._transaction_manager = tx_manager
            else:
                # Fallback: try to import and use a default transaction manager
                # This is for testing purposes - in production, the transaction manager
                # would be properly configured and injected
                raise TransactionException(
                    "No transaction manager available. Please configure a transaction manager "
                    "in your application context or set one in TransactionSynchronizationManager."
                )
        
        return self._transaction_manager
    
    def invoke(self, method: Callable, args: tuple, kwargs: dict) -> Any:
        """
        Invoke the method within a transaction.
        
        Args:
            method: The method to invoke
            args: Positional arguments
            kwargs: Keyword arguments
            
        Returns:
            The result of the method invocation
            
        Raises:
            TransactionException: If transaction management fails
        """
        transaction_manager = self.get_transaction_manager()
        definition = self.config.to_transaction_definition()
        
        # Get transaction status
        status = transaction_manager.get_transaction(definition)
        
        try:
            # Set transaction as active
            TransactionSynchronizationManager.set_transaction_active(True)
            TransactionSynchronizationManager.set_current_transaction(status.transaction_object)
            
            # Execute the method
            result = method(*args, **kwargs)
            
            # Check if transaction should be rolled back
            if status.is_rollback_only():
                transaction_manager.rollback(status)
            else:
                transaction_manager.commit(status)
                
            return result
            
        except Exception as e:
            # Check if we should rollback for this exception
            should_rollback = self.config.should_rollback_on(e)
            
            if should_rollback:
                transaction_manager.rollback(status)
            else:
                # Even if we don't rollback for this specific exception,
                # we still need to commit the transaction if it's not marked for rollback
                if not status.is_rollback_only():
                    transaction_manager.commit(status)
                else:
                    transaction_manager.rollback(status)
            
            # Re-raise the original exception wrapped in TransactionException
            raise TransactionException(f"Transactional method execution failed: {str(e)}") from e
            
        finally:
            # Clean up transaction state
            TransactionSynchronizationManager.set_transaction_active(False)
            TransactionSynchronizationManager.set_current_transaction(None)


def transactional(
    propagation: Propagation = Propagation.REQUIRED,
    isolation: Isolation = Isolation.DEFAULT,
    timeout: int = -1,
    read_only: bool = False,
    rollback_for: Optional[List[Type[Exception]]] = None,
    no_rollback_for: Optional[List[Type[Exception]]] = None,
    transaction_manager: Optional[str] = None,
    _transaction_manager_instance: Optional[PlatformTransactionManager] = None
) -> Callable[[F], F]:
    """
    Decorator for declarative transaction management.
    
    This decorator automatically manages transactions for the decorated method,
    handling transaction begin, commit, and rollback based on the method's
    execution outcome.
    
    Args:
        propagation: Transaction propagation behavior (default: REQUIRED)
        isolation: Transaction isolation level (default: DEFAULT)
        timeout: Transaction timeout in seconds, -1 for no timeout (default: -1)
        read_only: Whether the transaction is read-only (default: False)
        rollback_for: Exception types that should trigger rollback (default: [Exception])
        no_rollback_for: Exception types that should NOT trigger rollback (default: [])
        transaction_manager: Name of the transaction manager bean to use (default: None)
    
    Returns:
        The decorated function with transaction management
    
    Example:
        @transactional()
        def create_user(self, user_data):
            # This method will run in a transaction
            user = User(**user_data)
            self.user_repository.save(user)
            return user
        
        @transactional(
            propagation=Propagation.REQUIRES_NEW,
            isolation=Isolation.SERIALIZABLE,
            timeout=30,
            rollback_for=[ValueError, RuntimeError]
        )
        def critical_operation(self):
            # This method will run in a new transaction with specific settings
            pass
    """
    def decorator(func: F) -> F:
        # Create configuration
        config = TransactionalConfig(
            propagation=propagation,
            isolation=isolation,
            timeout=timeout,
            read_only=read_only,
            rollback_for=rollback_for,
            no_rollback_for=no_rollback_for,
            transaction_manager=transaction_manager
        )
        
        # Create interceptor
        interceptor = TransactionalInterceptor(config, _transaction_manager_instance)
        
        # Store transactional metadata on the function
        func._transactional_config = config
        func._transactional_interceptor = interceptor
        
        if inspect.iscoroutinefunction(func):
            # Handle async functions
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # For async functions, we need special handling
                # This is a simplified implementation - full async transaction support
                # would require more sophisticated handling
                return await func(*args, **kwargs)
            
            return async_wrapper
        else:
            # Handle sync functions
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return interceptor.invoke(func, args, kwargs)
            
            return sync_wrapper
    
    return decorator


# Convenience alias following Spring naming convention
Transactional = transactional


def is_transactional(func: Callable) -> bool:
    """
    Check if a function is decorated with @transactional.
    
    Args:
        func: The function to check
        
    Returns:
        True if the function is transactional, False otherwise
    """
    return hasattr(func, '_transactional_config')


def get_transactional_config(func: Callable) -> Optional[TransactionalConfig]:
    """
    Get the transactional configuration for a function.
    
    Args:
        func: The function to get configuration for
        
    Returns:
        The transactional configuration, or None if not transactional
    """
    return getattr(func, '_transactional_config', None)


def get_transactional_interceptor(func: Callable) -> Optional[TransactionalInterceptor]:
    """
    Get the transactional interceptor for a function.
    
    Args:
        func: The function to get interceptor for
        
    Returns:
        The transactional interceptor, or None if not transactional
    """
    return getattr(func, '_transactional_interceptor', None)