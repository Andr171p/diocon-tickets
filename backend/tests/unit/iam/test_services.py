from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from faker import Faker
from freezegun import freeze_time
from pydantic import SecretStr

from src.iam.domain.entities import Invitation, User
from src.iam.domain.exceptions import InvitationExpiredError, UnauthorizedError
from src.iam.domain.services import create_admin, create_customer, create_support, invite_customer
from src.iam.domain.vo import UserRole
from src.iam.schemas import Tokens, UserCreateForm
from src.iam.security import hash_password, validate_token
from src.iam.services import AuthService
from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError
from src.shared.utils.time import current_datetime

fake = Faker()


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_auth_service(mock_session, mock_user_repo, mock_invitation_repo):
    return AuthService(
        session=mock_session, user_repo=mock_user_repo, invitation_repo=mock_invitation_repo,
    )


@pytest.fixture
def sample_counterparty_id():
    return uuid4()


@pytest.fixture
def sample_password():
    return "StrongPass123!"


@pytest.fixture
def mock_invitation_for_customer(sample_counterparty_id):
    return invite_customer(
        invited_by=uuid4(),
        email="customer@emample.com",
        assigned_role=UserRole.CUSTOMER,
        counterparty_id=sample_counterparty_id,
    )


@pytest.fixture
def sample_form_data(sample_password):
    return UserCreateForm(
        username="customer1", full_name="Иванов Иван Иванович", password=sample_password,
    )


def generate_password_hash():
    return hash_password(
        fake.password(
            length=12,
            special_chars=True,
            digits=True,
            upper_case=True,
            lower_case=True,
        )
    )


def make_customer():
    return create_customer(
        email=fake.email(),
        password_hash=generate_password_hash(),
        username=fake.user_name(),
        full_name=fake.name(),
        counterparty_id=uuid4(),
        user_role=UserRole.CUSTOMER_ADMIN,
    )


def make_support():
    return create_support(
        email=fake.email(),
        password_hash=generate_password_hash(),
        full_name=fake.name(),
        user_role=UserRole.SUPPORT_MANAGER,
    )


def make_admin():
    return create_admin(email=fake.email(), password_hash=generate_password_hash())


class TestAuthServiceCreateTokensForUser:
    """Тесты для метода create_tokens_for_user"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("user", [make_support(), make_admin(), make_customer()])
    async def test_create_tokens_for_user(
            self, user, mock_auth_service, mock_user_repo
    ):
        # 1. Добавление пользователя в БД
        await mock_user_repo.create(user)

        # 2. Получение пары токенов
        tokens = await mock_auth_service.create_tokens_for_user(user)

        assert isinstance(tokens, Tokens)

        # 3. Валидация токенов для проверки claims
        access_payload = validate_token(tokens.access_token)
        refresh_payload = validate_token(tokens.refresh_token)

        # 4. Проверка access токена
        assert access_payload["sub"] == f"{user.id}"
        assert access_payload["type"] == "access"
        assert access_payload["email"] == user.email
        assert access_payload["role"] == user.role

        if user.counterparty_id is not None:
            assert "counterparty_id" in access_payload
            assert access_payload["counterparty_id"] == f"{user.counterparty_id}"

        # 4. Проверка refresh токена
        assert refresh_payload["sub"] == f"{user.id}"
        assert refresh_payload["type"] == "refresh"

        # 5. Проверка сохранённой информации о токене
        token_data = await mock_user_repo.get_token_data(tokens.refresh_token)

        assert token_data is not None
        assert token_data.token == tokens.refresh_token


class TestAuthServiceRegister:
    """Тесты для методы register (регистрация по приглашению)"""

    @pytest.mark.asyncio
    async def test_register_success_customer(
            self,
            mock_auth_service,
            mock_invitation_repo,
            mock_user_repo,
            mock_invitation_for_customer,
            sample_form_data,
    ):
        # 1. Сохранения приглашения
        invitation = await mock_invitation_repo.create(mock_invitation_for_customer)

        # 2. Регистрация по созданному приглашению
        tokens = await mock_auth_service.register(invitation.token, sample_form_data)

        # 3. Поиск зарегистрированного пользователя по email
        existing_user = await mock_user_repo.get_by_email(invitation.email)

        # 4. Поиск сохранённого токена
        token_data = await mock_user_repo.get_token_data(tokens.refresh_token)

        assert isinstance(tokens, Tokens)

        assert existing_user is not None
        assert existing_user.email == invitation.email
        assert token_data is not None
        assert token_data.token == tokens.refresh_token

    @pytest.mark.asyncio
    async def test_register_raises_invitation_not_found(self, mock_auth_service, sample_form_data):
        with pytest.raises(NotFoundError, match="Invitation not found"):
            await mock_auth_service.register("wrong-token", sample_form_data)

    @pytest.mark.asyncio
    async def test_register_raises_invitation_expired(
            self,
            mock_auth_service,
            mock_invitation_repo,
            mock_invitation_for_customer,
            sample_form_data,
    ):

        # 1. Сохранения приглашения
        invitation = await mock_invitation_repo.create(mock_invitation_for_customer)

        # 2. Прокрутка времени на 20 дней вперёд, чтобы приглашение истекло
        with (
            freeze_time(current_datetime() + timedelta(days=20)),
            pytest.raises(InvitationExpiredError)
        ):
            await mock_auth_service.register(invitation.token, sample_form_data)

    @pytest.mark.asyncio
    async def test_register_user_already_exists(
            self,
            mock_auth_service,
            mock_invitation_repo,
            mock_user_repo,
            mock_invitation_for_customer,
            sample_form_data,
            sample_counterparty_id,
    ):

        # 1. Создание и сохранение пользователя
        password = "StrongPass123!"
        user = create_customer(
            email="customer@emample.com",
            password_hash=hash_password(password),
            counterparty_id=sample_counterparty_id,
        )
        await mock_user_repo.create(user)

        # 2. Создание и сохранение приглашения (чтобы исключить ошибки с приглашением)
        invitation = await mock_invitation_repo.create(mock_invitation_for_customer)

        # 2. Попытка регистрации уже существующего пользователя
        with pytest.raises(AlreadyExistsError):
            await mock_auth_service.register(invitation.token, sample_form_data)


class TestAuthServiceAuthenticate:
    """Тесты для метода authenticate"""

    @pytest.mark.asyncio
    async def test_authenticate_success(
            self,
            sample_counterparty_id,
            sample_password,
            mock_user_repo,
            mock_auth_service,
    ):

        # 1. Сохранение пользователя на прямую в БД
        user = create_customer(
            email="customer@emample.com",
            password_hash=hash_password(sample_password),
            counterparty_id=sample_counterparty_id,
        )
        await mock_user_repo.create(user)

        # 2. Аутентификация пользователя
        tokens = await mock_auth_service.authenticate(user.email, sample_password)

        assert isinstance(tokens, Tokens)
