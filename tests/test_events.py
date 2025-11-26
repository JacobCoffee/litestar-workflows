"""Tests for domain events."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest


@pytest.mark.unit
class TestWorkflowEvents:
    """Tests for workflow-level domain events."""

    def test_workflow_started_event(self) -> None:
        """Test WorkflowStarted event creation."""
        from litestar_workflows.core.events import WorkflowStarted

        instance_id = uuid4()
        timestamp = datetime.now(timezone.utc)
        workflow_name = "test_workflow"
        workflow_version = "1.0.0"

        event = WorkflowStarted(
            instance_id=instance_id,
            timestamp=timestamp,
            workflow_name=workflow_name,
            workflow_version=workflow_version,
        )

        assert event.instance_id == instance_id
        assert event.workflow_name == workflow_name
        assert event.workflow_version == workflow_version
        assert isinstance(event.timestamp, datetime)

    def test_workflow_completed_event(self) -> None:
        """Test WorkflowCompleted event creation."""
        from litestar_workflows.core.events import WorkflowCompleted

        instance_id = uuid4()
        timestamp = datetime.now(timezone.utc)
        status = "COMPLETED"

        event = WorkflowCompleted(
            instance_id=instance_id,
            timestamp=timestamp,
            status=status,
        )

        assert event.instance_id == instance_id
        assert event.status == status
        assert isinstance(event.timestamp, datetime)

    def test_workflow_failed_event(self) -> None:
        """Test WorkflowFailed event creation."""
        from litestar_workflows.core.events import WorkflowFailed

        instance_id = uuid4()
        timestamp = datetime.now(timezone.utc)
        error = "Test error message"

        event = WorkflowFailed(
            instance_id=instance_id,
            timestamp=timestamp,
            error=error,
            failed_step="failing_step",
        )

        assert event.instance_id == instance_id
        assert event.error == error
        assert event.failed_step == "failing_step"
        assert isinstance(event.timestamp, datetime)

    def test_workflow_canceled_event(self) -> None:
        """Test WorkflowCanceled event creation."""
        from litestar_workflows.core.events import WorkflowCanceled

        instance_id = uuid4()
        timestamp = datetime.now(timezone.utc)
        reason = "User cancellation"

        event = WorkflowCanceled(
            instance_id=instance_id,
            timestamp=timestamp,
            reason=reason,
            canceled_by="user123",
        )

        assert event.instance_id == instance_id
        assert event.reason == reason
        assert event.canceled_by == "user123"
        assert isinstance(event.timestamp, datetime)


@pytest.mark.unit
class TestStepEvents:
    """Tests for step-level domain events."""

    def test_step_started_event(self) -> None:
        """Test StepStarted event creation."""
        from litestar_workflows.core.events import StepStarted

        instance_id = uuid4()
        timestamp = datetime.now(timezone.utc)
        step_name = "test_step"
        step_type = "MACHINE"

        event = StepStarted(
            instance_id=instance_id,
            timestamp=timestamp,
            step_name=step_name,
            step_type=step_type,
        )

        assert event.instance_id == instance_id
        assert event.step_name == step_name
        assert event.step_type == step_type
        assert isinstance(event.timestamp, datetime)

    def test_step_completed_event(self) -> None:
        """Test StepCompleted event creation."""
        from litestar_workflows.core.events import StepCompleted

        instance_id = uuid4()
        timestamp = datetime.now(timezone.utc)
        step_name = "test_step"
        status = "SUCCEEDED"
        result = {"success": True}

        event = StepCompleted(
            instance_id=instance_id,
            timestamp=timestamp,
            step_name=step_name,
            status=status,
            result=result,
        )

        assert event.instance_id == instance_id
        assert event.step_name == step_name
        assert event.status == status
        assert event.result == result
        assert isinstance(event.timestamp, datetime)

    def test_step_failed_event(self) -> None:
        """Test StepFailed event creation."""
        from litestar_workflows.core.events import StepFailed

        instance_id = uuid4()
        timestamp = datetime.now(timezone.utc)
        step_name = "failing_step"
        error = "Step execution failed"

        event = StepFailed(
            instance_id=instance_id,
            timestamp=timestamp,
            step_name=step_name,
            error=error,
        )

        assert event.instance_id == instance_id
        assert event.step_name == step_name
        assert event.error == error
        assert isinstance(event.timestamp, datetime)

    def test_step_skipped_event(self) -> None:
        """Test StepSkipped event creation."""
        from litestar_workflows.core.events import StepSkipped

        instance_id = uuid4()
        timestamp = datetime.now(timezone.utc)
        step_name = "skipped_step"
        reason = "Guard condition failed"

        event = StepSkipped(
            instance_id=instance_id,
            timestamp=timestamp,
            step_name=step_name,
            reason=reason,
        )

        assert event.instance_id == instance_id
        assert event.step_name == step_name
        assert event.reason == reason
        assert isinstance(event.timestamp, datetime)


@pytest.mark.unit
class TestHumanTaskEvents:
    """Tests for human task-related events."""

    def test_human_task_created_event(self) -> None:
        """Test HumanTaskCreated event creation."""
        from litestar_workflows.core.events import HumanTaskCreated

        instance_id = uuid4()
        timestamp = datetime.now(timezone.utc)
        step_name = "approval_step"
        task_id = uuid4()

        event = HumanTaskCreated(
            instance_id=instance_id,
            timestamp=timestamp,
            step_name=step_name,
            task_id=task_id,
            assignee="user123",
        )

        assert event.instance_id == instance_id
        assert event.step_name == step_name
        assert event.task_id == task_id
        assert event.assignee == "user123"
        assert isinstance(event.timestamp, datetime)

    def test_human_task_completed_event(self) -> None:
        """Test HumanTaskCompleted event creation."""
        from litestar_workflows.core.events import HumanTaskCompleted

        task_id = uuid4()
        instance_id = uuid4()
        timestamp = datetime.now(timezone.utc)
        completed_by = "user456"
        form_data = {"approved": True, "comments": "Looks good"}

        event = HumanTaskCompleted(
            instance_id=instance_id,
            timestamp=timestamp,
            step_name="approval",
            task_id=task_id,
            completed_by=completed_by,
            form_data=form_data,
        )

        assert event.task_id == task_id
        assert event.instance_id == instance_id
        assert event.step_name == "approval"
        assert event.completed_by == completed_by
        assert event.form_data == form_data
        assert isinstance(event.timestamp, datetime)

    def test_human_task_reassigned_event(self) -> None:
        """Test HumanTaskReassigned event creation."""
        from litestar_workflows.core.events import HumanTaskReassigned

        instance_id = uuid4()
        timestamp = datetime.now(timezone.utc)
        task_id = uuid4()
        step_name = "approval"
        from_user = "user123"
        to_user = "user456"
        reason = "Vacation coverage"

        event = HumanTaskReassigned(
            instance_id=instance_id,
            timestamp=timestamp,
            step_name=step_name,
            task_id=task_id,
            from_assignee=from_user,
            to_assignee=to_user,
            reason=reason,
        )

        assert event.instance_id == instance_id
        assert event.step_name == step_name
        assert event.task_id == task_id
        assert event.from_assignee == from_user
        assert event.to_assignee == to_user
        assert event.reason == reason
        assert isinstance(event.timestamp, datetime)


@pytest.mark.unit
class TestEventAttributes:
    """Tests for event attribute consistency."""

    def test_all_events_have_timestamp(self) -> None:
        """Test that all events have timestamp attribute."""
        from litestar_workflows.core.events import (
            HumanTaskCompleted,
            HumanTaskCreated,
            StepCompleted,
            StepFailed,
            StepStarted,
            WorkflowCompleted,
            WorkflowStarted,
        )

        instance_id = uuid4()
        timestamp = datetime.now(timezone.utc)

        events = [
            WorkflowStarted(
                instance_id=instance_id,
                timestamp=timestamp,
                workflow_name="test",
                workflow_version="1.0.0",
            ),
            WorkflowCompleted(
                instance_id=instance_id,
                timestamp=timestamp,
                status="COMPLETED",
            ),
            StepStarted(
                instance_id=instance_id,
                timestamp=timestamp,
                step_name="test",
                step_type="MACHINE",
            ),
            StepCompleted(
                instance_id=instance_id,
                timestamp=timestamp,
                step_name="test",
                status="SUCCEEDED",
                result={},
            ),
            StepFailed(
                instance_id=instance_id,
                timestamp=timestamp,
                step_name="test",
                error="error",
            ),
            HumanTaskCreated(
                instance_id=instance_id,
                timestamp=timestamp,
                step_name="test",
                task_id=uuid4(),
                assignee="user",
            ),
            HumanTaskCompleted(
                instance_id=instance_id,
                timestamp=timestamp,
                step_name="test",
                task_id=uuid4(),
                completed_by="user",
                form_data={},
            ),
        ]

        for event in events:
            assert hasattr(event, "timestamp")
            assert isinstance(event.timestamp, datetime)

    def test_workflow_events_have_instance_id(self) -> None:
        """Test that workflow events have instance_id."""
        from litestar_workflows.core.events import WorkflowCompleted, WorkflowStarted

        instance_id = uuid4()
        timestamp = datetime.now(timezone.utc)

        events = [
            WorkflowStarted(
                instance_id=instance_id,
                timestamp=timestamp,
                workflow_name="test",
                workflow_version="1.0.0",
            ),
            WorkflowCompleted(
                instance_id=instance_id,
                timestamp=timestamp,
                status="COMPLETED",
            ),
        ]

        for event in events:
            assert hasattr(event, "instance_id")
            assert isinstance(event.instance_id, UUID)

    def test_step_events_have_step_name(self) -> None:
        """Test that step events have step_name."""
        from litestar_workflows.core.events import StepCompleted, StepFailed, StepStarted

        instance_id = uuid4()
        timestamp = datetime.now(timezone.utc)

        events = [
            StepStarted(
                instance_id=instance_id,
                timestamp=timestamp,
                step_name="test_step",
                step_type="MACHINE",
            ),
            StepCompleted(
                instance_id=instance_id,
                timestamp=timestamp,
                step_name="test_step",
                status="SUCCEEDED",
                result={},
            ),
            StepFailed(
                instance_id=instance_id,
                timestamp=timestamp,
                step_name="test_step",
                error="error",
            ),
        ]

        for event in events:
            assert hasattr(event, "step_name")
            assert event.step_name == "test_step"
