import inspect
from typing import Any

__all__ = ("is_method_overridden",)


def is_method_overridden(method_name: str, child_class: Any, parent_class: Any) -> bool:
    child_method = inspect.getattr_static(child_class, method_name, None)
    parent_method = inspect.getattr_static(parent_class, method_name, None)

    if (child_method is None) or (parent_method is None):
        return False

    return child_method is not parent_method
