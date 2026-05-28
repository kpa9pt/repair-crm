from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from shared.settings import get_settings

_engine = None
_session_maker = None


async def get_session_maker():
    global _engine, _session_maker
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=True)
        _session_maker = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_maker
