import logging
import re
import timeit
from contextlib import ExitStack
from typing import Pattern

from fastapi import FastAPI
from prometheus_client import CollectorRegistry
from starlette.datastructures import Headers
from starlette.responses import Response
from starlette.routing import Mount, Route
from starlette.types import Message, Receive, Scope, Send

from .collectors import CollectorBase, LiveCollectorBase, MetricsContext, RegistrableCollector
from .starlette_patcher import patch_starlette_routes

logger = logging.getLogger(__name__)


class FastApiPrometheusMiddleware:
    """
    ASGI middleware for Prometheus metrics integration in FastAPI applications.

    This middleware wraps each incoming HTTP request to:
    - Track live metrics during the lifecycle of a request
    - Run post-request metrics collection logic
    - Attach request metrics to a Prometheus registry
    """

    def __init__(
        self,
        app: FastAPI,
        registry: CollectorRegistry,
        metrics_collectors: list[CollectorBase],
        live_metrics_collectors: list[LiveCollectorBase],
        excluded_paths: list[str],
    ):
        """
        Initialize the Prometheus middleware.

        :param app: The FastAPI application to wrap with middleware.
        :param registry: The Prometheus CollectorRegistry used to register metrics.
        :param metrics_collectors: A list of MetricBase instances to collect metrics
            after the request lifecycle is complete.
        :param live_metrics_collectors: A list of LiveMetricBase instances to track
            metrics during the active request lifecycle.
        :param excluded_paths: A list of path that will be excluded from the tracking.
        """
        self.app: FastAPI = app
        self.metrics_registry: CollectorRegistry = registry
        self.metrics_collectors: list[CollectorBase] = metrics_collectors
        self.live_metrics_collectors: list[LiveCollectorBase] = live_metrics_collectors
        self.global_active_requests: int = 0
        self.excluded_paths: set[Pattern] = set(re.compile(path) for path in excluded_paths)

        for metric_collector in self.metrics_collectors + self.live_metrics_collectors:
            if isinstance(metric_collector, RegistrableCollector):
                if not metric_collector.register(self.metrics_registry):
                    logger.warning(
                        f"Metric collector: {metric_collector.__class__.__name__} has been already registered "
                        f"on this registry."
                    )

        patch_starlette_routes(Route, Mount)

    def _is_path_excluded(self, scope: Scope) -> bool:
        requested_path: str = scope.get("path", None)
        if requested_path is None:
            return True
        return any(pattern.search(requested_path) for pattern in self.excluded_paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        """
        ASGI entry point for handling requests.

        Called automatically for each request and responsible for:
        - Filtering non-HTTP scopes
        - Managing live metric entry and exit (e.g. active counters)
        - Capturing request duration and status
        - Invoking post-request metric collectors

        :param scope: The ASGI scope object for the request.
        :param receive: The ASGI receive callable.
        :param send: The ASGI send callable.
        """

        # We collect metrics only from Http. If this is not http just forward it.
        if scope["type"] != "http" or self._is_path_excluded(scope):
            return await self.app(scope, receive, send)

        status_code = 500
        response_headers = []
        start_time = timeit.default_timer()
        self.global_active_requests += 1

        async def send_wrapper(message: Message):
            nonlocal status_code, response_headers
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = message["headers"]
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
                }
                self.global_active_requests -= 1

                response = Response(headers=Headers(raw=response_headers), status_code=status_code)
                metrics_context = MetricsContext(scope=scope, response=response)

                for metric_collector in self.metrics_collectors:
                    try:
                        metric_collector(metrics_context)
                    except Exception as exc:
                        logger.error(
                            f"An error occurred while processing metric. "
                            f"{metric_collector.__class__.__name__} -> {str(exc)}"
                        )
