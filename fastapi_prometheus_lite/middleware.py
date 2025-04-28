import logging
import timeit

from fastapi import FastAPI
from starlette.types import Scope, Send, Receive, Message
from starlette.routing import Route
from prometheus_client import CollectorRegistry, Gauge

from .route_patcher import patch_starlette_routes
from .metrics import MetricBase, MetricsContext

logger = logging.getLogger(__name__)


class FastApiPrometheusMiddleware:

    def __init__(
            self,
            app: FastAPI,
            registry: CollectorRegistry,
            metrics_collectors: list = None,
            enable_active_requests_metric: bool = True
    ):

        self.app: FastAPI = app
        self.metrics_registry: CollectorRegistry = registry
        self.metrics_collectors: list[MetricBase] = [] if metrics_collectors is None else metrics_collectors
        patch_starlette_routes(Route)

        self.active_requests_metrics: Gauge | None = None
        if enable_active_requests_metric:
            self.active_requests_metrics = Gauge(
                "http_active_requests",
                "Number of current active requests.",
                registry=self.metrics_registry
            )

    async def __call__(self, scope: Scope, receive: Receive, send: Send):

        # We collect metrics only from Http. If this is not http just forward it.
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        if self.active_requests_metrics:
            self.active_requests_metrics.inc()

        status_code = 500
        start_time = timeit.default_timer()

        async def send_wrapper(message: Message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as ex:
            raise ex
        finally:
            duration = max(timeit.default_timer() - start_time, 0.0)
            scope["metrics_context"] = {
                "request_duration": duration,
                "status_code": status_code,

            }
            if self.active_requests_metrics:
                self.active_requests_metrics.dec()

        metrics_context = MetricsContext(scope=scope)
        for metric_collector in self.metrics_collectors:
            try:
                metric_collector(metrics_context)
            except Exception as exc:
                logger.error(
                    f"An error occurred while processing metric. {metric_collector.__class__.__name__} -> {str(exc)}"
                )
