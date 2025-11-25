"""Tests for the WorkflowPlugin integration with Litestar.

These tests verify that the plugin correctly integrates with Litestar
applications and provides dependency injection for workflow components.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import pytest
from litestar import Controller, Litestar, get, post
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED
from litestar.testing import TestClient

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
# Test Fixtures - Workflow Components
# =============================================================================


class SampleStep(BaseMachineStep):
    """Simple sample step that records execution."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        context.set("executed", True)
        context.set("step_name", self.name)
        return {"success": True}


class StepA(BaseMachineStep):
    """First step in a multi-step workflow."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        context.set("step_a_done", True)
        return {"step": "a"}


class StepB(BaseMachineStep):
    """Second step in a multi-step workflow."""

    async def execute(self, context: WorkflowContext) -> dict[str, Any]:
        context.set("step_b_done", True)
        return {"step": "b"}


class SimpleWorkflow:
    """Single-step workflow for basic testing."""

    __workflow_name__ = "simple_workflow"
    __workflow_version__ = "1.0.0"
    __workflow_description__ = "A simple test workflow"

    @classmethod
    def get_definition(cls) -> WorkflowDefinition:
        return WorkflowDefinition(
            name=cls.__workflow_name__,
            version=cls.__workflow_version__,
            description=cls.__workflow_description__,
            steps={"test_step": SampleStep(name="test_step", description="A test step")},
            edges=[],
            initial_step="test_step",
            terminal_steps={"test_step"},
        )


class MultiStepWorkflow:
    """Multi-step workflow for testing sequential execution."""

    __workflow_name__ = "multi_step_workflow"
    __workflow_version__ = "1.0.0"
    __workflow_description__ = "A multi-step test workflow"

    @classmethod
    def get_definition(cls) -> WorkflowDefinition:
        return WorkflowDefinition(
            name=cls.__workflow_name__,
            version=cls.__workflow_version__,
            description=cls.__workflow_description__,
            steps={
                "step_a": StepA(name="step_a", description="Step A"),
                "step_b": StepB(name="step_b", description="Step B"),
            },
            edges=[
                Edge(source="step_a", target="step_b"),
            ],
            initial_step="step_a",
            terminal_steps={"step_b"},
        )


# =============================================================================
# Test Controllers
# =============================================================================


class WorkflowTestController(Controller):
    """Test controller for workflow operations."""

    path = "/workflows"

    @get("/")
    async def list_workflows(
        self,
        workflow_registry: WorkflowRegistry,
    ) -> list[dict[str, Any]]:
        """List registered workflows."""
        definitions = workflow_registry.list_definitions()
        return [{"name": d.name, "version": d.version} for d in definitions]

    @get("/{name:str}")
    async def get_workflow(
        self,
        name: str,
        workflow_registry: WorkflowRegistry,
    ) -> dict[str, Any]:
        """Get a workflow definition."""
        definition = workflow_registry.get_definition(name)
        return {
            "name": definition.name,
            "version": definition.version,
            "steps": list(definition.steps.keys()),
        }

    @post("/{name:str}/start")
    async def start_workflow(
        self,
        name: str,
        data: dict[str, Any],
        workflow_engine: LocalExecutionEngine,
        workflow_registry: WorkflowRegistry,
    ) -> dict[str, Any]:
        """Start a workflow instance."""
        workflow_class = workflow_registry.get_workflow_class(name)
        instance = await workflow_engine.start_workflow(workflow_class, initial_data=data)
        return {
            "instance_id": str(instance.id),
            "status": instance.status.value,
        }

    @get("/instances/{instance_id:uuid}")
    async def get_instance(
        self,
        instance_id: UUID,
        workflow_engine: LocalExecutionEngine,
    ) -> dict[str, Any]:
        """Get instance status."""
        instance = await workflow_engine.get_instance(instance_id)
        return {
            "instance_id": str(instance.id),
            "status": instance.status.value,
            "data": instance.context.data,
        }


# =============================================================================
# Plugin Initialization Tests
# =============================================================================


class TestPluginInitialization:
    """Tests for plugin initialization."""

    def test_plugin_creates_default_registry(self) -> None:
        """Plugin creates a default registry when none provided."""
        plugin = WorkflowPlugin()
        app = Litestar(plugins=[plugin])

        assert plugin._registry is not None
        assert isinstance(plugin._registry, WorkflowRegistry)

    def test_plugin_creates_default_engine(self) -> None:
        """Plugin creates a default engine when none provided."""
        plugin = WorkflowPlugin()
        app = Litestar(plugins=[plugin])

        assert plugin._engine is not None
        assert isinstance(plugin._engine, LocalExecutionEngine)

    def test_plugin_uses_provided_registry(self) -> None:
        """Plugin uses the provided registry."""
        custom_registry = WorkflowRegistry()
        config = WorkflowPluginConfig(registry=custom_registry)
        plugin = WorkflowPlugin(config=config)
        app = Litestar(plugins=[plugin])

        assert plugin._registry is custom_registry

    def test_plugin_uses_provided_engine(self) -> None:
        """Plugin uses the provided engine."""
        registry = WorkflowRegistry()
        custom_engine = LocalExecutionEngine(registry=registry)
        config = WorkflowPluginConfig(registry=registry, engine=custom_engine)
        plugin = WorkflowPlugin(config=config)
        app = Litestar(plugins=[plugin])

        assert plugin._engine is custom_engine

    def test_plugin_auto_registers_workflows(self) -> None:
        """Plugin auto-registers workflows from config."""
        config = WorkflowPluginConfig(
            auto_register_workflows=[SimpleWorkflow, MultiStepWorkflow],
        )
        plugin = WorkflowPlugin(config=config)
        app = Litestar(plugins=[plugin])

        assert plugin._registry is not None
        assert plugin._registry.has_workflow("simple_workflow")
        assert plugin._registry.has_workflow("multi_step_workflow")

    def test_plugin_custom_dependency_keys(self) -> None:
        """Plugin uses custom dependency keys when configured."""
        config = WorkflowPluginConfig(
            dependency_key_registry="my_registry",
            dependency_key_engine="my_engine",
        )
        plugin = WorkflowPlugin(config=config)
        app = Litestar(plugins=[plugin])

        assert "my_registry" in app.dependencies
        assert "my_engine" in app.dependencies


# =============================================================================
# Dependency Injection Tests
# =============================================================================


class TestDependencyInjection:
    """Tests for dependency injection of workflow components."""

    def test_registry_injection(self) -> None:
        """Registry is correctly injected into route handlers."""
        config = WorkflowPluginConfig(
            auto_register_workflows=[SimpleWorkflow],
        )

        app = Litestar(
            route_handlers=[WorkflowTestController],
            plugins=[WorkflowPlugin(config=config)],
        )

        with TestClient(app) as client:
            response = client.get("/workflows/")

            assert response.status_code == HTTP_200_OK
            workflows = response.json()
            assert len(workflows) == 1
            assert workflows[0]["name"] == "simple_workflow"

    def test_engine_injection(self) -> None:
        """Engine is correctly injected into route handlers."""
        config = WorkflowPluginConfig(
            auto_register_workflows=[SimpleWorkflow],
        )

        app = Litestar(
            route_handlers=[WorkflowTestController],
            plugins=[WorkflowPlugin(config=config)],
        )

        with TestClient(app) as client:
            # Start a workflow
            response = client.post(
                "/workflows/simple_workflow/start",
                json={"initial_value": "test"},
            )

            assert response.status_code == HTTP_201_CREATED
            data = response.json()
            assert "instance_id" in data
            assert data["status"] in ["running", "completed"]


# =============================================================================
# Helper Functions
# =============================================================================


def wait_for_workflow_completion(
    client: TestClient,
    instance_id: str,
    max_attempts: int = 20,
    delay_ms: int = 50,
) -> dict[str, Any]:
    """Poll for workflow completion.

    Args:
        client: The test client.
        instance_id: The workflow instance ID.
        max_attempts: Maximum polling attempts.
        delay_ms: Delay between attempts in milliseconds.

    Returns:
        The final status data.
    """
    import time

    for _ in range(max_attempts):
        response = client.get(f"/workflows/instances/{instance_id}")
        data = response.json()
        if data["status"] in ["completed", "failed", "canceled"]:
            return data
        time.sleep(delay_ms / 1000)

    return data  # Return last response even if not completed


# =============================================================================
# Integration Tests
# =============================================================================


class TestWorkflowExecution:
    """Integration tests for workflow execution through the plugin."""

    def test_start_and_complete_workflow(self) -> None:
        """Start a workflow and verify it completes."""
        config = WorkflowPluginConfig(
            auto_register_workflows=[SimpleWorkflow],
        )

        app = Litestar(
            route_handlers=[WorkflowTestController],
            plugins=[WorkflowPlugin(config=config)],
        )

        with TestClient(app) as client:
            # Start workflow
            start_response = client.post(
                "/workflows/simple_workflow/start",
                json={"test_key": "test_value"},
            )

            assert start_response.status_code == HTTP_201_CREATED
            start_data = start_response.json()
            instance_id = start_data["instance_id"]

            # Wait for completion and get status
            status_data = wait_for_workflow_completion(client, instance_id)

            assert status_data["status"] == "completed"
            assert status_data["data"]["executed"] is True

    def test_multi_step_workflow_execution(self) -> None:
        """Execute a multi-step workflow and verify all steps complete."""
        config = WorkflowPluginConfig(
            auto_register_workflows=[MultiStepWorkflow],
        )

        app = Litestar(
            route_handlers=[WorkflowTestController],
            plugins=[WorkflowPlugin(config=config)],
        )

        with TestClient(app) as client:
            # Start workflow
            start_response = client.post(
                "/workflows/multi_step_workflow/start",
                json={},
            )

            assert start_response.status_code == HTTP_201_CREATED
            instance_id = start_response.json()["instance_id"]

            # Wait for completion and check
            status_data = wait_for_workflow_completion(client, instance_id)

            assert status_data["status"] == "completed"
            assert status_data["data"]["step_a_done"] is True
            assert status_data["data"]["step_b_done"] is True

    def test_workflow_with_initial_data(self) -> None:
        """Workflow receives initial data from the start request."""
        config = WorkflowPluginConfig(
            auto_register_workflows=[SimpleWorkflow],
        )

        app = Litestar(
            route_handlers=[WorkflowTestController],
            plugins=[WorkflowPlugin(config=config)],
        )

        with TestClient(app) as client:
            # Start with custom data
            start_response = client.post(
                "/workflows/simple_workflow/start",
                json={"custom_field": "custom_value", "number": 42},
            )

            instance_id = start_response.json()["instance_id"]

            # Verify data was passed
            status_response = client.get(f"/workflows/instances/{instance_id}")
            status_data = status_response.json()

            assert status_data["data"]["custom_field"] == "custom_value"
            assert status_data["data"]["number"] == 42


# =============================================================================
# API Contract Tests
# =============================================================================


class TestWorkflowAPI:
    """Tests for the workflow REST API contract."""

    def test_list_workflows_returns_all_registered(self) -> None:
        """List endpoint returns all registered workflows."""
        config = WorkflowPluginConfig(
            auto_register_workflows=[SimpleWorkflow, MultiStepWorkflow],
        )

        app = Litestar(
            route_handlers=[WorkflowTestController],
            plugins=[WorkflowPlugin(config=config)],
        )

        with TestClient(app) as client:
            response = client.get("/workflows/")

            assert response.status_code == HTTP_200_OK
            workflows = response.json()
            assert len(workflows) == 2
            names = {w["name"] for w in workflows}
            assert "simple_workflow" in names
            assert "multi_step_workflow" in names

    def test_get_workflow_returns_definition(self) -> None:
        """Get endpoint returns workflow definition details."""
        config = WorkflowPluginConfig(
            auto_register_workflows=[MultiStepWorkflow],
        )

        app = Litestar(
            route_handlers=[WorkflowTestController],
            plugins=[WorkflowPlugin(config=config)],
        )

        with TestClient(app) as client:
            response = client.get("/workflows/multi_step_workflow")

            assert response.status_code == HTTP_200_OK
            data = response.json()
            assert data["name"] == "multi_step_workflow"
            assert data["version"] == "1.0.0"
            assert "step_a" in data["steps"]
            assert "step_b" in data["steps"]

    def test_get_nonexistent_workflow_returns_error(self) -> None:
        """Get endpoint returns error for nonexistent workflow."""
        app = Litestar(
            route_handlers=[WorkflowTestController],
            plugins=[WorkflowPlugin()],
        )

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/workflows/nonexistent")

            assert response.status_code == 500  # WorkflowNotFoundError


# =============================================================================
# Plugin Property Tests
# =============================================================================


class TestPluginProperties:
    """Tests for plugin property access."""

    def test_registry_property_before_init_raises(self) -> None:
        """Accessing registry before init raises RuntimeError."""
        plugin = WorkflowPlugin()

        with pytest.raises(RuntimeError, match="not been initialized"):
            _ = plugin.registry

    def test_engine_property_before_init_raises(self) -> None:
        """Accessing engine before init raises RuntimeError."""
        plugin = WorkflowPlugin()

        with pytest.raises(RuntimeError, match="not been initialized"):
            _ = plugin.engine

    def test_registry_property_after_init(self) -> None:
        """Registry property works after initialization."""
        plugin = WorkflowPlugin()
        app = Litestar(plugins=[plugin])

        registry = plugin.registry
        assert isinstance(registry, WorkflowRegistry)

    def test_engine_property_after_init(self) -> None:
        """Engine property works after initialization."""
        plugin = WorkflowPlugin()
        app = Litestar(plugins=[plugin])

        engine = plugin.engine
        assert isinstance(engine, LocalExecutionEngine)
