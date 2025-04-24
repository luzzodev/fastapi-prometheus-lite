# FastAPI Prometheus Lite

![Status](https://img.shields.io/badge/project-personal-blueviolet)

A fast, minimal Prometheus middleware for FastAPI — no multiprocessing, no env config, no body reads. Just clean, efficient metrics.

---

## 📖 Description

**FastAPI Prometheus Lite** is a lightweight and high-performance Prometheus middleware for FastAPI applications. It provides essential request-level metrics such as request counts and durations, while avoiding the overhead of more feature-rich instrumentors. This library is ideal for developers who want **precise, clean metrics** without pulling in unnecessary complexity.

### ✨ Why Lite?

This project was created with a clear goal in mind: provide **just enough instrumentation** for FastAPI performance and visibility — and nothing more.

Compared to full-fledged solutions, this package intentionally avoids:
- ❌ Multiprocessing support (unnecessary for most simple deployments)
- ❌ Environment-based configuration (explicit is better than implicit)
- ❌ Automatic registration of default or system-level metrics
- ❌ Request and response body parsing (to keep things fast and safe)

Instead, it focuses on:
- ✅ Precise, labeled Prometheus metrics (`http_requests_total`, `http_request_duration_seconds`)
- ✅ Zero-config setup with FastAPI’s native middleware interface
- ✅ Minimal dependency tree (just `fastapi` and `prometheus-client`)
- ✅ ASGI-native implementation with optional Starlette type support

It’s perfect for lean microservices, observability-conscious APIs, and production-like setups where **performance and control matter**.

> ⚠️ **Note**: This project was developed for **personal use and as a showcase of FastAPI middleware design**. It is not intended to be a production-ready replacement for full-featured solutions. Feel free to use it as inspiration, reference, or a learning tool — not as a drop-in replacement unless you've reviewed and tailored it to your own needs.

---

## Credits

This project is heavily inspired by [prometheus-fastapi-instrumentator](https://github.com/trallnag/prometheus-fastapi-instrumentator) by [@trallnag](https://github.com/trallnag).

It borrows the overall design philosophy of exposing route-aware, labeled Prometheus metrics for FastAPI applications. However, the codebase here is a ground-up reimplementation focused on simplicity, performance, and explicit configuration.
