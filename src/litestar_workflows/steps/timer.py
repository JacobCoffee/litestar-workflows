"""Timer and delay steps for workflow scheduling."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import timedelta
from typing import TYPE_CHECKING

from litestar_workflows.core import StepType
from litestar_workflows.steps.base import BaseStep

if TYPE_CHECKING:
    from litestar_workflows.core import WorkflowContext


class TimerStep(BaseStep):
    """Step that waits for a duration before continuing.

    Timer steps introduce delays in workflow execution. The duration can be
    static or dynamically calculated based on the workflow context.

    Example:
        >>> # Static delay
        >>> step = TimerStep("wait_5min", duration=timedelta(minutes=5))
        >>> await step.execute(context)

        >>> # Dynamic delay based on context
        >>> def get_delay(ctx: WorkflowContext) -> timedelta:
        ...     priority = ctx.get("priority", "normal")
        ...     return timedelta(hours=1) if priority == "low" else timedelta(minutes=5)
        >>> step = TimerStep("dynamic_wait", duration=get_delay)
        >>> await step.execute(context)
    """

    step_type: StepType = StepType.TIMER

    def __init__(
        self,
        name: str,
        duration: timedelta | Callable[[WorkflowContext], timedelta],
        description: str = "",
    ) -> None:
        """Initialize a timer step.

        Args:
            name: Unique identifier for the step.
            duration: Fixed duration or callable that returns duration from context.
            description: Human-readable description.
        """
        super().__init__(name, description)
        self.step_type = StepType.TIMER
        self._duration = duration

    def get_duration(self, context: WorkflowContext) -> timedelta:
        """Get the delay duration for this step.

        Args:
            context: The workflow execution context.

        Returns:
            The duration to wait.
        """
        if isinstance(self._duration, timedelta):
            return self._duration
        return self._duration(context)

    async def execute(self, context: WorkflowContext) -> None:
        """Wait for the specified duration.

        Args:
            context: The workflow execution context.

        Returns:
            None after the delay completes.
        """
        duration = self.get_duration(context)
        await asyncio.sleep(duration.total_seconds())
