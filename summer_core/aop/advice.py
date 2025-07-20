"""
Advice types and metadata for AOP framework.

This module defines the different types of advice (before, after, around, etc.)
and their associated metadata structures.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum
import functools
import inspect


class AdviceType(Enum):
    """Types of advice that can be applied to join points."""
    BEFORE = "before"
    AFTER = "after"
    AFTER_RETURNING = "after_returning"
    AFTER_THROWING = "after_throwing"
    AROUND = "around"


@dataclass
class AdviceMetadata:
    """Metadata for advice methods."""
    advice_type: AdviceType
    pointcut: str
    method: Callable
    order: int = 0
    returning_param: Optional[str] = None
    throwing_param: Optional[str] = None
    arg_names: List[str] = field(default_factory=list)


@dataclass
class AspectMetadata:
    """Metadata for aspect classes."""
    aspect_class: type
    order: int = 0
    advice_methods: List[AdviceMetadata] = field(default_factory=list)
    pointcuts: Dict[str, str] = field(default_factory=dict)


class JoinPoint:
    """Represents a join point in the execution of a program."""
    
    def __init__(self, target: Any, method: Callable, args: tuple, kwargs: dict):
        self.target = target
        self.method = method
        self.args = args
        self.kwargs = kwargs
        self.method_name = method.__name__
        self.target_class = target.__class__
    
    def get_target(self) -> Any:
        """Get the target object."""
        return self.target
    
    def get_method(self) -> Callable:
        """Get the method being called."""
        return self.method
    
    def get_args(self) -> tuple:
        """Get the method arguments."""
        return self.args
    
    def get_kwargs(self) -> dict:
        """Get the method keyword arguments."""
        return self.kwargs
    
    def get_signature(self) -> str:
        """Get a string representation of the method signature."""
        return f"{self.target_class.__name__}.{self.method_name}"


class ProceedingJoinPoint(JoinPoint):
    """Join point for around advice that allows proceeding with the original method call."""
    
    def __init__(self, target: Any, method: Callable, args: tuple, kwargs: dict):
        super().__init__(target, method, args, kwargs)
        self._proceeded = False
        self._result = None
        self._exception = None
    
    def proceed(self, *args, **kwargs) -> Any:
        """Proceed with the original method call."""
        if self._proceeded:
            raise RuntimeError("proceed() can only be called once")
        
        self._proceeded = True
        try:
            # Use provided args/kwargs if given, otherwise use original
            call_args = args if args else self.args
            call_kwargs = kwargs if kwargs else self.kwargs
            
            self._result = self.method(self.target, *call_args, **call_kwargs)
            return self._result
        except Exception as e:
            self._exception = e
            raise
    
    def has_proceeded(self) -> bool:
        """Check if proceed() has been called."""
        return self._proceeded
    
    def get_result(self) -> Any:
        """Get the result of the proceeded method call."""
        return self._result
    
    def get_exception(self) -> Optional[Exception]:
        """Get any exception thrown by the proceeded method call."""
        return self._exception


# Global registry for aspect metadata
_aspect_registry: Dict[type, AspectMetadata] = {}


def get_aspect_metadata(aspect_class: type) -> Optional[AspectMetadata]:
    """Get aspect metadata for a class."""
    return _aspect_registry.get(aspect_class)


def register_aspect_metadata(aspect_class: type, metadata: AspectMetadata):
    """Register aspect metadata for a class."""
    _aspect_registry[aspect_class] = metadata


def get_all_aspects() -> List[AspectMetadata]:
    """Get all registered aspect metadata."""
    return list(_aspect_registry.values())