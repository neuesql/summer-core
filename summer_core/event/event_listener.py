"""
Event listener decorator for the Summer Core framework.
"""

import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast

from summer_core.event.application_event import ApplicationEvent

T = TypeVar('T', bound=Callable[..., Any])


class EventListenerCondition:
    """
    Condition for conditional event processing.
    
    This class represents a condition that must be met for an event listener
    to process an event.
    """
    
    def __init__(self, condition: Callable[[ApplicationEvent], bool]):
        """
        Initialize a new event listener condition.
        
        Args:
            condition: A function that takes an event and returns a boolean
                indicating whether the event should be processed
        """
        self.condition = condition
    
    def matches(self, event: ApplicationEvent) -> bool:
        """
        Check if the condition matches the event.
        
        Args:
            event: The event to check
            
        Returns:
            True if the condition matches the event, False otherwise
        """
        return self.condition(event)


def EventListener(
    event_type: Optional[Type[ApplicationEvent]] = None,
    condition: Optional[Callable[[ApplicationEvent], bool]] = None,
    classes: Optional[List[Type[ApplicationEvent]]] = None
) -> Callable[[T], T]:
    """
    Decorator for methods that should listen for application events.
    
    This decorator marks a method as an event listener. The method will be
    automatically registered with the application event publisher when the
    bean is created.
    
    Args:
        event_type: The type of event to listen for. If not specified, the
            event type will be inferred from the method's type hints.
        condition: A function that takes an event and returns a boolean
            indicating whether the event should be processed
        classes: A list of event types to listen for. If specified, the method
            will be registered as a listener for all specified event types.
            
    Returns:
        The decorated method
    
    Example:
        ```python
        @Component
        class MyListener:
            @EventListener
            def on_context_refreshed(self, event: ContextRefreshedEvent):
                print(f"Context refreshed: {event.source}")
                
            @EventListener(ContextClosedEvent)
            def on_context_closed(self, event):
                print(f"Context closed: {event.source}")
                
            @EventListener(condition=lambda event: event.source == "important")
            def on_important_event(self, event: ApplicationEvent):
                print(f"Important event: {event}")
                
            @EventListener(classes=[ContextRefreshedEvent, ContextClosedEvent])
            def on_context_event(self, event: ApplicationEvent):
                print(f"Context event: {event}")
        ```
    """
    def decorator(func: T) -> T:
        # Store the event types on the function
        event_types = []
        
        if classes:
            # Use explicitly specified event types
            event_types.extend(classes)
        elif event_type is not None:
            # Use explicitly specified event type
            event_types.append(event_type)
        else:
            # Try to infer the event type from the method's type hints
            sig = inspect.signature(func)
            params = list(sig.parameters.values())
            
            # Skip 'self' parameter for instance methods
            start_idx = 1 if len(params) > 0 and params[0].name == 'self' else 0
            
            if len(params) <= start_idx:
                raise ValueError(
                    f"Event listener method {func.__name__} must have at least one parameter "
                    f"to receive the event"
                )
            
            event_param = params[start_idx]
            if event_param.annotation == inspect.Parameter.empty:
                raise ValueError(
                    f"Event listener method {func.__name__} must have a type hint "
                    f"for the event parameter or specify the event type explicitly"
                )
            
            if not issubclass(event_param.annotation, ApplicationEvent):
                raise ValueError(
                    f"Event listener method {func.__name__} must listen for a subclass "
                    f"of ApplicationEvent, got {event_param.annotation}"
                )
            
            event_types.append(event_param.annotation)
        
        # Store the event types on the function
        func.__event_types__ = event_types  # type: ignore
        
        # Store the condition on the function
        if condition:
            func.__event_condition__ = EventListenerCondition(condition)  # type: ignore
        
        # Mark the function as an event listener
        func.__is_event_listener__ = True  # type: ignore
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Check if the function is marked as async
            if hasattr(func, '__is_async__') and func.__is_async__:
                # The function is already wrapped with @Async, so just call it
                return func(*args, **kwargs)
            else:
                # Call the function synchronously
                return func(*args, **kwargs)
        
        # Copy the event listener metadata to the wrapper
        wrapper.__event_types__ = func.__event_types__  # type: ignore
        wrapper.__is_event_listener__ = True  # type: ignore
        if hasattr(func, '__event_condition__'):
            wrapper.__event_condition__ = func.__event_condition__  # type: ignore
        
        # For backward compatibility
        if event_types:
            wrapper.__event_type__ = event_types[0]  # type: ignore
        
        return cast(T, wrapper)
    
    return decorator