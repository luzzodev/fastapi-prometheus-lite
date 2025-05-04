from abc import abstractmethod
from typing import Any, Iterable, Optional

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, Summary

from fastapi_prometheus_lite.collectors.base import LiveCollectorBase, RegistrableCollector


class LiveCounterCollectorBase(LiveCollectorBase, RegistrableCollector):
    """
    Base for Counter‐style live metrics.

    Subclasses implement __enter__/__exit__ to inc()/dec() as desired.
    """

    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Iterable[str] = (),
        registry: Optional[CollectorRegistry] = None,
        **kwargs: Any,
    ):
        super().__init__()
        self._metric: Counter = Counter(name, documentation, labelnames=labelnames, registry=registry, **kwargs)

    @property
    def metric(self) -> Counter:
        return self._metric

    @abstractmethod
    def __enter__(self) -> "LiveCounterCollectorBase":
        """
        Called at request start. Use self.metric.labels(**...) to inc().
        """

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Called at request end. Use self.metric.labels(**...) to reset().
        """


class LiveGaugeCollectorBase(LiveCollectorBase, RegistrableCollector):
    """
    Base for Gauge‐style live metrics.

    Subclasses implement __enter__/__exit__ to inc()/dec()/set() as desired.
    """

    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Iterable[str] = (),
        registry: Optional[CollectorRegistry] = None,
        **kwargs: Any,
    ):
        super().__init__()
        self._metric: Gauge = Gauge(name, documentation, labelnames=labelnames, registry=registry, **kwargs)

    @property
    def metric(self) -> Gauge:
        return self._metric

    @abstractmethod
    def __enter__(self) -> "LiveGaugeCollectorBase":
        """
        Called at request start. Use self.metric.labels(**...) to set/inc().
        """

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Called at request end. Use self.metric.labels(**...) to dec() or reset.
        """


class LiveHistogramCollectorBase(LiveCollectorBase, RegistrableCollector):
    """
    Base for Histogram‐style live metrics.

    Subclasses implement __enter__/__exit__ to observe() as desired.
    """

    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Iterable[str] = (),
        registry: Optional[CollectorRegistry] = None,
        **kwargs: Any,  # e.g. buckets
    ):
        super().__init__()
        self._metric: Histogram = Histogram(name, documentation, labelnames=labelnames, registry=registry, **kwargs)

    @property
    def metric(self) -> Histogram:
        return self._metric

    @abstractmethod
    def __enter__(self) -> "LiveHistogramCollectorBase":
        """
        Called at request start. Could start a timer, etc.
        """

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Called at request end. Use self.metric.labels(**...).observe(duration).
        """


class LiveSummaryCollectorBase(LiveCollectorBase, RegistrableCollector):
    """
    Base for Summary‐style live metrics.

    Subclasses implement __enter__/__exit__ to observe() as desired.
    """

    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Iterable[str] = (),
        registry: Optional[CollectorRegistry] = None,
        **kwargs: Any,
    ):
        super().__init__()
        self._metric: Summary = Summary(name, documentation, labelnames=labelnames, registry=registry, **kwargs)

    @property
    def metric(self) -> Summary:
        return self._metric

    @abstractmethod
    def __enter__(self) -> "LiveSummaryCollectorBase":
        """
        Called at request start. Could record a start time.
        """

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Called at request end. Use self.metric.labels(**...).observe(value).
        """
