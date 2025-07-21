"""
AOP integration with IoC container.

This module provides integration between the AOP framework and the IoC container,
enabling automatic proxy creation for beans that have applicable aspects.
"""

from typing import Any, Dict, List, Optional, Type
from collections import defaultdict

from .advice import get_all_aspects, AspectMetadata, AdviceMetadata
from .pointcut import matches_pointcut
from .proxy_factory import ProxyFactory


class AopBeanPostProcessor:
    """
    Bean post processor that creates AOP proxies for beans with applicable aspects.
    
    This processor is called after bean creation to determine if the bean should
    be wrapped with a proxy to enable aspect weaving.
    """
    
    def __init__(self):
        self.proxy_factory = ProxyFactory()
        self._aspect_cache: Dict[Type, List[AspectMetadata]] = {}
    
    def post_process_before_initialization(self, bean: Any, bean_name: str) -> Any:
        """
        Apply this processor to the given new bean instance before any bean
        initialization callbacks.
        
        Args:
            bean: The new bean instance
            bean_name: The name of the bean
            
        Returns:
            The bean instance to use (either the original or a wrapped one)
        """
        # No processing needed before initialization
        return bean
    
    def post_process_after_initialization(self, bean: Any, bean_name: str) -> Any:
        """
        Apply this processor to the given new bean instance after any bean
        initialization callbacks.
        
        Args:
            bean: The new bean instance
            bean_name: The name of the bean
            
        Returns:
            The bean instance to use (either the original or a wrapped one)
        """
        if self._should_create_proxy(bean, bean_name):
            return self._create_proxy(bean, bean_name)
        return bean
    
    def _should_create_proxy(self, bean: Any, bean_name: str) -> bool:
        """
        Determine if a bean should be proxied based on applicable aspects.
        
        Args:
            bean: The bean instance
            bean_name: The name of the bean
            
        Returns:
            True if the bean should be proxied, False otherwise
        """
        applicable_advice = self._find_applicable_advice(bean)
        return len(applicable_advice) > 0
    
    def _create_proxy(self, bean: Any, bean_name: str) -> Any:
        """
        Create an AOP proxy for the given bean.
        
        Args:
            bean: The bean instance to proxy
            bean_name: The name of the bean
            
        Returns:
            The proxied bean instance
        """
        return self.proxy_factory.create_proxy(bean)
    
    def _find_applicable_advice(self, bean: Any) -> Dict[str, List[AdviceMetadata]]:
        """
        Find advice that applies to the given bean.
        
        Args:
            bean: The bean instance
            
        Returns:
            Dictionary mapping method names to applicable advice
        """
        applicable_advice = defaultdict(list)
        
        # Get all registered aspects
        aspects = get_all_aspects()
        
        # Sort aspects by order (lower values have higher precedence)
        sorted_aspects = sorted(aspects, key=lambda a: a.order)
        
        for aspect_metadata in sorted_aspects:
            for advice_metadata in aspect_metadata.advice_methods:
                # Check each method of the bean class
                import inspect
                for method_name, method in inspect.getmembers(bean.__class__, predicate=lambda x: inspect.isfunction(x) or inspect.ismethod(x)):
                    if self._advice_applies_to_method(advice_metadata, bean, method):
                        applicable_advice[method_name].append(advice_metadata)
        
        return dict(applicable_advice)
    
    def _advice_applies_to_method(self, advice: AdviceMetadata, target: Any, method) -> bool:
        """
        Check if advice applies to a specific method.
        
        Args:
            advice: The advice metadata
            target: The target bean instance
            method: The method to check
            
        Returns:
            True if the advice applies to the method
        """
        return matches_pointcut(advice.pointcut, target, method)


class AspectRegistry:
    """
    Registry for managing aspect instances and their lifecycle.
    
    This registry ensures that aspect instances are properly created and
    managed by the IoC container.
    """
    
    def __init__(self):
        self._aspect_instances: Dict[Type, Any] = {}
        self._bean_factory = None
    
    def set_bean_factory(self, bean_factory):
        """Set the bean factory for creating aspect instances."""
        self._bean_factory = bean_factory
    
    def get_aspect_instance(self, aspect_class: Type) -> Any:
        """
        Get or create an aspect instance.
        
        Args:
            aspect_class: The aspect class
            
        Returns:
            The aspect instance
        """
        if aspect_class not in self._aspect_instances:
            if self._bean_factory:
                # Try to get aspect from bean factory first
                try:
                    instance = self._bean_factory.get_bean_by_type(aspect_class)
                    self._aspect_instances[aspect_class] = instance
                except:
                    # Fall back to direct instantiation
                    instance = aspect_class()
                    self._aspect_instances[aspect_class] = instance
            else:
                # Direct instantiation
                instance = aspect_class()
                self._aspect_instances[aspect_class] = instance
        
        return self._aspect_instances[aspect_class]
    
    def register_aspect_instance(self, aspect_class: Type, instance: Any):
        """
        Register an aspect instance.
        
        Args:
            aspect_class: The aspect class
            instance: The aspect instance
        """
        self._aspect_instances[aspect_class] = instance


# Global aspect registry
_aspect_registry = AspectRegistry()


def get_aspect_registry() -> AspectRegistry:
    """Get the global aspect registry."""
    return _aspect_registry


def create_aop_bean_post_processor() -> AopBeanPostProcessor:
    """Create a new AOP bean post processor."""
    return AopBeanPostProcessor()