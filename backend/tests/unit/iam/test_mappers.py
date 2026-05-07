from uuid import uuid4

from pydantic import SecretStr

from src.iam.domain.entities import Invitation, User
from src.iam.domain.vo import FullName, Username, UserRole
from src.iam.infra.models import InvitationOrm, UserOrm
from src.iam.infra.repos import InvitationMapper, UserMapper
from src.iam.mappers import map_invitation_to_response, map_user_to_response
from src.shared.utils.time import current_datetime


class TestUserMapper:
    """
    Тесты для маппинга доменной сущности User в ORM модель и обратно
    """

    def test_to_entity(self):
        """
        Проверяем ORM-маппер пользователя: он нужен, чтобы преобразовать
        UserOrm из БД в доменную сущность User.
        Данные: ORM-пользователь со всеми основными полями.
        """
        password_hash = "hashed_password"
        model = UserOrm(
            email="test@example.com",
            username="john_doe",
            full_name="John Doe",
            counterparty_id=uuid4(),
            role=UserRole.CUSTOMER,
            password_hash=password_hash,
            is_active=True,
        )

        entity = UserMapper.to_entity(model)

        assert entity.id == model.id
        assert entity.created_at == model.created_at
        assert entity.updated_at == model.updated_at
        assert entity.email == model.email
        assert entity.username == Username(model.username)
        assert entity.full_name == FullName(model.full_name)
        assert entity.avatar_url == model.avatar_url
        assert entity.counterparty_id == model.counterparty_id
        assert entity.role == model.role
        assert entity.password_hash.get_secret_value() == model.password_hash
        assert entity.is_active == model.is_active

    def test_to_entity_with_none_values(self):
        """
        Проверяем ORM-маппер пользователя: он должен корректно переносить
        nullable поля из UserOrm в доменную сущность.
        Данные: ORM-пользователь без username, full_name, avatar_url и counterparty_id.
        """
        password_hash = "hashed_password"
        model = UserOrm(
            email="test@example.com",
            username=None,
            full_name=None,
            avatar_url=None,
            counterparty_id=None,
            role=UserRole.SUPPORT_AGENT,
            password_hash=password_hash,
            is_active=True,
        )

        entity = UserMapper.to_entity(model)

        assert entity.username is None
        assert entity.full_name is None
        assert entity.avatar_url is None
        assert entity.counterparty_id is None

    def test_from_entity(self):
        """
        Проверяем ORM-маппер пользователя: он нужен, чтобы преобразовать
        доменную сущность User в UserOrm для сохранения в БД.
        Данные: доменный customer-пользователь со всеми основными полями.
        """
        entity = User(
            email="test@example.com",
            username=Username("john_doe"),
            full_name=FullName("John Doe"),
            avatar_url="https://example.com/avatar.jpg",
            counterparty_id=uuid4(),
            role=UserRole.CUSTOMER,
            password_hash=SecretStr("hashed_password"),
            is_active=True,
        )

        model = UserMapper.from_entity(entity)

        assert model.id == entity.id
        assert model.created_at == entity.created_at
        assert model.updated_at == entity.updated_at
        assert model.email == entity.email
        assert model.username == entity.username.value
        assert model.full_name == entity.full_name.value
        assert model.avatar_url == entity.avatar_url
        assert model.counterparty_id == entity.counterparty_id
        assert model.role == entity.role
        assert model.password_hash == entity.password_hash.get_secret_value()
        assert model.is_active == entity.is_active

    def test_from_entity_with_none_values(self):
        """
        Проверяем ORM-маппер пользователя: он должен корректно сохранять
        отсутствующие nullable поля как None.
        Данные: support-пользователь без username, full_name, avatar_url и counterparty_id.
        """
        entity = User(
            email="test@example.com",
            username=None,
            full_name=None,
            avatar_url=None,
            counterparty_id=None,
            role=UserRole.SUPPORT_AGENT,
            password_hash=SecretStr("hashed_password"),
            is_active=True,
        )

        model = UserMapper.from_entity(entity)

        assert model.username is None
        assert model.full_name is None
        assert model.avatar_url is None
        assert model.counterparty_id is None


class TestInvitationMapper:
    """
    Тесты для маппинга доменной модели приглашения в ORM и обратно
    """

    def test_to_entity(self):
        """
        Проверяем ORM-маппер приглашения: он нужен, чтобы преобразовать
        InvitationOrm из БД в доменную сущность Invitation.
        Данные: ORM-приглашение customer-пользователя.
        """
        token = "some-token"
        model = InvitationOrm(
            email="invitee@example.com",
            token=token,
            invited_by=uuid4(),
            assigned_role=UserRole.CUSTOMER,
            counterparty_id=uuid4(),
            expires_at=current_datetime(),
            used_at=None,
            is_used=False,
        )

        entity = InvitationMapper.to_entity(model)

        assert entity.id == model.id
        assert entity.created_at == model.created_at
        assert entity.updated_at == model.updated_at
        assert entity.email == model.email
        assert entity.token == model.token
        assert entity.invited_by == model.invited_by
        assert entity.assigned_role == model.assigned_role
        assert entity.counterparty_id == model.counterparty_id
        assert entity.expires_at == model.expires_at
        assert entity.used_at == model.used_at
        assert entity.is_used == model.is_used

    def test_from_entity(self):
        """
        Проверяем ORM-маппер приглашения: он нужен, чтобы преобразовать
        доменную сущность Invitation в InvitationOrm для сохранения в БД.
        Данные: доменное приглашение customer_admin-пользователя.
        """
        token = "some-token"
        entity = Invitation(
            email="invitee@example.com",
            token=token,
            invited_by=uuid4(),
            assigned_role=UserRole.CUSTOMER_ADMIN,
            counterparty_id=uuid4(),
            expires_at=current_datetime(),
            used_at=None,
            is_used=False,
        )

        model = InvitationMapper.from_entity(entity)

        assert model.id == entity.id
        assert model.created_at == entity.created_at
        assert model.updated_at == entity.updated_at
        assert model.email == entity.email
        assert model.token == entity.token
        assert model.invited_by == entity.invited_by
        assert model.assigned_role == entity.assigned_role
        assert model.counterparty_id == entity.counterparty_id
        assert model.expires_at == entity.expires_at
        assert model.used_at == entity.used_at
        assert model.is_used == entity.is_used


class TestUserResponseMapper:
    def test_map_user_to_response(self):
        """
        Проверяем API-маппер пользователя: он нужен, чтобы роутеры отдавали наружу
        безопасную response-схему, а не доменную сущность с лишними полями.
        Данные: support-пользователь со всеми необязательными полями.
        """
        user = User(
            email="support@example.com",
            username=Username("support_user"),
            full_name=FullName("Support User"),
            avatar_url="https://example.com/avatar.jpg",
            role=UserRole.SUPPORT_AGENT,
            password_hash=SecretStr("hashed_password"),
            is_active=True,
        )

        response = map_user_to_response(user)

        assert response.id == user.id
        assert response.created_at == user.created_at
        assert response.updated_at == user.updated_at
        assert response.email == user.email
        assert response.username == user.username.value
        assert response.full_name == user.full_name.value
        assert response.avatar_url == user.avatar_url
        assert response.role == user.role
        assert response.counterparty_id == user.counterparty_id
        assert response.is_active == user.is_active


class TestInvitationResponseMapper:
    def test_map_invitation_to_response(self):
        """
        Проверяем API-маппер приглашения: он нужен для endpoint-ов приглашений,
        чтобы клиент получил только поля из InvitationResponse.
        Данные: неиспользованное приглашение для сотрудника поддержки.
        """
        invitation = Invitation(
            email="invitee@example.com",
            invited_by=uuid4(),
            assigned_role=UserRole.SUPPORT_MANAGER,
            expires_at=current_datetime(),
            used_at=None,
            is_used=False,
        )

        response = map_invitation_to_response(invitation)

        assert response.id == invitation.id
        assert response.created_at == invitation.created_at
        assert response.invited_by == invitation.invited_by
        assert response.email == invitation.email
        assert response.assigned_role == invitation.assigned_role
        assert response.counterparty_id == invitation.counterparty_id
        assert response.expires_at == invitation.expires_at
        assert response.used_at == invitation.used_at
        assert response.is_used == invitation.is_used
