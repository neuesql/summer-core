"""
Application event base class for the Summer Core framework.
"""

import time
from typing import Any, Optional


class ApplicationEvent:
    """
    Base class for all application events.
    
    Application events are used to communicate between components in a loosely coupled way.
    Components can publish events and other components can listen for these events.
    
    Attributes:
        source: The object that published the event
        timestamp: The time when the event was created (in milliseconds since epoch)
    """
    
    def __init__(self, source: Any):
        """
        Initialize a new application event.
        
        Args:
            source: The object that published the event
        """
        self._source = source
        self._timestamp = int(time.time() * 1000)  # Current time in milliseconds
    
    @property
    def source(self) -> Any:
        """
        Get the object that published the event.
        
        Returns:
            The source object
        """
        return self._source
    
    @property
    def timestamp(self) -> int:
        """
        Get the time when the event was created.
        
        Returns:
            The timestamp in milliseconds since epoch
        """
        return self._timestamp


class ContextRefreshedEvent(ApplicationEvent):
    """Event published when the application context is initialized or refreshed."""
    pass


class ContextClosedEvent(ApplicationEvent):
    """Event published when the application context is closed."""
    pass


class ContextStartedEvent(ApplicationEvent):
    """Event published when the application context is started."""
    pass


class ContextStoppedEvent(ApplicationEvent):
    """Event published when the application context is stopped."""
    pass


class BeanCreatedEvent(ApplicationEvent):
    """
    Event published when a bean is created.
    
    Attributes:
        bean_name: The name of the bean that was created
        bean: The bean instance that was created
    """
    
    def __init__(self, source: Any, bean_name: str, bean: Any):
        """
        Initialize a new bean created event.
        
        Args:
            source: The object that published the event
            bean_name: The name of the bean that was created
            bean: The bean instance that was created
        """
        super().__init__(source)
        self._bean_name = bean_name
        self._bean = bean
    
    @property
    def bean_name(self) -> str:
        """
        Get the name of the bean that was created.
        
        Returns:
            The bean name
        """
        return self._bean_name
    
    @property
    def bean(self) -> Any:
        """
        Get the bean instance that was created.
        
        Returns:
            The bean instance
        """
        return self._bean