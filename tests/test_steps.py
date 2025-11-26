"""Tests for step implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from litestar_workflows.core.context import WorkflowContext
    from litestar_workflows.steps.base import BaseHumanStep, BaseMachineStep


@pytest.mark.unit
class TestBaseStep:
    """Tests for BaseStep functionality."""

    def test_base_machine_step_defaults(self, sample_machine_step: BaseMachineStep) -> None:
        """Test BaseMachineStep has expected defaults."""
        from litestar_workflows.core.types import StepType

        assert sample_machine_step.name == "test_machine_step"
        assert sample_machine_step.description == "A test machine step"
        assert sample_machine_step.step_type == StepType.MACHINE

    def test_base_human_step_defaults(self, sample_human_step: BaseHumanStep) -> None:
        """Test BaseHumanStep has expected defaults."""
        from litestar_workflows.core.types import StepType

        assert sample_human_step.name == "test_human_step"
        assert sample_human_step.description == "A test human step"
        assert sample_human_step.step_type == StepType.HUMAN
        assert sample_human_step.title == "Test Approval"
        assert sample_human_step.form_schema is not None

    def test_human_step_form_schema(self, sample_human_step: BaseHumanStep) -> None:
        """Test human step has valid JSON schema for form."""
        schema = sample_human_step.form_schema

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "approved" in schema["properties"]
        assert "comments" in schema["properties"]
        assert "required" in schema
        assert "approved" in schema["required"]


@pytest.mark.unit
@pytest.mark.asyncio
class TestStepExecution:
    """Tests for step execution."""

    async def test_machine_step_execute(
        self, sample_machine_step: BaseMachineStep, sample_context: WorkflowContext
    ) -> None:
        """Test executing a machine step."""
        result = await sample_machine_step.execute(sample_context)

        assert result["executed"] is True
        assert result["count"] == 1
        assert sample_context.get("count") == 1

    async def test_machine_step_updates_context(
        self, sample_machine_step: BaseMachineStep, sample_context: WorkflowContext
    ) -> None:
        """Test machine step updates context data."""
        original_count = sample_context.get("count")
        await sample_machine_step.execute(sample_context)

        assert sample_context.get("count") == original_count + 1

    async def test_human_step_execute(self, sample_human_step: BaseHumanStep, sample_context: WorkflowContext) -> None:
        """Test executing a human step."""
        sample_context.set("approved", True)
        result = await sample_human_step.execute(sample_context)

        assert result["approved"] is True

    async def test_step_can_execute_guard_default(
        self, sample_machine_step: BaseMachineStep, sample_context: WorkflowContext
    ) -> None:
        """Test can_execute returns True by default."""
        can_execute = await sample_machine_step.can_execute(sample_context)
        assert can_execute is True

    async def test_step_can_execute_guard_custom(self, sample_context: WorkflowContext) -> None:
        """Test custom can_execute guard."""
        from litestar_workflows.steps.base import BaseMachineStep

        class GuardedStep(BaseMachineStep):
            async def can_execute(self, context: WorkflowContext) -> bool:
                return context.get("allowed", False) is True

            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"executed": True}

        step = GuardedStep(name="guarded_step", description="Step with guard")

        # Should not be allowed initially
        assert await step.can_execute(sample_context) is False

        # Allow execution
        sample_context.set("allowed", True)
        assert await step.can_execute(sample_context) is True


@pytest.mark.unit
@pytest.mark.asyncio
class TestStepHooks:
    """Tests for step lifecycle hooks."""

    async def test_on_success_hook(self, sample_context: WorkflowContext) -> None:
        """Test on_success hook is called after successful execution."""
        from litestar_workflows.steps.base import BaseMachineStep

        success_called = False

        class HookedStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"result": "success"}

            async def on_success(self, context: WorkflowContext, result: dict[str, Any]) -> None:
                nonlocal success_called
                success_called = True
                context.set("on_success_called", True)

        step = HookedStep(name="hooked_step", description="Step with hooks")
        result = await step.execute(sample_context)
        await step.on_success(sample_context, result)

        assert success_called is True
        assert sample_context.get("on_success_called") is True

    async def test_on_failure_hook(self, sample_context: WorkflowContext) -> None:
        """Test on_failure hook is called after failed execution."""
        from litestar_workflows.steps.base import BaseMachineStep

        failure_called = False

        class HookedStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                raise RuntimeError("Intentional failure")

            async def on_failure(self, context: WorkflowContext, error: Exception) -> None:
                nonlocal failure_called
                failure_called = True
                context.set("error_message", str(error))

        step = HookedStep(name="hooked_step", description="Step with hooks")

        try:
            await step.execute(sample_context)
        except RuntimeError as e:
            await step.on_failure(sample_context, e)

        assert failure_called is True
        assert sample_context.get("error_message") == "Intentional failure"

    async def test_hooks_receive_correct_arguments(self, sample_context: WorkflowContext) -> None:
        """Test hooks receive correct context and result/error."""
        from litestar_workflows.steps.base import BaseMachineStep

        captured_context = None
        captured_result = None

        class HookedStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"data": "test_value"}

            async def on_success(self, context: WorkflowContext, result: dict[str, Any]) -> None:
                nonlocal captured_context, captured_result
                captured_context = context
                captured_result = result

        step = HookedStep(name="hooked_step", description="Step with hooks")
        result = await step.execute(sample_context)
        await step.on_success(sample_context, result)

        assert captured_context is sample_context
        assert captured_result == {"data": "test_value"}


@pytest.mark.unit
@pytest.mark.asyncio
class TestStepCustomization:
    """Tests for custom step implementations."""

    async def test_custom_machine_step(self, sample_context: WorkflowContext) -> None:
        """Test creating and executing custom machine step."""
        from litestar_workflows.steps.base import BaseMachineStep

        class CustomStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                value = context.get("input", 0)
                result = value * 2
                context.set("output", result)
                return {"result": result}

        step = CustomStep(name="custom_step", description="Custom implementation")
        sample_context.set("input", 5)

        result = await step.execute(sample_context)

        assert result["result"] == 10
        assert sample_context.get("output") == 10

    async def test_custom_human_step(self, sample_context: WorkflowContext) -> None:
        """Test creating custom human step with form."""
        from litestar_workflows.steps.base import BaseHumanStep

        class ApprovalStep(BaseHumanStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                decision = context.get("decision")
                return {"approved": decision == "approve"}

        step = ApprovalStep(
            name="approval",
            title="Please Review",
            description="Approval step",
            form_schema={
                "type": "object",
                "properties": {
                    "decision": {"type": "string", "enum": ["approve", "reject"]},
                    "reason": {"type": "string"},
                },
                "required": ["decision"],
            },
        )

        assert step.title == "Please Review"
        assert "decision" in step.form_schema["properties"]

        sample_context.set("decision", "approve")
        result = await step.execute(sample_context)

        assert result["approved"] is True

    async def test_step_with_parameters(self, sample_context: WorkflowContext) -> None:
        """Test step with initialization parameters."""
        from litestar_workflows.steps.base import BaseMachineStep

        class ParameterizedStep(BaseMachineStep):
            def __init__(self, name: str, description: str = "", multiplier: int = 1):
                super().__init__(name, description)
                self.multiplier = multiplier

            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                value = context.get("value", 1)
                result = value * self.multiplier
                return {"result": result}

        step = ParameterizedStep(name="parameterized_step", description="Step with parameters", multiplier=3)
        sample_context.set("value", 7)

        result = await step.execute(sample_context)
        assert result["result"] == 21


@pytest.mark.unit
class TestWebhookStep:
    """Tests for WebhookStep."""

    def test_webhook_step_creation(self) -> None:
        """Test creating a WebhookStep instance."""
        from litestar_workflows.core.types import StepType
        from litestar_workflows.steps.webhook import WebhookStep

        step = WebhookStep(
            name="webhook_step",
            callback_key="payment_data",
            description="Wait for payment callback",
        )

        assert step.name == "webhook_step"
        assert step.callback_key == "payment_data"
        assert step.description == "Wait for payment callback"
        assert step.step_type == StepType.WEBHOOK

    def test_webhook_step_default_callback_key(self) -> None:
        """Test WebhookStep with default callback_key."""
        from litestar_workflows.steps.webhook import WebhookStep

        step = WebhookStep(name="webhook_step")

        assert step.callback_key == "webhook_data"

    def test_webhook_step_default_description(self) -> None:
        """Test WebhookStep with default description."""
        from litestar_workflows.steps.webhook import WebhookStep

        step = WebhookStep(name="webhook_step", callback_key="data")

        assert step.description == ""


@pytest.mark.unit
@pytest.mark.asyncio
class TestWebhookStepExecution:
    """Tests for WebhookStep execution."""

    async def test_webhook_step_execute_with_data(self, sample_context: WorkflowContext) -> None:
        """Test webhook step execution retrieves callback data."""
        from litestar_workflows.steps.webhook import WebhookStep

        step = WebhookStep(name="webhook_step", callback_key="payment_data")

        # Simulate webhook data being set in context
        payment_data = {
            "transaction_id": "txn_123456",
            "amount": 99.99,
            "status": "completed",
        }
        sample_context.set("payment_data", payment_data)

        # Execute step
        result = await step.execute(sample_context)

        # Should return the webhook data
        assert result == payment_data
        assert result["transaction_id"] == "txn_123456"
        assert result["amount"] == 99.99

    async def test_webhook_step_execute_with_no_data(self, sample_context: WorkflowContext) -> None:
        """Test webhook step execution when no callback data is present."""
        from litestar_workflows.steps.webhook import WebhookStep

        step = WebhookStep(name="webhook_step", callback_key="missing_data")

        # Execute step without setting callback data
        result = await step.execute(sample_context)

        # Should return None
        assert result is None

    async def test_webhook_step_custom_callback_key(self, sample_context: WorkflowContext) -> None:
        """Test webhook step with custom callback key."""
        from litestar_workflows.steps.webhook import WebhookStep

        step = WebhookStep(name="webhook_step", callback_key="custom_key")

        custom_data = {"custom": "value", "count": 42}
        sample_context.set("custom_key", custom_data)

        result = await step.execute(sample_context)

        assert result == custom_data
        assert result["custom"] == "value"

    async def test_webhook_step_multiple_callbacks(self, sample_context: WorkflowContext) -> None:
        """Test multiple webhook steps with different callback keys."""
        from litestar_workflows.steps.webhook import WebhookStep

        webhook1 = WebhookStep(name="webhook1", callback_key="callback1")
        webhook2 = WebhookStep(name="webhook2", callback_key="callback2")

        # Set different data for each callback
        sample_context.set("callback1", {"data": "from_webhook1"})
        sample_context.set("callback2", {"data": "from_webhook2"})

        result1 = await webhook1.execute(sample_context)
        result2 = await webhook2.execute(sample_context)

        assert result1["data"] == "from_webhook1"
        assert result2["data"] == "from_webhook2"

    async def test_webhook_step_integration_scenario(self, sample_context: WorkflowContext) -> None:
        """Test webhook step in a realistic integration scenario."""
        from litestar_workflows.steps.webhook import WebhookStep

        # Create webhook step for external API callback
        webhook = WebhookStep(
            name="wait_for_verification",
            callback_key="verification_result",
            description="Wait for identity verification service",
        )

        # Simulate external service callback data
        verification_result = {
            "verified": True,
            "confidence": 0.95,
            "verified_at": "2024-01-15T10:30:00Z",
            "document_type": "passport",
        }
        sample_context.set("verification_result", verification_result)

        # Execute webhook step
        result = await webhook.execute(sample_context)

        # Verify the result
        assert result["verified"] is True
        assert result["confidence"] == 0.95
        assert result["document_type"] == "passport"
