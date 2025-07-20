"""
Aspect-Oriented Programming.

This module provides the AOP framework including proxy factory,
aspect weaving, pointcut definitions, and advice types.
"""

from .advice import (
    AdviceType, AdviceMetadata, AspectMetadata, JoinPoint, ProceedingJoinPoint,
    get_aspect_metadata, register_aspect_metadata, get_all_aspects
)
from .pointcut import (
    PointcutExpression, PointcutMatcher, matches_pointcut, compile_pointcut
)
from .proxy_factory import (
    MethodInterceptor, AdviceChain, ProxyFactory, 
    create_proxy, is_proxy, get_target
)
from .integration import (
    AopBeanPostProcessor, AspectRegistry,
    get_aspect_registry, create_aop_bean_post_processor
)

__all__ = [
    # Advice types and metadata
    'AdviceType', 'AdviceMetadata', 'AspectMetadata', 
    'JoinPoint', 'ProceedingJoinPoint',
    'get_aspect_metadata', 'register_aspect_metadata', 'get_all_aspects',
    
    # Pointcut functionality
    'PointcutExpression', 'PointcutMatcher', 'matches_pointcut', 'compile_pointcut',
    
    # Proxy factory
    'MethodInterceptor', 'AdviceChain', 'ProxyFactory',
    'create_proxy', 'is_proxy', 'get_target',
    
    # Integration
    'AopBeanPostProcessor', 'AspectRegistry',
    'get_aspect_registry', 'create_aop_bean_post_processor',
]