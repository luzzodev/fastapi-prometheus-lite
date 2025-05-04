from typing import Any, Iterable, Optional

from prometheus_client import CollectorRegistry

from fastapi_prometheus_lite.collectors import LiveGaugeCollectorBase


class GlobalActiveRequests(LiveGaugeCollectorBase):
    def __init__(
        self,
        metric_name: str = "http_active_requests",
        metric_doc: str = "Number of current active requests.",
        labelnames: Iterable[str] = (),
        registry: Optional[CollectorRegistry] = None,
        **kwargs: Any,
    ):
        super().__init__(metric_name, metric_doc, labelnames=labelnames, registry=registry, **kwargs)

    def __enter__(self) -> "GlobalActiveRequests":
        self.metric.inc()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.metric.dec()
