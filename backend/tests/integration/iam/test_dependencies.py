import asyncio
import json
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import Depends, FastAPI, WebSocket
from fastapi.testclient import TestClient
from redis import Redis as SyncRedis
from redis.asyncio import Redis
from starlette.websockets import WebSocketDisconnect

from src.core.settings import settings
from src.iam.dependencies import (
    get_auth_service,
    get_current_customer_admin,
    get_current_support_user,
    get_current_user,
    get_current_user_ws,
    get_invitation_repo,
    get_invitation_service,
    get_mail_sender,
    get_token_blacklist,
    get_user_repo,
    require_role,
)
from src.iam.domain.exceptions import PermissionDeniedError, UnauthorizedError
from src.iam.domain.vo import UserRole
from src.iam.infra.blacklist import RedisTokenBlacklist
from src.iam.infra.repos import SqlInvitationRepository, SqlUserRepository
from src.iam.schemas import CurrentUser
from src.iam.security import create_access_token, validate_token
from src.iam.services import AuthService, InvitationService

WS_POLICY_VIOLATION_CODE = 1008


@pytest.fixture
async def redis_client(redis_url):
    client = Redis.from_url(redis_url, decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


@pytest.fixture
def redis_token_blacklist(redis_client):
    return RedisTokenBlacklist(redis_client)


def test_get_user_repo_returns_sql_user_repo(session):
    """
    Проверяем DI-функцию get_user_repo: она нужна, чтобы FastAPI получил
    SQL-репозиторий пользователей с текущей сессией БД.
    Данные: реальная AsyncSession из integration fixture.
    """
    repo = get_user_repo(session)

    assert isinstance(repo, SqlUserRepository)
    assert repo.session is session


def test_get_invitation_repo_returns_sql_invitation_repo(session):
    """
    Проверяем DI-функцию get_invitation_repo: она нужна, чтобы FastAPI получил
    SQL-репозиторий приглашений с текущей сессией БД.
    Данные: реальная AsyncSession из integration fixture.
    """
    repo = get_invitation_repo(session)

    assert isinstance(repo, SqlInvitationRepository)
    assert repo.session is session


def test_get_token_blacklist_returns_redis_blacklist():
    """
    Проверяем DI-функцию get_token_blacklist: она нужна, чтобы auth-слой
    использовал RedisTokenBlacklist.
    Данные: настройки Redis из приложения.
    """
    blacklist = get_token_blacklist()

    assert isinstance(blacklist, RedisTokenBlacklist)


def test_get_auth_service_wires_dependencies(session, redis_token_blacklist):
    """
    Проверяем DI-функцию get_auth_service: она нужна, чтобы собрать AuthService
    из сессии, user_repo, invitation_repo и blacklist.
    Данные: реальные SQL-репозитории и RedisTokenBlacklist.
    """
    user_repo = get_user_repo(session)
    invitation_repo = get_invitation_repo(session)

    service = get_auth_service(
        session=session,
        user_repo=user_repo,
        invitation_repo=invitation_repo,
        blacklist=redis_token_blacklist,
    )

    assert isinstance(service, AuthService)
    assert service.session is session
    assert isinstance(service.user_repo, SqlUserRepository)
    assert isinstance(service.invitation_repo, SqlInvitationRepository)
    assert isinstance(service.blacklist, RedisTokenBlacklist)




def test_get_mail_sender_returns_smtp_sender():
    """
    Проверяем DI-функцию get_mail_sender: она нужна, чтобы сервис приглашений
    получил настроенный SMTP sender.
    Данные: mail-настройки приложения.
    """
    sender = get_mail_sender()

    assert sender.smtp_config["hostname"]
    assert sender.smtp_config["port"] > 0


def test_get_invitation_service_wires_dependencies(session):
    """
    Проверяем DI-функцию get_invitation_service: она нужна, чтобы собрать
    InvitationService из сессии, репозитория и mail sender.
    Данные: SQL-репозиторий приглашений и SMTP sender.
    """
    invitation_repo = get_invitation_repo(session)
    sender = get_mail_sender()

    service = get_invitation_service(
        session=session,
        repository=invitation_repo,
        mail_sender=sender,
    )

    assert isinstance(service, InvitationService)
    assert service.session is session
    assert isinstance(service.repository, SqlInvitationRepository)
    assert service.mail_sender is sender


@pytest.mark.asyncio
async def test_get_current_user_success(redis_token_blacklist):
    """
    Проверяем get_current_user: он нужен, чтобы извлечь текущего пользователя
    из валидного access token.
    Данные: access token с user_id, email, role и counterparty_id.
    """
    token = create_access_token(
        user_id=uuid4(),
        email="user@example.com",
        user_role=UserRole.CUSTOMER,
        counterparty_id=uuid4(),
    )

    result = await get_current_user(token, redis_token_blacklist)
    payload = validate_token(token)

    assert str(result.user_id) == payload["sub"]
    assert result.email == payload["email"]
    assert result.role == payload["role"]
    assert str(result.counterparty_id) == payload["counterparty_id"]


@pytest.mark.asyncio
async def test_get_current_user_raises_when_jti_missing(redis_token_blacklist):
    """
    Проверяем get_current_user: он должен отказать, если в token нет jti.
    Данные: вручную созданный access token без jti claim.
    """
    payload = {
        "sub": str(uuid4()),
        "exp": 9999999999,
        "iat": 1000000000,
        "type": "access",
        "email": "user@example.com",
        "role": UserRole.CUSTOMER.value,
    }
    token = jwt.encode(payload=payload, key=settings.secret_key, algorithm=settings.jwt.algorithm)

    with pytest.raises(UnauthorizedError, match="revoked or missing jti"):
        await get_current_user(token, redis_token_blacklist)


@pytest.mark.asyncio
async def test_get_current_user_raises_when_revoked(redis_token_blacklist):
    """
    Проверяем get_current_user: он должен отказать, если token уже отозван.
    Данные: валидный access token, чей jti добавлен в Redis blacklist.
    """
    token = create_access_token(
        user_id=uuid4(),
        email="user@example.com",
        user_role=UserRole.CUSTOMER,
        counterparty_id=uuid4(),
    )
    payload = validate_token(token)
    await redis_token_blacklist.revoke(
        payload["jti"],
        user_id=UUID(payload["sub"]),
        exp=int(payload["exp"]),
        reason="test_revoke",
    )

    with pytest.raises(UnauthorizedError, match="revoked or missing jti"):
        await get_current_user(token, redis_token_blacklist)


@pytest.mark.asyncio
async def test_get_current_user_raises_when_sub_missing(redis_token_blacklist):
    """
    Проверяем get_current_user: он должен отказать, если в token нет sub.
    Данные: вручную созданный access token без sub claim.
    """
    payload = {
        "jti": str(uuid4()),
        "exp": 9999999999,
        "iat": 1000000000,
        "type": "access",
        "email": "user@example.com",
        "role": UserRole.CUSTOMER.value,
    }
    token = jwt.encode(payload=payload, key=settings.secret_key, algorithm=settings.jwt.algorithm)

    with pytest.raises(UnauthorizedError, match="missing sub claim"):
        await get_current_user(token, redis_token_blacklist)


def test_require_role_allows_user_with_allowed_role(current_admin_user):
    """
    Проверяем require_role: он нужен, чтобы пропустить пользователя
    с одной из разрешённых ролей.
    Данные: current_admin_user и набор ролей ADMIN/SUPPORT_MANAGER.
    """
    checker = require_role(UserRole.ADMIN, UserRole.SUPPORT_MANAGER)

    result = checker(current_admin_user)

    assert result is current_admin_user


def test_require_role_denies_user_with_not_allowed_role():
    """
    Проверяем require_role: он должен запретить доступ пользователю
    без нужной роли.
    Данные: customer-пользователь и требование роли ADMIN.
    """
    checker = require_role(UserRole.ADMIN)
    user = CurrentUser(
        user_id=uuid4(),
        email="customer@example.com",
        role=UserRole.CUSTOMER,
        counterparty_id=None,
    )

    with pytest.raises(PermissionDeniedError, match="Insufficient permissions"):
        checker(user)


def test_get_current_support_user_allows_support_roles():
    """
    Проверяем get_current_support_user: он нужен, чтобы пропустить
    пользователя из support-команды.
    Данные: CurrentUser с ролью SUPPORT_AGENT.
    """
    user = CurrentUser(
        user_id=uuid4(),
        email="agent@example.com",
        role=UserRole.SUPPORT_AGENT,
        counterparty_id=None,
    )

    result = get_current_support_user(user)

    assert result is user


def test_get_current_support_user_denies_customer():
    """
    Проверяем get_current_support_user: он должен запретить доступ customer.
    Данные: CurrentUser с ролью CUSTOMER.
    """
    user = CurrentUser(
        user_id=uuid4(),
        email="customer@example.com",
        role=UserRole.CUSTOMER,
        counterparty_id=None,
    )

    with pytest.raises(PermissionDeniedError, match="support staff only"):
        get_current_support_user(user)


def test_get_current_customer_admin_allows_customer_admin():
    """
    Проверяем get_current_customer_admin: он нужен, чтобы пропустить
    customer_admin пользователя.
    Данные: CurrentUser с ролью CUSTOMER_ADMIN.
    """
    user = CurrentUser(
        user_id=uuid4(),
        email="ca@example.com",
        role=UserRole.CUSTOMER_ADMIN,
        counterparty_id=None,
    )

    result = get_current_customer_admin(user)

    assert result is user


def test_get_current_customer_admin_denies_customer():
    """
    Проверяем get_current_customer_admin: он должен запретить доступ
    обычному customer.
    Данные: CurrentUser с ролью CUSTOMER.
    """
    user = CurrentUser(
        user_id=uuid4(),
        email="customer@example.com",
        role=UserRole.CUSTOMER,
        counterparty_id=None,
    )

    with pytest.raises(PermissionDeniedError, match="customer admin or higher"):
        get_current_customer_admin(user)


@pytest.fixture
def ws_app(redis_url):
    app = FastAPI()
    ws_redis = Redis.from_url(redis_url, decode_responses=True)
    ws_blacklist = RedisTokenBlacklist(ws_redis)

    @app.websocket("/ws")
    async def websocket_endpoint(
        websocket: WebSocket,
        current_user: CurrentUser | None = Depends(get_current_user_ws),
    ):
        if current_user is None:
            return

        await websocket.accept()
        await websocket.send_json(
            {
                "user_id": str(current_user.user_id),
                "email": current_user.email,
                "role": current_user.role,
            }
        )
        await websocket.close()

    app.dependency_overrides[get_token_blacklist] = lambda: ws_blacklist
    return app


def test_get_current_user_ws_returns_none_and_closes_when_missing_token(ws_app):
    """
    Проверяем WebSocket-аутентификацию: соединение должно закрыться,
    если token не передан.
    Данные: тестовое FastAPI WebSocket-приложение без query token.
    """
    with (
        TestClient(ws_app) as client,
        pytest.raises(WebSocketDisconnect) as exc_info,
        client.websocket_connect("/ws") as ws,
    ):
        ws.receive_text()

    assert exc_info.value.code == WS_POLICY_VIOLATION_CODE


def test_get_current_user_ws_returns_none_and_closes_when_revoked(ws_app, redis_url):
    """
    Проверяем WebSocket-аутентификацию: соединение должно закрыться,
    если token отозван.
    Данные: access token, чей jti вручную записан в Redis blacklist.
    """
    token = create_access_token(
        user_id=uuid4(),
        email="user@example.com",
        user_role=UserRole.SUPPORT_AGENT,
    )
    payload = validate_token(token)
    sync_redis = SyncRedis.from_url(redis_url, decode_responses=True)
    sync_redis.setex(
        f"blacklist:jti:{payload['jti']}",
        3600,
        json.dumps(
            {
                "revoked_at": 0,
                "user_id": str(UUID(payload["sub"])),
                "reason": "test_ws_revoke",
            }
        ),
    )

    with (
        TestClient(ws_app) as client,
        pytest.raises(WebSocketDisconnect) as exc_info,
        client.websocket_connect(f"/ws?token={token}") as ws,
    ):
        ws.receive_text()

    assert exc_info.value.code == WS_POLICY_VIOLATION_CODE


def test_get_current_user_ws_success(ws_app):
    """
    Проверяем WebSocket-аутентификацию: она нужна, чтобы пропустить
    пользователя с валидным token и отдать его данные.
    Данные: валидный access token support-пользователя.
    """
    token = create_access_token(
        user_id=uuid4(),
        email="user@example.com",
        user_role=UserRole.SUPPORT_AGENT,
    )
    payload = validate_token(token)

    with TestClient(ws_app) as client, client.websocket_connect(f"/ws?token={token}") as ws:
        data = ws.receive_json()

    assert data["user_id"] == payload["sub"]
    assert data["email"] == payload["email"]
    assert data["role"] == payload["role"]
