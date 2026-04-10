import re
from uuid import UUID

from ...iam.domain.vo import UserRole
from .repos import ProjectRepository
from .vo import ProjectRole

WORDS_COUNT = 2
MIN_KEY_LENGTH = 2
MAX_KEY_LENGTH = 10


def generate_project_key(name: str, default: str = "PRJ") -> str:
    """
    Генерирует предложение ключа проекта на основе его имени.

    Алгоритм:
     1. Оставляем только буквы (латиница, кириллица) и пробелы.
     2. Приводим к верхнему регистру.
     3. Берём первые буквы от первых 1-3 слов, если слов несколько.
     4. Если получилось слишком коротко (<2) – берём первые 2-4 буквы первого слова.
     5. Обрезаем до 10 символов.
     6. Если результат всё ещё пуст – возвращаем default.
    """

    if not name:
        return default

    # 1. Только буквы и пробелы (удаление цифр, знаков, эмодзи)
    cleaned = re.sub(r"[^A-Za-zА-Яа-яЁё\s]", "", name)
    cleaned = cleaned.upper()

    # 2. Разбиение на слова
    words = cleaned.split()
    if not words:
        return default

    # 3. Генерация ключа
    key = "".join(word[0] for word in words[:3]) if len(words) > WORDS_COUNT else words[0][:4]

    # 4. Обеспечение минимальной длины (2 символа)
    if len(key) < MIN_KEY_LENGTH:
        key = (key + key).ljust(2, "X")[:2]  # "А" -> "АА" или "АX"

    # 5. Обрезание до максимальной длины (10 символов)
    key = key[:10]

    # 6. Дополнительная проверка, что первый символ является буквой
    if not key[0].isalpha():
        key = "P" + key[1:] if len(key) > 1 else "PR"

    return key


class ProjectAccessService:
    def __init__(self, repository: ProjectRepository) -> None:
        self.repository = repository

    async def can_create_ticket(
            self, project_id: UUID, user_id: UUID, user_role: UserRole
    ) -> bool:
        """Может ли пользователь создать тикет"""

        # 1. Администраторы и менеджеры могут создавать тикеты в любом проекте
        if user_role in {UserRole.ADMIN, UserRole.SUPPORT_MANAGER}:
            return True

        # 2. Проверка состояние в проекте
        membership = await self.repository.get_membership(project_id, user_id)
        if membership is None or not membership.is_active:
            return False

        # 3. Разрешение на создание тикетов только для следующих ролей внутри проекта
        return membership.project_role in {
            ProjectRole.OWNER,
            ProjectRole.MANAGER,
            ProjectRole.MEMBER,
            ProjectRole.CUSTOMER,
            ProjectRole.CUSTOMER_ADMIN,
        }

    async def can_view_ticket(self, project_id: UUID, user_id: UUID, user_role: UserRole) -> bool:
        """Может ли пользователь просматривать тикеты проекта"""

        # 1. Администраторы и менеджеры могут просматривать тикеты любого проекта
        if user_role in {UserRole.ADMIN, UserRole.SUPPORT_MANAGER}:
            return True

        # 2. Участник должен быть активен
        membership = await self.repository.get_membership(project_id, user_id)
        return not (membership is None or not membership.is_active)

    async def can_assign_ticket(
            self, project_id: UUID, user_id: UUID, user_role: UserRole
    ) -> bool:
        """Может ли пользователь назначать исполнителя тикета"""

        if user_role in {UserRole.ADMIN, UserRole.SUPPORT_MANAGER}:
            return True

        membership = await self.repository.get_membership(project_id, user_id)
        if not membership or not membership.is_active:
            return False

        # Назначать могут только Owner и Manager проекта
        return membership.project_role in {ProjectRole.OWNER, ProjectRole.MANAGER}

    async def can_change_status(
        self, project_id: UUID, user_id: UUID, user_role: UserRole
    ) -> bool:
        """Может ли пользователь менять статус тикета"""

        if user_role in {UserRole.ADMIN, UserRole.SUPPORT_MANAGER}:
            return True

        membership = await self.repository.get_membership(project_id, user_id)
        if not membership or not membership.is_active:
            return False

        allowed_roles = {ProjectRole.OWNER, ProjectRole.MANAGER, ProjectRole.MEMBER}

        # Клиенты могут менять статус только в ограниченных случаях (например, переоткрывать)
        if membership.project_role in {ProjectRole.CUSTOMER, ProjectRole.CUSTOMER_ADMIN}:
            return False  # или добавить свою логику

        return membership.project_role in allowed_roles
