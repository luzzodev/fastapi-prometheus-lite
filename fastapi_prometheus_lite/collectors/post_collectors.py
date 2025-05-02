from typing import Any, Iterable, Optional

from prometheus_client import CollectorRegistry

from fastapi_prometheus_lite.metrics import CounterMetricBase, MetricsContext


class TotalRequestsCollector(CounterMetricBase):
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
        status_code = str(metrics_context.response_status_code)
        if self.group_status_code:
            status_code = status_code[0] + "xx"

        self.metric.labels(method=metrics_context.request_method, handler=path_template, status=status_code).inc()
