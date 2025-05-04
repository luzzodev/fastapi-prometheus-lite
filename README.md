# FastAPI Prometheus Lite

![Status](https://img.shields.io/badge/project-personal-blueviolet)

A fast, minimal Prometheus middleware for FastAPI — no multiprocessing, no env config, no body reads. Just clean, efficient metrics.

---

## 📋 Table of Contents

- [Description](#📖-description)
- [Installation](#💿-installation)
- [Quickstart](#🚀-quickstart)
- [Instrumentor Usage](#⚙️-instrumentor-usage)
- [Building Custom Collectors](#building-custom-collectors)
- [Credits](#credits)

---

## 📖 Description

**FastAPI Prometheus Lite** is a lightweight and high-performance Prometheus middleware for FastAPI applications. It provides essential request-level metrics such as request counts and durations, while avoiding the overhead of more feature-rich instrumentors. This library is ideal for developers who want **precise, clean metrics** without pulling in unnecessary complexity.

> ⚠️ **Limitations & Caveats**: This project was built for personal use and has certain constraints that are acceptable for my setup:
> - Does *not* support multi-worker (prefork) deployments. If you run multiple Gunicorn/Uvicorn workers in the same process, metrics will not aggregate correctly.
> - Works correctly when you deploy multiple **replicas** (separate processes or containers) behind a load‑balancer, since each replica maintains its own registry.
> - Live collectors cannot access the route template (`matched_path_template`) in the ASGI scope; only post-request collectors can utilize it for labeling.
> - Instrumentation currently supports only base HTTP and WebSocket routes patched via Starlette; mounted sub-applications (e.g., static file mounts) and other route types are not supported.

### ✨ Why Lite?

This project was created with a clear goal in mind: provide **just enough instrumentation** for FastAPI performance and visibility — and nothing more.

Compared to full-fledged solutions, this package intentionally avoids:
- ❌ Multiprocessing support (unnecessary for most simple deployments)
- ❌ Environment-based configuration (explicit is better than implicit)
- ❌ Automatic registration of default or system-level metrics
- ❌ Double routing (avoiding processing the same request twice through middleware)
- ❌ Request and response body parsing (to keep things fast and safe)

Instead, it focuses on:
- ✅ Precise, labeled Prometheus metrics (`http_requests_total`, `http_request_duration_seconds`)
- ✅ Zero-config setup with FastAPI’s native middleware interface
- ✅ Minimal dependency tree (just `fastapi` and `prometheus-client`)
- ✅ ASGI-native implementation with optional Starlette type support

It’s perfect for lean microservices, observability-conscious APIs, and production-like setups where **performance and control matter**.

> ⚠️ **Note**: This project was developed for **personal use and as a showcase of FastAPI middleware design**. It is not intended to be a production-ready replacement for full-featured solutions. Feel free to use it as inspiration, reference, or a learning tool — not as a drop-in replacement unless you've reviewed and tailored it to your own needs.

---

## 💿 Installation

```bash
pip install fastapi-prometheus-lite
```

---

## 🚀 Quickstart

```python
from fastapi import FastAPI
from fastapi_prometheus_lite import Instrumentor
from fastapi_prometheus_lite.metrics.post_metrics import TotalRequests
from fastapi_prometheus_lite.metrics.live_metrics import GlobalActiveRequests

app = FastAPI()

instrumentor = Instrumentor(
    metrics_collectors=[TotalRequests()],
    live_metrics_collectors=[GlobalActiveRequests()],
    excluded_paths=["^/docs"]
).instrument(app).expose(app)
```

------

## ⚙️ Instrumentor Usage

The `Instrumentor` (alias for `FastApiPrometheusLite`) provides a simple, fluent API for integrating Prometheus metrics into your FastAPI application.

### Initialize

Instantiate the instrumentor with optional configuration:

```python
instrumentor = Instrumentor(
    registry=None,                 # optional CollectorRegistry, defaults to global
    metrics_collectors=[],         # post-request collectors (list of CollectorBase; e.g., TotalRequests())
    live_metrics_collectors=[],    # in-request collectors (list of LiveCollectorBase; e.g., GlobalActiveRequests())
    excluded_paths=["^/health$"], # regex patterns of paths to skip
)
```

- **`registry`**: Prometheus `CollectorRegistry` (uses global registry if `None`).
- **`metrics_collectors`**: list of `CollectorBase` instances executed **after** each request (counters, histograms, etc.).
- **`live_metrics_collectors`**: list of `LiveCollectorBase` instances wrapping each request (**during** execution, e.g., in-flight gauges, timers).
- **`excluded_paths`**: regex patterns matching request paths to skip instrumentation.

### Instrument the App

Attach the Prometheus middleware to your FastAPI application:

```python
instrumentor.instrument(app)
```

This call adds the ASGI middleware that records metrics on every HTTP request (except excluded paths).

### Expose Metrics Endpoint

Register a scrape endpoint that serves collected metrics:

```python
instrumentor.expose(
    app,
    endpoint="/metrics",      # URL path (default: "/metrics")
    include_in_schema=True,     # include in OpenAPI schema
    tags=["Metrics"],          # optional OpenAPI tags
)
```

- **`endpoint`**: path at which metrics are exposed.
- **`include_in_schema`**: toggle inclusion in OpenAPI docs.
- **`tags`**: list of tags for documentation grouping.
- **`**kwargs`**: additional parameters forwarded to `app.get()`.

### Fluent Chaining

All methods return the `instrumentor` instance, allowing chaining:

```python
Instrumentor(...)
    .instrument(app)
    .expose(app)
```

### Building Custom Collectors

For more advanced collectors, you can extend the provided typed-base abstractions:

- **`CounterCollectorBase`**, **`GaugeCollectorBase`**, **`HistogramCollectorBase`**, **`SummaryCollectorBase`** for post-request collectors.
- **`LiveCounterCollectorBase`**, **`LiveGaugeCollectorBase`**, **`LiveHistogramCollectorBase`**, **`LiveSummaryCollectorBase`** for in-request (live) collectors.

#### Example: Custom Counter

```python
from fastapi_prometheus_lite.collectors.typed_collector_bases import CounterCollectorBase
from fastapi_prometheus_lite.collectors.base import MetricsContext


class MyRequestCounter(CounterCollectorBase):
    def __call__(self, ctx: MetricsContext):
        matched, path_format = ctx.matched_path_template
        labels = {
            "method": ctx.request_method,
            "path": path_format,
            "status": str(ctx.response_status_code),
        }
        # Increment the counter with custom labels
        self.metric.labels(**labels).inc()
```

#### Example: Custom Live Gauge Collector

```python
from fastapi_prometheus_lite.collectors.typed_live_collector_bases import LiveGaugeCollectorBase


class InFlightRequestsGauge(LiveGaugeCollectorBase):
    def __enter__(self):
        labels = {"method": self._scope["method"], "path": self._scope["path"]}
        self.metric.labels(**labels).inc()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        labels = {"method": self._scope["method"], "path": self._scope["path"]}
        self.metric.labels(**labels).dec()
```

Use these base classes when initializing your instrumentor:

```python
instrumentor = Instrumentor(
    metrics_collectors=[MyRequestCounter()],
    live_metrics_collectors=[InFlightRequestsGauge()],
    excluded_paths=["^/docs$"],
).instrument(app).expose(app)
```

------

## Credits

This project is heavily inspired by [prometheus-fastapi-instrumentator](https://github.com/trallnag/prometheus-fastapi-instrumentator) by [@trallnag](https://github.com/trallnag).

It borrows the overall design philosophy of exposing route-aware, labeled Prometheus metrics for FastAPI applications. However, the codebase here is a ground-up reimplementation focused on simplicity, performance, and explicit configuration.

