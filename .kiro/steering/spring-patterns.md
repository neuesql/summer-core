# Spring Framework Design Patterns

## Decorator-Based Annotations

### Component Stereotypes
```python
# Core component decorators
@Component      # Generic component
@Service        # Business logic layer
@Repository     # Data access layer
@Controller     # Presentation layer (for web features)
@Configuration  # Configuration class
```

### Dependency Injection Decorators
```python
@Autowired      # Automatic dependency injection
@Qualifier      # Specify which bean to inject when multiple candidates exist
@Value          # Inject configuration values
@Bean           # Method-level bean definition
@Scope          # Define bean scope (singleton, prototype, etc.)
```

### AOP Decorators
```python
@Aspect         # Mark class as aspect
@Before         # Execute before method
@After          # Execute after method
@Around         # Wrap method execution
@Transactional  # Database transaction management
@Cacheable      # Method result caching
```

## Bean Lifecycle Management

### Initialization and Destruction
```python
@Component
class DatabaseConnection:
    @PostConstruct
    def initialize(self):
        # Setup connection pool
        pass
    
    @PreDestroy  
    def cleanup(self):
        # Close connections
        pass
```

### Bean Scopes
- **Singleton**: One instance per container (default)
- **Prototype**: New instance for each request
- **Request**: One instance per HTTP request (web contexts)
- **Session**: One instance per HTTP session (web contexts)

## Configuration Patterns

### Profile-Based Configuration
```python
@Configuration
@Profile("development")
class DevConfig:
    @Bean
    def database(self) -> Database:
        return InMemoryDatabase()

@Configuration  
@Profile("production")
class ProdConfig:
    @Bean
    def database(self) -> Database:
        return PostgreSQLDatabase()
```

### Property-Based Configuration
```python
@Component
class EmailService:
    def __init__(self):
        self.smtp_host = None
        self.smtp_port = None
    
    @Value("${email.smtp.host}")
    def set_smtp_host(self, host: str):
        self.smtp_host = host
        
    @Value("${email.smtp.port:587}")  # Default value
    def set_smtp_port(self, port: int):
        self.smtp_port = port
```

## Enterprise Integration Patterns

### Event-Driven Architecture
```python
@Component
class OrderService:
    @Autowired
    def __init__(self, event_publisher: ApplicationEventPublisher):
        self.event_publisher = event_publisher
    
    def create_order(self, order_data):
        order = Order(order_data)
        # Business logic
        self.event_publisher.publish(OrderCreatedEvent(order))

@EventListener
def handle_order_created(event: OrderCreatedEvent):
    # Handle the event
    pass
```

### Repository Pattern
```python
@Repository
class UserRepository:
    @Autowired
    def __init__(self, data_source: DataSource):
        self.data_source = data_source
    
    def find_by_email(self, email: str) -> Optional[User]:
        # Data access logic
        pass
    
    @Transactional
    def save(self, user: User) -> User:
        # Save with transaction management
        pass
```

## Testing Patterns

### Test Configuration
```python
@TestConfiguration
class TestConfig:
    @Bean
    @Primary  # Override production bean
    def mock_external_service(self) -> ExternalService:
        return MockExternalService()

@SpringTest
class ServiceTest:
    @Autowired
    private UserService user_service
    
    @MockBean
    private UserRepository user_repository
    
    def test_user_creation(self):
        # Test with mocked dependencies
        pass
```