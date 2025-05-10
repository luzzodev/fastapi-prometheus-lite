from pathlib import Path

import pytest
from fastapi import FastAPI, staticfiles
from httpx import ASGITransport, AsyncClient

from fastapi_prometheus_lite import Instrumentor


@pytest.fixture
def test_app() -> FastAPI:
    static_files_dir = Path(__file__).parent.parent / "static-files"

    app = FastAPI()
    app.mount("/static", staticfiles.StaticFiles(directory=static_files_dir), name="static")

    app_2 = FastAPI()
    app.mount("/app2", app_2, name="app2")

    @app.get("/ping")
    async def ping():
        return {"message": "pong"}

    @app_2.get("/ping")
    async def ping_2():
        return {"message": "pong_2"}

    Instrumentor().instrument(app).expose(app)

    return app


@pytest.mark.asyncio
async def test_ping(test_app: FastAPI):
    transport = ASGITransport(app=test_app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get("/ping")

    assert response.status_code == 200
    assert response.json() == {"message": "pong"}

    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get("/app2/ping")

    assert response.status_code == 200
    assert response.json() == {"message": "pong_2"}


@pytest.mark.asyncio
async def test_static_files(test_app: FastAPI):
    transport = ASGITransport(app=test_app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get("/static/hello-world.txt")

    assert response.status_code == 200
    assert response.content == b"Hello World!"
