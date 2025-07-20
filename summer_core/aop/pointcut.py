"""
Pointcut expressions and matching for AOP framework.

This module provides basic pointcut expression parsing and matching
functionality for determining which methods should be advised.
"""

import re
from typing import Any, Callable, List, Optional, Pattern
from dataclasses import dataclass


@dataclass
class PointcutExpression:
    """Represents a parsed pointcut expression."""
    expression: str
    method_pattern: Optional[Pattern] = None
    class_pattern: Optional[Pattern] = None
    annotation_pattern: Optional[str] = None


class PointcutMatcher:
    """Matches pointcut expressions against methods and classes."""
    
    def __init__(self):
        self._compiled_expressions: dict[str, PointcutExpression] = {}
    
    def compile_expression(self, expression: str) -> PointcutExpression:
        """Compile a pointcut expression for efficient matching."""
        if expression in self._compiled_expressions:
            return self._compiled_expressions[expression]
        
        pointcut = PointcutExpression(expression=expression)
        
        # Basic pointcut expression parsing
        # Format: execution(* package.Class.method(..))
        # Format: @annotation(AnnotationName)
        # Format: within(package.Class)
        
        if expression.startswith('@'):
            # Annotation-based pointcut
            pointcut.annotation_pattern = expression[1:]
        elif expression.startswith('execution('):
            # Method execution pointcut
            match_expr = expression[10:-1]  # Remove 'execution(' and ')'
            pointcut.method_pattern = self._parse_execution_expression(match_expr)
        elif expression.startswith('within('):
            # Class-based pointcut
            class_expr = expression[7:-1]  # Remove 'within(' and ')'
            pointcut.class_pattern = self._parse_class_expression(class_expr)
        else:
            # Simple method name pattern
            pointcut.method_pattern = re.compile(expression.replace('*', '.*'))
        
        self._compiled_expressions[expression] = pointcut
        return pointcut
    
    def _parse_execution_expression(self, expression: str) -> Pattern:
        """Parse execution pointcut expression."""
        # Simple parsing: * package.Class.method(..)
        # Convert to regex pattern, being careful with multiple wildcards
        pattern = expression.replace('..', '__DOUBLE_DOT__')  # Temporarily replace ..
        pattern = pattern.replace('*', '[^.]*')  # * matches anything except dots
        pattern = pattern.replace('__DOUBLE_DOT__', '.*')  # .. matches anything including dots
        return re.compile(pattern)
    
    def _parse_class_expression(self, expression: str) -> Pattern:
        """Parse class pointcut expression."""
        pattern = expression.replace('*', '.*')
        return re.compile(pattern)
    
    def matches(self, pointcut_expr: str, target: Any, method: Callable) -> bool:
        """Check if a method matches the pointcut expression."""
        pointcut = self.compile_expression(pointcut_expr)
        
        # Check annotation-based matching
        if pointcut.annotation_pattern:
            return self._matches_annotation(pointcut.annotation_pattern, target, method)
        
        # Check method pattern matching
        if pointcut.method_pattern:
            method_signature = f"{target.__class__.__module__}.{target.__class__.__name__}.{method.__name__}"
            return bool(pointcut.method_pattern.match(method_signature))
        
        # Check class pattern matching
        if pointcut.class_pattern:
            class_name = f"{target.__class__.__module__}.{target.__class__.__name__}"
            return bool(pointcut.class_pattern.match(class_name))
        
        return False
    
    def _matches_annotation(self, annotation_name: str, target: Any, method: Callable) -> bool:
        """Check if method or class has the specified annotation."""
        # Check method annotations
        if hasattr(method, '__annotations__'):
            for annotation in getattr(method, '__annotations__', {}):
                if annotation == annotation_name:
                    return True
        
        # Check for custom annotation attributes
        if hasattr(method, f'_spring_{annotation_name.lower()}'):
            return True
        
        # Check class annotations
        if hasattr(target.__class__, f'_spring_{annotation_name.lower()}'):
            return True
        
        return False


# Global pointcut matcher instance
_pointcut_matcher = PointcutMatcher()


def matches_pointcut(pointcut_expr: str, target: Any, method: Callable) -> bool:
    """Check if a method matches the given pointcut expression."""
    return _pointcut_matcher.matches(pointcut_expr, target, method)


def compile_pointcut(expression: str) -> PointcutExpression:
    """Compile a pointcut expression for efficient matching."""
    return _pointcut_matcher.compile_expression(expression)