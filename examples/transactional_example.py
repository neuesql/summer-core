#!/usr/bin/env python3
"""
Example demonstrating the @transactional decorator functionality.

This example shows how to use the @transactional decorator for declarative
transaction management with various configuration options.
"""

from summer_core.decorators.transactional import transactional, Transactional
from summer_core.transaction.transaction_manager import (
    Propagation, 
    Isolation, 
    PlatformTransactionManager,
    TransactionStatus,
    TransactionDefinition,
    TransactionSynchronizationManager
)
from summer_core.exceptions import TransactionException


class MockTransactionManager(PlatformTransactionManager):
    """Mock transaction manager for demonstration purposes."""
    
    def __init__(self):
        self.transactions = []
        self.committed = []
        self.rolled_back = []
    
    def get_transaction(self, definition=None):
        """Begin a new transaction."""
        tx_id = len(self.transactions) + 1
        status = MockTransactionStatus(tx_id, definition)
        self.transactions.append(status)
        print(f"🔄 Started transaction {tx_id} with {definition.propagation.name} propagation, "
              f"{definition.isolation.name} isolation, timeout={definition.timeout}s, "
              f"read_only={definition.read_only}")
        return status
    
    def commit(self, status):
        """Commit the transaction."""
        self.committed.append(status.transaction_id)
        print(f"✅ Committed transaction {status.transaction_id}")
    
    def rollback(self, status):
        """Rollback the transaction."""
        self.rolled_back.append(status.transaction_id)
        print(f"❌ Rolled back transaction {status.transaction_id}")


class MockTransactionStatus(TransactionStatus):
    """Mock transaction status for demonstration."""
    
    def __init__(self, transaction_id, definition):
        super().__init__(None, transaction_id, True, False, False)
        self.transaction_id = transaction_id
        self.definition = definition


class UserService:
    """Example service class demonstrating transactional methods."""
    
    def __init__(self):
        self.users = []
        self.audit_log = []
    
    @transactional()
    def create_user(self, username, email):
        """Create a user with default transaction settings."""
        print(f"📝 Creating user: {username} ({email})")
        user = {"id": len(self.users) + 1, "username": username, "email": email}
        self.users.append(user)
        self.audit_log.append(f"Created user {username}")
        return user
    
    @transactional(
        propagation=Propagation.REQUIRES_NEW,
        isolation=Isolation.SERIALIZABLE,
        timeout=30,
        read_only=False
    )
    def create_user_with_new_transaction(self, username, email):
        """Create a user in a new transaction with specific settings."""
        print(f"📝 Creating user in new transaction: {username} ({email})")
        user = {"id": len(self.users) + 1, "username": username, "email": email}
        self.users.append(user)
        self.audit_log.append(f"Created user {username} in new transaction")
        return user
    
    @transactional(read_only=True, isolation=Isolation.READ_COMMITTED)
    def get_user_count(self):
        """Get user count in a read-only transaction."""
        print("📊 Getting user count (read-only)")
        return len(self.users)
    
    @transactional(rollback_for=[ValueError])
    def create_user_with_validation(self, username, email):
        """Create user with validation that triggers rollback on ValueError."""
        print(f"📝 Creating user with validation: {username} ({email})")
        
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters")
        
        if "@" not in email:
            raise ValueError("Invalid email format")
        
        user = {"id": len(self.users) + 1, "username": username, "email": email}
        self.users.append(user)
        self.audit_log.append(f"Created validated user {username}")
        return user
    
    @transactional(no_rollback_for=[KeyError])
    def create_user_ignore_key_errors(self, username, email, metadata=None):
        """Create user but don't rollback on KeyError."""
        print(f"📝 Creating user (ignoring KeyError): {username} ({email})")
        
        # This will raise KeyError but won't rollback the transaction
        if metadata:
            required_field = metadata["required_field"]  # May raise KeyError
        
        user = {"id": len(self.users) + 1, "username": username, "email": email}
        self.users.append(user)
        self.audit_log.append(f"Created user {username} (ignored KeyError)")
        return user
    
    @transactional(
        propagation=Propagation.NESTED,
        rollback_for=[RuntimeError],
        no_rollback_for=[ValueError]
    )
    def complex_user_operation(self, username, email, should_fail=None):
        """Complex operation with nested transaction and custom rollback rules."""
        print(f"📝 Complex user operation: {username} ({email})")
        
        if should_fail == "runtime":
            raise RuntimeError("Runtime error - will rollback")
        elif should_fail == "value":
            raise ValueError("Value error - will NOT rollback")
        
        user = {"id": len(self.users) + 1, "username": username, "email": email}
        self.users.append(user)
        self.audit_log.append(f"Complex operation for user {username}")
        return user


def demonstrate_transactional_decorator():
    """Demonstrate various @transactional decorator features."""
    print("🚀 Demonstrating @transactional decorator functionality\n")
    
    # Set up mock transaction manager
    tx_manager = MockTransactionManager()
    TransactionSynchronizationManager.bind_resource('transaction_manager', tx_manager)
    
    # Create service instance
    service = UserService()
    
    print("=" * 60)
    print("1. Basic transactional method (default settings)")
    print("=" * 60)
    try:
        user = service.create_user("alice", "alice@example.com")
        print(f"✅ Created user: {user}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    print("=" * 60)
    print("2. Transactional method with custom settings")
    print("=" * 60)
    try:
        user = service.create_user_with_new_transaction("bob", "bob@example.com")
        print(f"✅ Created user: {user}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    print("=" * 60)
    print("3. Read-only transaction")
    print("=" * 60)
    try:
        count = service.get_user_count()
        print(f"✅ User count: {count}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    print("=" * 60)
    print("4. Transaction with validation (successful)")
    print("=" * 60)
    try:
        user = service.create_user_with_validation("charlie", "charlie@example.com")
        print(f"✅ Created validated user: {user}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    print("=" * 60)
    print("5. Transaction with validation (rollback on ValueError)")
    print("=" * 60)
    try:
        user = service.create_user_with_validation("x", "invalid-email")
        print(f"✅ Created user: {user}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    print("=" * 60)
    print("6. Transaction ignoring KeyError (no rollback)")
    print("=" * 60)
    try:
        user = service.create_user_ignore_key_errors("dave", "dave@example.com", {})
        print(f"✅ Created user: {user}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    print("=" * 60)
    print("7. Complex transaction with nested propagation (success)")
    print("=" * 60)
    try:
        user = service.complex_user_operation("eve", "eve@example.com")
        print(f"✅ Created user: {user}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    print("=" * 60)
    print("8. Complex transaction with RuntimeError (rollback)")
    print("=" * 60)
    try:
        user = service.complex_user_operation("frank", "frank@example.com", "runtime")
        print(f"✅ Created user: {user}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    print("=" * 60)
    print("9. Complex transaction with ValueError (no rollback)")
    print("=" * 60)
    try:
        user = service.complex_user_operation("grace", "grace@example.com", "value")
        print(f"✅ Created user: {user}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    # Print summary
    print("=" * 60)
    print("TRANSACTION SUMMARY")
    print("=" * 60)
    print(f"Total transactions started: {len(tx_manager.transactions)}")
    print(f"Transactions committed: {len(tx_manager.committed)} - {tx_manager.committed}")
    print(f"Transactions rolled back: {len(tx_manager.rolled_back)} - {tx_manager.rolled_back}")
    print(f"Users created: {len(service.users)}")
    print(f"Audit log entries: {len(service.audit_log)}")
    print()
    
    print("Users in database:")
    for user in service.users:
        print(f"  - {user}")
    print()
    
    print("Audit log:")
    for entry in service.audit_log:
        print(f"  - {entry}")
    
    # Clean up
    TransactionSynchronizationManager.clear()


if __name__ == "__main__":
    demonstrate_transactional_decorator()