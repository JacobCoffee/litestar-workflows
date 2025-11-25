"""Tests for type definitions and enums."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest


@pytest.mark.unit
class TestStepType:
    """Tests for StepType enum."""

    def test_step_type_values(self) -> None:
        """Test StepType enum has expected values."""
        from litestar_workflows.core.types import StepType

        assert StepType.MACHINE == "machine"
        assert StepType.HUMAN == "human"
        assert StepType.WEBHOOK == "webhook"
        assert StepType.TIMER == "timer"
        assert StepType.GATEWAY == "gateway"

    def test_step_type_members(self) -> None:
        """Test StepType enum has all expected members."""
        from litestar_workflows.core.types import StepType

        assert len(StepType) == 5
        assert set(StepType) == {
            StepType.MACHINE,
            StepType.HUMAN,
            StepType.WEBHOOK,
            StepType.TIMER,
            StepType.GATEWAY,
        }

    def test_step_type_string_conversion(self) -> None:
        """Test StepType can be converted to string."""
        from litestar_workflows.core.types import StepType

        assert str(StepType.MACHINE) == "machine"
        assert str(StepType.HUMAN) == "human"

    def test_step_type_comparison(self) -> None:
        """Test StepType enum equality."""
        from litestar_workflows.core.types import StepType

        assert StepType.MACHINE == StepType.MACHINE
        assert StepType.MACHINE != StepType.HUMAN


@pytest.mark.unit
class TestStepStatus:
    """Tests for StepStatus enum."""

    def test_step_status_values(self) -> None:
        """Test StepStatus enum has expected values."""
        from litestar_workflows.core.types import StepStatus

        assert StepStatus.PENDING == "pending"
        assert StepStatus.SCHEDULED == "scheduled"
        assert StepStatus.RUNNING == "running"
        assert StepStatus.WAITING == "waiting"
        assert StepStatus.SUCCEEDED == "succeeded"
        assert StepStatus.FAILED == "failed"
        assert StepStatus.CANCELED == "canceled"
        assert StepStatus.SKIPPED == "skipped"

    def test_step_status_members(self) -> None:
        """Test StepStatus enum has all expected members."""
        from litestar_workflows.core.types import StepStatus

        assert len(StepStatus) == 8
        expected = {
            StepStatus.PENDING,
            StepStatus.SCHEDULED,
            StepStatus.RUNNING,
            StepStatus.WAITING,
            StepStatus.SUCCEEDED,
            StepStatus.FAILED,
            StepStatus.CANCELED,
            StepStatus.SKIPPED,
        }
        assert set(StepStatus) == expected

    def test_step_status_string_conversion(self) -> None:
        """Test StepStatus can be converted to string."""
        from litestar_workflows.core.types import StepStatus

        assert str(StepStatus.PENDING) == "pending"
        assert str(StepStatus.SUCCEEDED) == "succeeded"
        assert str(StepStatus.FAILED) == "failed"

    def test_step_status_lifecycle(self) -> None:
        """Test typical step status lifecycle transitions."""
        from litestar_workflows.core.types import StepStatus

        # Typical success path
        lifecycle = [
            StepStatus.PENDING,
            StepStatus.SCHEDULED,
            StepStatus.RUNNING,
            StepStatus.SUCCEEDED,
        ]

        # All should be distinct
        assert len(lifecycle) == len(set(lifecycle))

        # Verify each status exists
        for status in lifecycle:
            assert status in StepStatus


@pytest.mark.unit
class TestWorkflowStatus:
    """Tests for WorkflowStatus enum."""

    def test_workflow_status_values(self) -> None:
        """Test WorkflowStatus enum has expected values."""
        from litestar_workflows.core.types import WorkflowStatus

        assert WorkflowStatus.PENDING == "pending"
        assert WorkflowStatus.RUNNING == "running"
        assert WorkflowStatus.PAUSED == "paused"
        assert WorkflowStatus.WAITING == "waiting"
        assert WorkflowStatus.COMPLETED == "completed"
        assert WorkflowStatus.FAILED == "failed"
        assert WorkflowStatus.CANCELED == "canceled"

    def test_workflow_status_members(self) -> None:
        """Test WorkflowStatus enum has all expected members."""
        from litestar_workflows.core.types import WorkflowStatus

        assert len(WorkflowStatus) == 7
        expected = {
            WorkflowStatus.PENDING,
            WorkflowStatus.RUNNING,
            WorkflowStatus.PAUSED,
            WorkflowStatus.WAITING,
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELED,
        }
        assert set(WorkflowStatus) == expected

    def test_workflow_status_string_conversion(self) -> None:
        """Test WorkflowStatus can be converted to string."""
        from litestar_workflows.core.types import WorkflowStatus

        assert str(WorkflowStatus.PENDING) == "pending"
        assert str(WorkflowStatus.RUNNING) == "running"
        assert str(WorkflowStatus.COMPLETED) == "completed"

    def test_workflow_terminal_states(self) -> None:
        """Test identification of terminal workflow states."""
        from litestar_workflows.core.types import WorkflowStatus

        terminal_states = {
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELED,
        }

        non_terminal_states = {
            WorkflowStatus.PENDING,
            WorkflowStatus.RUNNING,
            WorkflowStatus.PAUSED,
            WorkflowStatus.WAITING,
        }

        # Verify no overlap
        assert not terminal_states.intersection(non_terminal_states)

        # Verify covers all states
        assert terminal_states.union(non_terminal_states) == set(WorkflowStatus)


@pytest.mark.unit
class TestStepExecution:
    """Tests for StepExecution dataclass."""

    def test_step_execution_creation(self) -> None:
        """Test creating a StepExecution instance."""
        from litestar_workflows.core.types import StepExecution, StepStatus

        now = datetime.now(timezone.utc)
        execution = StepExecution(
            step_name="test_step",
            status=str(StepStatus.SUCCEEDED),
            started_at=now,
            completed_at=now,
            result={"key": "value"},
        )

        assert execution.step_name == "test_step"
        assert execution.status == str(StepStatus.SUCCEEDED)
        assert execution.result == {"key": "value"}
        assert execution.completed_at == now
        assert execution.started_at == now

    def test_step_execution_with_error(self) -> None:
        """Test StepExecution with error information."""
        from litestar_workflows.core.types import StepExecution, StepStatus

        now = datetime.now(timezone.utc)
        execution = StepExecution(
            step_name="failing_step",
            status=str(StepStatus.FAILED),
            started_at=now,
            completed_at=now,
            error="Something went wrong",
        )

        assert execution.status == str(StepStatus.FAILED)
        assert execution.error == "Something went wrong"
        assert execution.result is None

    def test_step_execution_optional_fields(self) -> None:
        """Test StepExecution with optional fields."""
        from litestar_workflows.core.types import StepExecution, StepStatus

        now = datetime.now(timezone.utc)
        execution = StepExecution(
            step_name="test_step",
            status=str(StepStatus.SUCCEEDED),
            started_at=now,
            completed_at=now,
        )

        assert execution.result is None
        assert execution.error is None
