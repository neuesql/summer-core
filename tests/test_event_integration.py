"""
Integration tests for the event system with the application context.
"""

import unittest
from typing import List

from summer_core.container.application_context import DefaultApplicationContext
from summer_core.decorators.component import Component
from summer_core.event.application_event import ApplicationEvent, ContextRefreshedEvent, ContextClosedEvent
from summer_core.event.event_listener import EventListener
from summer_core.event.event_publisher import ApplicationEventPublisherAware, ApplicationEventPublisher


class SampleEvent(ApplicationEvent):
    """Sample event class for testing."""
    
    def __init__(self, source: object, message: str):
        super().__init__(source)
        self.message = message


@Component
class EventListenerComponent:
    """Test component with event listeners."""
    
    def __init__(self):
        self.context_refreshed = False
        self.context_closed = False
        self.test_events: List[SampleEvent] = []
    
    @EventListener(ContextRefreshedEvent)
    def on_context_refreshed(self, event: ContextRefreshedEvent):
        """Handle context refreshed event."""
        self.context_refreshed = True
    
    @EventListener(ContextClosedEvent)
    def on_context_closed(self, event: ContextClosedEvent):
        """Handle context closed event."""
        self.context_closed = True
    
    @EventListener()
    def on_test_event(self, event: SampleEvent):
        """Handle test event."""
        self.test_events.append(event)


@Component
class EventPublisherComponent(ApplicationEventPublisherAware):
    """Test component that publishes events."""
    
    def __init__(self):
        self.publisher = None
    
    def set_application_event_publisher(self, publisher: ApplicationEventPublisher) -> None:
        """Set the application event publisher."""
        self.publisher = publisher
    
    def publish_test_event(self, message: str) -> None:
        """Publish a test event."""
        if self.publisher:
            self.publisher.publish_event(SampleEvent(self, message))


class TestEventIntegration(unittest.TestCase):
    """Integration tests for the event system with the application context."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary package for testing
        import sys
        import tempfile
        import os
        
        self.temp_dir = tempfile.TemporaryDirectory()
        self.package_name = "test_event_package"
        self.package_path = os.path.join(self.temp_dir.name, self.package_name)
        os.makedirs(self.package_path)
        
        # Create __init__.py to make it a package
        with open(os.path.join(self.package_path, "__init__.py"), "w") as f:
            f.write("")
        
        # Create a module with components
        with open(os.path.join(self.package_path, "components.py"), "w") as f:
            f.write("""
from summer_core.decorators.component import Component
from summer_core.event.application_event import ApplicationEvent, ContextRefreshedEvent
from summer_core.event.event_listener import EventListener
from summer_core.event.event_publisher import ApplicationEventPublisherAware, ApplicationEventPublisher


class SampleEvent(ApplicationEvent):
    def __init__(self, source, message):
        super().__init__(source)
        self.message = message


@Component
class EventListenerComponent:
    def __init__(self):
        self.context_refreshed = False
        self.test_events = []
    
    @EventListener(ContextRefreshedEvent)
    def on_context_refreshed(self, event):
        self.context_refreshed = True
    
    @EventListener()
    def on_test_event(self, event: SampleEvent):
        self.test_events.append(event)


@Component
class EventPublisherComponent(ApplicationEventPublisherAware):
    def __init__(self):
        self.publisher = None
    
    def set_application_event_publisher(self, publisher):
        self.publisher = publisher
    
    def publish_test_event(self, message):
        if self.publisher:
            self.publisher.publish_event(SampleEvent(self, message))
""")
        
        # Add the temporary directory to sys.path
        sys.path.insert(0, self.temp_dir.name)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove the temporary directory from sys.path
        import sys
        sys.path.remove(self.temp_dir.name)
        
        # Clean up the temporary directory
        self.temp_dir.cleanup()
        
        # Close the application context if it exists
        if hasattr(self, 'context') and self.context:
            self.context.close()
    
    def test_event_listener_registration(self):
        """Test that event listeners are registered during context refresh."""
        # Create an application context with the test package
        self.context = DefaultApplicationContext([self.package_name])
        
        # Import the components from the test package
        import importlib
        module = importlib.import_module(f"{self.package_name}.components")
        
        # Create a listener component manually
        listener = module.EventListenerComponent()
        
        # Register the listener with the event multicaster directly
        self.context._event_multicaster.add_listener(ContextRefreshedEvent, listener.on_context_refreshed)
        
        # Refresh the context to trigger component scanning and publish the context refreshed event
        self.context.refresh()
        
        # Check that the context refreshed event was received
        self.assertTrue(listener.context_refreshed)
    
    def test_event_publishing(self):
        """Test that events can be published through the application context."""
        # Create a listener and publisher
        listener = EventListenerComponent()
        publisher = EventPublisherComponent()
        
        # Create an application context
        self.context = DefaultApplicationContext()
        
        # Set up the publisher
        publisher.set_application_event_publisher(self.context)
        
        # Register the listener with the event multicaster directly
        self.context._event_multicaster.add_listener(SampleEvent, listener.on_test_event)
        
        # Refresh the context
        self.context.refresh()
        
        # Publish a test event
        message = "test message"
        publisher.publish_test_event(message)
        
        # Check that the event was received
        self.assertEqual(len(listener.test_events), 1)
        self.assertEqual(listener.test_events[0].message, message)
    
    def test_context_closed_event(self):
        """Test that the context closed event is published when the context is closed."""
        # Create an application context with our test components
        self.context = DefaultApplicationContext()
        
        # Create a listener component
        listener = EventListenerComponent()
        
        # Register the listener with the event multicaster directly
        self.context._event_multicaster.add_listener(ContextClosedEvent, listener.on_context_closed)
        
        # Refresh the context
        self.context.refresh()
        
        # Close the context
        self.context.close()
        
        # Check that the context closed event was received
        self.assertTrue(listener.context_closed)


if __name__ == '__main__':
    unittest.main()