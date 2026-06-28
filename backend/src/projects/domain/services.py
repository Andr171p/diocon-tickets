import random
import string
from uuid import UUID

from src.iam.domain.authz import Subject

from .entities import Project, ProjectMember
from .vo import ProjectKey, ProjectRole


def generate_key_suggestions(
        original_key: str,
        *,
        max_attempts: int = 5,
        min_key_length: int = 3
) -> list[str]:
    """
    Генерирует альтернативные ключи проекта на основе заданного ключа.
    Использовать для разрешения конфликтов уникальности.
    """

    base_key = original_key.strip().upper()

    if not base_key:
        base_key = "PROJ"  # fallback

    suggestions = [f"{base_key}{i}" for i in range(1, max_attempts + 1)]

    if len(base_key) <= min_key_length:
        suggestions.extend(
            f"{base_key}{letter}"
            for letter in random.sample(
                string.ascii_uppercase,
                len(string.ascii_uppercase),
            )
        )

    seen = set()
    result = []

    for key in suggestions:
        if key not in seen:
            seen.add(key)
            result.append(key)

    return result[: max_attempts * 2]


def create_project(
        *,
        name: str,
        key: ProjectKey,
        description: str | None,
        counterparty_id: UUID,
        creator: Subject,
) -> tuple[Project, ProjectMember]:
    """
    Создаёт новый проект вместе с владельцем.
    """

    project = Project.create(
        name=name,
        key=key,
        description=description,
        counterparty_id=counterparty_id,
        created_by=creator.id
    )
    owner = project.create_member(
        user_id=creator.id,
        project_roles=[ProjectRole.OWNER],
        created_by=creator.id
    )

    return project, owner
