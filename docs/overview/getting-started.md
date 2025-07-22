# Getting Started with Summer Core

This guide will help you set up a basic application using Summer Core.

## Installation

Summer Core can be installed using pip:

```bash
pip install summer-core
```

## Creating Your First Application

Let's create a simple application that demonstrates the core features of Summer Core.

### Project Structure

```
myapp/
├── __init__.py
├── config.py
├── models.py
├── repositories.py
├── services.py
└── main.py
```

### Step 1: Define Your Models

First, let's define a simple model in `models.py`:

```python
class User:
    def __init__(self, user_id, username, email):
        self.user_id = user_id
        self.username = username
        self.email = email
```

### Step 2: Create Repositories

Next, let's create a repository for data access in `repositories.py`:

```python
from summer_core.decorators import Repository
from myapp.models import User

@Repository
class UserRepository:
    def __init__(self):
        # Simulate a database with some users
        self.users = {
            1: User(1, "john_doe", "john@example.com"),
            2: User(2, "jane_smith", "jane@example.com")
        }
    
    def find_by_id(self, user_id):
        return self.users.get(user_id)
    
    def find_all(self):
        return list(self.users.values())
```

### Step 3: Create Services

Now, let's create a service that uses the repository in `services.py`:

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

### Step 4: Create Configuration

Let's create a configuration class in `config.py`:

```python
from summer_core.decorators import Configuration, Bean

@Configuration
class AppConfig:
    @Bean
    def app_name(self):
        return "My Summer Core App"
    
    @Bean
    def version(self):
        return "1.0.0"
```

### Step 5: Create Main Application

Finally, let's create the main application in `main.py`:

```python
from summer_core.container import ApplicationContext

def main():
    # Create and configure the application context
    context = ApplicationContext(base_packages=["myapp"])
    context.refresh()
    
    # Get the user service from the container
    user_service = context.get_bean("userService")
    
    # Use the service
    user = user_service.get_user(1)
    print(f"User: {user.username} ({user.email})")
    
    # Get configuration beans
    app_name = context.get_bean("app_name")
    version = context.get_bean("version")
    print(f"Application: {app_name} v{version}")
    
    # Close the context when done
    context.close()

if __name__ == "__main__":
    main()
```

## Running the Application

To run the application, simply execute the main.py file:

```bash
python myapp/main.py
```

You should see output similar to:

```
User: john_doe (john@example.com)
Application: My Summer Core App v1.0.0
```

## Next Steps

Now that you've created a basic application with Summer Core, you can explore more advanced features:

- [IoC Container](../core/ioc.md): Learn more about the IoC container
- [Beans](../core/beans.md): Understand bean lifecycle and scopes
- [AOP](../aop/introduction.md): Explore aspect-oriented programming
- [Event System](../event/introduction.md): Build event-driven applications

!!! tip "Best Practice"
    Always close the application context when your application shuts down to properly release resources.