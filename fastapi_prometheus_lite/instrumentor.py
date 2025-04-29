"""
FastApiPrometheusLite

This module was inspired by the structure and design philosophy of the 'prometheus-fastapi-instrumentator'
and similar Prometheus client libraries for FastAPI.

Credits:
- Prometheus Python Client (https://github.com/prometheus/client_python)
- FastAPI Prometheus Instrumentator (https://github.com/trallnag/prometheus-fastapi-instrumentator)

This codebase borrows the idea of modular metric collectors and ASGI middleware-driven instrumentation,
adapted into a minimalistic and flexible form.
"""

from enum import Enum
from typing import Any

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, CollectorRegistry, generate_latest

from fastapi_prometheus_lite.metrics import LiveMetricBase, MetricBase
from fastapi_prometheus_lite.middleware import FastApiPrometheusMiddleware


class FastApiPrometheusLite:
    def __init__(
        self,
        registry: CollectorRegistry | None = None,
        metrics_collectors: list[MetricBase] | None = None,
        live_metrics_collectors: list[LiveMetricBase] | None = None,
    ):
        self.registry = registry or REGISTRY
        self.metrics_collectors: list[MetricBase] = []
        self.live_metrics_collectors: list[LiveMetricBase] = []

        if metrics_collectors is not None:
            self.metrics_collectors = metrics_collectors

        if live_metrics_collectors is not None:
            self.live_metrics_collectors = live_metrics_collectors

    def instrument(self, app: FastAPI) -> "FastApiPrometheusLite":
        app.add_middleware(
            FastApiPrometheusMiddleware,
            self.registry,
            metrics_collectors=self.metrics_collectors,
            live_metrics_collectors=self.live_metrics_collectors,
        )
        return self

    def expose(
        self,
        app: FastAPI,
        endpoint: str = "/metrics",
        include_in_schema: bool = True,
        tags: list[str | Enum] | None = None,
        **kwargs: Any,
    ) -> "FastApiPrometheusLite":
        assert isinstance(app, FastAPI), "Metrics must be exposed on FastApi app!"

        def metrics_endpoint() -> Response:
            response = Response(content=generate_latest(self.registry))
            response.headers.append("Content-Type", CONTENT_TYPE_LATEST)
            return response

        app.get(endpoint, include_in_schema=include_in_schema, tags=tags, **kwargs)(metrics_endpoint)
        return self
