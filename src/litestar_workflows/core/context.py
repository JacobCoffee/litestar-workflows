"""Workflow execution context.

This module provides the WorkflowContext dataclass which carries state and metadata
throughout workflow execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

__all__ = ["StepExecution", "WorkflowContext"]


@dataclass
class StepExecution:
    """Record of a single step execution within a workflow.

    Attributes:
        step_name: Name of the executed step.
        status: Final status of the step execution.
        started_at: Timestamp when step execution began.
        completed_at: Timestamp when step execution finished (if completed).
        result: Return value from successful execution.
        error: Error message if execution failed.
        input_data: Input data passed to the step.
        output_data: Output data produced by the step.
    """

    step_name: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    result: Any = None
    error: str | None = None
    input_data: dict[str, Any] | None = None
    output_data: dict[str, Any] | None = None


@dataclass
class WorkflowContext:
    """Execution context passed between workflow steps.

    The WorkflowContext carries all state, metadata, and execution history throughout
    a workflow's lifecycle. It provides a mutable data dictionary for step communication
    and immutable metadata for audit and tracking purposes.

    Attributes:
        workflow_id: Unique identifier for the workflow definition.
        instance_id: Unique identifier for this workflow instance.
        data: Mutable state dictionary for inter-step communication.
        metadata: Immutable metadata about the workflow execution.
        current_step: Name of the currently executing step.
        step_history: Chronological record of all step executions.
        started_at: Timestamp when the workflow instance was created.
        user_id: Optional user identifier for human task contexts.
        tenant_id: Optional tenant identifier for multi-tenancy support.

    Example:
        >>> from uuid import uuid4
        >>> from datetime import datetime
        >>> context = WorkflowContext(
        ...     workflow_id=uuid4(),
        ...     instance_id=uuid4(),
        ...     data={"input": "value"},
        ...     metadata={"creator": "user123"},
        ...     current_step="initial_step",
        ...     step_history=[],
        ...     started_at=datetime.utcnow(),
        ... )
        >>> context.set("result", 42)
        >>> context.get("result")
        42
    """

    workflow_id: UUID
    instance_id: UUID
    data: dict[str, Any]
    metadata: dict[str, Any]
    current_step: str
    step_history: list[StepExecution]
    started_at: datetime
    user_id: str | None = None
    tenant_id: str | None = None

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the workflow data dictionary.

        Args:
            key: The key to look up in the data dictionary.
            default: Default value to return if key is not found.

        Returns:
            The value associated with the key, or the default if not present.

        Example:
            >>> context.get("some_key", "default_value")
            'default_value'
        """
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the workflow data dictionary.

        Args:
            key: The key to set in the data dictionary.
            value: The value to associate with the key.

        Example:
            >>> context.set("status", "approved")
            >>> context.get("status")
            'approved'
        """
        self.data[key] = value

    def with_step(self, step_name: str) -> WorkflowContext:
        """Create a new context for the given step execution.

        This method returns a shallow copy of the context with the current_step
        updated to the provided step name. The data and metadata dictionaries
        are shared with the original context.

        Args:
            step_name: Name of the step to execute next.

        Returns:
            A new WorkflowContext instance with updated current_step.

        Example:
            >>> new_context = context.with_step("next_step")
            >>> new_context.current_step
            'next_step'
        """
        return WorkflowContext(
            workflow_id=self.workflow_id,
            instance_id=self.instance_id,
            data=self.data,
            metadata=self.metadata,
            current_step=step_name,
            step_history=self.step_history,
            started_at=self.started_at,
            user_id=self.user_id,
            tenant_id=self.tenant_id,
        )

    def get_last_execution(self, step_name: str | None = None) -> StepExecution | None:
        """Get the most recent execution record for a step.

        Args:
            step_name: Optional step name to filter by. If None, returns the
                last execution regardless of step.

        Returns:
            The most recent StepExecution matching the criteria, or None if not found.

        Example:
            >>> last_exec = context.get_last_execution("approval_step")
            >>> if last_exec and last_exec.status == "SUCCEEDED":
            ...     print("Step succeeded")
        """
        if step_name is None:
            return self.step_history[-1] if self.step_history else None

        for execution in reversed(self.step_history):
            if execution.step_name == step_name:
                return execution
        return None

    def has_step_executed(self, step_name: str) -> bool:
        """Check if a step has been executed in this workflow instance.

        Args:
            step_name: Name of the step to check.

        Returns:
            True if the step appears in the execution history, False otherwise.

        Example:
            >>> if context.has_step_executed("validation"):
            ...     print("Validation already completed")
        """
        return any(step_exec.step_name == step_name for step_exec in self.step_history)
