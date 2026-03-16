from typing import Any

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.entities import RefreshToken
from ..core.errors import UnauthorizedError
from ..db.repos import RefreshTokenRepository, UserRepository
from ..schemas import Token, TokensPair, TokenType, UserCreateForm
from ..settings import settings
from ..utils.commons import current_datetime, get_expiration_timestamp
from ..utils.secutiry import generate_token, verify_password


def create_tokens_pair(payload: dict[str, Any]) -> TokensPair:
    """Создаёт пару токенов 'access' и 'refresh'"""

    access_token_expires_in = timedelta(minutes=settings.jwt.access_token_expires_in_minutes)
    refresh_token_expires_in = timedelta(days=settings.jwt.refresh_token_expires_in_days)
    access_token = generate_token(
        token_type=TokenType.ACCESS,
        payload=payload,
        expires_in=access_token_expires_in,
    )
    refresh_token = generate_token(
        token_type=TokenType.REFRESH, payload=payload, expires_in=refresh_token_expires_in
    )
    return TokensPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=get_expiration_timestamp(access_token_expires_in),
    )


def create_access_token(payload: dict[str, Any]) -> Token:
    """Создание 'access' токена"""

    expires_in = timedelta(days=settings.jwt.guest_access_token_expires_in_days)
    access_token = generate_token(token_type=TokenType.ACCESS, payload=payload)
    return Token(access_token=access_token, expires_at=get_expiration_timestamp(expires_in))


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.refresh_repo = RefreshTokenRepository(session)

    async def register(self, token: str, form: UserCreateForm) -> TokensPair:
        """Регистрация нового пользователя"""

    async def authenticate(self, email: str, password: str) -> TokensPair:
        """Аутентификация пользователя по логин + пароль"""

        user = await self.user_repo.get_by_email(email)
        if user is None:
            raise UnauthorizedError(f"User not found by email - '{email}'")
        if (
                not verify_password(password, user.password_hash)
                and not user.is_active
        ):
            raise UnauthorizedError("Invalid password or user is not active")

        payload = {
            "iss": settings.app.url,
            "sub": f"{user.id}",
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role.value,
        }
        tokens = create_tokens_pair(payload)
        refresh_token = RefreshToken(
            user_id=user.id,
            token=tokens.refresh_token,
            expires_at=current_datetime() + timedelta(settings.jwt.refresh_token_expires_in_days),
        )
        await self.refresh_repo.create(refresh_token)
        await self.session.commit()
        return tokens

    async def refresh_tokens(self, refresh_token: str) -> TokensPair:
        """Обновление токенов с ротацией"""

        stored_token = await self.refresh_repo.get_by_token(refresh_token)
        if stored_token is None:
            raise UnauthorizedError("Refresh token not found")
        if not stored_token.is_valid:
            raise UnauthorizedError("Refresh token is already revoked or expired")
        user = await self.user_repo.read(stored_token.user_id)
        if user is None or not user.is_active:
            await self.refresh_repo.revoke(stored_token.id)
            raise UnauthorizedError("User is not active")
        await self.refresh_repo.revoke(stored_token.id)

        payload = {
            "iss": settings.app.url,
            "sub": f"{user.id}",
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
        }
        new_tokens = create_tokens_pair(payload)
        new_refresh_token = RefreshToken(
            user_id=user.id,
            token=new_tokens.refresh_token,
            expires_at=current_datetime() + timedelta(settings.jwt.refresh_token_expires_in_days)
        )
        await self.refresh_repo.create(new_refresh_token)
        await self.session.commit()
        return new_tokens
