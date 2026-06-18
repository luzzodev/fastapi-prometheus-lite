"""
Regression test for a concurrency bug in the live-collector pattern, driven
through a real FastAPI app.

A single live-collector instance is shared across all requests, and per-request
state is stored via ``update_scope`` (read back through ``self._scope``).
``__enter__`` runs synchronously right after ``update_scope``, so entry sees the
correct scope. But ``__exit__`` runs at the *end* of the request, after ``await``
points -- by then a concurrent request may have run ``update_scope`` again.

Previously the scope lived in a plain instance attribute, so the concurrent
request corrupted it and ``__exit__`` would ``dec()`` a different label set than
``__enter__`` ``inc()``'d, causing gauge drift. The scope is now held in a
per-instance ``ContextVar``, which is isolated per request task, so entry and
exit always agree.

The route handlers block on ``asyncio.Event``s so the request interleaving is
deterministic (not timing-dependent), but the request path is otherwise a real
FastAPI + Instrumentor + httpx stack.
"""

import asyncio

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from prometheus_client import CollectorRegistry

from fastapi_prometheus_lite import Instrumentor
from fastapi_prometheus_lite.collectors import LiveGaugeCollectorBase


class InFlightRequestsGauge(LiveGaugeCollectorBase):
    """Mirror of the README example: labels are read from ``self._scope``."""

    def __init__(self):
        # registry=None: let the middleware register the metric (as the bundled collectors do).
        super().__init__("inflight_requests", "In-flight requests by path", labelnames=("path",))

    def __enter__(self) -> "InFlightRequestsGauge":
        self.metric.labels(path=self._scope["path"]).inc()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.metric.labels(path=self._scope["path"]).dec()


@pytest.mark.asyncio
async def test_live_collector_scope_isolated_under_concurrency():
    registry = CollectorRegistry()
    started = {"/a": asyncio.Event(), "/b": asyncio.Event()}
    release = {"/a": asyncio.Event(), "/b": asyncio.Event()}

    app = FastAPI()

    @app.get("/a")
    async def handler_a():
        started["/a"].set()
        await release["/a"].wait()
        return {"path": "/a"}

    @app.get("/b")
    async def handler_b():
        started["/b"].set()
        await release["/b"].wait()
        return {"path": "/b"}

    Instrumentor(registry=registry, live_metrics_collectors=[InFlightRequestsGauge()]).instrument(app)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        # 1. Request /a enters the middleware: update_scope(/a) + __enter__ -> inc(path=/a),
        #    then blocks inside the handler.
        task_a = asyncio.create_task(ac.get("/a"))
        await started["/a"].wait()

        # 2. Request /b enters while /a is still in flight: update_scope(/b) runs in
        #    /b's own task context, then __enter__ -> inc(path=/b), then blocks.
        task_b = asyncio.create_task(ac.get("/b"))
        await started["/b"].wait()

        # 3. Release /a first. Its __exit__ reads /a's own ContextVar scope, so it
        #    correctly decrements path=/a despite /b having run update_scope.
        release["/a"].set()
        resp_a = await task_a

        # 4. Release /b. Its __exit__ decrements path=/b.
        release["/b"].set()
        resp_b = await task_b

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200

    val_a = registry.get_sample_value("inflight_requests", labels={"path": "/a"})
    val_b = registry.get_sample_value("inflight_requests", labels={"path": "/b"})

    # Correct behavior: every request that incremented also decremented its own
    # label, so both gauges return to 0. Before the per-request ContextVar fix
    # the shared _scope was corrupted: /a leaked at 1 and /b drifted to -1.
    assert val_a == 0, f"path=/a gauge leaked (expected 0, got {val_a})"
    assert val_b == 0, f"path=/b gauge drifted (expected 0, got {val_b})"
