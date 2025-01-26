from enum import Enum
from typing import Any, Optional


class BeanScope(Enum):
    """Enum defining the possible scopes of a bean.

    Attributes:
        SINGLETON: The bean will be created once and reused.
        PROTOTYPE: A new instance of the bean will be created each time it is requested.
    """

    SINGLETON = "singleton"
    PROTOTYPE = "prototype"


class BeanDefinition:
    """Class for storing metadata about a bean.

    This class holds all necessary information about a bean, including its name,
    class type, scope, and any dependencies it might have.

    Attributes:
        name: The unique identifier of the bean.
        bean_class: The actual class type of the bean.
        scope: The scope of the bean (singleton or prototype).
        dependencies: Optional dictionary of dependency names to their types.
    """

    def __init__(
        self,
        name: str,
        bean_class: type[Any],
        scope: BeanScope = BeanScope.SINGLETON,
        dependencies: Optional[dict[str, type[Any]]] = None,
    ) -> None:
        self.name = name
        self.bean_class = bean_class
        self.scope = scope
        self.dependencies = {} if dependencies is None else dependencies
