#!/usr/bin/env python3
"""
Demonstration of lifecycle callback functionality in Summer Core.

This script shows how @PostConstruct, @PreDestroy, InitializingBean, 
and DisposableBean work in the Summer Core framework.
"""

from summer_core import (
    Service, Autowired, DefaultApplicationContext,
    PostConstruct, PreDestroy, InitializingBean, DisposableBean
)


@Service
class DatabaseService:
    """Service that manages database connections."""
    
    def __init__(self):
        print("DatabaseService: Constructor called")
        self.connection = None
        self.is_connected = False
    
    @PostConstruct
    def initialize_connection(self):
        """Initialize database connection after dependency injection."""
        print("DatabaseService: @PostConstruct - Initializing database connection")
        self.connection = "mock_database_connection"
        self.is_connected = True
    
    @PreDestroy
    def close_connection(self):
        """Close database connection before bean destruction."""
        print("DatabaseService: @PreDestroy - Closing database connection")
        if self.connection:
            self.connection = None
            self.is_connected = False
    
    def execute_query(self, query: str):
        """Execute a database query."""
        if self.is_connected:
            return f"Executed: {query}"
        else:
            return "Database not connected"


@Service
class CacheService(InitializingBean, DisposableBean):
    """Service that implements lifecycle interfaces."""
    
    def __init__(self):
        print("CacheService: Constructor called")
        self.cache = {}
        self.is_initialized = False
    
    def after_properties_set(self):
        """Initialize cache after all properties are set."""
        print("CacheService: InitializingBean.after_properties_set() - Setting up cache")
        self.cache = {"default": "value"}
        self.is_initialized = True
    
    def destroy(self):
        """Clean up cache before destruction."""
        print("CacheService: DisposableBean.destroy() - Clearing cache")
        self.cache.clear()
        self.is_initialized = False
    
    def get(self, key: str):
        """Get value from cache."""
        return self.cache.get(key, "Not found") if self.is_initialized else "Cache not initialized"
    
    def put(self, key: str, value: str):
        """Put value in cache."""
        if self.is_initialized:
            self.cache[key] = value


@Service
class UserService:
    """Service that uses other services and has lifecycle methods."""
    
    @Autowired
    def __init__(self, database_service: DatabaseService, cache_service: CacheService):
        print("UserService: Constructor called with dependencies")
        self.database_service = database_service
        self.cache_service = cache_service
        self.is_ready = False
    
    @PostConstruct
    def initialize(self):
        """Initialize service after dependency injection."""
        print("UserService: @PostConstruct - Service initialization")
        # Use injected dependencies
        result = self.database_service.execute_query("SELECT * FROM users")
        print(f"UserService: Database query result: {result}")
        
        self.cache_service.put("last_query", "users")
        cached_value = self.cache_service.get("last_query")
        print(f"UserService: Cached value: {cached_value}")
        
        self.is_ready = True
    
    @PreDestroy
    def cleanup(self):
        """Clean up before destruction."""
        print("UserService: @PreDestroy - Service cleanup")
        self.is_ready = False
    
    def get_user(self, user_id: int):
        """Get user by ID."""
        if not self.is_ready:
            return "Service not ready"
        
        # Check cache first
        cache_key = f"user_{user_id}"
        cached_user = self.cache_service.get(cache_key)
        if cached_user != "Not found":
            return f"From cache: {cached_user}"
        
        # Query database
        query_result = self.database_service.execute_query(f"SELECT * FROM users WHERE id = {user_id}")
        user_data = f"User {user_id} data"
        
        # Cache the result
        self.cache_service.put(cache_key, user_data)
        
        return user_data


def main():
    """Demonstrate lifecycle callback functionality."""
    print("=== Summer Core Lifecycle Callback Demo ===\n")
    
    print("1. Creating ApplicationContext...")
    context = DefaultApplicationContext(base_packages=["__main__"])
    
    print("\n2. Refreshing context (this triggers bean creation and @PostConstruct methods)...")
    context.refresh()
    
    print("\n3. Using the services...")
    user_service = context.get_bean("userService")
    
    # Use the service
    user1 = user_service.get_user(1)
    print(f"First call - {user1}")
    
    user1_again = user_service.get_user(1)
    print(f"Second call (should be from cache) - {user1_again}")
    
    user2 = user_service.get_user(2)
    print(f"Different user - {user2}")
    
    print("\n4. Closing context (this triggers @PreDestroy methods and DisposableBean.destroy())...")
    context.close()
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()