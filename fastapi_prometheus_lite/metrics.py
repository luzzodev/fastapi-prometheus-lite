import typing
from abc import ABC, abstractmethod

from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge
from starlette.requests import HTTPConnection
from starlette.types import Scope

from .utils import extract_path_template_from_scope


class MetricsContext(HTTPConnection):
    def __init__(self, scope: Scope):
        super().__init__(scope)

    @property
    def global_active_requests(self) -> tuple[bool, str]:
        if not hasattr(self, "_global_active_requests"):
            self._global_active_requests = self.scope["metrics_context"]["global_active_requests"]
        return self._global_active_requests

    @property
    def matched_path_template(self) -> tuple[bool, str]:
        if not hasattr(self, "_matched_path_template"):
            self._matched_path_template = extract_path_template_from_scope(self.scope)
        return self._matched_path_template

    @property
    def request_method(self) -> str:
        return typing.cast(str, self.scope["method"])

    @property
    def request_duration(self):
        if not hasattr(self, "_request_duration"):
            self._request_duration = self.scope["metrics_context"]["request_duration"]
        return self._request_duration

    @property
    def response_status_code(self) -> int:
        if not hasattr(self, "_response_status_code"):
            self._response_status_code = self.scope["metrics_context"]["status_code"]
        return self._response_status_code


class MetricBase(ABC):
    @abstractmethod
    def __call__(self, metrics_context: MetricsContext):
        pass


class LiveMetricBase(ABC):
    def __init__(self):
        self._scope: Scope = {}

    def update_scope(self, scope: Scope):
        self._scope = scope

    @abstractmethod
    def __enter__(self) -> "LiveMetricBase":
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class TotalRequestsMetric(MetricBase):
    def __init__(
        self,
        metric_name: str = "http_requests_total",
        metric_doc: str = "Total number of requests by method, status and handler.",
        group_status_code: bool = True,
        group_unmatched_template: bool = True,
        registry: CollectorRegistry = REGISTRY,
    ):
        self._metric = Counter(metric_name, metric_doc, labelnames=("method", "handler", "status"), registry=registry)

        self.group_status_code: bool = group_status_code
        self.group_unmatched_template: bool = group_unmatched_template

    def __call__(self, metrics_context: MetricsContext):
        matched, path_template = metrics_context.matched_path_template
        if self.group_unmatched_template and not matched:
            path_template = "None"
        status_code = str(metrics_context.response_status_code)
        if self.group_status_code:
            status_code = status_code[0] + "xx"

        self._metric.labels(method=metrics_context.request_method, handler=path_template, status=status_code).inc()


class GlobalActiveRequests(LiveMetricBase):
    def __init__(
        self,
        metric_name: str = "http_active_requests",
        metric_doc: str = "Number of current active requests.",
        registry: CollectorRegistry = REGISTRY,
    ):
        super(GlobalActiveRequests, self).__init__()

        self._metric = Gauge(metric_name, metric_doc, registry=registry)

    def __enter__(self) -> "GlobalActiveRequests":
        self._metric.inc()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._metric.dec()
