"""Domain events for workflow lifecycle.

This module defines the event types that are emitted during workflow execution.
These events can be used for logging, monitoring, triggering side effects, or
integrating with external systems.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

__all__ = [
    "HumanTaskCompleted",
    "HumanTaskCreated",
    "HumanTaskReassigned",
    "StepCompleted",
    "StepFailed",
    "StepSkipped",
    "StepStarted",
    "WorkflowCanceled",
    "WorkflowCompleted",
    "WorkflowEvent",
    "WorkflowFailed",
    "WorkflowPaused",
    "WorkflowResumed",
    "WorkflowStarted",
]


@dataclass
class WorkflowEvent:
    """Base class for all workflow events.

    All workflow events include the instance_id and timestamp for tracking
    and correlation.

    Attributes:
        instance_id: Unique identifier of the workflow instance.
        timestamp: When the event occurred.
    """

    instance_id: UUID
    timestamp: datetime


@dataclass
class WorkflowStarted(WorkflowEvent):
    """Event emitted when a workflow instance starts execution.

    Attributes:
        instance_id: Unique identifier of the workflow instance.
        timestamp: When the workflow started.
        workflow_name: Name of the workflow definition.
        workflow_version: Version of the workflow definition.
        initial_data: Initial data provided when starting the workflow.
        user_id: Optional user who initiated the workflow.
        tenant_id: Optional tenant identifier for multi-tenancy.

    Example:
        >>> event = WorkflowStarted(
        ...     instance_id=uuid4(),
        ...     timestamp=datetime.utcnow(),
        ...     workflow_name="approval_flow",
        ...     workflow_version="1.0.0",
        ...     initial_data={"document_id": "doc_123"},
        ... )
    """

    workflow_name: str
    workflow_version: str
    initial_data: dict[str, Any] | None = None
    user_id: str | None = None
    tenant_id: str | None = None


@dataclass
class WorkflowCompleted(WorkflowEvent):
    """Event emitted when a workflow instance completes successfully.

    Attributes:
        instance_id: Unique identifier of the workflow instance.
        timestamp: When the workflow completed.
        status: Final status of the workflow.
        final_step: Name of the final step that was executed.
        duration_seconds: Total execution time in seconds.

    Example:
        >>> event = WorkflowCompleted(
        ...     instance_id=uuid4(),
        ...     timestamp=datetime.utcnow(),
        ...     status="COMPLETED",
        ...     final_step="approve",
        ...     duration_seconds=3600.5,
        ... )
    """

    status: str
    final_step: str | None = None
    duration_seconds: float | None = None


@dataclass
class WorkflowFailed(WorkflowEvent):
    """Event emitted when a workflow instance fails.

    Attributes:
        instance_id: Unique identifier of the workflow instance.
        timestamp: When the workflow failed.
        error: Error message describing the failure.
        failed_step: Name of the step that caused the failure.
        error_type: Type/class of the error that occurred.
        stack_trace: Optional stack trace for debugging.

    Example:
        >>> event = WorkflowFailed(
        ...     instance_id=uuid4(),
        ...     timestamp=datetime.utcnow(),
        ...     error="Database connection failed",
        ...     failed_step="data_validation",
        ...     error_type="ConnectionError",
        ... )
    """

    error: str
    failed_step: str | None = None
    error_type: str | None = None
    stack_trace: str | None = None


@dataclass
class WorkflowCanceled(WorkflowEvent):
    """Event emitted when a workflow instance is manually canceled.

    Attributes:
        instance_id: Unique identifier of the workflow instance.
        timestamp: When the workflow was canceled.
        reason: Explanation for the cancellation.
        canceled_by: User who canceled the workflow.
        current_step: Step that was executing when canceled.

    Example:
        >>> event = WorkflowCanceled(
        ...     instance_id=uuid4(),
        ...     timestamp=datetime.utcnow(),
        ...     reason="Request withdrawn",
        ...     canceled_by="user_123",
        ...     current_step="review",
        ... )
    """

    reason: str
    canceled_by: str | None = None
    current_step: str | None = None


@dataclass
class WorkflowPaused(WorkflowEvent):
    """Event emitted when a workflow instance is paused.

    Attributes:
        instance_id: Unique identifier of the workflow instance.
        timestamp: When the workflow was paused.
        reason: Explanation for pausing.
        paused_at_step: Step where execution was paused.

    Example:
        >>> event = WorkflowPaused(
        ...     instance_id=uuid4(),
        ...     timestamp=datetime.utcnow(),
        ...     reason="Awaiting external data",
        ...     paused_at_step="data_ingestion",
        ... )
    """

    reason: str | None = None
    paused_at_step: str | None = None


@dataclass
class WorkflowResumed(WorkflowEvent):
    """Event emitted when a paused workflow instance resumes.

    Attributes:
        instance_id: Unique identifier of the workflow instance.
        timestamp: When the workflow resumed.
        resumed_by: User who resumed the workflow.
        resuming_at_step: Step where execution will resume.

    Example:
        >>> event = WorkflowResumed(
        ...     instance_id=uuid4(),
        ...     timestamp=datetime.utcnow(),
        ...     resumed_by="user_456",
        ...     resuming_at_step="data_processing",
        ... )
    """

    resumed_by: str | None = None
    resuming_at_step: str | None = None


@dataclass
class StepStarted(WorkflowEvent):
    """Event emitted when a step begins execution.

    Attributes:
        instance_id: Unique identifier of the workflow instance.
        timestamp: When the step started.
        step_name: Name of the step that started.
        step_type: Type of the step (MACHINE, HUMAN, etc.).
        input_data: Input data provided to the step.

    Example:
        >>> event = StepStarted(
        ...     instance_id=uuid4(),
        ...     timestamp=datetime.utcnow(),
        ...     step_name="validation",
        ...     step_type="MACHINE",
        ...     input_data={"data": "to_validate"},
        ... )
    """

    step_name: str
    step_type: str
    input_data: dict[str, Any] | None = None


@dataclass
class StepCompleted(WorkflowEvent):
    """Event emitted when a step completes successfully.

    Attributes:
        instance_id: Unique identifier of the workflow instance.
        timestamp: When the step completed.
        step_name: Name of the step that completed.
        status: Final status of the step execution.
        result: Return value from the step execution.
        output_data: Output data produced by the step.
        duration_seconds: Execution time in seconds.

    Example:
        >>> event = StepCompleted(
        ...     instance_id=uuid4(),
        ...     timestamp=datetime.utcnow(),
        ...     step_name="validation",
        ...     status="SUCCEEDED",
        ...     result={"valid": True},
        ...     duration_seconds=1.5,
        ... )
    """

    step_name: str
    status: str
    result: Any = None
    output_data: dict[str, Any] | None = None
    duration_seconds: float | None = None


@dataclass
class StepFailed(WorkflowEvent):
    """Event emitted when a step fails execution.

    Attributes:
        instance_id: Unique identifier of the workflow instance.
        timestamp: When the step failed.
        step_name: Name of the step that failed.
        error: Error message describing the failure.
        error_type: Type/class of the error.
        retry_count: Number of retry attempts made.

    Example:
        >>> event = StepFailed(
        ...     instance_id=uuid4(),
        ...     timestamp=datetime.utcnow(),
        ...     step_name="api_call",
        ...     error="Connection timeout",
        ...     error_type="TimeoutError",
        ...     retry_count=3,
        ... )
    """

    step_name: str
    error: str
    error_type: str | None = None
    retry_count: int = 0


@dataclass
class StepSkipped(WorkflowEvent):
    """Event emitted when a step is skipped due to conditions.

    Attributes:
        instance_id: Unique identifier of the workflow instance.
        timestamp: When the step was skipped.
        step_name: Name of the step that was skipped.
        reason: Explanation for why the step was skipped.

    Example:
        >>> event = StepSkipped(
        ...     instance_id=uuid4(),
        ...     timestamp=datetime.utcnow(),
        ...     step_name="optional_notification",
        ...     reason="Notification disabled in settings",
        ... )
    """

    step_name: str
    reason: str | None = None


@dataclass
class HumanTaskCreated(WorkflowEvent):
    """Event emitted when a human task is created.

    Attributes:
        instance_id: Unique identifier of the workflow instance.
        timestamp: When the task was created.
        step_name: Name of the human step.
        task_id: Unique identifier for this task.
        assignee: User or group assigned to the task.
        title: Display title for the task.
        description: Detailed description of what needs to be done.
        due_at: Optional deadline for task completion.

    Example:
        >>> event = HumanTaskCreated(
        ...     instance_id=uuid4(),
        ...     timestamp=datetime.utcnow(),
        ...     step_name="manager_approval",
        ...     task_id=uuid4(),
        ...     assignee="manager_group",
        ...     title="Approve expense report",
        ...     description="Review and approve expense report for project X",
        ... )
    """

    step_name: str
    task_id: UUID
    assignee: str | None = None
    title: str | None = None
    description: str | None = None
    due_at: datetime | None = None


@dataclass
class HumanTaskCompleted(WorkflowEvent):
    """Event emitted when a human task is completed.

    Attributes:
        instance_id: Unique identifier of the workflow instance.
        timestamp: When the task was completed.
        step_name: Name of the human step.
        task_id: Unique identifier for this task.
        completed_by: User who completed the task.
        form_data: Data submitted by the user.
        comment: Optional comment provided by the user.

    Example:
        >>> event = HumanTaskCompleted(
        ...     instance_id=uuid4(),
        ...     timestamp=datetime.utcnow(),
        ...     step_name="manager_approval",
        ...     task_id=uuid4(),
        ...     completed_by="manager_123",
        ...     form_data={"approved": True, "amount": 1500.00},
        ...     comment="Approved for payment",
        ... )
    """

    step_name: str
    task_id: UUID
    completed_by: str
    form_data: dict[str, Any] | None = None
    comment: str | None = None


@dataclass
class HumanTaskReassigned(WorkflowEvent):
    """Event emitted when a human task is reassigned.

    Attributes:
        instance_id: Unique identifier of the workflow instance.
        timestamp: When the task was reassigned.
        step_name: Name of the human step.
        task_id: Unique identifier for this task.
        from_assignee: Previous assignee.
        to_assignee: New assignee.
        reassigned_by: User who performed the reassignment.
        reason: Explanation for the reassignment.

    Example:
        >>> event = HumanTaskReassigned(
        ...     instance_id=uuid4(),
        ...     timestamp=datetime.utcnow(),
        ...     step_name="review",
        ...     task_id=uuid4(),
        ...     from_assignee="user_123",
        ...     to_assignee="user_456",
        ...     reassigned_by="admin_789",
        ...     reason="Original assignee on vacation",
        ... )
    """

    step_name: str
    task_id: UUID
    from_assignee: str | None = None
    to_assignee: str | None = None
    reassigned_by: str | None = None
    reason: str | None = None
