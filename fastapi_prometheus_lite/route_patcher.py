from typing import Union
from starlette.routing import Match, Route, WebSocketRoute
from starlette.types import Scope

# Type alias to represent any supported route type
RouteType = Union[Route, WebSocketRoute]


def patched_matches(self: RouteType, scope: Scope) -> tuple[Match, Scope]:
    """
    Replacement for the route.matches() method.

    Injects the matched route's path into the ASGI scope if a match is found.
    This enables downstream middleware or handlers to access the route template
    that matched the request.

    :param self: The Route or WebSocketRoute instance.
    :param scope: The ASGI scope dictionary.
    :return: A tuple of (Match enum, updated scope).
    """
    match, scope = getattr(self, "__original_matches")(scope)

    if match != Match.NONE:
        scope["matched_path_template"] = self.path

    return match, scope


def patch_starlette_routes(*route_classes: type[RouteType]) -> None:
    """
    Monkey-patches the matches() method of the given Starlette route classes
    (typically Route and WebSocketRoute) to enrich the ASGI scope with
    the matched route path.

    This is useful when route information is needed early in the request lifecycle,
    such as in middleware or dependency injection.

    This patch is idempotent and safe to call multiple times.

    :param route_classes: One or more route classes to patch.
    """
    for route_class in route_classes:
        if not hasattr(route_class, "__original_matches"):
            # Preserve the original method for potential unpatching/debugging
            setattr(route_class, "__original_matches", route_class.matches)

            # Override the method with the patched version
            route_class.matches = patched_matches
