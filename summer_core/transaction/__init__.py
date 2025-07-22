"""
Transaction Management.

This module provides declarative and programmatic transaction management
including transaction managers and transaction templates.
"""

from summer_core.transaction.database_transaction_manager import (
    AbstractDatabaseTransactionManager,
    DatabaseTransactionStatus,
    JDBCLikeTransactionManager,
    SQLAlchemyTransactionManager,
)
from summer_core.transaction.transaction_manager import (
    DEFAULT_TRANSACTION_DEFINITION,
    Isolation,
    PlatformTransactionManager,
    Propagation,
    TransactionDefinition,
    TransactionStatus,
    TransactionSynchronization,
    TransactionSynchronizationManager,
    TransactionTemplate,
)

__all__ = [
    'PlatformTransactionManager',
    'TransactionStatus',
    'TransactionDefinition',
    'DEFAULT_TRANSACTION_DEFINITION',
    'Propagation',
    'Isolation',
    'TransactionSynchronization',
    'TransactionSynchronizationManager',
    'TransactionTemplate',
    'AbstractDatabaseTransactionManager',
    'DatabaseTransactionStatus',
    'SQLAlchemyTransactionManager',
    'JDBCLikeTransactionManager',
]