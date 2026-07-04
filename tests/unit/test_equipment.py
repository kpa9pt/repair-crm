"""Unit тесты для модели Equipment"""

from shared.models import Equipment


def test_equipment_creation():
    """Тест создания модели Equipment"""
    equipment = Equipment(
        name="Квадроцикл-5",
        type="квадроцикл",
        serial_number="SN-12345",
        owner_name="Топ Лес",
        owner_phone="+7-999-123-45-67",
    )
    assert equipment.name == "Квадроцикл-5"
    assert equipment.type == "квадроцикл"
    assert equipment.serial_number == "SN-12345"
    assert equipment.owner_name == "Топ Лес"
    assert equipment.owner_phone == "+7-999-123-45-67"


def test_equipment_str():
    """Тест строкового представления"""
    equipment = Equipment(name="Квадроцикл-5")
    assert str(equipment) == "Квадроцикл-5"
