from fastapi import APIRouter, Depends, HTTPException, status
from shared import get_session_maker
from shared.auth import (
    create_access_token,
    User,
    Token,
    UserLogin,
    UserCreate,
    UserResponse,
    require_role,
    get_current_user,
)
from ..repositories.user import UserRepository

from pydantic import BaseModel  # ← ДОБАВИТЬ ЭТУ СТРОКУ

router = APIRouter(tags=["auth"])


# ========== НОВАЯ СХЕМА ДЛЯ VALIDATE ==========
class ValidateTokenRequest(BaseModel):
    """Запрос на валидацию токена"""

    token: str


# =============================================


async def get_repo():
    """Dependency для репозитория User"""
    session_maker = get_session_maker()
    async with session_maker() as session:
        yield UserRepository(session)


@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,  # ← Pydantic модель
    repo: UserRepository = Depends(get_repo),
):
    user = await repo.authenticate(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
        }
    )
    return Token(access_token=access_token)


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    current_user: User = Depends(require_role(["admin"])),
    repo: UserRepository = Depends(get_repo),
):
    """
    Регистрация нового пользователя.
    Доступно только для админов.
    """
    existing = await repo.get_by_username(user_data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    user = await repo.create(
        username=user_data.username,
        password=user_data.password,
        role=user_data.role,
    )
    await repo.session.commit()
    await repo.session.refresh(user)

    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        telegram_id=user.telegram_id,
        created_at=user.created_at.isoformat(),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    repo: UserRepository = Depends(get_repo),
):
    """
    Получить информацию о текущем пользователе.
    """
    user = await repo.get_by_id(current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        telegram_id=user.telegram_id,
        created_at=user.created_at.isoformat(),
    )


@router.post("/validate")
async def validate_token(
    request: ValidateTokenRequest,
    repo: UserRepository = Depends(get_repo),
):
    """
    Валидация JWT токена.
    Используется другими сервисами для проверки токенов.
    """
    from shared.auth import decode_token

    try:
        token_data = decode_token(request.token)  # ← меняем token на request.token
        user = await repo.get_by_id(token_data.sub)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        return {
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "telegram_id": user.telegram_id,
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
