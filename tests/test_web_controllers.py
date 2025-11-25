"""Comprehensive tests for web controllers with actual implementations.

This module tests the actual controller implementations in
src/litestar_workflows/web/controllers.py to increase test coverage.

Coverage targets:
- Error handling paths (KeyError, NotFoundException)
- Pagination and filtering parameters
- Graph endpoint variations (format=mermaid, format=json)
- Controller dependencies and providers
- Repository interactions
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from litestar import Litestar
from litestar.di import Provide
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient

from litestar_workflows import WorkflowPlugin, WorkflowPluginConfig
from litestar_workflows.core.context import WorkflowContext
from litestar_workflows.core.definition import Edge, WorkflowDefinition
from litestar_workflows.core.types import StepStatus, WorkflowStatus
from litestar_workflows.engine.local import LocalExecutionEngine
from litestar_workflows.engine.registry import WorkflowRegistry
from litestar_workflows.steps.base import BaseMachineStep

if TYPE_CHECKING:
    from uuid import UUID


# Test workflow steps and definitions
class SampleStep(BaseMachineStep):
    """Simple sample step for testing."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        """Execute the step."""
        context.set("executed", True)
        return {"result": "success"}


class TestWorkflow:
    """Test workflow class."""

    name = "test_workflow"
    version = "1.0.0"

    @classmethod
    def get_definition(cls) -> WorkflowDefinition:
        """Get workflow definition."""
        return WorkflowDefinition(
            name=cls.name,
            version=cls.version,
            description="Test workflow",
            steps={
                "step1": SampleStep(name="step1", description="Step 1"),
                "step2": SampleStep(name="step2", description="Step 2"),
            },
            edges=[Edge(source="step1", target="step2")],
            initial_step="step1",
            terminal_steps={"step2"},
        )


class ComplexWorkflow:
    """Complex workflow with conditions."""

    name = "complex_workflow"
    version = "2.0.0"

    @classmethod
    def get_definition(cls) -> WorkflowDefinition:
        """Get workflow definition with conditions."""
        return WorkflowDefinition(
            name=cls.name,
            version=cls.version,
            description="Complex workflow with conditional edges",
            steps={
                "start": SampleStep(name="start", description="Start"),
                "validate": SampleStep(name="validate", description="Validate"),
                "approve": SampleStep(name="approve", description="Approve"),
                "reject": SampleStep(name="reject", description="Reject"),
            },
            edges=[
                Edge(source="start", target="validate"),
                Edge(source="validate", target="approve", condition=lambda ctx: ctx.get("valid")),
                Edge(source="validate", target="reject", condition=lambda ctx: not ctx.get("valid")),
            ],
            initial_step="start",
            terminal_steps={"approve", "reject"},
        )


@pytest.mark.integration
@pytest.mark.asyncio
class TestWorkflowDefinitionController:
    """Tests for WorkflowDefinitionController with actual implementation."""

    async def test_list_definitions_with_multiple_workflows(self) -> None:
        """List definitions returns all registered workflows."""
        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        auto_register_workflows=[TestWorkflow, ComplexWorkflow],
                    )
                )
            ]
        )

        async with AsyncTestClient(app=app) as client:
            response = await client.get("/workflows/definitions")
            assert response.status_code == HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2

            # Check both workflows are present
            workflow_names = {d["name"] for d in data}
            assert "test_workflow" in workflow_names
            assert "complex_workflow" in workflow_names

            # Verify structure
            test_wf = next(d for d in data if d["name"] == "test_workflow")
            assert test_wf["version"] == "1.0.0"
            assert "steps" in test_wf
            assert "edges" in test_wf
            assert test_wf["initial_step"] == "step1"
            assert "step2" in test_wf["terminal_steps"]

    async def test_get_definition_not_found(self) -> None:
        """Get definition returns 404 for unknown workflow."""
        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        auto_register_workflows=[TestWorkflow],
                    )
                )
            ]
        )

        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.get("/workflows/definitions/nonexistent_workflow")
            assert response.status_code == HTTP_404_NOT_FOUND
            data = response.json()
            assert "not found" in data["detail"].lower()
            assert "nonexistent_workflow" in data["detail"]

    async def test_get_definition_with_version(self) -> None:
        """Get definition with specific version parameter."""
        registry = WorkflowRegistry()
        registry.register(TestWorkflow)

        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        registry=registry,
                    )
                )
            ]
        )

        async with AsyncTestClient(app=app) as client:
            response = await client.get(
                "/workflows/definitions/test_workflow",
                params={"version": "1.0.0"},
            )
            assert response.status_code == HTTP_200_OK
            data = response.json()
            assert data["name"] == "test_workflow"
            assert data["version"] == "1.0.0"

    async def test_get_definition_graph_mermaid_format(self) -> None:
        """Get definition graph in mermaid format."""
        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        auto_register_workflows=[TestWorkflow],
                    )
                )
            ]
        )

        async with AsyncTestClient(app=app) as client:
            response = await client.get(
                "/workflows/definitions/test_workflow/graph",
                params={"graph_format": "mermaid"},
            )
            assert response.status_code == HTTP_200_OK
            data = response.json()
            assert "mermaid_source" in data
            assert "nodes" in data
            assert "edges" in data
            # Verify mermaid source contains graph definition
            assert len(data["mermaid_source"]) > 0
            # Verify nodes structure
            assert len(data["nodes"]) == 2
            # Verify edges structure
            assert len(data["edges"]) == 1

    async def test_get_definition_graph_json_format(self) -> None:
        """Get definition graph in json format."""
        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        auto_register_workflows=[ComplexWorkflow],
                    )
                )
            ]
        )

        async with AsyncTestClient(app=app) as client:
            response = await client.get(
                "/workflows/definitions/complex_workflow/graph",
                params={"graph_format": "json"},
            )
            assert response.status_code == HTTP_200_OK
            data = response.json()
            # JSON format should still include structure but no mermaid source
            assert "mermaid_source" in data
            assert data["mermaid_source"] == ""
            assert "nodes" in data
            assert "edges" in data
            # Verify nodes
            assert len(data["nodes"]) == 4
            node_ids = {node["id"] for node in data["nodes"]}
            assert {"start", "validate", "approve", "reject"} == node_ids
            # Verify edges with conditions
            assert len(data["edges"]) == 3

    async def test_get_definition_graph_unknown_format(self) -> None:
        """Get definition graph with unknown format returns 404."""
        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        auto_register_workflows=[TestWorkflow],
                    )
                )
            ]
        )

        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.get(
                "/workflows/definitions/test_workflow/graph",
                params={"graph_format": "xml"},
            )
            assert response.status_code == HTTP_404_NOT_FOUND
            data = response.json()
            assert "unknown format" in data["detail"].lower()
            assert "xml" in data["detail"].lower()

    async def test_get_definition_graph_workflow_not_found(self) -> None:
        """Get graph for nonexistent workflow returns 404."""
        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        auto_register_workflows=[TestWorkflow],
                    )
                )
            ]
        )

        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.get("/workflows/definitions/nonexistent/graph")
            assert response.status_code == HTTP_404_NOT_FOUND
            data = response.json()
            assert "not found" in data["detail"].lower()

    async def test_definition_edges_with_conditions(self) -> None:
        """Definition edges include condition information."""
        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        auto_register_workflows=[ComplexWorkflow],
                    )
                )
            ]
        )

        async with AsyncTestClient(app=app) as client:
            response = await client.get("/workflows/definitions/complex_workflow")
            assert response.status_code == HTTP_200_OK
            data = response.json()

            # Check edges have condition info
            edges = data["edges"]
            assert len(edges) == 3

            # Find conditional edges
            conditional_edges = [e for e in edges if e.get("condition")]
            assert len(conditional_edges) == 2

            # Verify condition is serialized to string
            for edge in conditional_edges:
                assert isinstance(edge["condition"], str)


@pytest.mark.integration
@pytest.mark.asyncio
class TestWorkflowInstanceController:
    """Tests for WorkflowInstanceController with actual implementation."""

    async def test_start_workflow_success(self) -> None:
        """Start workflow returns instance details."""
        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        auto_register_workflows=[TestWorkflow],
                    )
                )
            ]
        )

        async with AsyncTestClient(app=app) as client:
            response = await client.post(
                "/workflows/instances",
                json={
                    "definition_name": "test_workflow",
                    "input_data": {"test": "data"},
                    "user_id": "user_123",
                },
            )
            assert response.status_code == HTTP_201_CREATED
            data = response.json()
            assert "id" in data
            assert data["definition_name"] == "test_workflow"
            # Status can be lowercase or uppercase depending on DTO serialization
            assert data["status"].upper() in ["PENDING", "RUNNING", "SUCCEEDED"]
            assert "started_at" in data
            assert data["created_by"] == "user_123"
            assert data["current_step"] is not None

    async def test_start_workflow_not_found(self) -> None:
        """Start workflow with unknown name returns 404."""
        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        auto_register_workflows=[TestWorkflow],
                    )
                )
            ]
        )

        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.post(
                "/workflows/instances",
                json={
                    "definition_name": "nonexistent_workflow",
                    "input_data": {},
                },
            )
            assert response.status_code == HTTP_404_NOT_FOUND
            data = response.json()
            assert "not found" in data["detail"].lower()
            assert "nonexistent_workflow" in data["detail"]


@pytest.mark.integration
@pytest.mark.asyncio
class TestHumanTaskController:
    """Tests for HumanTaskController error handling.

    Note: Most task endpoints require [db] extra and return 501 errors.
    These are tested in test_web_db_requirement.py.
    """

    pass  # Human task tests require DB which isn't installed without [db] extra


@pytest.mark.integration
@pytest.mark.asyncio
class TestControllersEndToEnd:
    """End-to-end tests with real components where possible."""

    async def test_full_workflow_api_flow(self) -> None:
        """Test complete workflow through API endpoints."""
        import asyncio

        # Create app with real components
        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        auto_register_workflows=[TestWorkflow],
                    )
                )
            ]
        )

        async with AsyncTestClient(app=app) as client:
            # 1. List definitions
            definitions_response = await client.get("/workflows/definitions")
            assert definitions_response.status_code == HTTP_200_OK
            definitions = definitions_response.json()
            assert len(definitions) >= 1

            # 2. Get specific definition
            definition_response = await client.get("/workflows/definitions/test_workflow")
            assert definition_response.status_code == HTTP_200_OK

            # 3. Get graph
            graph_response = await client.get("/workflows/definitions/test_workflow/graph")
            assert graph_response.status_code == HTTP_200_OK

            # 4. Start workflow
            start_response = await client.post(
                "/workflows/instances",
                json={
                    "definition_name": "test_workflow",
                    "input_data": {"key": "value"},
                    "user_id": "test_user",
                },
            )
            assert start_response.status_code == HTTP_201_CREATED
            instance_data = start_response.json()
            assert "id" in instance_data

            # Allow workflow to execute
            await asyncio.sleep(0.1)
