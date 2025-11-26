"""Base step implementations for litestar-workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar_workflows.core import StepType

if TYPE_CHECKING:
    from litestar_workflows.core import WorkflowContext


class BaseStep:
    """Base implementation with common functionality for all steps.

    This class provides default implementations of the Step protocol methods
    and common attributes. Subclass this to create custom step types.
    """

    name: str
    """Unique identifier for the step."""

    description: str = ""
    """Human-readable description of what the step does."""

    step_type: StepType = StepType.MACHINE
    """Type of step (MACHINE, HUMAN, WEBHOOK, TIMER, GATEWAY)."""

    def __init__(self, name: str, description: str = "") -> None:
        """Initialize the base step.

        Args:
            name: Unique identifier for the step.
            description: Human-readable description.
        """
        self.name = name
        self.description = description

    async def execute(self, context: WorkflowContext) -> Any:
        """Execute the step with the given context.

        Override this method to implement step logic.

        Args:
            context: The workflow execution context.

        Returns:
            The result of the step execution.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        msg = f"Step {self.name} must implement execute()"
        raise NotImplementedError(msg)

    async def can_execute(self, context: WorkflowContext) -> bool:
        """Check if step can execute given the current context.

        Override this method to implement guard logic.

        Args:
            context: The workflow execution context.

        Returns:
            True if the step can execute, False to skip.
        """
        return True

    async def on_success(self, context: WorkflowContext, result: Any) -> None:
        """Hook called after successful step execution.

        Override this method to implement post-success logic.

        Args:
            context: The workflow execution context.
            result: The result returned by execute().
        """

    async def on_failure(self, context: WorkflowContext, error: Exception) -> None:
        """Hook called after failed step execution.

        Override this method to implement error handling logic.

        Args:
            context: The workflow execution context.
            error: The exception that caused the failure.
        """


class BaseMachineStep(BaseStep):
    """Base for automated machine steps.

    Machine steps execute automatically without requiring human interaction.
    They are the building blocks for automated workflow processes.
    """

    step_type: StepType = StepType.MACHINE

    def __init__(self, name: str, description: str = "") -> None:
        """Initialize the machine step.

        Args:
            name: Unique identifier for the step.
            description: Human-readable description.
        """
        super().__init__(name, description)
        self.step_type = StepType.MACHINE


class BaseHumanStep(BaseStep):
    """Base for human approval/interaction steps.

    Human steps pause workflow execution and wait for user input.
    They support forms, assignments, and deadline tracking.
    """

    step_type: StepType = StepType.HUMAN

    title: str
    """Display title for the human task."""

    form_schema: dict[str, Any] | None = None
    """JSON Schema defining the form structure for user input."""

    assignee_key: str | None = None
    """Context key for dynamic assignment of tasks."""

    def __init__(
        self,
        name: str,
        title: str,
        description: str = "",
        form_schema: dict[str, Any] | None = None,
        assignee_key: str | None = None,
    ) -> None:
        """Initialize the human step.

        Args:
            name: Unique identifier for the step.
            title: Display title for the human task.
            description: Human-readable description.
            form_schema: Optional JSON Schema for the task form.
            assignee_key: Optional context key to get assignee dynamically.
        """
        super().__init__(name, description)
        self.step_type = StepType.HUMAN
        self.title = title
        self.form_schema = form_schema
        self.assignee_key = assignee_key

    async def get_assignee(self, context: WorkflowContext) -> str | None:
        """Get the assignee for this task from context.

        Args:
            context: The workflow execution context.

        Returns:
            User ID to assign the task to, or None for unassigned.
        """
        if self.assignee_key:
            return context.get(self.assignee_key)
        return None

    async def execute(self, context: WorkflowContext) -> Any:
        """Execute the human step.

        For human steps, execution typically means waiting for user input.
        Override this if you need custom behavior.

        Args:
            context: The workflow execution context.

        Returns:
            The form data submitted by the user.
        """
        # Default implementation - the engine will handle pausing and resuming
        return context.get(f"{self.name}_result")
