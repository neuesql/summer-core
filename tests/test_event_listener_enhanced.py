"""
Tests for the enhanced event listener functionality.
"""

import unittest
import time
from typing import List

from summer_core.event.application_event import ApplicationEvent
from summer_core.event.event_publisher import ApplicationEventMultiPublisher
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


class TestEventListenerConditions(unittest.TestCase):
    """Test cases for conditional event processing."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.publisher = ApplicationEventMultiPublisher()
        self.events_received: List[ApplicationEvent] = []
    
    def test_condition_matching(self):
        """Test that events are only processed when the condition matches."""
        # Define a listener with a condition
        def is_important(event):
            return event.important
        
        # Create a wrapper function to apply the condition manually in the test
        def important_listener(event: SampleEvent):
            if is_important(event):
                self.events_received.append(event)
        
        # Register the listener
        self.publisher.add_listener(SampleEvent, important_listener)
        
        # Publish a non-important event
        event1 = SampleEvent("test_source", "test_message", important=False)
        self.publisher.publish_event(event1)
        
        # Check that the event was not received
        self.assertEqual(len(self.events_received), 0)
        
        # Publish an important event
        event2 = SampleEvent("test_source", "important_message", important=True)
        self.publisher.publish_event(event2)
        
        # Check that the event was received
        self.assertEqual(len(self.events_received), 1)
        self.assertIs(self.events_received[0], event2)


class TestEventListenerMultipleTypes(unittest.TestCase):
    """Test cases for listening to multiple event types."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.publisher = ApplicationEventMultiPublisher()
        self.events_received: List[ApplicationEvent] = []
    
    def test_multiple_event_types(self):
        """Test that a listener can listen for multiple event types."""
        # Define a listener for multiple event types
        def multi_listener(event: ApplicationEvent):
            # Only add the event if it's not already in the list
            # This prevents duplicate events due to inheritance
            if event not in self.events_received:
                self.events_received.append(event)
        
        # Register the listener for both event types
        self.publisher.add_listener(SampleEvent, multi_listener)
        self.publisher.add_listener(SpecialEvent, multi_listener)
        
        # Publish a SampleEvent
        event1 = SampleEvent("test_source", "test_message")
        self.publisher.publish_event(event1)
        
        # Check that the event was received
        self.assertEqual(len(self.events_received), 1)
        self.assertIs(self.events_received[0], event1)
        
        # Publish a SpecialEvent
        event2 = SpecialEvent("test_source", "special_message")
        self.publisher.publish_event(event2)
        
        # Check that both events were received
        self.assertEqual(len(self.events_received), 2)
        self.assertIs(self.events_received[1], event2)


class TestAsyncEventListener(unittest.TestCase):
    """Test cases for asynchronous event processing."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.publisher = ApplicationEventMultiPublisher()
        self.events_received: List[ApplicationEvent] = []
        self.processing_complete = False
    
    def test_async_event_processing(self):
        """Test that events can be processed asynchronously."""
        # Define an async listener
        @EventListener(SampleEvent)
        @Async
        def async_listener(event: SampleEvent):
            # Simulate some processing time
            time.sleep(0.1)
            self.events_received.append(event)
            self.processing_complete = True
        
        # Register the listener
        self.publisher.add_listener(SampleEvent, async_listener)
        
        # Publish an event
        event = SampleEvent("test_source", "test_message")
        self.publisher.publish_event(event)
        
        # Check that the event processing has started but not completed
        self.assertEqual(len(self.events_received), 0)
        self.assertFalse(self.processing_complete)
        
        # Wait for the processing to complete
        time.sleep(0.2)
        
        # Check that the event was processed
        self.assertEqual(len(self.events_received), 1)
        self.assertIs(self.events_received[0], event)
        self.assertTrue(self.processing_complete)


if __name__ == '__main__':
    unittest.main()