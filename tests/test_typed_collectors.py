import pytest
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, Summary

# Import the abstract bases to test
from fastapi_prometheus_lite.collectors import (
    CounterCollectorBase,
    GaugeCollectorBase,
    HistogramCollectorBase,
    LiveCounterCollectorBase,
    LiveGaugeCollectorBase,
    LiveHistogramCollectorBase,
    LiveSummaryCollectorBase,
    SummaryCollectorBase,
)


# Registry fixture for collecting metrics
@pytest.fixture
def registry():
    return CollectorRegistry()


# Dummy subclasses to satisfy the abstract __call__
class DummyCounter(CounterCollectorBase):
    def __call__(self, ctx):
        pass


class DummyGauge(GaugeCollectorBase):
    def __call__(self, ctx):
        pass


class DummyHistogram(HistogramCollectorBase):
    def __call__(self, ctx):
        pass


class DummySummary(SummaryCollectorBase):
    def __call__(self, ctx):
        pass


# Dummy subclasses to satisfy the abstract __enter__, __exit__
class LiveDummyCounter(LiveCounterCollectorBase):
    def __enter__(self) -> "LiveDummyCounter":
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class LiveDummyGauge(LiveGaugeCollectorBase):
    def __enter__(self) -> "LiveDummyGauge":
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class LiveDummyHistogram(LiveHistogramCollectorBase):
    def __enter__(self) -> "LiveDummyHistogram":
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class LiveDummySummary(LiveSummaryCollectorBase):
    def __enter__(self) -> "LiveDummySummary":
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.parametrize(
    "cls,prom_cls,name,labels",
    [
        (DummyCounter, Counter, "c1", []),
        (DummyCounter, Counter, "c2", ["x", "y"]),
        (DummyGauge, Gauge, "g1", []),
        (DummyGauge, Gauge, "g2", ["a"]),
        (DummyHistogram, Histogram, "h1", []),
        (DummyHistogram, Histogram, "h2", ["p", "q", "r"]),
        (DummySummary, Summary, "s1", []),
        (DummySummary, Summary, "s2", ["foo"]),
        (LiveDummyCounter, Counter, "lc1", []),
        (LiveDummyCounter, Counter, "lc2", ["x", "y"]),
        (LiveDummyGauge, Gauge, "lg1", []),
        (LiveDummyGauge, Gauge, "lg2", ["a"]),
        (LiveDummyHistogram, Histogram, "lh1", []),
        (LiveDummyHistogram, Histogram, "lh2", ["p", "q", "r"]),
        (LiveDummySummary, Summary, "ls1", []),
        (LiveDummySummary, Summary, "ls2", ["foo"]),
    ],
)
def test_typed_metric_base_init(registry, cls, prom_cls, name, labels):
    # Instantiate the metric base with provided labels and registry
    instance = cls(
        name=name,
        documentation="test doc",
        labelnames=labels,
        registry=registry,
    )

    # Verify the underlying Prometheus metric type
    assert isinstance(instance.metric, prom_cls)

    # Check that the metric's name and documentation match
    assert instance.metric._name == name
    assert instance.metric._documentation == "test doc"

    # Check that the metric's label names were registered correctly
    assert instance.metric._labelnames == tuple(labels)

    # The provided registry should now contain this metric
    collected_names = [m.name for m in registry.collect()]
    assert name in collected_names
