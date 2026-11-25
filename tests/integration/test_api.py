from contextlib import AsyncExitStack

import fakeredis
import pytest
from httpx import ASGITransport, AsyncClient

from app.container import Container
from app.core.config import Settings
from app.infrastructure.db.base import Base
from app.infrastructure.db.session import create_engine
from app.main import create_app


@pytest.fixture
async def replicas(tmp_path):
    """Two independent app instances sharing one Redis server and one database,
    mimicking a horizontally scaled deployment."""
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    server = fakeredis.FakeServer()

    setup_engine = create_engine(db_url)
    async with setup_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await setup_engine.dispose()

    clients = []
    async with AsyncExitStack() as stack:
        for i in range(2):
            settings = Settings(
                database_url=db_url,
                instance_id=f"replica-{i}",
                rate_limit_requests=1000,
                _env_file=None,
            )
            container = Container(
                settings,
                redis=fakeredis.FakeAsyncRedis(server=server, decode_responses=True),
                engine=create_engine(db_url),
            )
            app = create_app(settings, container)
            await stack.enter_async_context(app.router.lifespan_context(app))
            client = await stack.enter_async_context(
                AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
            )
            clients.append(client)
        yield clients


async def test_crud_and_cross_replica_cache_invalidation(replicas):
    a, b = replicas

    r = await a.post("/api/v1/products", json={"name": "Widget", "sku": "W-1", "price": "9.99"})
    assert r.status_code == 201, r.text
    assert r.headers["x-instance-id"] == "replica-0"
    pid = r.json()["id"]

    # Replica B reads (and caches) the product and the list.
    assert (await b.get(f"/api/v1/products/{pid}")).json()["stock"] == 0
    assert (await b.get("/api/v1/products")).json()["total"] == 1

    # Replica A updates; replica B must observe it immediately via the shared cache.
    r = await a.patch(f"/api/v1/products/{pid}", json={"stock": 7})
    assert r.status_code == 200
    assert (await b.get(f"/api/v1/products/{pid}")).json()["stock"] == 7
    assert (await b.get("/api/v1/products")).json()["items"][0]["stock"] == 7

    assert (await b.delete(f"/api/v1/products/{pid}")).status_code == 204
    assert (await a.get(f"/api/v1/products/{pid}")).status_code == 404


async def test_conflict_and_validation(replicas):
    a, b = replicas
    body = {"name": "X", "sku": "DUP", "price": "1.00"}
    assert (await a.post("/api/v1/products", json=body)).status_code == 201
    assert (await b.post("/api/v1/products", json=body)).status_code == 409
    bad = {"name": "X", "sku": "Y", "price": "-1"}
    assert (await a.post("/api/v1/products", json=bad)).status_code == 422


async def test_health_and_request_id(replicas):
    a, _ = replicas
    r = await a.get("/health/ready", headers={"X-Request-ID": "abc"})
    assert r.status_code == 200
    assert r.json()["checks"] == {"redis": True, "database": True}
    assert r.headers["x-request-id"] == "abc"
