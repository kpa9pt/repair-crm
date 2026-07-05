import asyncio
import sys
from pathlib import Path


from shared import get_session_maker
from shared.auth import get_password_hash
from shared.models import User
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).parent.parent))


async def create_admin():
    session_maker = get_session_maker()

    async with session_maker() as session:
        # Проверяем есть ли админ
        result = await session.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()

        if admin:
            # Если есть — обновляем пароль
            admin.password_hash = get_password_hash("admin123")
            await session.commit()
            print("✅ Admin password updated!")
        else:
            # Если нет — создаем
            admin = User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                role="admin",
            )
            session.add(admin)
            await session.commit()
            print("✅ Admin created!")

        print("   Username: admin")
        print("   Password: admin123")


if __name__ == "__main__":
    asyncio.run(create_admin())
