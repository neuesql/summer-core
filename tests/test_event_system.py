"""
Tests for the event system.
"""

import unittest
from typing import List

from summer_core.event.application_event import ApplicationEvent, ContextRefreshedEvent
from summer_core.event.event_publisher import ApplicationEventMultiPublisher
from summer_core.event.event_listener import EventListener


class SampleEvent(ApplicationEvent):
    """Sample event class for testing."""
    
    def __init__(self, source: object, message: str):
        super().__init__(source)
        self.message = message


class ChildSampleEvent(SampleEvent):
    """Child test event class for testing event hierarchy."""
    pass


class TestApplicationEvent(unittest.TestCase):
    """Test cases for the ApplicationEvent class."""
    
    def test_event_properties(self):
        """Test that event properties are set correctly."""
        source = "test_source"
        event = ApplicationEvent(source)
        
        self.assertEqual(event.source, source)
        self.assertIsNotNone(event.timestamp)
    
    def test_custom_event(self):
        """Test that custom event properties are set correctly."""
        source = "test_source"
        message = "test_message"
        event = SampleEvent(source, message)
        
        self.assertEqual(event.source, source)
        self.assertEqual(event.message, message)
        self.assertIsNotNone(event.timestamp)


class TestEventPublisher(unittest.TestCase):
    """Test cases for the ApplicationEventMultiPublisher class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.publisher = ApplicationEventMultiPublisher()
        self.events_received: List[ApplicationEvent] = []
    
    def event_listener(self, event: ApplicationEvent):
        """Event listener for testing."""
        self.events_received.append(event)
    
    def test_event_publishing(self):
        """Test that events are published to registered listeners."""
        # Register listener
        self.publisher.add_listener(SampleEvent, self.event_listener)
        
        # Publish event
        source = "test_source"
        message = "test_message"
        event = SampleEvent(source, message)
        self.publisher.publish_event(event)
        
        # Check that the event was received
        self.assertEqual(len(self.events_received), 1)
        received_event = self.events_received[0]
        self.assertIs(received_event, event)
        self.assertEqual(received_event.source, source)
        self.assertEqual(received_event.message, message)
    
    def test_event_hierarchy(self):
        """Test that listeners receive events from subclasses."""
        # Register listener for parent class
        self.publisher.add_listener(SampleEvent, self.event_listener)
        
        # Publish child event
        source = "test_source"
        message = "test_message"
        event = ChildSampleEvent(source, message)
        self.publisher.publish_event(event)
        
        # Check that the event was received
        self.assertEqual(len(self.events_received), 1)
        received_event = self.events_received[0]
        self.assertIs(received_event, event)
        self.assertEqual(received_event.source, source)
        self.assertEqual(received_event.message, message)
    
    def test_multiple_listeners(self):
        """Test that multiple listeners receive the same event."""
        # Create a second list for the second listener
        events_received2: List[ApplicationEvent] = []
        
        def event_listener2(event: ApplicationEvent):
            events_received2.append(event)
        
        # Register both listeners
        self.publisher.add_listener(SampleEvent, self.event_listener)
        self.publisher.add_listener(SampleEvent, event_listener2)
        
        # Publish event
        event = SampleEvent("test_source", "test_message")
        self.publisher.publish_event(event)
        
        # Check that both listeners received the event
        self.assertEqual(len(self.events_received), 1)
        self.assertEqual(len(events_received2), 1)
        self.assertIs(self.events_received[0], event)
        self.assertIs(events_received2[0], event)
    
    def test_listener_removal(self):
        """Test that removed listeners don't receive events."""
        # Register listener
        self.publisher.add_listener(SampleEvent, self.event_listener)
        
        # Remove listener
        self.publisher.remove_listener(SampleEvent, self.event_listener)
        
        # Publish event
        event = SampleEvent("test_source", "test_message")
        self.publisher.publish_event(event)
        
        # Check that the event was not received
        self.assertEqual(len(self.events_received), 0)
    
    def test_specific_event_type(self):
        """Test that listeners only receive events of the specified type."""
        # Register listener for ContextRefreshedEvent
        self.publisher.add_listener(ContextRefreshedEvent, self.event_listener)
        
        # Publish SampleEvent
        event = SampleEvent("test_source", "test_message")
        self.publisher.publish_event(event)
        
        # Check that the event was not received
        self.assertEqual(len(self.events_received), 0)
        
        # Publish ContextRefreshedEvent
        event = ContextRefreshedEvent("test_source")
        self.publisher.publish_event(event)
        
        # Check that the event was received
        self.assertEqual(len(self.events_received), 1)
        self.assertIs(self.events_received[0], event)


class TestEventListenerDecorator(unittest.TestCase):
    """Test cases for the EventListener decorator."""
    
    def test_explicit_event_type(self):
        """Test that the event type can be specified explicitly."""
        @EventListener(SampleEvent)
        def listener(event):
            pass
        
        self.assertTrue(hasattr(listener, '__is_event_listener__'))
        self.assertTrue(listener.__is_event_listener__)
        self.assertTrue(hasattr(listener, '__event_type__'))
        self.assertEqual(listener.__event_type__, SampleEvent)
    
    def test_inferred_event_type(self):
        """Test that the event type can be inferred from type hints."""
        @EventListener()
        def listener(event: SampleEvent):
            pass
        
        self.assertTrue(hasattr(listener, '__is_event_listener__'))
        self.assertTrue(listener.__is_event_listener__)
        self.assertTrue(hasattr(listener, '__event_type__'))
        self.assertEqual(listener.__event_type__, SampleEvent)
    
    def test_method_event_type(self):
        """Test that the event type can be inferred from method type hints."""
        class Listener:
            @EventListener()
            def on_event(self, event: SampleEvent):
                pass
        
        method = Listener.on_event
        self.assertTrue(hasattr(method, '__is_event_listener__'))
        self.assertTrue(method.__is_event_listener__)
        self.assertTrue(hasattr(method, '__event_type__'))
        self.assertEqual(method.__event_type__, SampleEvent)
    
    def test_missing_type_hint(self):
        """Test that an error is raised when the event type cannot be inferred."""
        with self.assertRaises(ValueError):
            @EventListener()
            def listener(event):
                pass
    
    def test_invalid_event_type(self):
        """Test that an error is raised when the event type is not an ApplicationEvent."""
        with self.assertRaises(ValueError):
            @EventListener()
            def listener(event: str):
                pass


if __name__ == '__main__':
    unittest.main()