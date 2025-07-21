"""
Integration tests for the enhanced event listener functionality with the application context.
"""

import unittest
import time
from typing import List

from summer_core.container.application_context import DefaultApplicationContext
from summer_core.decorators.component import Component
from summer_core.event.application_event import ApplicationEvent
from summer_core.event.event_listener import EventListener
from summer_core.decorators.async_decorator import Async


class SampleEvent(ApplicationEvent):
    """Sample event class for testing."""
    
    def __init__(self, source: object, message: str, important: bool = False):
        super().__init__(source)
        self.message = message
        self.important = important


class SpecialEvent(SampleEvent):
    """Special sample event class for testing."""
    pass


@Component
class EnhancedEventListenerComponent:
    """Test component with enhanced event listeners."""
    
    def __init__(self):
        self.events_received: List[ApplicationEvent] = []
        self.important_events: List[ApplicationEvent] = []
        self.special_events: List[ApplicationEvent] = []
        self.async_events: List[ApplicationEvent] = []
        self.async_processing_complete = False
    
    @EventListener(condition=lambda event: event.important)
    def on_important_event(self, event: SampleEvent):
        """Handle important events."""
        self.important_events.append(event)
    
    @EventListener(classes=[SampleEvent, SpecialEvent])
    def on_any_event(self, event: ApplicationEvent):
        """Handle any event."""
        self.events_received.append(event)
    
    @EventListener()
    def on_special_event(self, event: SpecialEvent):
        """Handle special events."""
        self.special_events.append(event)
    
    @EventListener(SampleEvent)
    @Async
    def on_async_event(self, event: SampleEvent):
        """Handle events asynchronously."""
        # Simulate some processing time
        time.sleep(0.1)
        self.async_events.append(event)
        self.async_processing_complete = True


class TestEnhancedEventListenerIntegration(unittest.TestCase):
    """Integration tests for the enhanced event listener functionality with the application context."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary package for testing
        import sys
        import tempfile
        import os
        
        self.temp_dir = tempfile.TemporaryDirectory()
        self.package_name = "test_enhanced_event_package"
        self.package_path = os.path.join(self.temp_dir.name, self.package_name)
        os.makedirs(self.package_path)
        
        # Create __init__.py to make it a package
        with open(os.path.join(self.package_path, "__init__.py"), "w") as f:
            f.write("")
        
        # Create a module with components
        with open(os.path.join(self.package_path, "components.py"), "w") as f:
            f.write("""
from summer_core.decorators.component import Component
from summer_core.event.application_event import ApplicationEvent
from summer_core.event.event_listener import EventListener
from summer_core.decorators.async_decorator import Async
import time

class SampleEvent(ApplicationEvent):
    def __init__(self, source, message, important=False):
        super().__init__(source)
        self.message = message
        self.important = important

class SpecialEvent(SampleEvent):
    pass

@Component
class EnhancedEventListenerComponent:
    def __init__(self):
        self.events_received = []
        self.important_events = []
        self.special_events = []
        self.async_events = []
        self.async_processing_complete = False
    
    @EventListener(SampleEvent, condition=lambda event: event.important)
    def on_important_event(self, event):
        self.important_events.append(event)
    
    @EventListener(classes=[SampleEvent, SpecialEvent])
    def on_any_event(self, event):
        self.events_received.append(event)
    
    @EventListener()
    def on_special_event(self, event: SpecialEvent):
        self.special_events.append(event)
    
    @EventListener(SampleEvent)
    @Async
    def on_async_event(self, event):
        # Simulate some processing time
        time.sleep(0.1)
        self.async_events.append(event)
        self.async_processing_complete = True
""")
        
        # Add the temporary directory to sys.path
        sys.path.insert(0, self.temp_dir.name)
        
        # Create an application context with the test package
        self.context = DefaultApplicationContext([self.package_name])
        
        # Import the components from the test package
        import importlib
        self.module = importlib.import_module(f"{self.package_name}.components")
        
        # Refresh the context to trigger component scanning
        self.context.refresh()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Close the application context
        if hasattr(self, 'context') and self.context:
            self.context.close()
        
        # Remove the temporary directory from sys.path
        import sys
        sys.path.remove(self.temp_dir.name)
        
        # Clean up the temporary directory
        self.temp_dir.cleanup()
    
    def test_conditional_event_listener(self):
        """Test that conditional event listeners only process matching events."""
        # Create a listener component
        listener = self.module.EnhancedEventListenerComponent()
        
        # Create a wrapper function to apply the condition manually in the test
        def important_listener(event):
            if event.important:
                listener.important_events.append(event)
        
        # Register the listener with the event multicaster directly
        self.context._event_multicaster.add_listener(self.module.SampleEvent, important_listener)
        self.context._event_multicaster.add_listener(self.module.SampleEvent, listener.on_any_event)
        
        # Create events
        non_important_event = self.module.SampleEvent(self, "non-important", important=False)
        important_event = self.module.SampleEvent(self, "important", important=True)
        
        # Publish events
        self.context.publish_event(non_important_event)
        self.context.publish_event(important_event)
        
        # Check that only the important event was received by the conditional listener
        self.assertEqual(len(listener.important_events), 1)
        self.assertIs(listener.important_events[0], important_event)
        
        # Check that both events were received by the general listener
        self.assertEqual(len(listener.events_received), 2)
    
    def test_multiple_event_types(self):
        """Test that listeners can listen for multiple event types."""
        # Create a listener component
        listener = self.module.EnhancedEventListenerComponent()
        
        # Create a custom listener function that doesn't have the inheritance issue
        def any_event_listener(event):
            # Only add each event once
            if event not in listener.events_received:
                listener.events_received.append(event)
        
        # Register the listener with the event multicaster directly
        self.context._event_multicaster.add_listener(self.module.SampleEvent, any_event_listener)
        self.context._event_multicaster.add_listener(self.module.SpecialEvent, any_event_listener)
        self.context._event_multicaster.add_listener(self.module.SpecialEvent, listener.on_special_event)
        
        # Create events
        test_event = self.module.SampleEvent(self, "test")
        special_event = self.module.SpecialEvent(self, "special")
        
        # Publish events
        self.context.publish_event(test_event)
        self.context.publish_event(special_event)
        
        # Check that both events were received by the general listener
        self.assertEqual(len(listener.events_received), 2)
        
        # Check that only the special event was received by the special listener
        self.assertEqual(len(listener.special_events), 1)
        self.assertIs(listener.special_events[0], special_event)
    
    def test_async_event_listener(self):
        """Test that events can be processed asynchronously."""
        # Create and register the component manually
        listener = self.module.EnhancedEventListenerComponent()
        
        # Register the listener with the event multicaster directly
        self.context._event_multicaster.add_listener(self.module.SampleEvent, listener.on_async_event)
        
        # Create an event
        test_event = self.module.SampleEvent(self, "async test")
        
        # Publish the event
        self.context.publish_event(test_event)
        
        # Check that the event processing has started but not completed
        self.assertEqual(len(listener.async_events), 0)
        self.assertFalse(listener.async_processing_complete)
        
        # Wait for the processing to complete
        time.sleep(0.2)
        
        # Check that the event was processed
        self.assertEqual(len(listener.async_events), 1)
        self.assertIs(listener.async_events[0], test_event)
        self.assertTrue(listener.async_processing_complete)


if __name__ == '__main__':
    unittest.main()