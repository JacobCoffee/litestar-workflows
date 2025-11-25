"""Minimal example of litestar-workflows integration.

This example demonstrates the basic usage of the WorkflowPlugin
with a simple order processing workflow.

Run with:
    cd examples/minimal
    litestar run

Or:
    uvicorn app:app --reload
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from litestar import Controller, Litestar, get, post

from litestar_workflows import (
    BaseMachineStep,
    Edge,
    LocalExecutionEngine,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowPlugin,
    WorkflowPluginConfig,
    WorkflowRegistry,
)

# =============================================================================
# Step Definitions
# =============================================================================


class ValidateOrder(BaseMachineStep):
    """Validate the incoming order data."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        """Validate the order."""
        order_id = context.get("order_id")
        items = context.get("items", [])

        # Simulate validation
        is_valid = bool(order_id and items)
        context.set("validation_passed", is_valid)

        return {"order_id": order_id, "valid": is_valid, "item_count": len(items)}


class ProcessPayment(BaseMachineStep):
    """Process payment for the order."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        """Process the payment."""
        order_id = context.get("order_id")
        amount = context.get("amount", 0)

        # Simulate payment processing
        payment_id = f"PAY-{order_id}"
        context.set("payment_id", payment_id)

        return {"payment_id": payment_id, "amount": amount, "status": "completed"}


class FulfillOrder(BaseMachineStep):
    """Fulfill the order by preparing shipment."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        """Fulfill the order."""
        order_id = context.get("order_id")
        payment_id = context.get("payment_id")

        # Simulate fulfillment
        tracking_number = f"TRACK-{order_id}"
        context.set("tracking_number", tracking_number)

        return {
            "order_id": order_id,
            "payment_id": payment_id,
            "tracking_number": tracking_number,
            "status": "shipped",
        }


# =============================================================================
# Workflow Definition
# =============================================================================


class OrderWorkflow:
    """Order processing workflow definition.

    This workflow processes an order through validation, payment, and fulfillment.

    Flow:
        validate_order -> process_payment -> fulfill_order
    """

    __workflow_name__ = "order_processing"
    __workflow_version__ = "1.0.0"
    __workflow_description__ = "Process customer orders through validation, payment, and fulfillment"

    @classmethod
    def get_definition(cls) -> WorkflowDefinition:
        """Get the workflow definition."""
        return WorkflowDefinition(
            name=cls.__workflow_name__,
            version=cls.__workflow_version__,
            description=cls.__workflow_description__,
            steps={
                "validate_order": ValidateOrder(
                    name="validate_order",
                    description="Validate order data and check inventory",
                ),
                "process_payment": ProcessPayment(
                    name="process_payment",
                    description="Process payment through payment gateway",
                ),
                "fulfill_order": FulfillOrder(
                    name="fulfill_order",
                    description="Prepare order for shipment",
                ),
            },
            edges=[
                Edge(source="validate_order", target="process_payment"),
                Edge(source="process_payment", target="fulfill_order"),
            ],
            initial_step="validate_order",
            terminal_steps={"fulfill_order"},
        )


# =============================================================================
# API Controller
# =============================================================================


class WorkflowController(Controller):
    """REST API for workflow management."""

    path = "/workflows"
    tags = ["Workflows"]

    @get("/")
    async def list_workflows(
        self,
        workflow_registry: WorkflowRegistry,
    ) -> list[dict[str, Any]]:
        """List all registered workflows."""
        definitions = workflow_registry.list_definitions()
        return [
            {
                "name": d.name,
                "version": d.version,
                "description": d.description,
                "steps": list(d.steps.keys()),
                "initial_step": d.initial_step,
                "terminal_steps": list(d.terminal_steps),
            }
            for d in definitions
        ]

    @get("/{name:str}")
    async def get_workflow(
        self,
        name: str,
        workflow_registry: WorkflowRegistry,
    ) -> dict[str, Any]:
        """Get a specific workflow definition."""
        definition = workflow_registry.get_definition(name)
        return {
            "name": definition.name,
            "version": definition.version,
            "description": definition.description,
            "steps": list(definition.steps.keys()),
            "edges": [
                {"source": e.get_source_name(), "target": e.get_target_name(), "condition": e.condition}
                for e in definition.edges
            ],
            "initial_step": definition.initial_step,
            "terminal_steps": list(definition.terminal_steps),
            "mermaid": definition.to_mermaid(),
        }

    @post("/{name:str}/start")
    async def start_workflow(
        self,
        name: str,
        data: dict[str, Any],
        workflow_engine: LocalExecutionEngine,
        workflow_registry: WorkflowRegistry,
    ) -> dict[str, Any]:
        """Start a new workflow instance."""
        workflow_class = workflow_registry.get_workflow_class(name)
        instance = await workflow_engine.start_workflow(workflow_class, initial_data=data)
        return {
            "instance_id": str(instance.id),
            "workflow_name": instance.workflow_name,
            "status": instance.status.value,
        }

    @get("/instances/{instance_id:uuid}")
    async def get_instance(
        self,
        instance_id: UUID,
        workflow_engine: LocalExecutionEngine,
    ) -> dict[str, Any]:
        """Get workflow instance status."""
        instance = await workflow_engine.get_instance(instance_id)
        return {
            "instance_id": str(instance.id),
            "workflow_name": instance.workflow_name,
            "status": instance.status.value,
            "current_step": instance.current_step,
            "data": instance.context.data,
            "error": instance.error,
        }


# =============================================================================
# Application
# =============================================================================

# Configure the plugin
plugin_config = WorkflowPluginConfig(
    auto_register_workflows=[OrderWorkflow],
)

# Create the Litestar application
app = Litestar(
    route_handlers=[WorkflowController],
    plugins=[WorkflowPlugin(config=plugin_config)],
    debug=True,
)


# =============================================================================
# Health Check (for testing)
# =============================================================================


@get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# Add health check to app
app.register(health_check)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
