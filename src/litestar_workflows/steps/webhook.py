"""Webhook wait steps for external event integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar_workflows.core import StepType
from litestar_workflows.steps.base import BaseStep

if TYPE_CHECKING:
    from litestar_workflows.core import WorkflowContext


class WebhookStep(BaseStep):
    """Step that waits for external webhook callback.

    Webhook steps pause workflow execution until an external system
    sends a callback with data. This is useful for integrating with
    third-party services or async external processes.

    The execution engine is responsible for managing the actual waiting
    and resuming the workflow when the webhook is received.

    Example:
        >>> # Wait for payment confirmation
        >>> step = WebhookStep(
        ...     "wait_payment",
        ...     callback_key="payment_data",
        ...     description="Wait for payment gateway callback",
        ... )
        >>> # Workflow pauses here until webhook received
        >>> payment_data = await step.execute(context)
        >>> # Continue with payment_data from webhook
    """

    step_type: StepType = StepType.WEBHOOK

    def __init__(
        self,
        name: str,
        callback_key: str = "webhook_data",
        description: str = "",
    ) -> None:
        """Initialize a webhook step.

        Args:
            name: Unique identifier for the step.
            callback_key: Context key where webhook data will be stored.
            description: Human-readable description.
        """
        super().__init__(name, description)
        self.step_type = StepType.WEBHOOK
        self.callback_key = callback_key

    async def execute(self, context: WorkflowContext) -> Any:
        """Retrieve webhook data from context.

        This step pauses execution until a webhook is received.
        The execution engine handles the actual waiting mechanism.

        Args:
            context: The workflow execution context.

        Returns:
            The data received from the webhook callback.

        Note:
            The engine will populate the callback_key in context
            when the webhook is received before resuming execution.
        """
        return context.get(self.callback_key)
