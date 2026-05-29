import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from services.gateway.app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def reset():
    from shared.db.session import reset_db

    reset_db()
