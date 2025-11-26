"""Full example demonstrating litestar-workflows with built-in REST API and persistence.

This example shows:
- Human approval tasks with form schemas
- Conditional branching based on human decisions
- SQLite database persistence with PersistentExecutionEngine
- Built-in REST API endpoints (auto-enabled)
- Complete workflow management lifecycle

Run with:
    cd examples/full
    uv run litestar run --port 8001

Or:
    uv run uvicorn app:app --reload --port 8001

API Endpoints (auto-enabled):
    Definitions:
        GET  /workflows/definitions                     - List all workflows
        GET  /workflows/definitions/{name}              - Get workflow details
        GET  /workflows/definitions/{name}/graph        - Get MermaidJS graph

    Instances:
        POST /workflows/instances                       - Start a workflow
        GET  /workflows/instances                       - List instances
        GET  /workflows/instances/{id}                  - Get instance details
        GET  /workflows/instances/{id}/graph            - Get instance graph with state
        POST /workflows/instances/{id}/cancel           - Cancel a workflow

    Human Tasks:
        GET  /workflows/tasks                           - List pending tasks
        GET  /workflows/tasks/{id}                      - Get task details
        POST /workflows/tasks/{id}/complete             - Complete a task
        POST /workflows/tasks/{id}/reassign             - Reassign a task

Example API Usage:
    # List available workflows
    curl http://localhost:8001/workflows/definitions

    # Start a document approval workflow
    curl -X POST http://localhost:8001/workflows/instances \\
        -H "Content-Type: application/json" \\
        -d '{
            "definition_name": "document_approval",
            "input_data": {
                "document_id": "DOC-001",
                "submitter": "alice@example.com",
                "title": "Q4 Budget Report"
            },
            "user_id": "alice"
        }'

    # List pending human tasks
    curl http://localhost:8001/workflows/tasks

    # Complete a human review task
    curl -X POST http://localhost:8001/workflows/tasks/{task_id}/complete \\
        -H "Content-Type: application/json" \\
        -d '{
            "completed_by": "manager@example.com",
            "output_data": {
                "decision": "approve",
                "comments": "Looks good, approved!"
            }
        }'

    # View workflow graph
    curl http://localhost:8001/workflows/definitions/document_approval/graph
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar import Litestar, Router, get
from litestar.di import Provide
from litestar.openapi import OpenAPIConfig
from litestar.plugins.sqlalchemy import SQLAlchemyAsyncConfig, SQLAlchemyPlugin

from litestar_workflows import (
    BaseHumanStep,
    BaseMachineStep,
    Edge,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowRegistry,
)
from litestar_workflows.db import (
    HumanTaskRepository,
    PersistentExecutionEngine,
    WorkflowDefinitionModel,
    WorkflowInstanceRepository,
)
from litestar_workflows.web.controllers import (
    HumanTaskController,
    WorkflowDefinitionController,
    WorkflowInstanceController,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# =============================================================================
# Document Approval Workflow Steps
# =============================================================================


class SubmitDocument(BaseMachineStep):
    """Initial document submission step.

    Records the document submission and prepares it for human review.
    """

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        """Process document submission."""
        doc_id = context.get("document_id")
        submitter = context.get("submitter")
        title = context.get("title", "Untitled Document")

        context.set("submission_timestamp", "2024-01-15T10:30:00Z")
        context.set("document_status", "submitted")

        return {
            "document_id": doc_id,
            "submitter": submitter,
            "title": title,
            "status": "submitted",
        }


class ReviewDocument(BaseHumanStep):
    """Human review step for document approval.

    Presents a form to the reviewer with approve/reject/request changes options.
    The form schema is defined in the step configuration and rendered by the UI.
    """

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        """Process the review decision after human input."""
        decision = context.get("decision")
        comments = context.get("comments", "")

        context.set("review_decision", decision)
        context.set("review_comments", comments)
        context.set("reviewer", context.get("completed_by", "unknown"))

        return {"decision": decision, "comments": comments}


class ApproveDocument(BaseMachineStep):
    """Final approval step - marks document as approved."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        """Mark document as approved."""
        doc_id = context.get("document_id")

        context.set("document_status", "approved")
        context.set("approval_timestamp", "2024-01-15T14:30:00Z")

        return {"document_id": doc_id, "status": "approved"}


class RejectDocument(BaseMachineStep):
    """Document rejection step - marks document as rejected with reason."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        """Mark document as rejected."""
        doc_id = context.get("document_id")
        reason = context.get("review_comments", "No reason provided")

        context.set("document_status", "rejected")
        context.set("rejection_reason", reason)

        return {"document_id": doc_id, "status": "rejected", "reason": reason}


class RequestChanges(BaseMachineStep):
    """Request changes step - sends document back for revision."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        """Request changes to document."""
        doc_id = context.get("document_id")
        changes = context.get("review_comments", "Changes required")

        context.set("document_status", "changes_requested")
        context.set("requested_changes", changes)

        return {"document_id": doc_id, "status": "changes_requested", "changes": changes}


class NotifySubmitter(BaseMachineStep):
    """Notification step - notifies the submitter of the final decision."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        """Send notification to submitter."""
        submitter = context.get("submitter")
        status = context.get("document_status")
        doc_id = context.get("document_id")

        context.set("notification_sent", True)

        # In a real application, this would send an email or push notification
        return {
            "notified": submitter,
            "document_id": doc_id,
            "final_status": status,
            "message": f"Document {doc_id} has been {status}",
        }


# =============================================================================
# Workflow Definitions
# =============================================================================


class DocumentApprovalWorkflow:
    """Document approval workflow with human review and conditional branching.

    This workflow demonstrates:
    - Human task with JSON Schema form
    - Conditional branching based on human decision
    - Multiple terminal paths (approve/reject/request changes)
    - Notification step at the end

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
                    description="Review the submitted document and make a decision",
                    form_schema={
                        "type": "object",
                        "title": "Document Review Form",
                        "properties": {
                            "decision": {
                                "type": "string",
                                "title": "Decision",
                                "enum": ["approve", "reject", "request_changes"],
                                "enumNames": ["Approve", "Reject", "Request Changes"],
                                "description": "Select your decision for this document",
                            },
                            "comments": {
                                "type": "string",
                                "title": "Comments",
                                "description": "Add any comments or feedback",
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
# Simple Workflow (for quick testing)
# =============================================================================


class SimpleStep(BaseMachineStep):
    """Simple step that records execution - useful for testing."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        context.set("simple_executed", True)
        return {"success": True, "message": "Simple workflow completed!"}


class SimpleWorkflow:
    """Simple single-step workflow for basic testing.

    This workflow completes immediately without human intervention.
    Useful for testing the API and verifying the setup works.
    """

    __workflow_name__ = "simple_workflow"
    __workflow_version__ = "1.0.0"
    __workflow_description__ = "Simple test workflow that completes immediately"

    @classmethod
    def get_definition(cls) -> WorkflowDefinition:
        """Get the workflow definition."""
        return WorkflowDefinition(
            name=cls.__workflow_name__,
            version=cls.__workflow_version__,
            description=cls.__workflow_description__,
            steps={"simple_step": SimpleStep(name="simple_step", description="A simple automated step")},
            edges=[],
            initial_step="simple_step",
            terminal_steps={"simple_step"},
        )


# =============================================================================
# Dependency Providers
# =============================================================================

# Global registry - shared across requests
_registry = WorkflowRegistry()
_registry.register(DocumentApprovalWorkflow)
_registry.register(SimpleWorkflow)


def provide_registry() -> WorkflowRegistry:
    """Provide the workflow registry."""
    return _registry


async def provide_workflow_engine(db_session: AsyncSession) -> PersistentExecutionEngine:
    """Provide a PersistentExecutionEngine with database session."""
    return PersistentExecutionEngine(
        registry=_registry,
        session=db_session,
    )


async def provide_workflow_instance_repo(db_session: AsyncSession) -> WorkflowInstanceRepository:
    """Provide WorkflowInstanceRepository with database session."""
    return WorkflowInstanceRepository(session=db_session)


async def provide_human_task_repo(db_session: AsyncSession) -> HumanTaskRepository:
    """Provide HumanTaskRepository with database session."""
    return HumanTaskRepository(session=db_session)


# =============================================================================
# Application Setup
# =============================================================================


@get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "litestar-workflows-example"}


@get("/")
async def index() -> dict[str, Any]:
    """API documentation index."""
    return {
        "name": "Litestar Workflows Example",
        "description": "Full example with built-in REST API and persistence",
        "endpoints": {
            "openapi": "/schema",
            "health": "/health",
            "workflows": {
                "definitions": "/workflows/definitions",
                "instances": "/workflows/instances",
                "tasks": "/workflows/tasks",
            },
        },
        "example_usage": {
            "start_simple_workflow": {
                "method": "POST",
                "url": "/workflows/instances",
                "body": {
                    "definition_name": "simple_workflow",
                    "input_data": {},
                    "user_id": "demo-user",
                },
            },
            "start_document_approval": {
                "method": "POST",
                "url": "/workflows/instances",
                "body": {
                    "definition_name": "document_approval",
                    "input_data": {
                        "document_id": "DOC-001",
                        "submitter": "alice@example.com",
                        "title": "Q4 Budget Report",
                    },
                    "user_id": "alice",
                },
            },
        },
    }


# Database configuration - SQLite for simplicity
# In production, use PostgreSQL or another production database
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///./workflows.db",
    metadata=WorkflowDefinitionModel.metadata,
    create_all=True,  # Auto-create tables on startup
)

# Create workflow API router with proper dependency injection
workflow_router = Router(
    path="/workflows",
    route_handlers=[
        WorkflowDefinitionController,
        WorkflowInstanceController,
        HumanTaskController,
    ],
    dependencies={
        "workflow_registry": Provide(provide_registry, sync_to_thread=False),
        "workflow_engine": Provide(provide_workflow_engine),
        "workflow_instance_repo": Provide(provide_workflow_instance_repo),
        "human_task_repo": Provide(provide_human_task_repo),
    },
    tags=["Workflows"],
)

# Create the Litestar application
app = Litestar(
    route_handlers=[health_check, index, workflow_router],
    plugins=[
        SQLAlchemyPlugin(config=sqlalchemy_config),
    ],
    openapi_config=OpenAPIConfig(
        title="Litestar Workflows - Full Example",
        version="1.0.0",
        description=(
            "Full example demonstrating litestar-workflows with human tasks, "
            "conditional branching, database persistence, and built-in REST API."
        ),
    ),
    debug=True,
)


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 80)
    print("Litestar Workflows - Full Example")
    print("=" * 80)
    print("\nStarting server on http://localhost:8001")
    print("\nKey endpoints:")
    print("  - http://localhost:8001/          - API index")
    print("  - http://localhost:8001/schema    - OpenAPI documentation")
    print("  - http://localhost:8001/health    - Health check")
    print("\nWorkflow API:")
    print("  - GET  /workflows/definitions     - List workflows")
    print("  - POST /workflows/instances       - Start a workflow")
    print("  - GET  /workflows/tasks           - List pending human tasks")
    print("=" * 80 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8001)
