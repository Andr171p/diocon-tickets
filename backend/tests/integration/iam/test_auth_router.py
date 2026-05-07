from uuid import uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from src.crm.domain.vo import CounterpartyType
from src.crm.infra.models import CounterpartyOrm
from src.iam.dependencies import get_auth_service, get_current_user
from src.iam.domain.services import create_customer, invite_customer, invite_support
from src.iam.domain.vo import UserRole
from src.iam.infra.blacklist import RedisTokenBlacklist
from src.iam.infra.repos import SqlInvitationRepository, SqlUserRepository
from src.iam.security import hash_password, validate_token
from src.iam.services import AuthService, create_tokens_for_user


@pytest.fixture
async def redis_client(redis_url):
    client = Redis.from_url(redis_url, decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


@pytest.fixture
def auth_service(session, redis_client):
    return AuthService(
        session=session,
        user_repo=SqlUserRepository(session),
        invitation_repo=SqlInvitationRepository(session),
        blacklist=RedisTokenBlacklist(redis_client),
    )


@pytest.fixture
async def auth_client(auth_service, current_admin_user):
    from main import app

    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_current_user] = lambda: current_admin_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides = {}


@pytest.fixture
async def counterparty_id(session):
    counterparty = CounterpartyOrm(
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name=f"Test Counterparty {uuid4()}",
        legal_name=f"Test Legal {uuid4()}",
        inn=f"{uuid4().int % 10**10:010d}",
        kpp=None,
        okpo=None,
        phone="+70000000000",
        email=f"cp-{uuid4()}@example.com",
        address=None,
        avatar_url=None,
        contact_persons=[],
        is_active=True,
        parent_id=None,
    )
    session.add(counterparty)
    await session.commit()
    return counterparty.id


@pytest.mark.asyncio
async def test_register_success(auth_client, auth_service, counterparty_id):
    """
    Проверяем endpoint регистрации: он нужен, чтобы пользователь мог создать
    аккаунт по валидному приглашению и получить токены.
    Данные: customer-приглашение в реальной БД и форма регистрации.
    """
    invitation = invite_customer(
        invited_by=uuid4(),
        email="new.customer@example.com",
        counterparty_id=counterparty_id,
        assigned_role=UserRole.CUSTOMER,
    )
    await auth_service.invitation_repo.create(invitation)
    await auth_service.session.commit()

    response = await auth_client.post(
        f"/api/v1/auth/register/{invitation.token}",
        json={
            "username": "customer_1",
            "full_name": "Ivan Ivanov",
            "password": "StrongPass123!",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["token_type"] == "Bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["expires_at"] > 0

    created_user = await auth_service.user_repo.get_by_email(invitation.email)
    assert created_user is not None

    updated_invite = await auth_service.invitation_repo.get_by_token(invitation.token)
    assert updated_invite is not None
    assert updated_invite.is_used is True


@pytest.mark.asyncio
async def test_login_success(auth_client, auth_service, counterparty_id):
    """
    Проверяем endpoint логина: он нужен, чтобы существующий активный пользователь
    мог войти по email и паролю.
    Данные: customer-пользователь в реальной БД и корректный пароль.
    """
    user = create_customer(
        email="login.customer@example.com",
        password_hash=hash_password("StrongPass123!"),
        counterparty_id=counterparty_id,
        user_role=UserRole.CUSTOMER,
    )
    await auth_service.user_repo.create(user)
    await auth_service.session.commit()

    response = await auth_client.post(
        "/api/v1/auth/login",
        data={"username": user.email, "password": "StrongPass123!"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["token_type"] == "Bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["expires_at"] > 0


@pytest.mark.asyncio
async def test_login_invalid_password_integration(auth_client, auth_service, counterparty_id):
    """
    Проверяем endpoint логина: он должен вернуть 401, если пароль неверный.
    Данные: customer-пользователь в реальной БД и неправильный пароль.
    """
    user = create_customer(
        email="wrong.password@example.com",
        password_hash=hash_password("StrongPass123!"),
        counterparty_id=counterparty_id,
        user_role=UserRole.CUSTOMER,
    )
    await auth_service.user_repo.create(user)
    await auth_service.session.commit()

    response = await auth_client.post(
        "/api/v1/auth/login",
        data={"username": user.email, "password": "WrongPass123!"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert data["error"]["message"] == "Invalid password or user is not active"


@pytest.mark.asyncio
async def test_refresh_success(auth_client, auth_service, counterparty_id):
    """
    Проверяем endpoint обновления токенов: он нужен, чтобы пользователь мог
    получить новую пару токенов по валидному refresh token.
    Данные: customer-пользователь в реальной БД и его refresh token.
    """
    user = create_customer(
        email="refresh.customer@example.com",
        password_hash=hash_password("StrongPass123!"),
        counterparty_id=counterparty_id,
        user_role=UserRole.CUSTOMER,
    )
    await auth_service.user_repo.create(user)
    await auth_service.session.commit()
    tokens = create_tokens_for_user(user)

    response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens.refresh_token},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["token_type"] == "Bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["expires_at"] > 0


@pytest.mark.asyncio
async def test_logout_success(auth_client, auth_service):
    """
    Проверяем endpoint logout: он нужен, чтобы access и refresh токены
    попадали в blacklist после выхода пользователя.
    Данные: customer-пользователь и созданная для него пара токенов.
    """
    user = create_customer(
        email="logout.customer@example.com",
        password_hash=hash_password("StrongPass123!"),
        counterparty_id=uuid4(),
        user_role=UserRole.CUSTOMER,
    )
    tokens = create_tokens_for_user(user)
    access_payload = validate_token(tokens.access_token)
    refresh_payload = validate_token(tokens.refresh_token)

    response = await auth_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens.access_token}"},
        json={"refresh_token": tokens.refresh_token},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert await auth_service.blacklist.is_revoked(access_payload["jti"]) is True
    assert await auth_service.blacklist.is_revoked(refresh_payload["jti"]) is True


@pytest.mark.asyncio
async def test_userinfo_success(auth_client, current_admin_user):
    """
    Проверяем endpoint userinfo: он нужен, чтобы вернуть данные текущего
    аутентифицированного пользователя.
    Данные: current_admin_user из fixture и переопределённая FastAPI-зависимость.
    """
    response = await auth_client.get("/api/v1/auth/userinfo")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["user_id"] == str(current_admin_user.user_id)
    assert data["email"] == current_admin_user.email
    assert data["role"] == current_admin_user.role
    assert data["counterparty_id"] is None


@pytest.mark.asyncio
async def test_register_invitation_not_found_integration(auth_client):
    """
    Проверяем endpoint регистрации: он должен вернуть 404, если token
    приглашения не найден.
    Данные: несуществующий token и валидная форма регистрации.
    """
    response = await auth_client.post(
        "/api/v1/auth/register/non-existent-token",
        json={
            "username": "customer_404",
            "full_name": "Ivan Ivanov",
            "password": "StrongPass123!",
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert data["error"]["message"] == "Invitation not found"


@pytest.mark.asyncio
async def test_register_invitation_already_used_integration(
        auth_client, auth_service, counterparty_id
):
    """
    Проверяем endpoint регистрации: он должен вернуть 410, если приглашение
    уже использовано.
    Данные: customer-приглашение, заранее помеченное как used.
    """
    invitation = invite_customer(
        invited_by=uuid4(),
        email="used.customer@example.com",
        counterparty_id=counterparty_id,
        assigned_role=UserRole.CUSTOMER,
    )
    invitation.mark_as_used()
    await auth_service.invitation_repo.create(invitation)
    await auth_service.session.commit()

    response = await auth_client.post(
        f"/api/v1/auth/register/{invitation.token}",
        json={
            "username": "customer_used",
            "full_name": "Ivan Ivanov",
            "password": "StrongPass123!",
        },
    )

    assert response.status_code == status.HTTP_410_GONE
    data = response.json()
    assert data["error"]["code"] == "INVITATION_EXPIRED"
    assert data["error"]["message"] == "Invitation expired or already used"


@pytest.mark.asyncio
async def test_register_user_already_exists_integration(
        auth_client, auth_service, counterparty_id
):
    """
    Проверяем endpoint регистрации: он должен вернуть 409, если пользователь
    с email из приглашения уже существует.
    Данные: customer-приглашение и существующий пользователь с тем же email.
    """
    invitation = invite_customer(
        invited_by=uuid4(),
        email="existing.customer@example.com",
        counterparty_id=counterparty_id,
        assigned_role=UserRole.CUSTOMER,
    )
    await auth_service.invitation_repo.create(invitation)

    existing_user = create_customer(
        email=invitation.email,
        password_hash=hash_password("StrongPass123!"),
        counterparty_id=counterparty_id,
        user_role=UserRole.CUSTOMER,
    )
    await auth_service.user_repo.create(existing_user)
    await auth_service.session.commit()

    response = await auth_client.post(
        f"/api/v1/auth/register/{invitation.token}",
        json={
            "username": "customer_duplicate",
            "full_name": "Ivan Ivanov",
            "password": "StrongPass123!",
        },
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    data = response.json()
    assert data["error"]["code"] == "ALREADY_EXISTS"
    assert "already exists" in data["error"]["message"]


@pytest.mark.asyncio
async def test_register_by_support_invitation_creates_support_user(auth_client, auth_service):
    """
    Проверяем регистрацию по support-приглашению: она нужна, чтобы приглашенный
    сотрудник поддержки создавался как support-пользователь, а не как customer.
    Данные: настоящее неиспользованное приглашение с support-ролью.
    """

    invitation = invite_support(
        invited_by=uuid4(),
        email=f"support-{uuid4()}@example.com",
        assigned_role=UserRole.SUPPORT_AGENT,
    )

    await auth_service.invitation_repo.create(invitation)
    await auth_service.session.commit()

    response = await auth_client.post(
        f"/api/v1/auth/register/{invitation.token}",
        json={
            "username": "support_1",
            "full_name": "Support User",
            "password": "StrongPass123!",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    created_user = await auth_service.user_repo.get_by_email(invitation.email)
    assert created_user is not None
    assert created_user.email == invitation.email
    assert created_user.role == UserRole.SUPPORT_AGENT
    assert created_user.counterparty_id is None
    assert str(created_user.username) == "support_1"
    assert str(created_user.full_name) == "Support User"

    updated_invitation = await auth_service.invitation_repo.get_by_token(invitation.token)
    assert updated_invitation is not None
    assert updated_invitation.is_used is True


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(auth_client):
    """
    Проверяем endpoint логина: он должен вернуть 401, если email не найден в БД
    Данные: несуществующий email и любой пароль.
    """

    response = await auth_client.post(
        f"/api/v1/auth/login",
        data={
            "username": "missing-user@example.com",
            "password": "StrongPass123!",
        }
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "User not found by email" in data["error"]["message"]

@pytest.mark.asyncio
async def test_refresh_invalid_token_returns_401(auth_client):
    """
    Проверяем endpoint обновления токенов: он должен вернуть 401, если refresh token
    не валидный.
    Данные: невалидный refresh token.
    """

    response = await auth_client.post(
        f"/api/v1/auth/refresh",
        json={
            "refresh_token": "invalid-refresh-token",
        }
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"

@pytest.mark.asyncio
async def test_refresh_inactive_user_returns_401_and_revokes_token(auth_client, auth_service, counterparty_id):
    """
    Проверяем endpoint обновления токенов: он должен вернуть 401, если пользователь
    не активный, и при этом поместить refresh token в blacklist.
    Данные: неактивный пользователь в БД и валидный refresh token для него.
    """
    
    user = create_customer(
        email=f"inactive-{uuid4()}@example.com",
        password_hash=hash_password("StrongPass123!"),
        counterparty_id=counterparty_id,
        user_role=UserRole.CUSTOMER,
    )

    user.is_active = False

    await auth_service.user_repo.create(user)
    await auth_service.session.commit()

    tokens = create_tokens_for_user(user)
    refresh_payload = validate_token(tokens.refresh_token)

    response = await auth_client.post(
        f"/api/v1/auth/refresh",
        json={
            "refresh_token": tokens.refresh_token,
        }
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert data["error"]["message"] == "User is not active"

    assert await auth_service.blacklist.is_revoked(refresh_payload["jti"]) is True