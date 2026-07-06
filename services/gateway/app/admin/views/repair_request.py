from decimal import Decimal
from zoneinfo import ZoneInfo
from sqladmin import ModelView

from shared.models import RepairRequest
from shared.enums import Urgency, RequestStatus


MOSCOW_TZ = ZoneInfo("Europe/Moscow")


class RepairRequestAdmin(ModelView, model=RepairRequest):
    """Админка RepairRequest"""

    name = "Заявка"
    name_plural = "Заявки на ремонт"
    icon = "fa-solid fa-wrench"

    # --------------------
    # СПИСОК
    # --------------------
    column_list = [
        RepairRequest.id,
        RepairRequest.vehicle_name,
        RepairRequest.equipment_id,
        RepairRequest.created_by_username,  # ← добавить
        RepairRequest.status,
        RepairRequest.urgency,
        RepairRequest.is_operational,
        RepairRequest.created_at,
        RepairRequest.deadline,
        RepairRequest.client_name,
    ]

    column_labels = {
        RepairRequest.vehicle_name: "Техника",
        RepairRequest.equipment_id: "Техника (из БД)",
        RepairRequest.created_by_username: "Создатель",  # ← добавить
        RepairRequest.client_name: "Клиент",
        RepairRequest.status: "Статус заявки",
        RepairRequest.urgency: "Срочность",
        RepairRequest.created_at: "Создано",
        RepairRequest.deadline: "Дедлайн",
        RepairRequest.is_operational: "Техника на ходу?",
    }

    column_editable_list = [
        RepairRequest.status,
        RepairRequest.urgency,
    ]

    column_filters = []

    column_default_sort = [(RepairRequest.created_at, True)]

    search_fields = [
        "vehicle_name",
        "client_name",
        "description",
        "equipment.name",
    ]

    can_export = True
    can_view_details = True

    # --------------------
    # ФОРМА (ОСНОВНОЙ ФИКС)
    # --------------------
    form_columns = [
        "vehicle_name",
        "equipment",  # <- Теперь поле точно появится
        "description",
        "is_operational",
        "urgency",
        "status",
        "deadline",
        "parts_cost",
        "client_payment",
        "client_name",
        "phone",
        "email",
    ]

    # 👇 Выпадающий список с поиском (дополнительно)

    # Удали form_overrides, если он был
    # form_overrides = {...}

    form_args = {
        "vehicle_name": {"label": "Техника"},
        "equipment_id": {"label": "Выбрать технику из базы"},
        "client_name": {"label": "Клиент", "default": "Топ Лес"},
        "phone": {"label": "Телефон"},
        "email": {"label": "Email"},
        "description": {"label": "Описание проблемы"},
        "urgency": {"label": "Срочность", "default": Urgency.NORMAL.value},
        "status": {"label": "Статус заявки", "default": RequestStatus.NEW.value},
        "deadline": {"label": "Дедлайн"},
        "parts_cost": {"label": "Стоимость запчастей", "default": Decimal("0.00")},
        "client_payment": {"label": "Оплата клиента", "default": Decimal("0.00")},
        "is_operational": {"label": "Техника на ходу?", "default": False},
    }

    # --------------------
    # ВЫПАДАЮЩИЕ СПИСКИ
    # --------------------
    form_choices = {
        "urgency": [
            ("low", "🟢 Низкая"),
            ("normal", "🟡 Обычная"),
            ("high", "🟠 Высокая"),
            ("critical", "🔴 Критическая"),
        ],
        "status": [
            ("new", "🟢 Новая"),
            ("in_progress", "🟡 В работе"),
            ("waiting_parts", "🔴 Ожидает запчасти"),
            ("diagnostics", "🔵 Диагностика"),
            ("waiting_approval", "🟠 Ожидает согласования"),
            ("done", "✅ Готово"),
        ],
        "is_operational": [
            (True, "Да"),
            (False, "Нет"),
        ],
    }

    # --------------------
    # ФОРМАТИРОВАНИЕ ДАТ (MSK)
    # --------------------
    column_formatters = {
        RepairRequest.status: lambda m, a: {
            "new": "🟢 Новая",
            "in_progress": "🟡 В работе",
            "waiting_parts": "🔴 Ожидает запчасти",
            "diagnostics": "🔵 Диагностика",
            "waiting_approval": "🟠 Ожидает согласования",
            "done": "✅ Готово",
        }.get(m.status, m.status),
        RepairRequest.urgency: lambda m, a: {
            "low": "🟢 Низкая",
            "normal": "🟡 Обычная",
            "high": "🟠 Высокая",
            "critical": "🔴 Критическая",
        }.get(m.urgency, m.urgency),
        RepairRequest.created_at: lambda m, a: (
            m.created_at.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M")
            if m.created_at
            else ""
        ),
        RepairRequest.deadline: lambda m, a: (
            m.deadline.strftime("%d.%m.%Y") if m.deadline else ""
        ),
    }
