from zoneinfo import ZoneInfo
from sqladmin import ModelView
from shared.models import Equipment

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


class EquipmentAdmin(ModelView, model=Equipment):
    """Админка для техники"""

    name = "Техника"
    name_plural = "Техника"
    icon = "fa-solid fa-tools"

    column_list = [
        Equipment.id,
        Equipment.name,
        Equipment.type,
        Equipment.serial_number,
        Equipment.owner_name,
        Equipment.owner_phone,
        Equipment.created_at,
    ]

    column_labels = {
        Equipment.name: "Название",
        Equipment.type: "Тип",
        Equipment.serial_number: "Серийный номер",
        Equipment.owner_name: "Владелец",
        Equipment.owner_phone: "Телефон владельца",
        Equipment.created_at: "Создано",
        Equipment.updated_at: "Обновлено",
    }

    column_searchable_list = [
        Equipment.name,
        Equipment.serial_number,
        Equipment.owner_name,
    ]

    column_default_sort = [(Equipment.created_at, True)]

    form_columns = [
        Equipment.name,
        Equipment.type,
        Equipment.serial_number,
        Equipment.owner_name,
        Equipment.owner_phone,
    ]

    form_args = {
        "name": {"label": "Название техники"},
        "type": {"label": "Тип техники"},
        "serial_number": {"label": "Серийный номер"},
        "owner_name": {"label": "Имя владельца"},
        "owner_phone": {"label": "Телефон владельца"},
    }
