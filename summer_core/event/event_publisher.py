"""
Event publisher interface and implementation for the Summer Core framework.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type

from summer_core.event.application_event import ApplicationEvent


class ApplicationEventPublisher(ABC):
    """
    Interface for publishing application events.
    
    This interface is implemented by objects that can publish events to be
    consumed by event listeners.
    """
    
    @abstractmethod
    def publish_event(self, event: ApplicationEvent) -> None:
        """
        Publish an application event.
        
        Args:
            event: The event to publish
        """
        pass


class ApplicationEventPublisherAware(ABC):
    """
    Interface to be implemented by any object that wishes to be notified of
    the ApplicationEventPublisher that it runs in.
    """
    
    @abstractmethod
    def set_application_event_publisher(self, publisher: ApplicationEventPublisher) -> None:
        """
        Set the ApplicationEventPublisher that this object runs in.
        
        Args:
            publisher: The ApplicationEventPublisher to be used
        """
        pass


class ApplicationEventMultiPublisher(ApplicationEventPublisher):
    """
    Implementation of the ApplicationEventPublisher interface that publishes events to multiple listeners.
    
    This implementation maintains a registry of event listeners and multicasts
    events to all listeners that are interested in that event type.
    """
    
    def __init__(self):
        """Initialize a new event multicaster."""
        self._listeners: Dict[Type[ApplicationEvent], List[callable]] = {}
    
    def add_listener(self, event_type: Type[ApplicationEvent], listener: callable) -> None:
        """
        Add a listener for a specific event type.
        
        Args:
            event_type: The type of event to listen for
            listener: The listener function or method
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        
        if listener not in self._listeners[event_type]:
            self._listeners[event_type].append(listener)
    
    def remove_listener(self, event_type: Type[ApplicationEvent], listener: callable) -> None:
        """
        Remove a listener for a specific event type.
        
        Args:
            event_type: The type of event
            listener: The listener to remove
        """
        if event_type in self._listeners and listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)
            
            # Clean up empty lists
            if not self._listeners[event_type]:
                del self._listeners[event_type]
    
    def publish_event(self, event: ApplicationEvent) -> None:
        """
        Publish an application event.
        
        This method notifies all listeners that are registered for the event type.
        
        Args:
            event: The event to publish
        """
        # Get the event's class and all its parent classes
        event_types = [event.__class__]
        current_class = event.__class__
        
        # Add all parent classes that are subclasses of ApplicationEvent
        while True:
            parent = current_class.__base__
            if parent is ApplicationEvent:
                event_types.append(parent)
                break
            elif issubclass(parent, ApplicationEvent):
                event_types.append(parent)
                current_class = parent
            else:
                break
        
        # Notify listeners for each event type
        for event_type in event_types:
            if event_type in self._listeners:
                for listener in self._listeners[event_type]:
                    try:
                        listener(event)
                    except Exception as e:
                        # Throw an exception instead of printing
                        raise RuntimeError(f"Error notifying listener {listener} for event {event}") from e