from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from src.shared.domain.exceptions import InvalidStateError, InvariantViolationError
from src.shared.utils.time import current_datetime
from src.timetracking.domain.entities import Worklog
from src.timetracking.domain.vo import WorklogStatus


@pytest.fixture
def worklog_factory():

    def make_worklog(**kwargs):
        return Worklog(
            timesheet_id=kwargs.pop("timesheet_id", None),
            ticket_id=kwargs.pop("ticket_id", uuid4()),
            task_id=kwargs.pop("task_id", uuid4()),
            user_id=kwargs.pop("author_id", uuid4()),
            hours_spent=kwargs.pop("hours_spent", Decimal(1)),
            entry_date=kwargs.pop("entry_date", current_datetime().date()),
            description=kwargs.pop("description", None),
            status=kwargs.pop("status", WorklogStatus.DRAFT),
            approved_by=kwargs.pop("submitted_by", None),
            approved_at=kwargs.pop("approved_at", None),
            rejection_reason=kwargs.pop("rejection_reason", None),
        )

    return make_worklog


class TestInvariants:
    """Проверки инвариантов"""

    def test_hours_spent_must_be_positive(self):
        with pytest.raises(ValueError, match="Hours spent must be positive"):
            Worklog(
                task_id=uuid4(),
                user_id=uuid4(),
                hours_spent=Decimal("-0.01"),
                entry_date=current_datetime().date(),
                status=WorklogStatus.DRAFT,
            )

    def test_worklog_must_be_linked_to_ticket_or_task(self):
        with pytest.raises(InvariantViolationError):
            Worklog(
                user_id=uuid4(),
                hours_spent=Decimal("0.5"),
                entry_date=current_datetime().date(),
                status=WorklogStatus.DRAFT
            )


def test_log_time_should_set_status_to_draft():
    """При создании записи должен устанавливаться статус - DRAFT"""

    worklog = Worklog.log_time(
        user_id=uuid4(),
        hours_spent=Decimal(2),
        entry_date=current_datetime().date(),
        ticket_id=uuid4(),
    )
    assert worklog.status == WorklogStatus.DRAFT


class TestSubmit:

    def test_submit_success(self, worklog_factory):
        worklog = worklog_factory()
        worklog.submit()
        assert worklog.status == WorklogStatus.SUBMITTED
        assert worklog.updated_at > worklog.created_at

    @pytest.mark.parametrize(
        "wrong_status", [WorklogStatus.SUBMITTED, WorklogStatus.APPROVED, WorklogStatus.REJECTED]
    )
    def test_submit_failed_when_wrong_status(self, wrong_status, worklog_factory):
        worklog = worklog_factory(status=wrong_status)

        with pytest.raises(InvalidStateError, match="Only draft worklogs can be submitted"):
            worklog.submit()


class TestApprove:

    def test_approve_success(self, worklog_factory):
        worklog = worklog_factory(status=WorklogStatus.SUBMITTED)
        approved_by = uuid4()
        old_updated_at = worklog.updated_at
        worklog.approve(approved_by=approved_by)

        assert worklog.status == WorklogStatus.APPROVED
        assert worklog.approved_at is not None
        assert worklog.approved_by == approved_by
        assert worklog.updated_at > old_updated_at

    @pytest.mark.parametrize(
        "wrong_status", [WorklogStatus.DRAFT, WorklogStatus.APPROVED, WorklogStatus.REJECTED]
    )
    def test_failed_when_not_submitted_status(self, wrong_status, worklog_factory):
        worklog = worklog_factory(status=wrong_status)

        with pytest.raises(InvalidStateError, match="Only submitted worklogs can be approved"):
            worklog.approve(approved_by=uuid4())

        assert worklog.approved_at is None
        assert worklog.approved_by is None


class TestReject:

    def test_reject_success(self, worklog_factory):
        worklog = worklog_factory(status=WorklogStatus.SUBMITTED)
        old_updated_at = worklog.updated_at
        rejected_by = uuid4()
        reason = "Херня переделывай"
        worklog.reject(rejected_by=rejected_by, reason=reason)

        assert worklog.status == WorklogStatus.REJECTED
        assert worklog.rejection_reason == reason
        assert worklog.updated_at > old_updated_at

    @pytest.mark.parametrize(
        "wrong_status", [WorklogStatus.DRAFT, WorklogStatus.APPROVED, WorklogStatus.REJECTED]
    )
    def test_failed_when_not_submitted_status(self, wrong_status, worklog_factory):
        worklog = worklog_factory(status=wrong_status)

        with pytest.raises(InvalidStateError, match="Only submitted entries can be rejected"):
            worklog.reject(rejected_by=uuid4(), reason="Херня переделывай")


class TestEdit:

    def test_edit_all_possible_fields(self, worklog_factory):
        worklog = worklog_factory(
            status=WorklogStatus.DRAFT,
            hours_spent=Decimal("2.2"),
            entry_date=current_datetime().date(),
            description="Test description",
        )
        old_updated_at = worklog.updated_at

        new_hours_spent = Decimal("0.5")
        new_entry_date = current_datetime().date() + timedelta(days=3)
        new_description = "  New test description  "
        worklog.edit(
            hours_spent=new_hours_spent,
            entry_date=new_entry_date,
            description=new_description,
        )

        assert worklog.updated_at > old_updated_at
        assert worklog.hours_spent == new_hours_spent
        assert worklog.entry_date == new_entry_date
        assert worklog.description == new_description.strip()

    @pytest.mark.parametrize(
        "not_editable_status", [status for status in WorklogStatus if not status.is_editable]
    )
    def test_failed_when_not_editable_status(self, not_editable_status, worklog_factory):
        worklog = worklog_factory(status=not_editable_status)

        with pytest.raises(InvalidStateError, match="in non editable status"):
            worklog.edit(hours_spent=Decimal("0.1"))

    @pytest.mark.parametrize(
        "non_positive_hours_spent", [Decimal("-0.1"), Decimal(0), Decimal(-2)]
    )
    def test_failed_when_non_positive_hours_spent(self, non_positive_hours_spent, worklog_factory):
        worklog = worklog_factory()

        with pytest.raises(ValueError, match="Hours spent must be positive"):
            worklog.edit(hours_spent=non_positive_hours_spent)

    def test_edit_do_nothing_when_empty_description(self, worklog_factory):
        old_description = "Some description"
        worklog = worklog_factory(description=old_description)
        old_updated_at = worklog.updated_at
        worklog.edit(description="     ")

        assert worklog.description == old_description
        assert worklog.updated_at == old_updated_at

    def test_new_value_not_set_when_null_provided(self, worklog_factory):
        old_hours_spent = Decimal(5)
        worklog = worklog_factory(hours_spent=old_hours_spent)
        old_updated_at = worklog.updated_at
        worklog.edit(hours_spent=None)

        assert worklog.hours_spent == old_hours_spent
        assert worklog.updated_at == old_updated_at


class TestAssignToTimesheet:

    def test_assign_to_timesheet_success(self, worklog_factory):
        worklog = worklog_factory()
        old_updated_at = worklog.updated_at
        timesheet_id = uuid4()
        worklog.assign_to_timesheet(timesheet_id)

        assert worklog.timesheet_id == timesheet_id
        assert worklog.updated_at > old_updated_at

    def test_failed_when_already_assigned(self, worklog_factory):
        worklog = worklog_factory(timesheet_id=uuid4())

        with pytest.raises(InvariantViolationError, match="is already assigned to timesheet"):
            worklog.assign_to_timesheet(timesheet_id=uuid4())


class TestRemove:

    @pytest.mark.parametrize("status", [WorklogStatus.DRAFT, WorklogStatus.REJECTED])
    def test_remove_success(self, status, worklog_factory):
        worklog = worklog_factory(status=status)
        worklog.remove(deleted_by=uuid4())
        assert worklog.deleted_at is not None
        assert worklog.is_deleted is True

    @pytest.mark.parametrize("wrong_status", [WorklogStatus.SUBMITTED, WorklogStatus.APPROVED])
    def test_failed_when_wrong_status(self, wrong_status, worklog_factory):
        worklog = worklog_factory(status=wrong_status)

        with pytest.raises(InvalidStateError, match="Can only delete DRAFT or REJECTED worklog"):
            worklog.remove(deleted_by=uuid4())

    def test_failed_when_already_assigned(self, worklog_factory):
        worklog = worklog_factory(timesheet_id=uuid4())

        with pytest.raises(InvalidStateError, match="already assigned to timesheet"):
            worklog.remove(deleted_by=uuid4())
