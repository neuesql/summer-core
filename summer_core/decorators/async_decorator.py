"""
Async decorator for asynchronous method execution.
"""

import functools
import threading
from typing import Any, Callable, TypeVar, cast

T = TypeVar('T', bound=Callable[..., Any])


def Async(func: T) -> T:
    """
    Decorator for methods that should be executed asynchronously.
    
    This decorator marks a method for asynchronous execution. When the method
    is called, it will be executed in a separate thread.
    
    Args:
        func: The function to decorate
        
    Returns:
        The decorated function
        
    Example:
        ```python
        @Component
        class AsyncService:
            @Async
            def process_data(self, data):
                # This will be executed in a separate thread
                time.sleep(5)
                print(f"Processed data: {data}")
        ```
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread
    
    # Mark the function as async
    wrapper.__is_async__ = True  # type: ignore
    
    return cast(T, wrapper)