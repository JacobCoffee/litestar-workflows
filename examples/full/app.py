"""Full example demonstrating advanced litestar-workflows features.

This example shows:
- Human approval tasks
- Conditional branching
- Parallel execution
- Multi-step workflows
- Complete REST API for workflow management

Run with:
    cd examples/full
    litestar run --port 8001

Or:
    uvicorn app:app --reload --port 8001
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from litestar import Controller, Litestar, get, post
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED

from litestar_workflows import (
    BaseHumanStep,
    BaseMachineStep,
    Edge,
    LocalExecutionEngine,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowPlugin,
    WorkflowPluginConfig,
    WorkflowRegistry,
    WorkflowStatus,
)


# =============================================================================
# Document Approval Workflow Steps
# =============================================================================


class SubmitDocument(BaseMachineStep):
    """Initial document submission step."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        """Process document submission."""
        doc_id = context.get("document_id")
        submitter = context.get("submitter")

        context.set("submission_timestamp", "2024-01-15T10:30:00Z")
        context.set("document_status", "submitted")

        return {
            "document_id": doc_id,
            "submitter": submitter,
            "status": "submitted",
        }


class ReviewDocument(BaseHumanStep):
    """Human review step for document approval."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        """Process the review decision."""
        decision = context.get("decision")
        comments = context.get("comments", "")

        context.set("review_decision", decision)
        context.set("review_comments", comments)

        return {"decision": decision, "comments": comments}


class ApproveDocument(BaseMachineStep):
    """Final approval step."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        """Mark document as approved."""
        doc_id = context.get("document_id")

        context.set("document_status", "approved")
        context.set("approval_timestamp", "2024-01-15T14:30:00Z")

        return {"document_id": doc_id, "status": "approved"}


class RejectDocument(BaseMachineStep):
    """Document rejection step."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        """Mark document as rejected."""
        doc_id = context.get("document_id")
        reason = context.get("review_comments", "No reason provided")

        context.set("document_status", "rejected")
        context.set("rejection_reason", reason)

        return {"document_id": doc_id, "status": "rejected", "reason": reason}


class RequestChanges(BaseMachineStep):
    """Request changes step."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        """Request changes to document."""
        doc_id = context.get("document_id")
        changes = context.get("review_comments", "Changes required")

        context.set("document_status", "changes_requested")
        context.set("requested_changes", changes)

        return {"document_id": doc_id, "status": "changes_requested", "changes": changes}


class NotifySubmitter(BaseMachineStep):
    """Notify the document submitter of the decision."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        """Send notification to submitter."""
        submitter = context.get("submitter")
        status = context.get("document_status")

        context.set("notification_sent", True)

        return {"notified": submitter, "status": status}


# =============================================================================
# Workflow Definitions
# =============================================================================


class DocumentApprovalWorkflow:
    """Document approval workflow with human review and conditional branching.

    Flow:
        submit_document -> review_document -> [approve|reject|request_changes] -> notify_submitter
    """

    __workflow_name__ = "document_approval"
    __workflow_version__ = "1.0.0"
    __workflow_description__ = "Document approval workflow with human review"

    @classmethod
    def get_definition(cls) -> WorkflowDefinition:
        """Get the workflow definition."""
        return WorkflowDefinition(
            name=cls.__workflow_name__,
            version=cls.__workflow_version__,
            description=cls.__workflow_description__,
            steps={
                "submit_document": SubmitDocument(
                    name="submit_document",
                    description="Submit document for review",
                ),
                "review_document": ReviewDocument(
                    name="review_document",
                    title="Review Document",
                    description="Human review of document",
                    form_schema={
                        "type": "object",
                        "properties": {
                            "decision": {
                                "type": "string",
                                "enum": ["approve", "reject", "request_changes"],
                                "title": "Decision",
                            },
                            "comments": {
                                "type": "string",
                                "title": "Comments",
                            },
                        },
                        "required": ["decision"],
                    },
                ),
                "approve_document": ApproveDocument(
                    name="approve_document",
                    description="Approve the document",
                ),
                "reject_document": RejectDocument(
                    name="reject_document",
                    description="Reject the document",
                ),
                "request_changes": RequestChanges(
                    name="request_changes",
                    description="Request changes to document",
                ),
                "notify_submitter": NotifySubmitter(
                    name="notify_submitter",
                    description="Notify submitter of decision",
                ),
            },
            edges=[
                Edge(source="submit_document", target="review_document"),
                Edge(
                    source="review_document",
                    target="approve_document",
                    condition="context.get('review_decision') == 'approve'",
                ),
                Edge(
                    source="review_document",
                    target="reject_document",
                    condition="context.get('review_decision') == 'reject'",
                ),
                Edge(
                    source="review_document",
                    target="request_changes",
                    condition="context.get('review_decision') == 'request_changes'",
                ),
                Edge(source="approve_document", target="notify_submitter"),
                Edge(source="reject_document", target="notify_submitter"),
                Edge(source="request_changes", target="notify_submitter"),
            ],
            initial_step="submit_document",
            terminal_steps={"notify_submitter"},
        )


# =============================================================================
# Simple Workflow (for basic testing)
# =============================================================================


class SimpleStep(BaseMachineStep):
    """Simple step that records execution."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        context.set("simple_executed", True)
        return {"success": True}


class SimpleWorkflow:
    """Simple single-step workflow for testing."""

    __workflow_name__ = "simple_workflow"
    __workflow_version__ = "1.0.0"
    __workflow_description__ = "Simple test workflow"

    @classmethod
    def get_definition(cls) -> WorkflowDefinition:
        """Get the workflow definition."""
        return WorkflowDefinition(
            name=cls.__workflow_name__,
            version=cls.__workflow_version__,
            description=cls.__workflow_description__,
            steps={"simple_step": SimpleStep(name="simple_step", description="A simple step")},
            edges=[],
            initial_step="simple_step",
            terminal_steps={"simple_step"},
        )


# =============================================================================
# API Controllers
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
            "steps": {
                step_name: {
                    "name": step.name,
                    "description": step.description,
                    "type": step.step_type.value,
                }
                for step_name, step in definition.steps.items()
            },
            "edges": [
                {
                    "source": e.get_source_name(),
                    "target": e.get_target_name(),
                    "condition": e.condition,
                }
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


class InstanceController(Controller):
    """REST API for workflow instance management."""

    path = "/instances"
    tags = ["Instances"]

    @get("/")
    async def list_instances(
        self,
        workflow_engine: LocalExecutionEngine,
    ) -> list[dict[str, Any]]:
        """List all workflow instances."""
        instances = workflow_engine.get_all_instances()
        return [
            {
                "instance_id": str(i.id),
                "workflow_name": i.workflow_name,
                "status": i.status.value,
                "current_step": i.current_step,
            }
            for i in instances
        ]

    @get("/{instance_id:uuid}")
    async def get_instance(
        self,
        instance_id: UUID,
        workflow_engine: LocalExecutionEngine,
    ) -> dict[str, Any]:
        """Get workflow instance details."""
        instance = await workflow_engine.get_instance(instance_id)
        return {
            "instance_id": str(instance.id),
            "workflow_name": instance.workflow_name,
            "status": instance.status.value,
            "current_step": instance.current_step,
            "data": instance.context.data,
            "step_history": [
                {
                    "step_name": h.step_name,
                    "status": str(h.status),
                    "result": h.result,
                }
                for h in instance.context.step_history
            ],
            "error": instance.error,
        }

    @post("/{instance_id:uuid}/complete-task")
    async def complete_human_task(
        self,
        instance_id: UUID,
        data: dict[str, Any],
        workflow_engine: LocalExecutionEngine,
    ) -> dict[str, Any]:
        """Complete a human task with provided data."""
        instance = await workflow_engine.get_instance(instance_id)

        if instance.status != WorkflowStatus.WAITING:
            return {
                "error": f"Instance is not waiting for input (status: {instance.status.value})",
                "instance_id": str(instance_id),
            }

        step_name = instance.current_step
        if step_name is None:
            return {
                "error": "Instance has no current step",
                "instance_id": str(instance_id),
            }

        user_id = data.pop("user_id", "anonymous")

        await workflow_engine.complete_human_task(
            instance_id=instance_id,
            step_name=step_name,
            user_id=user_id,
            data=data,
        )

        # Get updated instance
        instance = await workflow_engine.get_instance(instance_id)

        return {
            "instance_id": str(instance.id),
            "status": instance.status.value,
            "current_step": instance.current_step,
        }

    @post("/{instance_id:uuid}/cancel")
    async def cancel_workflow(
        self,
        instance_id: UUID,
        data: dict[str, Any],
        workflow_engine: LocalExecutionEngine,
    ) -> dict[str, Any]:
        """Cancel a running workflow."""
        reason = data.get("reason", "Canceled by user")
        await workflow_engine.cancel_workflow(instance_id, reason)

        instance = await workflow_engine.get_instance(instance_id)
        return {
            "instance_id": str(instance.id),
            "status": instance.status.value,
            "error": instance.error,
        }


# =============================================================================
# Application
# =============================================================================


@get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# Configure the plugin
plugin_config = WorkflowPluginConfig(
    auto_register_workflows=[DocumentApprovalWorkflow, SimpleWorkflow],
)

# Create the Litestar application
app = Litestar(
    route_handlers=[WorkflowController, InstanceController, health_check],
    plugins=[WorkflowPlugin(config=plugin_config)],
    debug=True,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
