"""
Proxy factory for creating AOP proxies.

This module provides the ProxyFactory class that creates proxies for objects
to enable method interception and aspect weaving.
"""

import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, Type, Union
from collections import defaultdict

from .advice import (
    AdviceType, AdviceMetadata, AspectMetadata, JoinPoint, ProceedingJoinPoint,
    get_all_aspects
)
from .pointcut import matches_pointcut


class MethodInterceptor:
    """Base class for method interceptors."""
    
    def intercept(self, target: Any, method: Callable, args: tuple, kwargs: dict) -> Any:
        """Intercept a method call."""
        raise NotImplementedError("Subclasses must implement intercept method")


class AdviceChain:
    """Represents a chain of advice to be executed for a method."""
    
    def __init__(self, target: Any, method: Callable, advice_list: List[AdviceMetadata]):
        self.target = target
        self.method = method
        self.advice_list = sorted(advice_list, key=lambda a: getattr(a.method, '_spring_order', 0))
        self.current_index = 0
    
    def proceed(self, args: tuple, kwargs: dict) -> Any:
        """Execute the next advice in the chain or the target method."""
        if self.current_index < len(self.advice_list):
            advice = self.advice_list[self.current_index]
            self.current_index += 1
            return self._execute_advice(advice, args, kwargs)
        else:
            # Execute the original method
            return self.method(*args, **kwargs)
    
    def _execute_advice(self, advice: AdviceMetadata, args: tuple, kwargs: dict) -> Any:
        """Execute a specific advice."""
        join_point = JoinPoint(self.target, self.method, args, kwargs)
        
        if advice.advice_type == AdviceType.BEFORE:
            # Execute before advice
            self._call_advice_method(advice, join_point)
            # Continue with the chain
            return self.proceed(args, kwargs)
        
        elif advice.advice_type == AdviceType.AFTER:
            try:
                result = self.proceed(args, kwargs)
                # Execute after advice
                self._call_advice_method(advice, join_point)
                return result
            except Exception as e:
                # Execute after advice even on exception
                self._call_advice_method(advice, join_point)
                raise
        
        elif advice.advice_type == AdviceType.AFTER_RETURNING:
            try:
                result = self.proceed(args, kwargs)
                # Execute after returning advice with result
                self._call_advice_method(advice, join_point, result=result)
                return result
            except Exception:
                # Don't execute after returning advice on exception
                raise
        
        elif advice.advice_type == AdviceType.AFTER_THROWING:
            try:
                return self.proceed(args, kwargs)
            except Exception as e:
                # Execute after throwing advice with exception
                self._call_advice_method(advice, join_point, exception=e)
                raise
        
        elif advice.advice_type == AdviceType.AROUND:
            # Create proceeding join point for around advice
            proceeding_jp = ProceedingJoinPoint(self.target, self.method, args, kwargs)
            
            # Override proceed to continue with the advice chain
            original_proceed = proceeding_jp.proceed
            def chain_proceed(*proc_args, **proc_kwargs):
                if proceeding_jp._proceeded:
                    raise RuntimeError("proceed() can only be called once")
                proceeding_jp._proceeded = True
                
                # Use provided args if given, otherwise use original
                call_args = proc_args if proc_args else args
                call_kwargs = proc_kwargs if proc_kwargs else kwargs
                
                try:
                    # Call the original method directly to avoid infinite recursion
                    result = self.method(*call_args, **call_kwargs)
                    proceeding_jp._result = result
                    return result
                except Exception as e:
                    proceeding_jp._exception = e
                    raise
            
            proceeding_jp.proceed = chain_proceed
            
            # Execute around advice
            return self._call_advice_method(advice, proceeding_jp)
        
        else:
            # Unknown advice type, just proceed
            return self.proceed(args, kwargs)
    
    def _call_advice_method(self, advice: AdviceMetadata, join_point: Union[JoinPoint, ProceedingJoinPoint], 
                           result: Any = None, exception: Exception = None) -> Any:
        """Call the advice method with appropriate parameters."""
        # Get the aspect instance (assuming it's bound to the method)
        if hasattr(advice.method, '__self__'):
            aspect_instance = advice.method.__self__
            method = advice.method
        else:
            # For unbound methods, we need to get the aspect instance
            # This would be handled by the container in a real implementation
            aspect_instance = None
            method = advice.method
        
        # Prepare arguments based on advice method signature
        call_args = []
        call_kwargs = {}
        
        # Add join point as first argument
        if isinstance(join_point, ProceedingJoinPoint):
            call_args.append(join_point)
        else:
            call_args.append(join_point)
        
        # Add result parameter if specified
        if advice.returning_param and result is not None:
            if advice.returning_param in advice.arg_names:
                call_kwargs[advice.returning_param] = result
        
        # Add exception parameter if specified
        if advice.throwing_param and exception is not None:
            if advice.throwing_param in advice.arg_names:
                call_kwargs[advice.throwing_param] = exception
        
        # Call the advice method
        if aspect_instance:
            return method(*call_args, **call_kwargs)
        else:
            # For testing or unbound methods (standalone functions)
            return method(*call_args, **call_kwargs)


class ProxyFactory:
    """Factory for creating AOP proxies."""
    
    def __init__(self):
        self._aspect_cache: Dict[Type, List[AspectMetadata]] = {}
        self._advice_cache: Dict[str, List[AdviceMetadata]] = defaultdict(list)
    
    def create_proxy(self, target: Any, target_class: Optional[Type] = None) -> Any:
        """
        Create a proxy for the given target object.
        
        Args:
            target: The target object to proxy
            target_class: Optional target class (defaults to target.__class__)
        
        Returns:
            Proxied object with method interception
        """
        if target_class is None:
            target_class = target.__class__
        
        # Find applicable aspects
        applicable_advice = self._find_applicable_advice(target, target_class)
        
        if not applicable_advice:
            # No advice applies, return original target
            return target
        
        # Create proxy class
        proxy_class = self._create_proxy_class(target_class, applicable_advice)
        
        # Create proxy instance
        proxy = proxy_class(target, applicable_advice)
        
        return proxy
    
    def _find_applicable_advice(self, target: Any, target_class: Type) -> Dict[str, List[AdviceMetadata]]:
        """Find advice that applies to the target object."""
        applicable_advice = defaultdict(list)
        
        # Get all registered aspects
        aspects = get_all_aspects()
        
        for aspect_metadata in aspects:
            for advice_metadata in aspect_metadata.advice_methods:
                # Check each method of the target class
                for method_name, method in inspect.getmembers(target_class, inspect.isfunction):
                    if self._advice_applies_to_method(advice_metadata, target, method):
                        applicable_advice[method_name].append(advice_metadata)
        
        return dict(applicable_advice)
    
    def _advice_applies_to_method(self, advice: AdviceMetadata, target: Any, method: Callable) -> bool:
        """Check if advice applies to a specific method."""
        return matches_pointcut(advice.pointcut, target, method)
    
    def _create_proxy_class(self, target_class: Type, applicable_advice: Dict[str, List[AdviceMetadata]]) -> Type:
        """Create a proxy class for the target class."""
        
        class AopProxy:
            """Dynamic AOP proxy class."""
            
            def __init__(self, target: Any, advice_map: Dict[str, List[AdviceMetadata]]):
                self._target = target
                self._advice_map = advice_map
                
                # Copy attributes from target
                for attr_name in dir(target):
                    if not attr_name.startswith('_') and not callable(getattr(target, attr_name)):
                        setattr(self, attr_name, getattr(target, attr_name))
            
            def __getattr__(self, name: str) -> Any:
                """Handle method calls with interception."""
                target_attr = getattr(self._target, name)
                
                if callable(target_attr) and name in self._advice_map:
                    # Create intercepted method
                    def intercepted_method(*args, **kwargs):
                        advice_list = self._advice_map[name]
                        chain = AdviceChain(self._target, target_attr, advice_list)
                        return chain.proceed(args, kwargs)
                    
                    return intercepted_method
                else:
                    # Return original attribute
                    return target_attr
            
            def __setattr__(self, name: str, value: Any) -> None:
                """Handle attribute setting."""
                if name.startswith('_'):
                    super().__setattr__(name, value)
                else:
                    setattr(self._target, name, value)
        
        return AopProxy
    
    def is_proxy(self, obj: Any) -> bool:
        """Check if an object is an AOP proxy."""
        return hasattr(obj, '_target') and hasattr(obj, '_advice_map')
    
    def get_target(self, proxy: Any) -> Any:
        """Get the target object from a proxy."""
        if self.is_proxy(proxy):
            return proxy._target
        return proxy


# Global proxy factory instance
_proxy_factory = ProxyFactory()


def create_proxy(target: Any, target_class: Optional[Type] = None) -> Any:
    """Create a proxy for the given target object."""
    return _proxy_factory.create_proxy(target, target_class)


def is_proxy(obj: Any) -> bool:
    """Check if an object is an AOP proxy."""
    return _proxy_factory.is_proxy(obj)


def get_target(proxy: Any) -> Any:
    """Get the target object from a proxy."""
    return _proxy_factory.get_target(proxy)