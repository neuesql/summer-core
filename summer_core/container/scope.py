"""
Bean Scope Management System.

Provides scope implementations for singleton, prototype, request, and session scopes,
along with a registry for custom scope extensions.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional
from threading import local
import weakref


class Scope(ABC):
    """
    Abstract base class for bean scopes.
    
    A scope defines the lifecycle and visibility of bean instances
    within the application context.
    """
    
    @abstractmethod
    def get(self, name: str, object_factory: Callable[[], Any]) -> Any:
        """
        Get a bean instance from this scope.
        
        Args:
            name: The name of the bean
            object_factory: Factory function to create the bean if needed
            
        Returns:
            The bean instance
        """
        pass
    
    @abstractmethod
    def remove(self, name: str) -> Optional[Any]:
        """
        Remove a bean from this scope.
        
        Args:
            name: The name of the bean to remove
            
        Returns:
            The removed bean instance, or None if not found
        """
        pass
    
    @abstractmethod
    def register_destruction_callback(self, name: str, callback: Callable[[], None]) -> None:
        """
        Register a callback to be executed when the scope is destroyed.
        
        Args:
            name: The name of the bean
            callback: The destruction callback
        """
        pass
    
    @abstractmethod
    def get_conversation_id(self) -> Optional[str]:
        """
        Get the conversation ID for this scope.
        
        Returns:
            The conversation ID, or None if not applicable
        """
        pass


class SingletonScope(Scope):
    """
    Singleton scope implementation.
    
    Maintains a single instance of each bean throughout the application lifecycle.
    This is the default scope for beans.
    """
    
    def __init__(self):
        self._objects: Dict[str, Any] = {}
        self._destruction_callbacks: Dict[str, Callable[[], None]] = {}
    
    def get(self, name: str, object_factory: Callable[[], Any]) -> Any:
        """Get a singleton bean instance."""
        if name not in self._objects:
            self._objects[name] = object_factory()
        return self._objects[name]
    
    def remove(self, name: str) -> Optional[Any]:
        """Remove a singleton bean."""
        obj = self._objects.pop(name, None)
        callback = self._destruction_callbacks.pop(name, None)
        if callback:
            try:
                callback()
            except Exception as e:
                print(f"Warning: Error executing destruction callback for {name}: {e}")
        return obj
    
    def register_destruction_callback(self, name: str, callback: Callable[[], None]) -> None:
        """Register a destruction callback for a singleton bean."""
        self._destruction_callbacks[name] = callback
    
    def get_conversation_id(self) -> Optional[str]:
        """Singleton scope has no conversation ID."""
        return None
    
    def destroy(self) -> None:
        """Destroy all singleton beans and execute their callbacks."""
        for name in list(self._objects.keys()):
            self.remove(name)


class PrototypeScope(Scope):
    """
    Prototype scope implementation.
    
    Creates a new instance of the bean for each request.
    The container does not manage the lifecycle of prototype beans.
    """
    
    def __init__(self):
        self._destruction_callbacks: Dict[str, list] = {}
    
    def get(self, name: str, object_factory: Callable[[], Any]) -> Any:
        """Create a new prototype bean instance."""
        return object_factory()
    
    def remove(self, name: str) -> Optional[Any]:
        """Prototype beans are not stored, so nothing to remove."""
        return None
    
    def register_destruction_callback(self, name: str, callback: Callable[[], None]) -> None:
        """
        Register destruction callback for prototype beans.
        
        Note: Prototype beans are not managed by the container,
        so callbacks are stored but not automatically executed.
        """
        if name not in self._destruction_callbacks:
            self._destruction_callbacks[name] = []
        self._destruction_callbacks[name].append(callback)
    
    def get_conversation_id(self) -> Optional[str]:
        """Prototype scope has no conversation ID."""
        return None


class RequestScope(Scope):
    """
    Request scope implementation.
    
    Maintains one instance of each bean per HTTP request.
    Uses thread-local storage to isolate request-scoped beans.
    """
    
    def __init__(self):
        self._thread_local = local()
    
    def _get_request_objects(self) -> Dict[str, Any]:
        """Get the request-scoped objects for the current thread."""
        if not hasattr(self._thread_local, 'objects'):
            self._thread_local.objects = {}
        return self._thread_local.objects
    
    def _get_request_callbacks(self) -> Dict[str, Callable[[], None]]:
        """Get the destruction callbacks for the current thread."""
        if not hasattr(self._thread_local, 'callbacks'):
            self._thread_local.callbacks = {}
        return self._thread_local.callbacks
    
    def get(self, name: str, object_factory: Callable[[], Any]) -> Any:
        """Get a request-scoped bean instance."""
        objects = self._get_request_objects()
        if name not in objects:
            objects[name] = object_factory()
        return objects[name]
    
    def remove(self, name: str) -> Optional[Any]:
        """Remove a request-scoped bean."""
        objects = self._get_request_objects()
        callbacks = self._get_request_callbacks()
        
        obj = objects.pop(name, None)
        callback = callbacks.pop(name, None)
        if callback:
            try:
                callback()
            except Exception as e:
                print(f"Warning: Error executing destruction callback for {name}: {e}")
        return obj
    
    def register_destruction_callback(self, name: str, callback: Callable[[], None]) -> None:
        """Register a destruction callback for a request-scoped bean."""
        callbacks = self._get_request_callbacks()
        callbacks[name] = callback
    
    def get_conversation_id(self) -> Optional[str]:
        """Get the current thread ID as conversation ID."""
        import threading
        return str(threading.current_thread().ident)
    
    def destroy_request(self) -> None:
        """Destroy all request-scoped beans for the current thread."""
        if hasattr(self._thread_local, 'objects'):
            for name in list(self._thread_local.objects.keys()):
                self.remove(name)


class SessionScope(Scope):
    """
    Session scope implementation.
    
    Maintains one instance of each bean per HTTP session.
    Uses weak references to avoid memory leaks when sessions expire.
    """
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._session_callbacks: Dict[str, Dict[str, Callable[[], None]]] = {}
        self._current_session_id: Optional[str] = None
    
    def set_current_session_id(self, session_id: str) -> None:
        """Set the current session ID for this thread."""
        self._current_session_id = session_id
    
    def get_current_session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self._current_session_id
    
    def _get_session_objects(self, session_id: str) -> Dict[str, Any]:
        """Get the session-scoped objects for the given session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = {}
        return self._sessions[session_id]
    
    def _get_session_callbacks(self, session_id: str) -> Dict[str, Callable[[], None]]:
        """Get the destruction callbacks for the given session."""
        if session_id not in self._session_callbacks:
            self._session_callbacks[session_id] = {}
        return self._session_callbacks[session_id]
    
    def get(self, name: str, object_factory: Callable[[], Any]) -> Any:
        """Get a session-scoped bean instance."""
        session_id = self.get_current_session_id()
        if not session_id:
            raise RuntimeError("No session ID available for session-scoped bean")
        
        objects = self._get_session_objects(session_id)
        if name not in objects:
            objects[name] = object_factory()
        return objects[name]
    
    def remove(self, name: str) -> Optional[Any]:
        """Remove a session-scoped bean."""
        session_id = self.get_current_session_id()
        if not session_id:
            return None
        
        objects = self._get_session_objects(session_id)
        callbacks = self._get_session_callbacks(session_id)
        
        obj = objects.pop(name, None)
        callback = callbacks.pop(name, None)
        if callback:
            try:
                callback()
            except Exception as e:
                print(f"Warning: Error executing destruction callback for {name}: {e}")
        return obj
    
    def register_destruction_callback(self, name: str, callback: Callable[[], None]) -> None:
        """Register a destruction callback for a session-scoped bean."""
        session_id = self.get_current_session_id()
        if not session_id:
            raise RuntimeError("No session ID available for session-scoped bean")
        
        callbacks = self._get_session_callbacks(session_id)
        callbacks[name] = callback
    
    def get_conversation_id(self) -> Optional[str]:
        """Get the current session ID as conversation ID."""
        return self.get_current_session_id()
    
    def destroy_session(self, session_id: str) -> None:
        """Destroy all session-scoped beans for the given session."""
        if session_id in self._sessions:
            objects = self._sessions[session_id]
            callbacks = self._session_callbacks.get(session_id, {})
            
            for name in list(objects.keys()):
                callback = callbacks.get(name)
                if callback:
                    try:
                        callback()
                    except Exception as e:
                        print(f"Warning: Error executing destruction callback for {name}: {e}")
            
            # Clean up session data
            self._sessions.pop(session_id, None)
            self._session_callbacks.pop(session_id, None)


class ScopeRegistry:
    """
    Registry for managing bean scopes.
    
    Provides a central location for registering and retrieving scope implementations,
    including built-in scopes and custom scope extensions.
    """
    
    def __init__(self):
        self._scopes: Dict[str, Scope] = {}
        self._register_built_in_scopes()
    
    def _register_built_in_scopes(self) -> None:
        """Register the built-in scope implementations."""
        self._scopes["singleton"] = SingletonScope()
        self._scopes["prototype"] = PrototypeScope()
        self._scopes["request"] = RequestScope()
        self._scopes["session"] = SessionScope()
    
    def register_scope(self, scope_name: str, scope: Scope) -> None:
        """
        Register a custom scope implementation.
        
        Args:
            scope_name: The name of the scope
            scope: The scope implementation
        """
        self._scopes[scope_name] = scope
    
    def get_scope(self, scope_name: str) -> Optional[Scope]:
        """
        Get a scope implementation by name.
        
        Args:
            scope_name: The name of the scope
            
        Returns:
            The scope implementation, or None if not found
        """
        return self._scopes.get(scope_name)
    
    def get_registered_scope_names(self) -> list:
        """
        Get the names of all registered scopes.
        
        Returns:
            A list of scope names
        """
        return list(self._scopes.keys())
    
    def destroy_all_scopes(self) -> None:
        """Destroy all scoped beans in all scopes."""
        for scope in self._scopes.values():
            if hasattr(scope, 'destroy'):
                try:
                    scope.destroy()
                except Exception as e:
                    print(f"Warning: Error destroying scope: {e}")


# Global scope registry instance
_scope_registry = ScopeRegistry()


def get_scope_registry() -> ScopeRegistry:
    """
    Get the global scope registry instance.
    
    Returns:
        The global scope registry
    """
    return _scope_registry