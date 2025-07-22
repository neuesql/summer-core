# Repositories

The repository pattern is a design pattern that abstracts the data access layer from the rest of the application. Summer Core provides support for implementing repositories using the `@Repository` annotation.

## Overview

Repositories provide a clean separation between the domain model and the data access layer. They hide the details of data retrieval and storage, allowing the rest of the application to focus on business logic.

## Creating Repositories

To create a repository, annotate a class with `@Repository`:

```python
from summer_core.decorators import Repository
from myapp.models import User

@Repository
class UserRepository:
    def __init__(self):
        # Initialize data access
        pass
    
    def find_by_id(self, user_id):
        # Find a user by ID
        pass
    
    def find_all(self):
        # Find all users
        pass
    
    def save(self, user):
        # Save a user
        pass
    
    def delete(self, user):
        # Delete a user
        pass
```

## Using Repositories

Repositories can be injected into services and other components:

```python
from summer_core.decorators import Service, Autowired

@Service
class UserService:
    @Autowired
    def __init__(self, user_repository):
        self.user_repository = user_repository
    
    def get_user(self, user_id):
        return self.user_repository.find_by_id(user_id)
    
    def get_all_users(self):
        return self.user_repository.find_all()
```

## Exception Translation

Repositories automatically translate data access exceptions into Spring's data access exception hierarchy. This allows you to handle data access exceptions in a consistent way, regardless of the underlying data access technology.

## ORM Integration

Summer Core provides integration with popular ORM frameworks like SQLAlchemy:

```python
from summer_core.decorators import Repository
from summer_core.data import SQLAlchemyRepository
from myapp.models import User

@Repository
class UserRepository(SQLAlchemyRepository):
    def __init__(self, session_factory):
        super().__init__(session_factory, User)
    
    def find_by_username(self, username):
        return self.query().filter_by(username=username).first()
```

## Best Practices

1. **Use Repository Interfaces**: Define repository interfaces to abstract the implementation details
2. **Keep Repositories Focused**: Each repository should focus on a single domain entity
3. **Use Meaningful Method Names**: Use descriptive names for repository methods
4. **Handle Exceptions**: Handle data access exceptions appropriately
5. **Use Transactions**: Use transactions for operations that modify data