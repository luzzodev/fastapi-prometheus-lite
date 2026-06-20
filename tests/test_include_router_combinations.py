"""
Integration tests for ``matched_path_template`` resolution across the different
ways routes can be registered on a FastAPI app:

- direct routes (with/without path params)
- ``include_router`` with a prefix given on the router
- ``include_router`` with a prefix given at include-time
- nested routers (router includes a sub-router)
- mounted sub-FastAPI apps
- mounted ``StaticFiles``
- unmatched paths (404)

The whole point of the library is that the Prometheus ``handler`` label is the
route *template* (e.g. ``/items/{item_id}``) rather than the raw URL, so each
case below fires a real request through the instrumented app and asserts the
``handler`` label recorded by ``TotalRequests``.

Running the debugger
--------------------
Two easy entry points, both let you set breakpoints in
``starlette_patcher.patched_matches`` / the collectors and step through:

1. Debug a single test in your IDE (PyCharm/VS Code) -- put a breakpoint and
   run the parametrized ``test_handler_label_matches_template`` case you care about.
2. Just run this file directly (Run/Debug ``__main__``). It builds the app and
   walks every scenario printing the resolved template -- no pytest needed.
"""

from pathlib import Path

import pytest
from fastapi import APIRouter, FastAPI, staticfiles
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry
from starlette.routing import Mount, Route, WebSocketRoute

from fastapi_prometheus_lite import Instrumentor
from fastapi_prometheus_lite.metrics.post_metrics import TotalRequests
from fastapi_prometheus_lite.starlette_patcher import EffectiveRouteContext
from tests.utils import unpatch_starlette_routes

STATIC_DIR = Path(__file__).parent / "static-files"


def build_app() -> tuple[FastAPI, CollectorRegistry]:
    """
    Build one app that exercises every route-registration style, instrumented
    with a single ``TotalRequests`` collector on a fresh registry.

    ``group_status_code=False`` keeps the raw status (e.g. "200") and
    ``group_unmatched_template=True`` collapses unmatched routes to "None", so
    assertions read cleanly.
    """
    registry = CollectorRegistry()
    app = FastAPI()

    # 1. direct route with a path param
    @app.get("/items/{item_id}")
    async def get_item(item_id: int):
        return {"item_id": item_id}

    # 2. router carrying its own prefix, included as-is
    users = APIRouter(prefix="/api/v1/users")

    @users.get("/{user_id}")
    async def get_user(user_id: int):
        return {"user_id": user_id}

    app.include_router(users)

    # 3. prefix-less router, prefix supplied at include-time
    orders = APIRouter()

    @orders.get("/{order_id}")
    async def get_order(order_id: int):
        return {"order_id": order_id}

    app.include_router(orders, prefix="/orders")

    # 4. nested routers: parent.include_router(child), then app.include_router(parent)
    parent = APIRouter(prefix="/parent")
    child = APIRouter(prefix="/child")

    @child.get("/{leaf_id}")
    async def get_leaf(leaf_id: int):
        return {"leaf_id": leaf_id}

    parent.include_router(child)
    app.include_router(parent)

    # 5. mounted sub-FastAPI app
    sub = FastAPI()

    @sub.get("/ping")
    async def sub_ping():
        return {"message": "pong"}

    app.mount("/app2", sub, name="app2")

    # 6. mounted StaticFiles
    app.mount("/static", staticfiles.StaticFiles(directory=STATIC_DIR), name="static")

    # registry goes to the Instrumentor; the middleware registers the collector on
    # it. (Passing registry= to the collector too would double-register and warn.)
    Instrumentor(
        registry=registry,
        metrics_collectors=[
            TotalRequests(group_status_code=False, group_unmatched_template=True),
        ],
    ).instrument(app)

    return app, registry


def handler_count(registry: CollectorRegistry, method: str, handler: str, status: str) -> float | None:
    """Read the http_requests_total sample for a given label set (None if absent)."""
    return registry.get_sample_value(
        "http_requests_total",
        labels={"method": method, "handler": handler, "status": status},
    )


@pytest.fixture
def app_and_registry():
    app, registry = build_app()
    try:
        yield app, registry
    finally:
        # The middleware monkeypatches Starlette routing globally; undo it so
        # this test doesn't leak the patch into others.
        unpatch_starlette_routes(Route, Mount, WebSocketRoute, EffectiveRouteContext)


# (request path, expected handler template, expected status)
CASES = [
    ("/items/123", "/items/{item_id}", "200"),
    ("/api/v1/users/7", "/api/v1/users/{user_id}", "200"),
    ("/orders/42", "/orders/{order_id}", "200"),
    ("/parent/child/9", "/parent/child/{leaf_id}", "200"),
    ("/app2/ping", "/app2/ping", "200"),
    ("/static/hello-world.txt", "/static/{path}", "200"),
    # unmatched -> no template injected -> grouped as "None"
    ("/does-not-exist", "None", "404"),
]


@pytest.mark.parametrize("path,expected_handler,expected_status", CASES)
def test_handler_label_matches_template(app_and_registry, path, expected_handler, expected_status):
    app, registry = app_and_registry

    with TestClient(app) as client:
        response = client.get(path)

    assert str(response.status_code) == expected_status
    assert handler_count(registry, "GET", expected_handler, expected_status) == 1


def test_repeated_requests_accumulate(app_and_registry):
    app, registry = app_and_registry

    with TestClient(app) as client:
        for _ in range(3):
            client.get("/items/123")

    assert handler_count(registry, "GET", "/items/{item_id}", "200") == 3


def main() -> None:
    """Debugger entry point: run/debug this file directly to walk every scenario.

    Set breakpoints in fastapi_prometheus_lite/starlette_patcher.py:patched_matches
    or in TotalRequests.__call__ to watch template resolution per case.
    """
    app, registry = build_app()
    with TestClient(app) as client:
        for path, expected_handler, expected_status in CASES:
            resp = client.get(path)
            recorded = handler_count(registry, "GET", expected_handler, expected_status)
            ok = "OK " if (str(resp.status_code) == expected_status and recorded == 1) else "FAIL"
            print(
                f"[{ok}] {path:<28} -> handler={expected_handler!r:<28} status={resp.status_code} recorded={recorded}"
            )
    unpatch_starlette_routes(Route, Mount, WebSocketRoute, EffectiveRouteContext)


if __name__ == "__main__":
    main()
