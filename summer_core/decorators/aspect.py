"""
AOP decorators for aspect-oriented programming.

This module provides decorators for defining aspects, pointcuts, and advice
in the Summer Core framework.
"""

from typing import Any, Callable, Optional, Union
import functools
import inspect

from ..aop.advice import (
    AdviceType, AdviceMetadata, AspectMetadata, 
    register_aspect_metadata, get_aspect_metadata
)


def aspect(cls: Optional[type] = None, *, order: int = 0) -> Union[type, Callable[[type], type]]:
    """
    Mark a class as an aspect.
    
    Args:
        cls: The class to mark as an aspect
        order: The order of this aspect (lower values have higher precedence)
    
    Returns:
        The decorated class or decorator function
    """
    def decorator(aspect_class: type) -> type:
        # Create aspect metadata
        metadata = AspectMetadata(
            aspect_class=aspect_class,
            order=order
        )
        
        # Register the aspect
        register_aspect_metadata(aspect_class, metadata)
        
        # Mark the class as an aspect
        aspect_class._spring_aspect = True
        aspect_class._spring_aspect_order = order
        
        return aspect_class
    
    if cls is None:
        return decorator
    return decorator(cls)


def pointcut(expression: str) -> Callable[[Callable], Callable]:
    """
    Define a pointcut expression.
    
    Args:
        expression: The pointcut expression string
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        func._spring_pointcut = expression
        func._spring_pointcut_name = func.__name__
        
        # Add pointcut to aspect metadata if the class is an aspect
        if hasattr(func, '__self__'):
            aspect_class = func.__self__.__class__
        else:
            # This will be set when the class is instantiated
            func._spring_is_pointcut = True
        
        return func
    
    return decorator


def before(pointcut_expr: str) -> Callable[[Callable], Callable]:
    """
    Define before advice.
    
    Args:
        pointcut_expr: The pointcut expression or pointcut method name
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        # Create advice metadata
        advice_metadata = AdviceMetadata(
            advice_type=AdviceType.BEFORE,
            pointcut=pointcut_expr,
            method=func,
            arg_names=list(inspect.signature(func).parameters.keys())
        )
        
        # Store metadata on the function
        func._spring_advice = advice_metadata
        func._spring_advice_type = AdviceType.BEFORE
        func._spring_pointcut_expr = pointcut_expr
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Copy metadata to wrapper
        wrapper._spring_advice = advice_metadata
        wrapper._spring_advice_type = AdviceType.BEFORE
        wrapper._spring_pointcut_expr = pointcut_expr
        
        return wrapper
    
    return decorator


def after(pointcut_expr: str) -> Callable[[Callable], Callable]:
    """
    Define after advice (runs after method completion, regardless of outcome).
    
    Args:
        pointcut_expr: The pointcut expression or pointcut method name
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        advice_metadata = AdviceMetadata(
            advice_type=AdviceType.AFTER,
            pointcut=pointcut_expr,
            method=func,
            arg_names=list(inspect.signature(func).parameters.keys())
        )
        
        func._spring_advice = advice_metadata
        func._spring_advice_type = AdviceType.AFTER
        func._spring_pointcut_expr = pointcut_expr
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        wrapper._spring_advice = advice_metadata
        wrapper._spring_advice_type = AdviceType.AFTER
        wrapper._spring_pointcut_expr = pointcut_expr
        
        return wrapper
    
    return decorator


def after_returning(pointcut_expr: str, returning: Optional[str] = None) -> Callable[[Callable], Callable]:
    """
    Define after returning advice (runs after successful method completion).
    
    Args:
        pointcut_expr: The pointcut expression or pointcut method name
        returning: Name of parameter to bind the return value to
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        advice_metadata = AdviceMetadata(
            advice_type=AdviceType.AFTER_RETURNING,
            pointcut=pointcut_expr,
            method=func,
            returning_param=returning,
            arg_names=list(inspect.signature(func).parameters.keys())
        )
        
        func._spring_advice = advice_metadata
        func._spring_advice_type = AdviceType.AFTER_RETURNING
        func._spring_pointcut_expr = pointcut_expr
        func._spring_returning_param = returning
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        wrapper._spring_advice = advice_metadata
        wrapper._spring_advice_type = AdviceType.AFTER_RETURNING
        wrapper._spring_pointcut_expr = pointcut_expr
        wrapper._spring_returning_param = returning
        
        return wrapper
    
    return decorator


def after_throwing(pointcut_expr: str, throwing: Optional[str] = None) -> Callable[[Callable], Callable]:
    """
    Define after throwing advice (runs after method throws an exception).
    
    Args:
        pointcut_expr: The pointcut expression or pointcut method name
        throwing: Name of parameter to bind the exception to
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        advice_metadata = AdviceMetadata(
            advice_type=AdviceType.AFTER_THROWING,
            pointcut=pointcut_expr,
            method=func,
            throwing_param=throwing,
            arg_names=list(inspect.signature(func).parameters.keys())
        )
        
        func._spring_advice = advice_metadata
        func._spring_advice_type = AdviceType.AFTER_THROWING
        func._spring_pointcut_expr = pointcut_expr
        func._spring_throwing_param = throwing
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        wrapper._spring_advice = advice_metadata
        wrapper._spring_advice_type = AdviceType.AFTER_THROWING
        wrapper._spring_pointcut_expr = pointcut_expr
        wrapper._spring_throwing_param = throwing
        
        return wrapper
    
    return decorator


def around(pointcut_expr: str) -> Callable[[Callable], Callable]:
    """
    Define around advice (wraps method execution).
    
    Args:
        pointcut_expr: The pointcut expression or pointcut method name
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        advice_metadata = AdviceMetadata(
            advice_type=AdviceType.AROUND,
            pointcut=pointcut_expr,
            method=func,
            arg_names=list(inspect.signature(func).parameters.keys())
        )
        
        func._spring_advice = advice_metadata
        func._spring_advice_type = AdviceType.AROUND
        func._spring_pointcut_expr = pointcut_expr
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        wrapper._spring_advice = advice_metadata
        wrapper._spring_advice_type = AdviceType.AROUND
        wrapper._spring_pointcut_expr = pointcut_expr
        
        return wrapper
    
    return decorator


def _collect_aspect_metadata(aspect_class: type):
    """Collect advice methods from an aspect class and update metadata."""
    metadata = get_aspect_metadata(aspect_class)
    if not metadata:
        return
    
    # Collect pointcuts
    for name, method in inspect.getmembers(aspect_class, inspect.isfunction):
        if hasattr(method, '_spring_pointcut'):
            metadata.pointcuts[name] = method._spring_pointcut
    
    # Collect advice methods
    for name, method in inspect.getmembers(aspect_class, inspect.isfunction):
        if hasattr(method, '_spring_advice'):
            advice_metadata = method._spring_advice
            # Resolve pointcut references
            if advice_metadata.pointcut in metadata.pointcuts:
                advice_metadata.pointcut = metadata.pointcuts[advice_metadata.pointcut]
            metadata.advice_methods.append(advice_metadata)


# Hook into class creation to collect metadata
def __init_subclass_hook__(cls):
    """Hook called when an aspect class is created."""
    if hasattr(cls, '_spring_aspect'):
        _collect_aspect_metadata(cls)