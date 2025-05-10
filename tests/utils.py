from functools import wraps
from typing import Callable

from fastapi_prometheus_lite.starlette_patcher import RouteType


def unpatch_starlette_routes(*route_classes: type[RouteType]) -> None:
    """
    Unpatch Starlette routes.

    This unpatch is idempotent and safe to call multiple times.

    :param route_classes: One or more route classes to patch.
    """
    for route_class in route_classes:
        if not hasattr(route_class, "__original_matches"):
            continue

        # Override the method with the patched version
        route_class.matches = getattr(route_class, "__original_matches")
        delattr(route_class, "__original_matches")


def cleanup_starlette_patch(*route_classes: type[RouteType]) -> Callable:
    """
    Decorator to ensure Starlette routes are unpatched before the test,
    regardless of who applied the patch.
    """

    def decorator(test_func: Callable) -> Callable:
        @wraps(test_func)
        def wrapper(*args, **kwargs):
            for cls in route_classes:
                unpatch_starlette_routes(cls)
            return test_func(*args, **kwargs)

        return wrapper

    return decorator
