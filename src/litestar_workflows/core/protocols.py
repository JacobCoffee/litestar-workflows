"""Core protocols for litestar-workflows.

This module defines the Protocol-based interfaces that provide structural typing
for steps, workflows, and execution engines. Using Protocol allows duck typing
while maintaining type safety.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from datetime import timedelta

    from litestar_workflows.core.context import WorkflowContext
    from litestar_workflows.core.types import StepType, WorkflowStatus

    # Use forward reference to avoid circular imports
    WorkflowDefinition = Any  # Will be defined in definition module


__all__ = ["ExecutionEngine", "Step", "Workflow", "WorkflowInstance"]

T = TypeVar("T", covariant=True)


@runtime_checkable
class Step(Protocol[T]):
    """Protocol defining the interface for workflow steps.

    Steps are the atomic units of work within a workflow. They can be machine-automated,
    human-interactive, or event-driven. Each step must implement the core execution
    interface along with lifecycle hooks.

    Attributes:
        name: Unique identifier for this step within its workflow.
        description: Human-readable description of the step's purpose.
        step_type: Classification of this step (MACHINE, HUMAN, WEBHOOK, etc.).

    Example:
        >>> class ApprovalStep:
        ...     name = "approval"
        ...     description = "Manager approval required"
        ...     step_type = StepType.HUMAN
        ...
        ...     async def execute(self, context: WorkflowContext) -> bool:
        ...         return context.get("approved", False)
        ...
        ...     async def can_execute(self, context: WorkflowContext) -> bool:
        ...         return context.get("request_submitted", False)
        ...
        ...     async def on_success(self, context: WorkflowContext, result: bool) -> None:
        ...         context.set("approval_result", result)
        ...
        ...     async def on_failure(self, context: WorkflowContext, error: Exception) -> None:
        ...         context.set("approval_error", str(error))
    """

    name: str
    description: str
    step_type: StepType

    async def execute(self, context: WorkflowContext) -> T:
        """Execute the step's primary logic.

        This method contains the core functionality of the step. It receives the
        workflow context and can read/write data, perform operations, and return
        a result that will be stored in the execution history.

        Args:
            context: The current workflow execution context.

        Returns:
            The result of the step execution, which will be stored in step history.

        Raises:
            Exception: Any exception raised will trigger the on_failure hook and
                potentially fail the workflow.
        """
        ...

    async def can_execute(self, context: WorkflowContext) -> bool:
        """Determine if the step is eligible to execute.

        This method acts as a guard or validator, checking preconditions before
        execution. If it returns False, the step will be marked as SKIPPED.

        Args:
            context: The current workflow execution context.

        Returns:
            True if the step should execute, False to skip it.

        Example:
            >>> async def can_execute(self, context: WorkflowContext) -> bool:
            ...     return context.get("prerequisites_met", False)
        """
        ...

    async def on_success(self, context: WorkflowContext, result: T) -> None:
        """Hook called after successful step execution.

        This method is invoked after execute() completes without raising an exception.
        Use it to update context, trigger side effects, or perform cleanup.

        Args:
            context: The current workflow execution context.
            result: The return value from the execute() method.

        Example:
            >>> async def on_success(self, context: WorkflowContext, result: dict) -> None:
            ...     context.set("last_result", result)
            ...     await send_notification(f"Step {self.name} completed")
        """
        ...

    async def on_failure(self, context: WorkflowContext, error: Exception) -> None:
        """Hook called after failed step execution.

        This method is invoked when execute() raises an exception. Use it for
        error logging, compensation logic, or triggering alerts.

        Args:
            context: The current workflow execution context.
            error: The exception that was raised during execution.

        Example:
            >>> async def on_failure(self, context: WorkflowContext, error: Exception) -> None:
            ...     context.set("error", str(error))
            ...     await log_error(f"Step {self.name} failed: {error}")
        """
        ...


@runtime_checkable
class Workflow(Protocol):
    """Protocol defining the interface for workflow definitions.

    Workflows orchestrate a collection of steps connected by edges (transitions).
    They define the structure and flow logic but not the runtime state.

    Attributes:
        name: Unique identifier for this workflow.
        version: Version string for workflow definition versioning.
        description: Human-readable description of the workflow's purpose.

    Example:
        >>> class DocumentApproval:
        ...     name = "document_approval"
        ...     version = "1.0.0"
        ...     description = "Multi-level document approval workflow"
        ...
        ...     def get_definition(self) -> WorkflowDefinition:
        ...         return WorkflowDefinition(
        ...             name=self.name,
        ...             version=self.version,
        ...             description=self.description,
        ...             steps={...},
        ...             edges=[...],
        ...             initial_step="submit",
        ...             terminal_steps={"approved", "rejected"},
        ...         )
    """

    name: str
    version: str
    description: str

    def get_definition(self) -> WorkflowDefinition:
        """Extract the workflow definition from the class.

        Returns:
            A WorkflowDefinition instance containing steps, edges, and metadata.
        """
        ...


class WorkflowInstance(Protocol):
    """Protocol for workflow runtime instances.

    A WorkflowInstance represents a single execution of a workflow definition.
    It tracks runtime state, progress, and results.

    Attributes:
        id: Unique identifier for this workflow instance.
        workflow_id: Identifier of the workflow definition being executed.
        workflow_name: Name of the workflow definition.
        workflow_version: Version of the workflow definition.
        status: Current execution status.
        context: Runtime execution context.
        current_step: Name of the currently executing or next step.
        started_at: Timestamp when the instance was created.
        completed_at: Timestamp when the instance finished (if applicable).
        error: Error message if the workflow failed.
    """

    id: UUID
    workflow_id: UUID
    workflow_name: str
    workflow_version: str
    status: WorkflowStatus
    context: WorkflowContext
    current_step: str | None
    started_at: Any  # datetime
    completed_at: Any | None  # datetime | None
    error: str | None


class ExecutionEngine(Protocol):
    """Protocol for workflow execution engines.

    The ExecutionEngine is responsible for orchestrating workflow execution,
    including starting workflows, executing steps, scheduling, and handling
    human tasks.

    Example:
        >>> engine = LocalExecutionEngine()
        >>> instance = await engine.start_workflow(MyWorkflow, initial_data={"input": "value"})
    """

    async def start_workflow(
        self,
        workflow: type[Workflow],
        initial_data: dict[str, Any] | None = None,
    ) -> WorkflowInstance:
        """Start a new workflow instance.

        Args:
            workflow: The workflow class to instantiate and execute.
            initial_data: Optional initial data to populate the workflow context.

        Returns:
            A WorkflowInstance representing the started workflow.

        Example:
            >>> instance = await engine.start_workflow(
            ...     ApprovalWorkflow, initial_data={"document_id": "doc_123"}
            ... )
        """
        ...

    async def execute_step(
        self,
        step: Step[Any],
        context: WorkflowContext,
        previous_result: Any = None,
    ) -> Any:
        """Execute a single step within a workflow.

        Args:
            step: The step to execute.
            context: The current workflow context.
            previous_result: Optional result from a previous step.

        Returns:
            The result of the step execution.

        Raises:
            Exception: If step execution fails and error handling doesn't compensate.
        """
        ...

    async def schedule_step(
        self,
        instance_id: UUID,
        step_name: str,
        delay: timedelta | None = None,
    ) -> None:
        """Schedule a step for later execution.

        Args:
            instance_id: The workflow instance identifier.
            step_name: Name of the step to schedule.
            delay: Optional delay before execution. If None, executes immediately.

        Example:
            >>> from datetime import timedelta
            >>> await engine.schedule_step(
            ...     instance_id=instance.id, step_name="reminder", delay=timedelta(hours=24)
            ... )
        """
        ...

    async def complete_human_task(
        self,
        instance_id: UUID,
        step_name: str,
        user_id: str,
        data: dict[str, Any],
    ) -> None:
        """Complete a human task with user-provided data.

        Args:
            instance_id: The workflow instance identifier.
            step_name: Name of the human step to complete.
            user_id: Identifier of the user completing the task.
            data: User-provided form data or input.

        Example:
            >>> await engine.complete_human_task(
            ...     instance_id=instance.id,
            ...     step_name="approval",
            ...     user_id="user_123",
            ...     data={"approved": True, "comments": "Looks good"},
            ... )
        """
        ...

    async def cancel_workflow(self, instance_id: UUID, reason: str) -> None:
        """Cancel a running workflow instance.

        Args:
            instance_id: The workflow instance identifier.
            reason: Explanation for the cancellation.

        Example:
            >>> await engine.cancel_workflow(
            ...     instance_id=instance.id, reason="Request withdrawn by submitter"
            ... )
        """
        ...
