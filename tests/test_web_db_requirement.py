"""Tests for web endpoint database requirement handling.

This module tests that endpoints correctly handle the presence/absence of [db] extra:
- Core endpoints work WITHOUT [db] (definitions, graph, start workflow)
- DB-dependent endpoints return 501 WITH helpful error message
- Exception handler formats errors correctly
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from litestar import Litestar
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_501_NOT_IMPLEMENTED
from litestar.testing import AsyncTestClient

from litestar_workflows import WorkflowPlugin, WorkflowPluginConfig
from litestar_workflows.core.context import WorkflowContext
from litestar_workflows.core.definition import Edge, WorkflowDefinition
from litestar_workflows.engine.registry import WorkflowRegistry
from litestar_workflows.steps.base import BaseMachineStep

if TYPE_CHECKING:
    pass


# Test workflow for use in tests
class SimpleTestStep(BaseMachineStep):
    """Simple test step."""

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
                "step1": SimpleTestStep(name="step1", description="Step 1"),
                "step2": SimpleTestStep(name="step2", description="Step 2"),
            },
            edges=[Edge(source="step1", target="step2")],
            initial_step="step1",
            terminal_steps={"step2"},
        )


@pytest.mark.integration
@pytest.mark.asyncio
class TestWebEndpointsWithoutDB:
    """Test that core endpoints work WITHOUT [db] extra installed."""

    async def test_list_definitions_works_without_db(self) -> None:
        """GET /workflows/definitions works without [db] extra."""
        # Create app with workflow plugin
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
            response = await client.get("/workflows/definitions")
            assert response.status_code == HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["name"] == "test_workflow"

    async def test_get_definition_works_without_db(self) -> None:
        """GET /workflows/definitions/{name} works without [db] extra."""
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
            response = await client.get("/workflows/definitions/test_workflow")
            assert response.status_code == HTTP_200_OK
            data = response.json()
            assert data["name"] == "test_workflow"
            assert data["version"] == "1.0.0"
            assert "steps" in data

    async def test_get_definition_graph_works_without_db(self) -> None:
        """GET /workflows/definitions/{name}/graph works without [db] extra."""
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
            response = await client.get("/workflows/definitions/test_workflow/graph")
            assert response.status_code == HTTP_200_OK
            data = response.json()
            assert "mermaid_source" in data
            assert "nodes" in data
            assert "edges" in data
            # MermaidJS format should be present
            assert "graph" in data["mermaid_source"].lower()

    async def test_start_workflow_works_without_db(self) -> None:
        """POST /workflows/instances works without [db] extra (fire-and-forget)."""
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
            assert data["status"] in ["pending", "running", "succeeded", "PENDING", "RUNNING", "SUCCEEDED"]
            assert "started_at" in data


@pytest.mark.integration
@pytest.mark.asyncio
class TestWebEndpointsRequireDB:
    """Test that DB-dependent endpoints return 501 WITHOUT [db] extra."""

    async def test_list_instances_requires_db(self) -> None:
        """GET /workflows/instances returns 501 without [db] extra."""
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
            response = await client.get("/workflows/instances")
            assert response.status_code == HTTP_501_NOT_IMPLEMENTED
            data = response.json()
            assert data["error"] == "database_required"
            assert "pip install litestar-workflows[db]" in data["install"]
            assert "message" in data
            assert "docs" in data

    async def test_get_instance_requires_db(self) -> None:
        """GET /workflows/instances/{id} returns 501 without [db] extra."""
        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        auto_register_workflows=[TestWorkflow],
                    )
                )
            ]
        )

        instance_id = uuid4()
        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.get(f"/workflows/instances/{instance_id}")
            assert response.status_code == HTTP_501_NOT_IMPLEMENTED
            data = response.json()
            assert data["error"] == "database_required"
            assert "database persistence" in data["message"].lower()

    async def test_get_instance_graph_requires_db(self) -> None:
        """GET /workflows/instances/{id}/graph returns 501 without [db] extra."""
        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        auto_register_workflows=[TestWorkflow],
                    )
                )
            ]
        )

        instance_id = uuid4()
        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.get(f"/workflows/instances/{instance_id}/graph")
            assert response.status_code == HTTP_501_NOT_IMPLEMENTED
            data = response.json()
            assert data["error"] == "database_required"

    async def test_cancel_instance_requires_db(self) -> None:
        """POST /workflows/instances/{id}/cancel returns 501 without [db] extra."""
        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        auto_register_workflows=[TestWorkflow],
                    )
                )
            ]
        )

        instance_id = uuid4()
        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.post(
                f"/workflows/instances/{instance_id}/cancel",
                params={"reason": "test"},
            )
            assert response.status_code == HTTP_501_NOT_IMPLEMENTED
            data = response.json()
            assert data["error"] == "database_required"

    async def test_retry_instance_requires_db(self) -> None:
        """POST /workflows/instances/{id}/retry returns 501 without [db] extra."""
        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        auto_register_workflows=[TestWorkflow],
                    )
                )
            ]
        )

        instance_id = uuid4()
        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.post(f"/workflows/instances/{instance_id}/retry")
            assert response.status_code == HTTP_501_NOT_IMPLEMENTED
            data = response.json()
            assert data["error"] == "database_required"

    async def test_list_tasks_requires_db(self) -> None:
        """GET /workflows/tasks returns 501 without [db] extra."""
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
            response = await client.get("/workflows/tasks")
            assert response.status_code == HTTP_501_NOT_IMPLEMENTED
            data = response.json()
            assert data["error"] == "database_required"

    async def test_get_task_requires_db(self) -> None:
        """GET /workflows/tasks/{id} returns 501 without [db] extra."""
        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        auto_register_workflows=[TestWorkflow],
                    )
                )
            ]
        )

        task_id = uuid4()
        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.get(f"/workflows/tasks/{task_id}")
            assert response.status_code == HTTP_501_NOT_IMPLEMENTED
            data = response.json()
            assert data["error"] == "database_required"

    async def test_complete_task_requires_db(self) -> None:
        """POST /workflows/tasks/{id}/complete returns 501 without [db] extra."""
        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        auto_register_workflows=[TestWorkflow],
                    )
                )
            ]
        )

        task_id = uuid4()
        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.post(
                f"/workflows/tasks/{task_id}/complete",
                json={"output_data": {}, "completed_by": "user_123"},
            )
            assert response.status_code == HTTP_501_NOT_IMPLEMENTED
            data = response.json()
            assert data["error"] == "database_required"

    async def test_reassign_task_requires_db(self) -> None:
        """POST /workflows/tasks/{id}/reassign returns 501 without [db] extra."""
        app = Litestar(
            plugins=[
                WorkflowPlugin(
                    config=WorkflowPluginConfig(
                        auto_register_workflows=[TestWorkflow],
                    )
                )
            ]
        )

        task_id = uuid4()
        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.post(
                f"/workflows/tasks/{task_id}/reassign",
                json={"new_assignee": "user_456"},
            )
            assert response.status_code == HTTP_501_NOT_IMPLEMENTED
            data = response.json()
            assert data["error"] == "database_required"


@pytest.mark.unit
class TestDatabaseRequiredError:
    """Test DatabaseRequiredError exception and handler."""

    def test_error_default_message(self) -> None:
        """DatabaseRequiredError has helpful default message."""
        from litestar_workflows.web.exceptions import DatabaseRequiredError

        error = DatabaseRequiredError()
        message = str(error)
        assert "database persistence" in message.lower()
        assert "pip install litestar-workflows[db]" in message

    def test_error_custom_message(self) -> None:
        """DatabaseRequiredError accepts custom message."""
        from litestar_workflows.web.exceptions import DatabaseRequiredError

        custom_msg = "Custom error message"
        error = DatabaseRequiredError(custom_msg)
        assert str(error) == custom_msg

    def test_error_handler_response_format(self) -> None:
        """database_required_handler returns properly formatted response."""
        from litestar import Request
        from litestar.datastructures import State

        from litestar_workflows.web.exceptions import DatabaseRequiredError, database_required_handler

        # Create mock request
        mock_request = Mock(spec=Request)
        mock_request.state = State()

        # Create error
        error = DatabaseRequiredError()

        # Call handler
        response = database_required_handler(mock_request, error)

        # Verify response
        assert response.status_code == HTTP_501_NOT_IMPLEMENTED
        assert response.media_type == "application/json"

        # Verify response content structure
        content = response.content
        assert content["error"] == "database_required"
        assert "message" in content
        assert "install" in content
        assert "docs" in content
        assert "pip install litestar-workflows[db]" in content["install"]
        assert "litestar-workflows.readthedocs.io" in content["docs"]


@pytest.mark.integration
@pytest.mark.asyncio
class TestErrorMessageQuality:
    """Test that error messages are user-friendly and actionable."""

    async def test_error_message_includes_install_command(self) -> None:
        """Error response includes exact pip install command."""
        app = Litestar(plugins=[WorkflowPlugin()])

        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.get("/workflows/instances")
            data = response.json()
            assert "pip install litestar-workflows[db]" in data["install"]

    async def test_error_message_includes_docs_link(self) -> None:
        """Error response includes link to documentation."""
        app = Litestar(plugins=[WorkflowPlugin()])

        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.get("/workflows/instances")
            data = response.json()
            assert "docs" in data
            assert "http" in data["docs"]  # Should be a URL

    async def test_error_message_explains_requirement(self) -> None:
        """Error response explains why database is required."""
        app = Litestar(plugins=[WorkflowPlugin()])

        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.get("/workflows/instances")
            data = response.json()
            assert "database" in data["message"].lower()
            assert "persistence" in data["message"].lower()

    async def test_error_format_is_consistent(self) -> None:
        """All DB-required endpoints return same error format."""
        app = Litestar(plugins=[WorkflowPlugin()])

        endpoints_to_test = [
            ("GET", "/workflows/instances"),
            ("GET", f"/workflows/instances/{uuid4()}"),
            ("GET", f"/workflows/instances/{uuid4()}/graph"),
            ("POST", f"/workflows/instances/{uuid4()}/cancel"),
            ("POST", f"/workflows/instances/{uuid4()}/retry"),
            ("GET", "/workflows/tasks"),
            ("GET", f"/workflows/tasks/{uuid4()}"),
        ]

        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            for method, endpoint in endpoints_to_test:
                if method == "GET":
                    response = await client.get(endpoint)
                else:
                    response = await client.post(endpoint, json={})

                assert response.status_code == HTTP_501_NOT_IMPLEMENTED
                data = response.json()
                # All should have consistent structure
                assert data["error"] == "database_required"
                assert "message" in data
                assert "install" in data
                assert "docs" in data
