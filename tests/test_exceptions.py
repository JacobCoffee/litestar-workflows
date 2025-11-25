"""Tests for exception hierarchy."""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestWorkflowsError:
    """Tests for base WorkflowsError exception."""

    def test_base_exception_creation(self) -> None:
        """Test creating base WorkflowsError."""
        from litestar_workflows.exceptions import WorkflowsError

        error = WorkflowsError("Test error message")

        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_base_exception_inheritance(self) -> None:
        """Test WorkflowsError inherits from Exception."""
        from litestar_workflows.exceptions import WorkflowsError

        assert issubclass(WorkflowsError, Exception)

    def test_base_exception_can_be_raised(self) -> None:
        """Test WorkflowsError can be raised and caught."""
        from litestar_workflows.exceptions import WorkflowsError

        with pytest.raises(WorkflowsError, match="test"):
            raise WorkflowsError("test")


@pytest.mark.unit
class TestWorkflowNotFoundError:
    """Tests for WorkflowNotFoundError exception."""

    def test_workflow_not_found_error(self) -> None:
        """Test WorkflowNotFoundError creation."""
        from litestar_workflows.exceptions import WorkflowNotFoundError

        error = WorkflowNotFoundError("test_workflow")

        assert "test_workflow" in str(error)
        assert isinstance(error, Exception)

    def test_workflow_not_found_inherits_from_base(self) -> None:
        """Test WorkflowNotFoundError inherits from WorkflowsError."""
        from litestar_workflows.exceptions import WorkflowNotFoundError, WorkflowsError

        assert issubclass(WorkflowNotFoundError, WorkflowsError)

    def test_workflow_not_found_with_version(self) -> None:
        """Test WorkflowNotFoundError with version info."""
        from litestar_workflows.exceptions import WorkflowNotFoundError

        error = WorkflowNotFoundError("test_workflow", version="1.0.0")

        error_str = str(error)
        assert "test_workflow" in error_str
        assert "1.0.0" in error_str

    def test_workflow_not_found_catchable(self) -> None:
        """Test WorkflowNotFoundError can be caught."""
        from litestar_workflows.exceptions import WorkflowNotFoundError, WorkflowsError

        with pytest.raises(WorkflowsError):
            raise WorkflowNotFoundError("missing_workflow")

        with pytest.raises(WorkflowNotFoundError):
            raise WorkflowNotFoundError("missing_workflow")


@pytest.mark.unit
class TestStepExecutionError:
    """Tests for StepExecutionError exception."""

    def test_step_execution_error_creation(self) -> None:
        """Test StepExecutionError creation."""
        from litestar_workflows.exceptions import StepExecutionError

        error = StepExecutionError("test_step")

        error_str = str(error)
        assert "test_step" in error_str

    def test_step_execution_error_inherits_from_base(self) -> None:
        """Test StepExecutionError inherits from WorkflowsError."""
        from litestar_workflows.exceptions import StepExecutionError, WorkflowsError

        assert issubclass(StepExecutionError, WorkflowsError)

    def test_step_execution_error_with_cause(self) -> None:
        """Test StepExecutionError with cause exception."""
        from litestar_workflows.exceptions import StepExecutionError

        cause_error = ValueError("Original error")
        error = StepExecutionError("test_step", cause=cause_error)

        assert error.cause is cause_error
        assert isinstance(error.cause, ValueError)
        assert "Original error" in str(error)

    def test_step_execution_error_attributes(self) -> None:
        """Test StepExecutionError has expected attributes."""
        from litestar_workflows.exceptions import StepExecutionError

        error = StepExecutionError("test_step")

        assert hasattr(error, "step_name")
        assert error.step_name == "test_step"
        assert hasattr(error, "cause")


@pytest.mark.unit
class TestInvalidTransitionError:
    """Tests for InvalidTransitionError exception."""

    def test_invalid_transition_error(self) -> None:
        """Test InvalidTransitionError creation."""
        from litestar_workflows.exceptions import InvalidTransitionError

        error = InvalidTransitionError("step_a", "step_b")

        error_str = str(error)
        assert "step_a" in error_str
        assert "step_b" in error_str

    def test_invalid_transition_inherits_from_base(self) -> None:
        """Test InvalidTransitionError inherits from WorkflowsError."""
        from litestar_workflows.exceptions import InvalidTransitionError, WorkflowsError

        assert issubclass(InvalidTransitionError, WorkflowsError)

    def test_invalid_transition_with_reason(self) -> None:
        """Test InvalidTransitionError with reason."""
        from litestar_workflows.exceptions import InvalidTransitionError

        error = InvalidTransitionError("step_a", "step_b", reason="No edge exists")

        error_str = str(error)
        assert "No edge exists" in error_str


@pytest.mark.unit
class TestWorkflowValidationError:
    """Tests for WorkflowValidationError exception."""

    def test_validation_error_creation(self) -> None:
        """Test WorkflowValidationError creation."""
        from litestar_workflows.exceptions import WorkflowValidationError

        error = WorkflowValidationError(["Invalid workflow configuration"])

        assert "Invalid workflow configuration" in str(error)

    def test_validation_error_inherits_from_base(self) -> None:
        """Test WorkflowValidationError inherits from WorkflowsError."""
        from litestar_workflows.exceptions import WorkflowsError, WorkflowValidationError

        assert issubclass(WorkflowValidationError, WorkflowsError)

    def test_validation_error_with_multiple_errors(self) -> None:
        """Test WorkflowValidationError with multiple validation errors."""
        from litestar_workflows.exceptions import WorkflowValidationError

        errors = ["Missing required field: initial_step", "Invalid step reference: unknown_step"]
        error = WorkflowValidationError(errors)

        error_str = str(error)
        assert "initial_step" in error_str
        assert "unknown_step" in error_str
        assert error.errors == errors


@pytest.mark.unit
class TestWorkflowInstanceNotFoundError:
    """Tests for WorkflowInstanceNotFoundError exception."""

    def test_instance_not_found_error_creation(self) -> None:
        """Test WorkflowInstanceNotFoundError creation."""
        from uuid import uuid4

        from litestar_workflows.exceptions import WorkflowInstanceNotFoundError

        instance_id = uuid4()
        error = WorkflowInstanceNotFoundError(instance_id)

        error_str = str(error)
        assert str(instance_id) in error_str
        assert "not found" in error_str

    def test_instance_not_found_error_inherits_from_base(self) -> None:
        """Test WorkflowInstanceNotFoundError inherits from WorkflowsError."""
        from litestar_workflows.exceptions import WorkflowInstanceNotFoundError, WorkflowsError

        assert issubclass(WorkflowInstanceNotFoundError, WorkflowsError)

    def test_instance_not_found_error_with_string_id(self) -> None:
        """Test WorkflowInstanceNotFoundError with string ID."""
        from litestar_workflows.exceptions import WorkflowInstanceNotFoundError

        error = WorkflowInstanceNotFoundError("test-instance-123")

        assert "test-instance-123" in str(error)
        assert error.instance_id == "test-instance-123"


@pytest.mark.unit
class TestWorkflowAlreadyCompletedError:
    """Tests for WorkflowAlreadyCompletedError exception."""

    def test_already_completed_error_creation(self) -> None:
        """Test WorkflowAlreadyCompletedError creation."""
        from uuid import uuid4

        from litestar_workflows.exceptions import WorkflowAlreadyCompletedError

        instance_id = uuid4()
        error = WorkflowAlreadyCompletedError(instance_id, "completed")

        error_str = str(error)
        assert str(instance_id) in error_str
        assert "completed" in error_str

    def test_already_completed_error_inherits_from_base(self) -> None:
        """Test WorkflowAlreadyCompletedError inherits from WorkflowsError."""
        from litestar_workflows.exceptions import WorkflowAlreadyCompletedError, WorkflowsError

        assert issubclass(WorkflowAlreadyCompletedError, WorkflowsError)

    def test_already_completed_error_attributes(self) -> None:
        """Test WorkflowAlreadyCompletedError has expected attributes."""
        from litestar_workflows.exceptions import WorkflowAlreadyCompletedError

        instance_id = "test-instance"
        error = WorkflowAlreadyCompletedError(instance_id, "failed")

        assert error.instance_id == instance_id
        assert error.status == "failed"


@pytest.mark.unit
class TestHumanTaskExceptions:
    """Tests for human task related exceptions."""

    def test_human_task_error_base(self) -> None:
        """Test HumanTaskError is a base exception."""
        from litestar_workflows.exceptions import HumanTaskError, WorkflowsError

        assert issubclass(HumanTaskError, WorkflowsError)

    def test_task_not_found_error(self) -> None:
        """Test TaskNotFoundError creation."""
        from uuid import uuid4

        from litestar_workflows.exceptions import TaskNotFoundError

        task_id = uuid4()
        error = TaskNotFoundError(task_id)

        assert str(task_id) in str(error)
        assert "not found" in str(error)
        assert error.task_id == task_id

    def test_task_not_found_error_with_string_id(self) -> None:
        """Test TaskNotFoundError with string ID."""
        from litestar_workflows.exceptions import TaskNotFoundError

        error = TaskNotFoundError("task-123")

        assert "task-123" in str(error)
        assert error.task_id == "task-123"

    def test_task_already_completed_error(self) -> None:
        """Test TaskAlreadyCompletedError creation."""
        from uuid import uuid4

        from litestar_workflows.exceptions import TaskAlreadyCompletedError

        task_id = uuid4()
        error = TaskAlreadyCompletedError(task_id)

        assert str(task_id) in str(error)
        assert "already completed" in str(error)
        assert error.task_id == task_id

    def test_unauthorized_task_error(self) -> None:
        """Test UnauthorizedTaskError creation."""
        from uuid import uuid4

        from litestar_workflows.exceptions import UnauthorizedTaskError

        task_id = uuid4()
        user_id = "user123"
        error = UnauthorizedTaskError(task_id, user_id)

        error_str = str(error)
        assert str(task_id) in error_str
        assert user_id in error_str
        assert "not authorized" in error_str
        assert error.task_id == task_id
        assert error.user_id == user_id

    def test_human_task_exceptions_inherit_from_base(self) -> None:
        """Test human task exceptions inherit from HumanTaskError."""
        from litestar_workflows.exceptions import (
            HumanTaskError,
            TaskAlreadyCompletedError,
            TaskNotFoundError,
            UnauthorizedTaskError,
        )

        human_task_exceptions = [
            TaskNotFoundError,
            TaskAlreadyCompletedError,
            UnauthorizedTaskError,
        ]

        for exc_class in human_task_exceptions:
            assert issubclass(exc_class, HumanTaskError)


@pytest.mark.unit
class TestExceptionHierarchy:
    """Tests for overall exception hierarchy."""

    def test_all_exceptions_inherit_from_base(self) -> None:
        """Test all exceptions inherit from WorkflowsError."""
        from litestar_workflows.exceptions import (
            HumanTaskError,
            InvalidTransitionError,
            StepExecutionError,
            TaskAlreadyCompletedError,
            TaskNotFoundError,
            UnauthorizedTaskError,
            WorkflowAlreadyCompletedError,
            WorkflowInstanceNotFoundError,
            WorkflowNotFoundError,
            WorkflowsError,
            WorkflowValidationError,
        )

        exceptions = [
            WorkflowNotFoundError,
            WorkflowInstanceNotFoundError,
            StepExecutionError,
            InvalidTransitionError,
            WorkflowValidationError,
            WorkflowAlreadyCompletedError,
            HumanTaskError,
            TaskNotFoundError,
            TaskAlreadyCompletedError,
            UnauthorizedTaskError,
        ]

        for exc_class in exceptions:
            assert issubclass(exc_class, WorkflowsError)

    def test_catch_all_with_base_exception(self) -> None:
        """Test catching all workflow exceptions with base exception."""
        from litestar_workflows.exceptions import (
            StepExecutionError,
            WorkflowNotFoundError,
            WorkflowsError,
        )

        # All specific exceptions should be catchable as WorkflowsError
        with pytest.raises(WorkflowsError):
            raise WorkflowNotFoundError("test")

        with pytest.raises(WorkflowsError):
            raise StepExecutionError("step")

    def test_exception_messages(self) -> None:
        """Test all exceptions have meaningful messages."""
        from uuid import uuid4

        from litestar_workflows.exceptions import (
            InvalidTransitionError,
            StepExecutionError,
            TaskAlreadyCompletedError,
            TaskNotFoundError,
            UnauthorizedTaskError,
            WorkflowAlreadyCompletedError,
            WorkflowInstanceNotFoundError,
            WorkflowNotFoundError,
            WorkflowValidationError,
        )

        exceptions = [
            WorkflowNotFoundError("test_workflow"),
            WorkflowInstanceNotFoundError(uuid4()),
            StepExecutionError("test_step"),
            InvalidTransitionError("step_a", "step_b"),
            WorkflowValidationError(["validation error"]),
            WorkflowAlreadyCompletedError(uuid4(), "completed"),
            TaskNotFoundError(uuid4()),
            TaskAlreadyCompletedError(uuid4()),
            UnauthorizedTaskError(uuid4(), "user123"),
        ]

        for exc in exceptions:
            # All exceptions should have non-empty string representation
            assert len(str(exc)) > 0
            assert str(exc) != ""
