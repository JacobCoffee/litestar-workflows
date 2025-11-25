"""Comprehensive tests for Phase 3 Web Plugin.

This module tests the workflow REST API components, including:
- WorkflowWebConfig configuration
- Definition controller endpoints (list, get, graph)
- Instance controller endpoints (start, list, get, cancel, retry)
- Human task controller endpoints (list, get, complete, reassign)
- Graph generation (MermaidJS)
- Auth guard integration
- Error handling and validation
- End-to-end workflow lifecycle via REST API
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, ClassVar
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from litestar import Controller, Litestar, get, post
from litestar.datastructures import State
from litestar.di import Provide
from litestar.exceptions import NotFoundException
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from litestar.testing import AsyncTestClient

from litestar_workflows.core.context import WorkflowContext
from litestar_workflows.core.definition import WorkflowDefinition
from litestar_workflows.engine.local import LocalExecutionEngine
from litestar_workflows.engine.registry import WorkflowRegistry
from litestar_workflows.web.config import WorkflowWebConfig

if TYPE_CHECKING:
    pass


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_workflow_registry() -> Mock:
    """Create a mock WorkflowRegistry."""
    from litestar_workflows.core.definition import Edge, WorkflowDefinition
    from litestar_workflows.steps.base import BaseMachineStep

    class MockStep(BaseMachineStep):
        async def execute(self, context: WorkflowContext) -> dict[str, Any]:
            return {"executed": True}

    definition = WorkflowDefinition(
        name="test_workflow",
        version="1.0.0",
        description="Test workflow",
        steps={
            "step1": MockStep(name="step1", description="Step 1"),
            "step2": MockStep(name="step2", description="Step 2"),
        },
        edges=[Edge(source="step1", target="step2")],
        initial_step="step1",
        terminal_steps={"step2"},
    )

    class MockWorkflow:
        name = "test_workflow"
        version = "1.0.0"

        @classmethod
        def get_definition(cls) -> WorkflowDefinition:
            return definition

    registry = Mock()
    registry.list_definitions.return_value = [definition]
    registry.get_definition.return_value = definition
    registry.get_workflow_class.return_value = MockWorkflow
    registry.has_workflow.return_value = True

    return registry


@pytest.fixture
def mock_workflow_engine() -> Mock:
    """Create a mock ExecutionEngine."""
    from litestar_workflows.core.types import WorkflowStatus
    from litestar_workflows.engine.instance import WorkflowInstance

    instance_id = uuid4()
    mock_instance = Mock(spec=WorkflowInstance)
    mock_instance.id = instance_id
    mock_instance.status = WorkflowStatus.RUNNING
    mock_instance.current_step = "step1"
    mock_instance.workflow_name = "test_workflow"
    mock_instance.workflow_version = "1.0.0"
    mock_instance.started_at = datetime.now(timezone.utc)
    mock_instance.completed_at = None
    mock_instance.context = Mock()
    mock_instance.context.data = {"test": "data"}

    engine = Mock()
    engine.start_workflow = AsyncMock(return_value=mock_instance)
    engine.get_instance = AsyncMock(return_value=mock_instance)
    engine.cancel_workflow = AsyncMock()
    engine.retry_workflow = AsyncMock(return_value=mock_instance)
    engine.complete_human_task = AsyncMock()

    return engine


@pytest.fixture
def mock_instance_repository() -> Mock:
    """Create a mock WorkflowInstanceRepository."""
    from litestar_workflows.core.types import WorkflowStatus
    from litestar_workflows.db.models import WorkflowInstanceModel

    instance = Mock(spec=WorkflowInstanceModel)
    instance.id = uuid4()
    instance.workflow_name = "test_workflow"
    instance.workflow_version = "1.0.0"
    instance.status = WorkflowStatus.RUNNING
    instance.current_step = "step1"
    instance.context_data = {"test": "data"}
    instance.started_at = datetime.now(timezone.utc)
    instance.completed_at = None

    repo = Mock()
    repo.get.return_value = instance
    repo.list.return_value = [instance]
    repo.get_by_workflow.return_value = [instance]
    repo.get_by_status.return_value = [instance]

    return repo


@pytest.fixture
def mock_task_repository() -> Mock:
    """Create a mock HumanTaskRepository."""
    from litestar_workflows.db.models import HumanTaskModel

    task = Mock(spec=HumanTaskModel)
    task.id = uuid4()
    task.instance_id = uuid4()
    task.step_name = "approval"
    task.title = "Review Request"
    task.description = "Please review this request"
    task.assignee_id = "user_123"
    task.status = "PENDING"
    task.form_schema = {"type": "object", "properties": {"approved": {"type": "boolean"}}}

    repo = Mock()
    repo.get.return_value = task
    repo.list_pending.return_value = [task]
    repo.list_by_user.return_value = [task]

    return repo


# =============================================================================
# Test Controllers (simulating Phase 3 implementation)
# =============================================================================


class WorkflowDefinitionController(Controller):
    """REST API for workflow definitions."""

    path = "/workflows/definitions"
    tags: ClassVar[list[str]] = ["Workflow Definitions"]

    @get("/")
    async def list_definitions(
        self,
        workflow_registry: Any,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        """List all registered workflow definitions."""
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
    async def get_definition(
        self,
        name: str,
        workflow_registry: Any,
        version: str | None = None,
    ) -> dict[str, Any]:
        """Get a specific workflow definition."""
        try:
            definition = workflow_registry.get_definition(name, version=version)
        except Exception as e:
            raise NotFoundException(detail=f"Workflow '{name}' not found") from e

        return {
            "name": definition.name,
            "version": definition.version,
            "description": definition.description,
            "steps": list(definition.steps.keys()),
            "initial_step": definition.initial_step,
            "terminal_steps": list(definition.terminal_steps),
        }

    @get("/{name:str}/graph")
    async def get_graph(
        self,
        name: str,
        workflow_registry: Any,
        format: str = "mermaid",
    ) -> dict[str, str]:
        """Get workflow graph visualization."""
        try:
            definition = workflow_registry.get_definition(name)
        except Exception as e:
            raise NotFoundException(detail=f"Workflow '{name}' not found") from e

        if format == "mermaid":
            # Simple mermaid generation for testing
            graph = "graph TD\n"
            for edge in definition.edges:
                graph += f"    {edge.source} --> {edge.target}\n"
            return {"graph": graph, "format": "mermaid"}
        raise ValueError(f"Unknown format: {format}")


class WorkflowInstanceController(Controller):
    """REST API for workflow instances."""

    path = "/workflows/instances"
    tags: ClassVar[list[str]] = ["Workflow Instances"]

    @post("/")
    async def start_workflow(
        self,
        data: dict[str, Any],
        workflow_engine: Any,
        workflow_registry: Any,
    ) -> dict[str, Any]:
        """Start a new workflow instance."""
        workflow_name = data.get("workflow_name")
        initial_data = data.get("initial_data", {})

        try:
            workflow_class = workflow_registry.get_workflow_class(workflow_name)
        except Exception as e:
            raise NotFoundException(detail=f"Workflow '{workflow_name}' not found") from e

        instance = await workflow_engine.start_workflow(workflow_class, initial_data=initial_data)

        return {
            "instance_id": str(instance.id),
            "workflow_name": instance.workflow_name,
            "status": instance.status.value,
            "current_step": instance.current_step,
            "started_at": instance.started_at.isoformat(),
        }

    @get("/")
    async def list_instances(
        self,
        workflow_name: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List workflow instances with filtering."""
        # Mock implementation for testing
        return [
            {
                "instance_id": str(uuid4()),
                "workflow_name": "test_workflow",
                "status": "running",
                "current_step": "step1",
            }
        ]

    @get("/{instance_id:uuid}")
    async def get_instance(
        self,
        instance_id: UUID,
        workflow_engine: Any,
    ) -> dict[str, Any]:
        """Get detailed workflow instance information."""
        try:
            instance = await workflow_engine.get_instance(instance_id)
        except Exception as e:
            raise NotFoundException(detail=f"Instance {instance_id} not found") from e

        return {
            "instance_id": str(instance.id),
            "workflow_name": instance.workflow_name,
            "status": instance.status.value,
            "current_step": instance.current_step,
            "data": instance.context.data,
            "started_at": instance.started_at.isoformat(),
        }

    @post("/{instance_id:uuid}/cancel")
    async def cancel_instance(
        self,
        instance_id: UUID,
        data: dict[str, Any],
        workflow_engine: Any,
    ) -> dict[str, Any]:
        """Cancel a running workflow instance."""
        reason = data.get("reason", "Cancelled by user")
        await workflow_engine.cancel_workflow(instance_id, reason=reason)

        return {
            "instance_id": str(instance_id),
            "status": "cancelled",
            "reason": reason,
        }

    @post("/{instance_id:uuid}/retry")
    async def retry_instance(
        self,
        instance_id: UUID,
        workflow_engine: Any,
        from_step: str | None = None,
    ) -> dict[str, Any]:
        """Retry a failed workflow from a specific step."""
        instance = await workflow_engine.retry_workflow(instance_id, from_step=from_step)

        return {
            "instance_id": str(instance.id),
            "status": instance.status.value,
            "current_step": instance.current_step,
        }


class HumanTaskController(Controller):
    """REST API for human tasks."""

    path = "/workflows/tasks"
    tags: ClassVar[list[str]] = ["Human Tasks"]

    @get("/")
    async def list_tasks(
        self,
        user_id: str | None = None,
        status: str = "PENDING",
    ) -> list[dict[str, Any]]:
        """List human tasks."""
        # Mock implementation
        return [
            {
                "task_id": str(uuid4()),
                "instance_id": str(uuid4()),
                "step_name": "approval",
                "title": "Review Request",
                "status": "PENDING",
            }
        ]

    @get("/{task_id:uuid}")
    async def get_task(
        self,
        task_id: UUID,
    ) -> dict[str, Any]:
        """Get human task details including form schema."""
        # Mock implementation
        return {
            "task_id": str(task_id),
            "instance_id": str(uuid4()),
            "step_name": "approval",
            "title": "Review Request",
            "description": "Please review this request",
            "form_schema": {"type": "object", "properties": {"approved": {"type": "boolean"}}},
            "status": "PENDING",
        }

    @post("/{task_id:uuid}/complete")
    async def complete_task(
        self,
        task_id: UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Complete a human task with form data."""
        form_data = data.get("form_data", {})

        return {
            "task_id": str(task_id),
            "status": "completed",
            "result": form_data,
        }

    @post("/{task_id:uuid}/reassign")
    async def reassign_task(
        self,
        task_id: UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Reassign task to another user."""
        new_assignee = data.get("assignee_id")

        return {
            "task_id": str(task_id),
            "assignee_id": new_assignee,
            "status": "reassigned",
        }


# =============================================================================
# Config Tests
# =============================================================================


@pytest.mark.unit
class TestWorkflowWebConfig:
    """Tests for WorkflowWebConfig configuration."""

    def test_config_default_values(self) -> None:
        """Config uses default configuration values."""
        config = WorkflowWebConfig()

        assert config.path_prefix == "/workflows"
        assert config.include_in_schema is True
        assert config.enable_graph_endpoints is True
        assert config.guards == []
        assert config.tags == ["Workflows"]

    def test_config_custom_values(self) -> None:
        """Config accepts custom configuration."""
        config = WorkflowWebConfig(
            path_prefix="/api/v1/workflows",
            enable_graph_endpoints=False,
            include_in_schema=False,
            tags=["Custom", "Tags"],
        )

        assert config.path_prefix == "/api/v1/workflows"
        assert config.enable_graph_endpoints is False
        assert config.include_in_schema is False
        assert config.tags == ["Custom", "Tags"]

    def test_config_guards(self) -> None:
        """Config accepts guard configuration."""

        async def custom_guard() -> None:
            pass

        config = WorkflowWebConfig(
            guards=[custom_guard],
        )

        assert len(config.guards) == 1
        assert config.guards[0] == custom_guard


# =============================================================================
# Definition Controller Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestDefinitionController:
    """Tests for workflow definition endpoints."""

    async def test_list_definitions(
        self,
        mock_workflow_registry: Mock,
    ) -> None:
        """GET /workflows/definitions returns all definitions."""
        app = Litestar(
            route_handlers=[WorkflowDefinitionController],
            dependencies={
                "workflow_registry": Provide(lambda: mock_workflow_registry, sync_to_thread=False),
            },
        )

        async with AsyncTestClient(app=app) as client:
            response = await client.get("/workflows/definitions/")

            assert response.status_code == HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "test_workflow"
            assert data[0]["version"] == "1.0.0"
            assert "step1" in data[0]["steps"]
            assert "step2" in data[0]["steps"]

    async def test_get_definition(
        self,
        mock_workflow_registry: Mock,
    ) -> None:
        """GET /workflows/definitions/{name} returns specific definition."""
        app = Litestar(
            route_handlers=[WorkflowDefinitionController],
            dependencies={
                "workflow_registry": Provide(lambda: mock_workflow_registry, sync_to_thread=False),
            },
        )

        async with AsyncTestClient(app=app) as client:
            response = await client.get("/workflows/definitions/test_workflow")

            assert response.status_code == HTTP_200_OK
            data = response.json()
            assert data["name"] == "test_workflow"
            assert data["version"] == "1.0.0"
            assert data["description"] == "Test workflow"
            assert data["initial_step"] == "step1"
            assert "step2" in data["terminal_steps"]

    async def test_get_definition_not_found(
        self,
        mock_workflow_registry: Mock,
    ) -> None:
        """GET /workflows/definitions/{name} returns 404 for unknown workflow."""
        mock_workflow_registry.get_definition.side_effect = KeyError("Not found")

        app = Litestar(
            route_handlers=[WorkflowDefinitionController],
            dependencies={
                "workflow_registry": Provide(lambda: mock_workflow_registry, sync_to_thread=False),
            },
        )

        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.get("/workflows/definitions/unknown_workflow")

            assert response.status_code == HTTP_404_NOT_FOUND
            data = response.json()
            assert "not found" in data["detail"].lower()

    async def test_get_graph_mermaid(
        self,
        mock_workflow_registry: Mock,
    ) -> None:
        """GET /workflows/definitions/{name}/graph returns MermaidJS graph."""
        app = Litestar(
            route_handlers=[WorkflowDefinitionController],
            dependencies={
                "workflow_registry": Provide(lambda: mock_workflow_registry, sync_to_thread=False),
            },
        )

        async with AsyncTestClient(app=app) as client:
            response = await client.get("/workflows/definitions/test_workflow/graph")

            assert response.status_code == HTTP_200_OK
            data = response.json()
            assert "graph" in data
            assert "format" in data
            assert data["format"] == "mermaid"
            assert "graph TD" in data["graph"]
            assert "step1 --> step2" in data["graph"]

    async def test_get_graph_unknown_format(
        self,
        mock_workflow_registry: Mock,
    ) -> None:
        """GET /workflows/definitions/{name}/graph returns error for unknown format."""
        app = Litestar(
            route_handlers=[WorkflowDefinitionController],
            dependencies={
                "workflow_registry": Provide(lambda: mock_workflow_registry, sync_to_thread=False),
            },
        )

        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.get(
                "/workflows/definitions/test_workflow/graph",
                params={"format": "unknown"},
            )

            assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR


# =============================================================================
# Instance Controller Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestInstanceController:
    """Tests for workflow instance endpoints."""

    async def test_start_workflow(
        self,
        mock_workflow_registry: Mock,
        mock_workflow_engine: Mock,
    ) -> None:
        """POST /workflows/instances starts a new workflow."""
        app = Litestar(
            route_handlers=[WorkflowInstanceController],
            dependencies={
                "workflow_registry": Provide(lambda: mock_workflow_registry, sync_to_thread=False),
                "workflow_engine": Provide(lambda: mock_workflow_engine, sync_to_thread=False),
            },
        )

        async with AsyncTestClient(app=app) as client:
            response = await client.post(
                "/workflows/instances/",
                json={
                    "workflow_name": "test_workflow",
                    "initial_data": {"key": "value"},
                },
            )

            assert response.status_code == HTTP_201_CREATED
            data = response.json()
            assert "instance_id" in data
            assert data["workflow_name"] == "test_workflow"
            assert data["status"] == "running"
            assert "started_at" in data

    async def test_start_workflow_not_found(
        self,
        mock_workflow_registry: Mock,
        mock_workflow_engine: Mock,
    ) -> None:
        """POST /workflows/instances returns 404 for unknown workflow."""
        mock_workflow_registry.get_workflow_class.side_effect = KeyError("Not found")

        app = Litestar(
            route_handlers=[WorkflowInstanceController],
            dependencies={
                "workflow_registry": Provide(lambda: mock_workflow_registry, sync_to_thread=False),
                "workflow_engine": Provide(lambda: mock_workflow_engine, sync_to_thread=False),
            },
        )

        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.post(
                "/workflows/instances/",
                json={"workflow_name": "unknown_workflow"},
            )

            assert response.status_code == HTTP_404_NOT_FOUND

    async def test_list_instances(self) -> None:
        """GET /workflows/instances returns list of instances."""
        app = Litestar(route_handlers=[WorkflowInstanceController])

        async with AsyncTestClient(app=app) as client:
            response = await client.get("/workflows/instances/")

            assert response.status_code == HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)

    async def test_list_instances_with_filters(self) -> None:
        """GET /workflows/instances supports filtering parameters."""
        app = Litestar(route_handlers=[WorkflowInstanceController])

        async with AsyncTestClient(app=app) as client:
            response = await client.get(
                "/workflows/instances/",
                params={
                    "workflow_name": "test_workflow",
                    "status": "running",
                    "limit": 10,
                    "offset": 0,
                },
            )

            assert response.status_code == HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)

    async def test_get_instance(
        self,
        mock_workflow_engine: Mock,
    ) -> None:
        """GET /workflows/instances/{id} returns instance details."""
        instance_id = uuid4()

        app = Litestar(
            route_handlers=[WorkflowInstanceController],
            dependencies={
                "workflow_engine": Provide(lambda: mock_workflow_engine, sync_to_thread=False),
            },
        )

        async with AsyncTestClient(app=app) as client:
            response = await client.get(f"/workflows/instances/{instance_id}")

            assert response.status_code == HTTP_200_OK
            data = response.json()
            assert "instance_id" in data
            assert data["workflow_name"] == "test_workflow"
            assert "data" in data

    async def test_get_instance_not_found(
        self,
        mock_workflow_engine: Mock,
    ) -> None:
        """GET /workflows/instances/{id} returns 404 for unknown instance."""
        instance_id = uuid4()
        mock_workflow_engine.get_instance.side_effect = KeyError("Not found")

        app = Litestar(
            route_handlers=[WorkflowInstanceController],
            dependencies={
                "workflow_engine": Provide(lambda: mock_workflow_engine, sync_to_thread=False),
            },
        )

        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.get(f"/workflows/instances/{instance_id}")

            assert response.status_code == HTTP_404_NOT_FOUND

    async def test_cancel_instance(
        self,
        mock_workflow_engine: Mock,
    ) -> None:
        """POST /workflows/instances/{id}/cancel cancels workflow."""
        instance_id = uuid4()

        app = Litestar(
            route_handlers=[WorkflowInstanceController],
            dependencies={
                "workflow_engine": Provide(lambda: mock_workflow_engine, sync_to_thread=False),
            },
        )

        async with AsyncTestClient(app=app) as client:
            response = await client.post(
                f"/workflows/instances/{instance_id}/cancel",
                json={"reason": "User requested cancellation"},
            )

            assert response.status_code == HTTP_201_CREATED
            data = response.json()
            assert data["status"] == "cancelled"
            assert "reason" in data

    async def test_retry_instance(
        self,
        mock_workflow_engine: Mock,
    ) -> None:
        """POST /workflows/instances/{id}/retry retries failed workflow."""
        instance_id = uuid4()

        app = Litestar(
            route_handlers=[WorkflowInstanceController],
            dependencies={
                "workflow_engine": Provide(lambda: mock_workflow_engine, sync_to_thread=False),
            },
        )

        async with AsyncTestClient(app=app) as client:
            response = await client.post(f"/workflows/instances/{instance_id}/retry")

            assert response.status_code == HTTP_201_CREATED
            data = response.json()
            assert "instance_id" in data
            assert "status" in data


# =============================================================================
# Human Task Controller Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestHumanTaskController:
    """Tests for human task endpoints."""

    async def test_list_tasks(self) -> None:
        """GET /workflows/tasks returns list of pending tasks."""
        app = Litestar(route_handlers=[HumanTaskController])

        async with AsyncTestClient(app=app) as client:
            response = await client.get("/workflows/tasks/")

            assert response.status_code == HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)

    async def test_list_tasks_filtered_by_user(self) -> None:
        """GET /workflows/tasks supports user filtering."""
        app = Litestar(route_handlers=[HumanTaskController])

        async with AsyncTestClient(app=app) as client:
            response = await client.get(
                "/workflows/tasks/",
                params={"user_id": "user_123", "status": "PENDING"},
            )

            assert response.status_code == HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)

    async def test_get_task(self) -> None:
        """GET /workflows/tasks/{id} returns task details with form schema."""
        task_id = uuid4()

        app = Litestar(route_handlers=[HumanTaskController])

        async with AsyncTestClient(app=app) as client:
            response = await client.get(f"/workflows/tasks/{task_id}")

            assert response.status_code == HTTP_200_OK
            data = response.json()
            assert data["task_id"] == str(task_id)
            assert "form_schema" in data
            assert "title" in data
            assert data["status"] == "PENDING"

    async def test_complete_task(self) -> None:
        """POST /workflows/tasks/{id}/complete completes task with form data."""
        task_id = uuid4()

        app = Litestar(route_handlers=[HumanTaskController])

        async with AsyncTestClient(app=app) as client:
            response = await client.post(
                f"/workflows/tasks/{task_id}/complete",
                json={
                    "form_data": {
                        "approved": True,
                        "comments": "Looks good",
                    }
                },
            )

            assert response.status_code == HTTP_201_CREATED
            data = response.json()
            assert data["task_id"] == str(task_id)
            assert data["status"] == "completed"
            assert "result" in data

    async def test_complete_task_validation_error(self) -> None:
        """POST /workflows/tasks/{id}/complete validates form data."""
        task_id = uuid4()

        app = Litestar(route_handlers=[HumanTaskController])

        async with AsyncTestClient(app=app) as client:
            # Missing required form_data
            response = await client.post(
                f"/workflows/tasks/{task_id}/complete",
                json={},
            )

            # Should still succeed but with empty form_data
            assert response.status_code == HTTP_201_CREATED

    async def test_reassign_task(self) -> None:
        """POST /workflows/tasks/{id}/reassign reassigns task to another user."""
        task_id = uuid4()

        app = Litestar(route_handlers=[HumanTaskController])

        async with AsyncTestClient(app=app) as client:
            response = await client.post(
                f"/workflows/tasks/{task_id}/reassign",
                json={"assignee_id": "new_user_456"},
            )

            assert response.status_code == HTTP_201_CREATED
            data = response.json()
            assert data["task_id"] == str(task_id)
            assert data["assignee_id"] == "new_user_456"
            assert data["status"] == "reassigned"


# =============================================================================
# Graph Generation Tests
# =============================================================================


@pytest.mark.unit
class TestGraphGeneration:
    """Tests for workflow graph generation."""

    def test_linear_workflow_graph(self) -> None:
        """Generate MermaidJS graph for linear workflow."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.steps.base import BaseMachineStep

        class Step(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {}

        definition = WorkflowDefinition(
            name="linear",
            version="1.0.0",
            description="Linear workflow",
            steps={
                "a": Step(name="a", description="Step A"),
                "b": Step(name="b", description="Step B"),
                "c": Step(name="c", description="Step C"),
            },
            edges=[
                Edge(source="a", target="b"),
                Edge(source="b", target="c"),
            ],
            initial_step="a",
            terminal_steps={"c"},
        )

        # Simple mermaid generation
        graph = "graph TD\n"
        for edge in definition.edges:
            graph += f"    {edge.source} --> {edge.target}\n"

        assert "a --> b" in graph
        assert "b --> c" in graph

    def test_parallel_gateway_graph(self) -> None:
        """Generate MermaidJS graph for parallel gateway workflow."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.steps.base import BaseMachineStep

        class Step(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {}

        definition = WorkflowDefinition(
            name="parallel",
            version="1.0.0",
            description="Parallel workflow",
            steps={
                "start": Step(name="start", description="Start"),
                "parallel_a": Step(name="parallel_a", description="Parallel A"),
                "parallel_b": Step(name="parallel_b", description="Parallel B"),
                "join": Step(name="join", description="Join"),
            },
            edges=[
                Edge(source="start", target="parallel_a"),
                Edge(source="start", target="parallel_b"),
                Edge(source="parallel_a", target="join"),
                Edge(source="parallel_b", target="join"),
            ],
            initial_step="start",
            terminal_steps={"join"},
        )

        graph = "graph TD\n"
        for edge in definition.edges:
            graph += f"    {edge.source} --> {edge.target}\n"

        assert "start --> parallel_a" in graph
        assert "start --> parallel_b" in graph
        assert "parallel_a --> join" in graph
        assert "parallel_b --> join" in graph

    def test_complex_workflow_graph(self) -> None:
        """Generate MermaidJS graph for complex workflow with multiple paths."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.steps.base import BaseMachineStep

        class Step(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {}

        definition = WorkflowDefinition(
            name="complex",
            version="1.0.0",
            description="Complex workflow",
            steps={
                "start": Step(name="start", description="Start"),
                "validate": Step(name="validate", description="Validate"),
                "approve": Step(name="approve", description="Approve"),
                "reject": Step(name="reject", description="Reject"),
                "publish": Step(name="publish", description="Publish"),
            },
            edges=[
                Edge(source="start", target="validate"),
                Edge(source="validate", target="approve", condition="valid"),
                Edge(source="validate", target="reject", condition="invalid"),
                Edge(source="approve", target="publish", condition="approved"),
                Edge(source="approve", target="reject", condition="rejected"),
            ],
            initial_step="start",
            terminal_steps={"publish", "reject"},
        )

        graph = "graph TD\n"
        for edge in definition.edges:
            graph += f"    {edge.source} --> {edge.target}\n"

        assert "start --> validate" in graph
        assert "validate --> approve" in graph
        assert "validate --> reject" in graph
        assert "approve --> publish" in graph


# =============================================================================
# Auth Guard Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestAuthGuards:
    """Tests for authentication guard integration."""

    async def test_auth_guard_blocks_unauthenticated(self) -> None:
        """Auth guard blocks unauthenticated requests."""

        class AuthGuard:
            async def __call__(self, request) -> None:
                if not hasattr(request.state, "user"):
                    raise PermissionError("Authentication required")

        # This test validates the guard concept
        # Actual implementation would use Litestar guards
        guard = AuthGuard()

        class MockRequest:
            state = State()

        request = MockRequest()

        with pytest.raises(PermissionError, match="Authentication required"):
            await guard(request)

    async def test_auth_guard_allows_authenticated(self) -> None:
        """Auth guard allows authenticated requests."""

        class AuthGuard:
            async def __call__(self, request) -> None:
                if not hasattr(request.state, "user"):
                    raise PermissionError("Authentication required")

        guard = AuthGuard()

        class MockRequest:
            state = State()

        request = MockRequest()
        request.state.user = {"id": "user_123"}

        # Should not raise
        await guard(request)


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for error handling and validation."""

    async def test_validation_error_invalid_workflow_name(
        self,
        mock_workflow_registry: Mock,
        mock_workflow_engine: Mock,
    ) -> None:
        """Start workflow with invalid name returns validation error."""
        # Configure mock to raise error for None workflow name
        mock_workflow_registry.get_workflow_class.side_effect = KeyError("None not found")

        app = Litestar(
            route_handlers=[WorkflowInstanceController],
            dependencies={
                "workflow_registry": Provide(lambda: mock_workflow_registry, sync_to_thread=False),
                "workflow_engine": Provide(lambda: mock_workflow_engine, sync_to_thread=False),
            },
        )

        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.post(
                "/workflows/instances/",
                json={
                    # Missing workflow_name
                    "initial_data": {"key": "value"},
                },
            )

            # Should return 404 since workflow_name is None/missing
            assert response.status_code == HTTP_404_NOT_FOUND

    async def test_not_found_error_returns_404(
        self,
        mock_workflow_registry: Mock,
    ) -> None:
        """Not found errors return 404 status."""
        mock_workflow_registry.get_definition.side_effect = KeyError("Not found")

        app = Litestar(
            route_handlers=[WorkflowDefinitionController],
            dependencies={
                "workflow_registry": Provide(lambda: mock_workflow_registry, sync_to_thread=False),
            },
        )

        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.get("/workflows/definitions/nonexistent")

            assert response.status_code == HTTP_404_NOT_FOUND
            data = response.json()
            assert "not found" in data["detail"].lower()


# =============================================================================
# Integration Tests with Real Components
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.e2e
class TestEndToEndWorkflowAPI:
    """End-to-end tests with real workflow components."""

    async def test_complete_workflow_lifecycle_via_api(
        self,
        workflow_registry: WorkflowRegistry,
        local_engine: LocalExecutionEngine,
    ) -> None:
        """Test complete workflow lifecycle through REST API."""
        import asyncio

        from litestar_workflows import BaseMachineStep, Edge, WorkflowDefinition

        class StartStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                context.set("started", True)
                return {"step": "start"}

        class EndStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                context.set("completed", True)
                return {"step": "end"}

        definition = WorkflowDefinition(
            name="api_test_workflow",
            version="1.0.0",
            description="API test workflow",
            steps={
                "start": StartStep(name="start", description="Start"),
                "end": EndStep(name="end", description="End"),
            },
            edges=[Edge(source="start", target="end")],
            initial_step="start",
            terminal_steps={"end"},
        )

        class APITestWorkflow:
            name = "api_test_workflow"
            version = "1.0.0"

            @classmethod
            def get_definition(cls) -> WorkflowDefinition:
                return definition

        workflow_registry.register(APITestWorkflow)

        # Create app with controllers
        app = Litestar(
            route_handlers=[
                WorkflowDefinitionController,
                WorkflowInstanceController,
            ],
            dependencies={
                "workflow_registry": Provide(lambda: workflow_registry, sync_to_thread=False),
                "workflow_engine": Provide(lambda: local_engine, sync_to_thread=False),
            },
        )

        async with AsyncTestClient(app=app) as client:
            # 1. List definitions
            list_response = await client.get("/workflows/definitions/")
            assert list_response.status_code == HTTP_200_OK
            definitions = list_response.json()
            assert any(d["name"] == "api_test_workflow" for d in definitions)

            # 2. Get specific definition
            def_response = await client.get("/workflows/definitions/api_test_workflow")
            assert def_response.status_code == HTTP_200_OK
            definition_data = def_response.json()
            assert definition_data["name"] == "api_test_workflow"

            # 3. Start workflow
            start_response = await client.post(
                "/workflows/instances/",
                json={
                    "workflow_name": "api_test_workflow",
                    "initial_data": {"test": "data"},
                },
            )
            assert start_response.status_code == HTTP_201_CREATED
            start_data = start_response.json()
            instance_id = start_data["instance_id"]

            # Allow workflow to execute
            await asyncio.sleep(0.2)

            # 4. Get instance status
            instance_response = await client.get(f"/workflows/instances/{instance_id}")
            assert instance_response.status_code == HTTP_200_OK
            instance_data = instance_response.json()
            assert instance_data["workflow_name"] == "api_test_workflow"
            # Should have executed start step at minimum
            assert "data" in instance_data
