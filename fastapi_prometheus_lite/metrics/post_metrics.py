from typing import Any, Iterable, Optional, Sequence

from prometheus_client import CollectorRegistry

from fastapi_prometheus_lite.collectors import CounterCollectorBase, HistogramCollectorBase, MetricsContext


class TotalRequests(CounterCollectorBase):
    def __init__(
        self,
        metric_name: str = "http_requests_total",
        metric_doc: str = "Total number of requests by method, status and handler.",
        labelnames: Iterable[str] = ("method", "handler", "status"),
        group_status_code: bool = True,
        group_unmatched_template: bool = True,
        registry: Optional[CollectorRegistry] = None,
        **kwargs: Any,
    ):
        super().__init__(metric_name, metric_doc, labelnames=labelnames, registry=registry, **kwargs)

        self.group_status_code: bool = group_status_code
        self.group_unmatched_template: bool = group_unmatched_template

    def __call__(self, metrics_context: MetricsContext):
        matched, path_template = metrics_context.matched_path_template
        if self.group_unmatched_template and not matched:
            path_template = "None"
        status_code = str(metrics_context.response.status_code)
        if self.group_status_code:
            status_code = status_code[0] + "xx"

        self.metric.labels(method=metrics_context.request_method, handler=path_template, status=status_code).inc()


class RequestLatency(HistogramCollectorBase):
    def __init__(
        self,
        metric_name: str = "http_request_duration_seconds",
        metric_doc: str = "Histogram of HTTP request durations (request start → response end).",
        labelnames: Iterable[str] = ("method", "handler"),
        buckets: Sequence[float | str] = (0.1, 0.5, 1),
        group_unmatched_template: bool = True,
        registry: Optional[CollectorRegistry] = None,
        **kwargs: Any,
    ):
        super().__init__(metric_name, metric_doc, labelnames=labelnames, buckets=buckets, registry=registry, **kwargs)
        self.group_unmatched_template: bool = group_unmatched_template

    def __call__(self, metrics_context: MetricsContext):
        duration = metrics_context.request_duration  # in seconds
        matched, path_template = metrics_context.matched_path_template
        if self.group_unmatched_template and not matched:
            path_template = "None"

        self.metric.labels(method=metrics_context.request_method, handler=path_template).observe(duration)
