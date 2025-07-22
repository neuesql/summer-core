# Integration Overview

Summer Core provides integration with various technologies and frameworks to help you build comprehensive enterprise applications.

## Web Integration

Summer Core integrates with popular Python web frameworks like Flask, FastAPI, and Django:

```python
from summer_core.integration.web import FlaskIntegration
from flask import Flask

app = Flask(__name__)
integration = FlaskIntegration(app, base_packages=["myapp"])
integration.initialize()

@app.route("/")
def index():
    user_service = integration.get_bean("userService")
    users = user_service.get_all_users()
    return {"users": [user.__dict__ for user in users]}
```

## Messaging Integration

Summer Core provides integration with message queues like RabbitMQ, Redis, and Apache Kafka:

```python
from summer_core.integration.messaging import RabbitMQIntegration
from summer_core.decorators import Component

@Component
class OrderProcessor:
    @RabbitMQIntegration.listener(queue="orders")
    def process_order(self, message):
        # Process the order
        print(f"Processing order: {message}")
```

## Caching Integration

Summer Core provides integration with caching systems like Redis and Memcached:

```python
from summer_core.decorators import Service
from summer_core.integration.caching import Cacheable

@Service
class UserService:
    @Cacheable(key="user:{0}")
    def get_user(self, user_id):
        # This result will be cached
        return self.user_repository.find_by_id(user_id)
```

## Scheduling Integration

Summer Core provides integration with scheduling systems:

```python
from summer_core.decorators import Component
from summer_core.integration.scheduling import Scheduled

@Component
class ReportGenerator:
    @Scheduled(cron="0 0 * * *")  # Run at midnight every day
    def generate_daily_report(self):
        # Generate the daily report
        print("Generating daily report")
```

## REST API Integration

Summer Core provides integration with REST APIs:

```python
from summer_core.decorators import Service
from summer_core.integration.rest import RestTemplate

@Service
class WeatherService:
    def __init__(self):
        self.rest_template = RestTemplate()
    
    def get_weather(self, city):
        url = f"https://api.weather.com/current?city={city}"
        response = self.rest_template.get(url)
        return response.json()
```

## Database Integration

Summer Core provides integration with various databases:

```python
from summer_core.decorators import Configuration, Bean
from summer_core.integration.database import DataSource

@Configuration
class DatabaseConfig:
    @Bean
    def data_source(self):
        data_source = DataSource()
        data_source.set_url("jdbc:postgresql://localhost:5432/mydb")
        data_source.set_username("user")
        data_source.set_password("password")
        return data_source
```

## Best Practices

1. **Use Integration Abstractions**: Use Summer Core's integration abstractions to decouple your application from specific technologies
2. **Configure Integration Points**: Configure integration points in a centralized location
3. **Handle Integration Errors**: Handle errors that may occur during integration
4. **Test Integration Points**: Test integration points in isolation and with the integrated systems
5. **Use Appropriate Integration Patterns**: Use appropriate integration patterns for each integration scenario