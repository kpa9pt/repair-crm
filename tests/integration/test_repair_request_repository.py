import pytest
from shared.db import get_session_maker
from shared.repository import RepairRequestRepository


@pytest.mark.asyncio
async def test_repository_create():
    session_maker = await get_session_maker()
    async with session_maker() as session:
        repo = RepairRequestRepository(session)
        request = await repo.create(
            vehicle_name="Квадроцикл-5", description="Не заводится"
        )
        assert request.id is not None
        assert request.status == "new"
