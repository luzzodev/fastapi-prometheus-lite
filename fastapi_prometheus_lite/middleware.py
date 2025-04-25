from fastapi import FastAPI
from starlette.types import Scope, Send, Receive, Message
from starlette.routing import Route
from prometheus_client import CollectorRegistry

from .route_patcher import patch_starlette_routes


class FastApiPrometheusMiddleware:

    def __init__(
            self,
            app: FastAPI,
            registry: CollectorRegistry
    ):

        self.app: FastAPI = app
        self.metrics_registry: CollectorRegistry = registry
        patch_starlette_routes(Route)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):

        # We collect metrics only from Http. If this is not http just forward it.
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_wrapper(message: Message):
            await send(message)

        await self.app(scope, receive, send_wrapper)
