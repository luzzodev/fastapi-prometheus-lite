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

from fastapi import FastAPI, Response
from typing import Any
from enum import Enum
from prometheus_client import CollectorRegistry, REGISTRY, generate_latest, CONTENT_TYPE_LATEST

from fastapi_prometheus_lite.metrics import MetricBase
from fastapi_prometheus_lite.middleware import FastApiPrometheusMiddleware


class FastApiPrometheusLite:

    def __init__(
            self,
            registry: CollectorRegistry | None = None,
            metrics_collectors: list | None = None,
            enable_active_requests_metric: bool = True
    ):
        self.registry = registry or REGISTRY
        self.metrics_collectors: list[MetricBase] = [] if metrics_collectors is None else metrics_collectors
        self.enable_active_requests_metric: bool = enable_active_requests_metric

    def instrument(self, app: FastAPI) -> "FastApiPrometheusLite":
        app.add_middleware(
            FastApiPrometheusMiddleware,
            self.registry,
            metrics_collectors=self.metrics_collectors,
            enable_active_requests_metric=self.enable_active_requests_metric
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
