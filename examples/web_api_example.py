"""Example demonstrating the WorkflowPlugin REST API endpoints.

This example shows how to use the WorkflowPlugin to expose workflow management
through REST API endpoints. The API is automatically enabled by default in the
WorkflowPlugin. It creates a simple approval workflow and demonstrates the
available API endpoints.

Run this example with:
    uv run python examples/web_api_example.py

Then access the API at:
    - http://localhost:8000/workflows/definitions - List workflow definitions
    - http://localhost:8000/workflows/instances - List workflow instances
    - http://localhost:8000/workflows/tasks - List human tasks
    - http://localhost:8000/schema - OpenAPI documentation
"""

from __future__ import annotations

from litestar import Litestar
from litestar.openapi import OpenAPIConfig

from litestar_workflows import WorkflowPlugin, WorkflowPluginConfig
from litestar_workflows.core.context import WorkflowContext
from litestar_workflows.core.definition import Edge, WorkflowDefinition
from litestar_workflows.steps.base import BaseMachineStep


# Define a simple approval workflow
class SubmitStep(BaseMachineStep):
    """Submit a request for approval."""

    async def execute(self, context: WorkflowContext) -> dict:
        """Execute the submission step."""
        request_data = context.get("request_data", {})
        context.set("submitted", True)
        context.set("status", "pending_review")
        return {"status": "submitted", "data": request_data}


class ReviewStep(BaseMachineStep):
    """Review the submitted request."""

    async def execute(self, context: WorkflowContext) -> dict:
        """Execute the review step."""
        # In a real workflow, this would be a human task
        # For demo purposes, we auto-approve
        context.set("reviewed", True)
        context.set("approved", True)
        return {"status": "approved"}


class ApproveStep(BaseMachineStep):
    """Finalize the approval."""

    async def execute(self, context: WorkflowContext) -> dict:
        """Execute the approval step."""
        context.set("final_status", "approved")
        return {"status": "completed"}


# Create the workflow definition
approval_definition = WorkflowDefinition(
    name="approval_workflow",
    version="1.0.0",
    description="Simple approval workflow for demonstration",
    steps={
        "submit": SubmitStep(name="submit", description="Submit request"),
        "review": ReviewStep(name="review", description="Review request"),
        "approve": ApproveStep(name="approve", description="Approve request"),
    },
    edges=[
        Edge(source="submit", target="review"),
        Edge(source="review", target="approve"),
    ],
    initial_step="submit",
    terminal_steps={"approve"},
)


# Create a mock workflow class for registration
class ApprovalWorkflow:
    """Approval workflow class."""

    __workflow_name__ = "approval_workflow"
    __workflow_version__ = "1.0.0"

    @classmethod
    def get_definition(cls) -> WorkflowDefinition:
        """Get the workflow definition."""
        return approval_definition


# Configure the application
def create_app() -> Litestar:
    """Create and configure the Litestar application.

    Returns:
        Configured Litestar application with workflow plugin.
    """
    # Configure the workflow plugin with API enabled
    workflow_config = WorkflowPluginConfig(
        auto_register_workflows=[ApprovalWorkflow],
        # API is enabled by default (enable_api=True)
        api_path_prefix="/workflows",
        api_tags=["Workflows API"],
        include_api_in_schema=True,
    )

    # Create the application
    app = Litestar(
        plugins=[
            WorkflowPlugin(config=workflow_config),
        ],
        openapi_config=OpenAPIConfig(
            title="Workflow Management API",
            version="1.0.0",
            description="REST API for managing workflows, instances, and human tasks",
        ),
        debug=True,
    )

    return app


if __name__ == "__main__":
    import uvicorn

    app = create_app()

    print("\n" + "=" * 80)
    print("Workflow Management API Server")
    print("=" * 80)
    print("\nAvailable endpoints:")
    print("  • http://localhost:8000/schema - OpenAPI documentation")
    print("  • http://localhost:8000/workflows/definitions - List workflow definitions")
    print("  • http://localhost:8000/workflows/definitions/approval_workflow - Get specific definition")
    print("  • http://localhost:8000/workflows/definitions/approval_workflow/graph - Get workflow graph")
    print("  • http://localhost:8000/workflows/instances - List workflow instances")
    print("  • http://localhost:8000/workflows/tasks - List human tasks")
    print("\nStarting server on http://localhost:8000")
    print("=" * 80 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
