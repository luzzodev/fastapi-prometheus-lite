import pytest
from starlette.routing import Match, Route, WebSocketRoute
from starlette.types import Scope

from fastapi_prometheus_lite.route_patcher import patch_starlette_routes, patched_matches

# --- helper endpoints (we only care about matches, not dispatch) ---


async def dummy_http(request):
    return None


async def dummy_ws(scope, receive, send):
    return None


def test_patch_is_idempotent_and_preserves_original_method():
    # capture the original before patch
    orig_http = Route.matches
    orig_ws = WebSocketRoute.matches

    # apply patch for the first time
    patch_starlette_routes(Route, WebSocketRoute)

    # __original_matches should be set once, and matches replaced
    assert Route.__original_matches is orig_http
    assert WebSocketRoute.__original_matches is orig_ws
    assert Route.matches is patched_matches
    assert WebSocketRoute.matches is patched_matches

    # calling patch again should not overwrite __original_matches
    patch_starlette_routes(Route, WebSocketRoute)
    assert Route.__original_matches is orig_http
    assert WebSocketRoute.__original_matches is orig_ws


@pytest.mark.parametrize(
    "path,should_match,expected_template",
    [
        ("/items/123", True, "/items/{item_id}"),
        ("/items/", False, None),
        ("/foo/123", False, None),
    ],
)
def test_http_route_match_injects_template(path, should_match, expected_template):
    # ensure patched
    patch_starlette_routes(Route)

    route = Route("/items/{item_id}", dummy_http, methods=["GET"])
    scope: Scope = {"type": "http", "method": "GET", "path": path}

    match, new_scope = route.matches(scope)

    if should_match:
        assert match == Match.FULL
        # ensure we got our new key
        assert new_scope["matched_path_template"] == expected_template
    else:
        assert match == Match.NONE
        # for non-matches, we do not inject
        assert "matched_path_template" not in new_scope


@pytest.mark.parametrize(
    "path,should_match,expected_template",
    [
        ("/ws/abc", True, "/ws/{client_id}"),
        ("/ws/", False, None),
    ],
)
def test_websocket_route_match_injects_template(path, should_match, expected_template):
    # ensure patched
    patch_starlette_routes(WebSocketRoute)

    route = WebSocketRoute("/ws/{client_id}", dummy_ws)
    # minimal websocket scope; only 'type' and 'path' needed by matches()
    scope: Scope = {"type": "websocket", "path": path}

    match, new_scope = route.matches(scope)

    if should_match:
        assert match == Match.FULL
        assert new_scope["matched_path_template"] == expected_template
    else:
        assert match == Match.NONE
        assert "matched_path_template" not in new_scope
