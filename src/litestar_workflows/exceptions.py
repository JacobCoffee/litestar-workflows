"""Exception hierarchy for litestar-workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

__all__ = (
    "HumanTaskError",
    "InvalidTransitionError",
    "StepExecutionError",
    "TaskAlreadyCompletedError",
    "TaskNotFoundError",
    "UnauthorizedTaskError",
    "WorkflowAlreadyCompletedError",
    "WorkflowInstanceNotFoundError",
    "WorkflowNotFoundError",
    "WorkflowValidationError",
    "WorkflowsError",
)


class WorkflowsError(Exception):
    """Base exception for all litestar-workflows errors.

    All exceptions raised by litestar-workflows should inherit from this class.
    This allows users to catch all workflow-related errors with a single except clause.
    """


class WorkflowNotFoundError(WorkflowsError):
    """Raised when a workflow definition is not found.

    This typically occurs when trying to retrieve or instantiate a workflow
    that hasn't been registered with the workflow registry.

    Attributes:
        name: The name of the workflow that was not found.
        version: The specific version requested, if any.
    """

    def __init__(self, name: str, version: str | None = None) -> None:
        """Initialize the exception with workflow details.

        Args:
            name: The name of the workflow that was not found.
            version: The specific version requested, if any.
        """
        self.name = name
        self.version = version
        msg = f"Workflow '{name}'"
        if version:
            msg += f" version '{version}'"
        msg += " not found"
        super().__init__(msg)


class WorkflowInstanceNotFoundError(WorkflowsError):
    """Raised when a workflow instance is not found.

    This occurs when trying to retrieve or operate on a workflow instance
    that doesn't exist in the workflow engine's storage.

    Attributes:
        instance_id: The ID of the workflow instance that was not found.
    """

    def __init__(self, instance_id: str | UUID) -> None:
        """Initialize the exception with instance details.

        Args:
            instance_id: The ID of the workflow instance that was not found.
        """
        self.instance_id = instance_id
        super().__init__(f"Workflow instance '{instance_id}' not found")


class StepExecutionError(WorkflowsError):
    """Raised when a step fails to execute.

    This wraps the underlying exception that caused the step to fail,
    providing context about which step failed.

    Attributes:
        step_name: The name of the step that failed.
        cause: The underlying exception that caused the failure, if any.
    """

    def __init__(self, step_name: str, cause: Exception | None = None) -> None:
        """Initialize the exception with step execution details.

        Args:
            step_name: The name of the step that failed.
            cause: The underlying exception that caused the failure, if any.
        """
        self.step_name = step_name
        self.cause = cause
        msg = f"Step '{step_name}' failed"
        if cause:
            msg += f": {cause}"
        super().__init__(msg)


class InvalidTransitionError(WorkflowsError):
    """Raised when an invalid state transition is attempted.

    This occurs when trying to transition between steps in a way that
    violates the workflow's defined graph structure or transition rules.

    Attributes:
        from_step: The step being transitioned from.
        to_step: The step being transitioned to.
    """

    def __init__(self, from_step: str, to_step: str, reason: str | None = None) -> None:
        """Initialize the exception with transition details.

        Args:
            from_step: The step being transitioned from.
            to_step: The step being transitioned to.
            reason: Additional context about why the transition is invalid.
        """
        self.from_step = from_step
        self.to_step = to_step
        msg = f"Invalid transition from '{from_step}' to '{to_step}'"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class WorkflowValidationError(WorkflowsError):
    """Raised when workflow definition validation fails.

    This occurs during workflow registration or modification when the
    workflow definition doesn't meet required constraints (e.g., cycles,
    unreachable nodes, invalid step types).

    Attributes:
        errors: List of validation error messages.
    """

    def __init__(self, errors: list[str]) -> None:
        """Initialize the exception with validation errors.

        Args:
            errors: List of validation error messages.
        """
        self.errors = errors
        super().__init__(f"Workflow validation failed: {'; '.join(errors)}")


class WorkflowAlreadyCompletedError(WorkflowsError):
    """Raised when trying to modify a completed workflow.

    This prevents operations on workflow instances that have reached a
    terminal state (completed, failed, or cancelled).

    Attributes:
        instance_id: The ID of the workflow instance.
        status: The current terminal status of the workflow.
    """

    def __init__(self, instance_id: str | UUID, status: str) -> None:
        """Initialize the exception with workflow state details.

        Args:
            instance_id: The ID of the workflow instance.
            status: The current terminal status of the workflow.
        """
        self.instance_id = instance_id
        self.status = status
        super().__init__(f"Workflow '{instance_id}' is already {status}")


class HumanTaskError(WorkflowsError):
    """Base exception for human task related errors.

    All human task specific exceptions should inherit from this class.
    This allows distinguishing between automated workflow errors and
    human interaction errors.
    """


class TaskNotFoundError(HumanTaskError):
    """Raised when a human task is not found.

    This occurs when trying to retrieve or complete a task that doesn't
    exist in the human task storage.

    Attributes:
        task_id: The ID of the task that was not found.
    """

    def __init__(self, task_id: str | UUID) -> None:
        """Initialize the exception with task details.

        Args:
            task_id: The ID of the task that was not found.
        """
        self.task_id = task_id
        super().__init__(f"Task '{task_id}' not found")


class TaskAlreadyCompletedError(HumanTaskError):
    """Raised when trying to complete an already completed task.

    This prevents double-completion of human tasks which could lead to
    inconsistent workflow state.

    Attributes:
        task_id: The ID of the task that was already completed.
    """

    def __init__(self, task_id: str | UUID) -> None:
        """Initialize the exception with task details.

        Args:
            task_id: The ID of the task that was already completed.
        """
        self.task_id = task_id
        super().__init__(f"Task '{task_id}' is already completed")


class UnauthorizedTaskError(HumanTaskError):
    """Raised when user is not authorized to complete a task.

    This enforces authorization rules for human tasks, ensuring only
    assigned users or users with appropriate roles can complete tasks.

    Attributes:
        task_id: The ID of the task.
        user_id: The ID of the user attempting to complete the task.
    """

    def __init__(self, task_id: str | UUID, user_id: str) -> None:
        """Initialize the exception with authorization details.

        Args:
            task_id: The ID of the task.
            user_id: The ID of the user attempting to complete the task.
        """
        self.task_id = task_id
        self.user_id = user_id
        super().__init__(f"User '{user_id}' is not authorized to complete task '{task_id}'")
