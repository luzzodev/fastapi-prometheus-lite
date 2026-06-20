from typing import Union

from starlette.routing import Match, Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

try:
    # FastAPI >=0.137 resolves include_router(prefix=...) / nested-router prefixes
    # through this private context instead of baking them into ``APIRoute.path``.
    from fastapi.routing import _EffectiveRouteContext as EffectiveRouteContext
except ImportError:  # older FastAPI, or the internal was renamed/removed
    EffectiveRouteContext = None

# Type alias to represent any supported route type whose matches() we patch.
RouteType = Union[Route, Mount, WebSocketRoute]
if EffectiveRouteContext is not None:
    RouteType = Union[Route, Mount, WebSocketRoute, EffectiveRouteContext]


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
    match, child_scope = getattr(self, "__original_matches")(scope)

    if match != Match.NONE:
        # Determine the matched path
        root_path = scope.get("root_path", "")
        matched_path = self.path

        if isinstance(self, Mount):
            matched_path = self.path_format
            if not isinstance(self.app, StaticFiles):
                return match, child_scope  # Skip StaticFiles mounts

        # Inject matched path template into child scope
        child_scope["matched_path_template"] = root_path + matched_path

    return match, child_scope


def patch_starlette_routes(*route_classes: type[RouteType] | None) -> None:
    """
    Monkey-patches the matches() method of the given Starlette route classes
    (typically Route and WebSocketRoute, Mount) to enrich the ASGI scope with
    the matched route path.

    This is useful when route information is needed early in the request lifecycle,
    such as in middleware or dependency injection.

    This patch is idempotent and safe to call multiple times.

    :param route_classes: One or more route classes to patch. When omitted, the
        version-appropriate set from :func:`default_route_classes` is used.
    """
    for route_class in route_classes:
        if route_class is None:
            continue
        if not hasattr(route_class, "__original_matches"):
            # Preserve the original method for potential un-patching/debugging
            setattr(route_class, "__original_matches", route_class.matches)

            # Override the method with the patched version
            route_class.matches = patched_matches
