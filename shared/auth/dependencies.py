from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from .schemas import User
from .utils import decode_token

security = HTTPBearer()  # ← вместо OAuth2PasswordBearer


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    token = credentials.credentials
    try:
        token_data = decode_token(token)
        return User(
            id=token_data.sub, username=token_data.username, role=token_data.role
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Проверяет, что пользователь активен (заглушка для будущего).
    """
    # В будущем можно добавить проверку is_active
    return current_user


def require_role(allowed_roles: list[str]):
    """
    Фабрика для проверки ролей.
    Используется в роутерах для ограничения доступа.

    Пример:
        @router.post("/")
        async def create(
            current_user: User = Depends(require_role(["admin", "mechanic"]))
        ):
            ...
    """

    async def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required roles: {allowed_roles}",
            )
        return current_user

    return dependency
