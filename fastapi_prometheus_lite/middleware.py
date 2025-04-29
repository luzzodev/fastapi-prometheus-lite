import logging
import timeit

from contextlib import ExitStack
from fastapi import FastAPI
from starlette.types import Scope, Send, Receive, Message
from starlette.routing import Route
from prometheus_client import CollectorRegistry

from .route_patcher import patch_starlette_routes
from .metrics import MetricBase, LiveMetricBase, MetricsContext

logger = logging.getLogger(__name__)


class FastApiPrometheusMiddleware:

    def __init__(
            self,
            app: FastAPI,
            registry: CollectorRegistry,
            metrics_collectors: list[MetricBase],
            live_metrics_collectors: list[LiveMetricBase]
    ):

        self.app: FastAPI = app
        self.metrics_registry: CollectorRegistry = registry
        self.metrics_collectors: list[MetricBase] = metrics_collectors
        self.live_metrics_collectors: list[LiveMetricBase] = live_metrics_collectors
        self.global_active_requests: int = 0

        patch_starlette_routes(Route)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):

        # We collect metrics only from Http. If this is not http just forward it.
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        status_code = 500
        start_time = timeit.default_timer()
        self.global_active_requests += 1

        async def send_wrapper(message: Message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        with ExitStack() as exit_stack:

            for live_metric_collector in self.live_metrics_collectors:
                live_metric_collector.update_scope(scope)
                exit_stack.enter_context(live_metric_collector)

            try:
                await self.app(scope, receive, send_wrapper)
            except Exception as ex:
                raise ex
            finally:
                duration = max(timeit.default_timer() - start_time, 0.0)
                scope["metrics_context"] = {
                    "global_active_requests": self.global_active_requests,
                    "request_duration": duration,
                    "status_code": status_code,

                }
                self.global_active_requests -= 1

                metrics_context = MetricsContext(scope=scope)
                for metric_collector in self.metrics_collectors:
                    try:
                        metric_collector(metrics_context)
                    except Exception as exc:
                        logger.error(
                            f"An error occurred while processing metric. "
                            f"{metric_collector.__class__.__name__} -> {str(exc)}"
                        )
