from uuid import uuid4

import pytest

from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.vo import UserRole
from src.tickets.domain.entities import Reaction
from src.tickets.domain.vo import ReactionType


@pytest.mark.parametrize("reaction_type", list(ReactionType))
def test_support_create_any_reaction_success(reaction_type):
    """
    Сотрудник поддержки может создавать реакции с любым типом
    """

    reaction = Reaction.create(
        comment_id=uuid4(),
        author_id=uuid4(),
        author_role=UserRole.SUPPORT_AGENT,
        reaction_type=ReactionType(reaction_type),
    )

    assert reaction.reaction_type == reaction_type


@pytest.mark.parametrize("author_role", [UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN])
def test_customers_cannot_create_in_progress_reaction(author_role):
    """
    Клиенты не могут ставить реакции 'in_progress'
    """

    with pytest.raises(PermissionDeniedError, match="Customers cannot set 'In Progress' reaction"):
        Reaction.create(
            comment_id=uuid4(),
            author_id=uuid4(),
            author_role=author_role,
            reaction_type=ReactionType.IN_PROGRESS,
        )
