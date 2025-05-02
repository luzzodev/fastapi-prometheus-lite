from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, Summary

from .base import LiveMetricBase


class LiveCounterMetricBase(LiveMetricBase, ABC):
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
        self.metric: Counter = Counter(name, documentation, labelnames=labelnames, registry=registry, **kwargs)

    @abstractmethod
    def __enter__(self) -> "LiveCounterMetricBase":
        """
        Called at request start. Use self.metric.labels(**...) to inc().
        """

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Called at request end. Use self.metric.labels(**...) to reset().
        """


class LiveGaugeMetricBase(LiveMetricBase, ABC):
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
        self.metric: Gauge = Gauge(name, documentation, labelnames=labelnames, registry=registry, **kwargs)

    @abstractmethod
    def __enter__(self) -> "LiveGaugeMetricBase":
        """
        Called at request start. Use self.metric.labels(**...) to set/inc().
        """

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Called at request end. Use self.metric.labels(**...) to dec() or reset.
        """


class LiveHistogramMetricBase(LiveMetricBase, ABC):
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
        self.metric: Histogram = Histogram(name, documentation, labelnames=labelnames, registry=registry, **kwargs)

    @abstractmethod
    def __enter__(self) -> "LiveHistogramMetricBase":
        """
        Called at request start. Could start a timer, etc.
        """

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Called at request end. Use self.metric.labels(**...).observe(duration).
        """


class LiveSummaryMetricBase(LiveMetricBase, ABC):
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
        self.metric: Summary = Summary(name, documentation, labelnames=labelnames, registry=registry, **kwargs)

    @abstractmethod
    def __enter__(self) -> "LiveSummaryMetricBase":
        """
        Called at request start. Could record a start time.
        """

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Called at request end. Use self.metric.labels(**...).observe(value).
        """
