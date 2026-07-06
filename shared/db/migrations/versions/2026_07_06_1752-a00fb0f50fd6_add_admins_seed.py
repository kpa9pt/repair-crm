"""add admins seed

Revision ID: a00fb0f50fd6
Revises: f8de3a86f713
Create Date: 2026-07-06 17:52:11.574814

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import os
from shared.auth import get_password_hash

# revision identifiers, used by Alembic.
revision: str = "a00fb0f50fd6"
down_revision: Union[str, Sequence[str], None] = "f8de3a86f713"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создаем админа при миграции"""

    # Берем данные из env или дефолтные
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "admin123")
    password_hash = get_password_hash(password)

    # SQL вставка с проверкой на дубли
    op.execute(
        f"""
        INSERT INTO users (username, password_hash, role, created_at)
        VALUES ('{username}', '{password_hash}', 'admin', NOW())
        ON CONFLICT (username) DO NOTHING
    """
    )

    print(f"✅ Admin user seeded: {username}")


def downgrade() -> None:
    """Удаляем админа при откате"""
    username = os.getenv("ADMIN_USERNAME", "admin")
    op.execute(
        f"""
        DELETE FROM users WHERE username = '{username}'
    """
    )
