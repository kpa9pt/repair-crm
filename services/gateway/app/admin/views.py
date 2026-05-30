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
        RepairRequest.status,
        RepairRequest.urgency,
        RepairRequest.is_operational,
        RepairRequest.created_at,
        RepairRequest.deadline,
        RepairRequest.client_name,
    ]

    column_labels = {
        RepairRequest.vehicle_name: "Техника",
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
    ]

    can_export = True
    can_view_details = True

    # --------------------
    # ФОРМА
    # --------------------
    form_columns = [
        # === ОСНОВНОЕ ===
        "vehicle_name",
        "description",
        "is_operational",
        # === УПРАВЛЕНИЕ ===
        "urgency",
        "status",
        "deadline",
        # === ФИНАНСЫ ===
        "parts_cost",
        "client_payment",
        # === КЛИЕНТ ===
        "client_name",
        "phone",
        "email",
    ]

    form_args = {
        "vehicle_name": {"label": "Техника"},
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

    # # ДЕФОЛТЫ (SQLAdmin правильный способ)
    # form_args = {
    #     "client_name": {"default": "Топ Лес"},
    #     "urgency": {"default": Urgency.NORMAL.value},
    #     "status": {"default": RequestStatus.NEW.value},
    #     "is_operational": {"default": False},
    #     "parts_cost": {"default": Decimal("0.00")},
    #     "client_payment": {"default": Decimal("0.00")},
    # }

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
