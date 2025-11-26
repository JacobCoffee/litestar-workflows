"""Decision gateway steps for workflow branching."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from litestar_workflows.core import StepType
from litestar_workflows.steps.base import BaseStep

if TYPE_CHECKING:
    from litestar_workflows.core import WorkflowContext


class ExclusiveGateway(BaseStep):
    """XOR gateway - exactly one path based on condition.

    This gateway evaluates a condition function and returns the name of the
    next step to execute. Only one path will be followed.

    Example:
        >>> def check_approval(ctx: WorkflowContext) -> str:
        ...     return "approved_step" if ctx.get("approved") else "rejected_step"
        >>> gateway = ExclusiveGateway("approval_gate", condition=check_approval)
        >>> next_step = await gateway.execute(context)  # Returns step name
    """

    step_type: StepType = StepType.GATEWAY

    def __init__(
        self,
        name: str,
        condition: Callable[[WorkflowContext], str],
        description: str = "",
    ) -> None:
        """Initialize an exclusive gateway.

        Args:
            name: Unique identifier for the gateway.
            condition: Function that evaluates context and returns next step name.
            description: Human-readable description.
        """
        super().__init__(name, description)
        self.step_type = StepType.GATEWAY
        self.condition = condition

    async def execute(self, context: WorkflowContext) -> str:
        """Evaluate condition and return the name of the next step.

        Args:
            context: The workflow execution context.

        Returns:
            The name of the next step to execute.

        Raises:
            Exception: If condition evaluation fails.
        """
        return self.condition(context)


class ParallelGateway(BaseStep):
    """AND gateway - all paths execute in parallel.

    This gateway splits execution into multiple parallel branches.
    All branches will be executed concurrently.

    Example:
        >>> gateway = ParallelGateway(
        ...     "fork_point", branches=["notify_team", "update_db", "send_email"]
        ... )
        >>> branch_names = await gateway.execute(context)
    """

    step_type: StepType = StepType.GATEWAY

    def __init__(
        self,
        name: str,
        branches: list[str],
        description: str = "",
    ) -> None:
        """Initialize a parallel gateway.

        Args:
            name: Unique identifier for the gateway.
            branches: List of step names to execute in parallel.
            description: Human-readable description.
        """
        super().__init__(name, description)
        self.step_type = StepType.GATEWAY
        self.branches = branches

    async def execute(self, context: WorkflowContext) -> list[str]:
        """Return the list of branches to execute in parallel.

        Args:
            context: The workflow execution context.

        Returns:
            List of step names to execute concurrently.
        """
        return self.branches
