from uuid import uuid4

import pytest

from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.vo import UserRole
from src.tickets.domain.entities import Comment
from src.tickets.domain.vo import CommentType


@pytest.fixture
def author_id():
    return uuid4()


@pytest.fixture
def ticket_id():
    return uuid4()


@pytest.fixture
def sample_public_comment(author_id, ticket_id):
    return Comment(
        ticket_id=ticket_id,
        author_id=author_id,
        author_role=UserRole.SUPPORT_AGENT,
        text="Публичный комментарий",
        type=CommentType.PUBLIC,
    )


def test_comment_text_cannot_be_empty():
    with pytest.raises(ValueError, match="text cannot be empty"):
        Comment.create(
            ticket_id=uuid4(),
            author_id=uuid4(),
            author_role=UserRole.SUPPORT_AGENT,
            text="           ",
            comment_type=CommentType.PUBLIC,
        )


class TestCreate:
    """
    Тесты для создания комментария
    """

    @pytest.mark.parametrize(
        "comment_type", [CommentType.PUBLIC, CommentType.NOTE, CommentType.INTERNAL]
    )
    def test_support_create_all_comment_types_success(self, comment_type):
        ticket_id = uuid4()
        comment = Comment.create(
            ticket_id=ticket_id,
            author_id=uuid4(),
            author_role=UserRole.SUPPORT_AGENT,
            text="Тестовый комментарий",
            comment_type=comment_type,
        )

        assert comment.ticket_id == ticket_id

    @pytest.mark.parametrize("comment_type", [CommentType.INTERNAL, CommentType.NOTE])
    def test_customer_create_not_public_failed(self, comment_type):
        with pytest.raises(PermissionDeniedError, match="can only post PUBLIC comments"):
            Comment.create(
                ticket_id=uuid4(),
                author_id=uuid4(),
                author_role=UserRole.CUSTOMER_ADMIN,
                text="Какой-то комментарий",
                comment_type=comment_type,
            )

    def test_customer_create_public_success(self):
        ticket_id = uuid4()
        comment = Comment.create(
            ticket_id=ticket_id,
            author_id=uuid4(),
            author_role=UserRole.CUSTOMER,
            text="Тестовый комментарий",
            comment_type=CommentType.PUBLIC,
        )

        assert comment.ticket_id == ticket_id


class TestEdit:
    """
    Тестирование редактирования комментария
    """

    def test_edit_by_author_success(self, author_id, sample_public_comment):
        sample_public_comment.edit(new_text="Новый текст", edited_by=author_id)

        assert sample_public_comment.updated_at != sample_public_comment.created_at

    def test_cannot_edit_by_not_author(self, sample_public_comment):
        with pytest.raises(PermissionDeniedError, match="Only author can edit comment"):
            sample_public_comment.edit(new_text="Новый текст", edited_by=uuid4())

    def test_edit_to_empty_text(self, author_id, sample_public_comment):
        with pytest.raises(ValueError, match="text cannot be empty"):
            sample_public_comment.edit(new_text="   ", edited_by=author_id)
