from shared.models import RepairRequest


def test_repair_request_creation():
    """Проверяем, что модель создаётся без ошибок."""
    request = RepairRequest(
        vehicle_name="Квадроцикл-5", description="Не заводится", status="new"
    )
    assert request.vehicle_name == "Квадроцикл-5"
    assert request.status == "new"
