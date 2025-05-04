from abc import abstractmethod
from typing import Any, Iterable, Optional

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, Summary

from fastapi_prometheus_lite.collectors.base import CollectorBase, MetricsContext, RegistrableCollector


class CounterCollectorBase(CollectorBase, RegistrableCollector):
    """
    Base for Counter-style metrics.

    Subclasses get `self.metric: prometheus_client.Counter` ready to use.
    Just implement `__call__(self, ctx: MetricsContext)` and
    do whatever labels/inc logic you need.
    """

    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Iterable[str] = (),
        registry: Optional[CollectorRegistry] = None,
        **kwargs: Any,
    ):
        self._metric: Counter = Counter(name, documentation, labelnames=labelnames, registry=registry, **kwargs)

    @property
    def metric(self) -> Counter:
        return self._metric

    @abstractmethod
    def __call__(self, ctx: MetricsContext):
        """
        Called after request. Use self.metric to inc(), inc(amount), etc.
        Example in subclass:
            labels = {...}
            self.metric.labels(**labels).inc()
        """


class GaugeCollectorBase(CollectorBase, RegistrableCollector):
    """
    Base for Gauge-style metrics.

    Users get `self.metric: prometheus_client.Gauge`.
    Implement `__call__` to set/inc/dec as you wish.
    """

    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Iterable[str] = (),
        registry: Optional[CollectorRegistry] = None,
        **kwargs: Any,
    ):
        self._metric: Gauge = Gauge(name, documentation, labelnames=labelnames, registry=registry, **kwargs)

    @property
    def metric(self) -> Gauge:
        return self._metric

    @abstractmethod
    def __call__(self, ctx: MetricsContext):
        """
        Called after request. Use self.metric to inc()/dec()/set().
        """


class HistogramCollectorBase(CollectorBase, RegistrableCollector):
    """
    Base for Histogram-style metrics.

    Users get `self.metric: prometheus_client.Histogram`.
    Implement `__call__` to observe whatever value you choose.
    """

    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Iterable[str] = (),
        registry: Optional[CollectorRegistry] = None,
        **kwargs: Any,  # e.g. buckets=(...)
    ):
        self._metric: Histogram = Histogram(name, documentation, labelnames=labelnames, registry=registry, **kwargs)

    @property
    def metric(self) -> Histogram:
        return self._metric

    @abstractmethod
    def __call__(self, ctx: MetricsContext):
        """
        Called after request. Use self.metric to observe().
        """


class SummaryCollectorBase(CollectorBase, RegistrableCollector):
    """
    Base for Summary-style metrics.

    Users get `self.metric: prometheus_client.Summary`.
    Implement `__call__` to observe whatever value you choose.
    """

    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Iterable[str] = (),
        registry: Optional[CollectorRegistry] = None,
        **kwargs: Any,
    ):
        self._metric: Summary = Summary(name, documentation, labelnames=labelnames, registry=registry, **kwargs)

    @property
    def metric(self) -> Summary:
        return self._metric

    @abstractmethod
    def __call__(self, ctx: MetricsContext):
        """
        Called after request. Use self.metric to observe().
        """
