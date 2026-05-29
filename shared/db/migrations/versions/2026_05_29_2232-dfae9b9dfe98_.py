from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "dfae9b9dfe98"
down_revision: Union[str, Sequence[str], None] = "ef27e3a3bb21"
branch_labels = None
depends_on = None


urgency_enum = sa.Enum("LOW", "NORMAL", "HIGH", "CRITICAL", name="urgency_enum")

request_status_enum = sa.Enum(
    "NEW",
    "IN_PROGRESS",
    "WAITING_PARTS",
    "DIAGNOSTICS",
    "WAITING_APPROVAL",
    "DONE",
    name="request_status_enum",
)


def upgrade() -> None:
    bind = op.get_bind()

    # 1. создаём enum-типы
    urgency_enum.create(bind, checkfirst=True)
    request_status_enum.create(bind, checkfirst=True)

    # 2. УБИРАЕМ старые дефолты (важно!)
    op.alter_column(
        "repair_requests",
        "urgency",
        existing_type=sa.VARCHAR(length=20),
        server_default=None,
    )

    op.alter_column(
        "repair_requests",
        "status",
        existing_type=sa.VARCHAR(length=30),
        server_default=None,
    )

    # 3. меняем типы
    op.alter_column(
        "repair_requests",
        "urgency",
        existing_type=sa.VARCHAR(length=20),
        type_=sa.Enum("LOW", "NORMAL", "HIGH", "CRITICAL", name="urgency_enum"),
        postgresql_using="urgency::text::urgency_enum",
        existing_nullable=False,
    )

    op.alter_column(
        "repair_requests",
        "status",
        existing_type=sa.VARCHAR(length=30),
        type_=sa.Enum(
            "NEW",
            "IN_PROGRESS",
            "WAITING_PARTS",
            "DIAGNOSTICS",
            "WAITING_APPROVAL",
            "DONE",
            name="request_status_enum",
        ),
        postgresql_using="status::text::request_status_enum",
        existing_nullable=False,
    )

    # 4. ставим новые enum defaults
    op.alter_column(
        "repair_requests",
        "urgency",
        server_default=sa.text("'NORMAL'::urgency_enum"),
    )

    op.alter_column(
        "repair_requests",
        "status",
        server_default=sa.text("'NEW'::request_status_enum"),
    )


def downgrade() -> None:
    op.alter_column(
        "repair_requests",
        "urgency",
        server_default=None,
    )
    op.alter_column(
        "repair_requests",
        "status",
        server_default=None,
    )

    op.alter_column(
        "repair_requests",
        "urgency",
        type_=sa.VARCHAR(length=20),
        existing_type=sa.Enum(name="urgency_enum"),
        postgresql_using="urgency::text",
        existing_nullable=False,
    )

    op.alter_column(
        "repair_requests",
        "status",
        type_=sa.VARCHAR(length=30),
        existing_type=sa.Enum(name="request_status_enum"),
        postgresql_using="status::text",
        existing_nullable=False,
    )

    # (опционально) удаление enum типов
    request_status_enum.drop(op.get_bind(), checkfirst=True)
    urgency_enum.drop(op.get_bind(), checkfirst=True)
