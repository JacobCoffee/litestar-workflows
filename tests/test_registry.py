"""Tests for WorkflowRegistry."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from litestar_workflows.core.definition import WorkflowDefinition
    from litestar_workflows.engine.registry import WorkflowRegistry


@pytest.mark.unit
class TestWorkflowRegistry:
    """Tests for WorkflowRegistry."""

    def test_registry_creation(self, workflow_registry: WorkflowRegistry) -> None:
        """Test creating a workflow registry."""
        assert workflow_registry is not None

    def test_register_workflow(self, workflow_registry: WorkflowRegistry, sample_workflow_class: type) -> None:
        """Test registering a workflow definition."""
        workflow_registry.register(sample_workflow_class)

        # Verify workflow is registered
        definition = workflow_registry.get_definition("test_workflow")
        assert definition is not None
        assert definition.name == "test_workflow"
        assert definition.version == "1.0.0"

    def test_register_workflow_duplicate_name_different_version(
        self, workflow_registry: WorkflowRegistry, sample_workflow_definition: WorkflowDefinition
    ) -> None:
        """Test registering multiple versions of same workflow."""
        from litestar_workflows.core.definition import WorkflowDefinition
        from tests.conftest import make_workflow_class

        # Register version 1.0.0
        workflow_registry.register(make_workflow_class(sample_workflow_definition))

        # Create and register version 2.0.0
        v2_definition = WorkflowDefinition(
            name="test_workflow",
            version="2.0.0",
            description="Version 2 of test workflow",
            steps=sample_workflow_definition.steps,
            edges=sample_workflow_definition.edges,
            initial_step=sample_workflow_definition.initial_step,
            terminal_steps=sample_workflow_definition.terminal_steps,
        )

        workflow_registry.register(make_workflow_class(v2_definition))

        # Both versions should be accessible
        v1 = workflow_registry.get_definition("test_workflow", version="1.0.0")
        v2 = workflow_registry.get_definition("test_workflow", version="2.0.0")

        assert v1.version == "1.0.0"
        assert v2.version == "2.0.0"

    def test_get_definition_by_name(self, workflow_registry: WorkflowRegistry, sample_workflow_class: type) -> None:
        """Test getting workflow definition by name."""
        workflow_registry.register(sample_workflow_class)

        definition = workflow_registry.get_definition("test_workflow")

        assert definition.name == "test_workflow"
        assert definition.version == "1.0.0"

    def test_get_definition_by_name_and_version(
        self, workflow_registry: WorkflowRegistry, sample_workflow_class: type
    ) -> None:
        """Test getting specific version of workflow."""
        workflow_registry.register(sample_workflow_class)

        definition = workflow_registry.get_definition("test_workflow", version="1.0.0")

        assert definition.name == "test_workflow"
        assert definition.version == "1.0.0"

    def test_get_definition_latest_version(
        self, workflow_registry: WorkflowRegistry, sample_workflow_definition: WorkflowDefinition
    ) -> None:
        """Test getting latest version when multiple versions exist."""
        from litestar_workflows.core.definition import WorkflowDefinition
        from tests.conftest import make_workflow_class

        # Register multiple versions
        workflow_registry.register(make_workflow_class(sample_workflow_definition))  # 1.0.0

        v2 = WorkflowDefinition(
            name="test_workflow",
            version="2.0.0",
            description="Version 2",
            steps=sample_workflow_definition.steps,
            edges=sample_workflow_definition.edges,
            initial_step=sample_workflow_definition.initial_step,
            terminal_steps=sample_workflow_definition.terminal_steps,
        )
        workflow_registry.register(make_workflow_class(v2))

        # Get without specifying version should return latest
        latest = workflow_registry.get_definition("test_workflow")
        assert latest.version == "2.0.0"

    def test_get_definition_not_found(self, workflow_registry: WorkflowRegistry) -> None:
        """Test getting non-existent workflow raises error."""
        with pytest.raises(KeyError, match="nonexistent_workflow"):
            workflow_registry.get_definition("nonexistent_workflow")

    def test_get_definition_version_not_found(
        self, workflow_registry: WorkflowRegistry, sample_workflow_class: type
    ) -> None:
        """Test getting non-existent version raises error."""
        workflow_registry.register(sample_workflow_class)

        with pytest.raises(KeyError, match="9.9.9"):
            workflow_registry.get_definition("test_workflow", version="9.9.9")

    def test_list_definitions(self, workflow_registry: WorkflowRegistry, sample_workflow_class: type) -> None:
        """Test listing all workflow definitions."""
        workflow_registry.register(sample_workflow_class)

        definitions = workflow_registry.list_definitions()

        assert len(definitions) >= 1
        assert any(d.name == "test_workflow" for d in definitions)

    def test_list_definitions_empty(self, workflow_registry: WorkflowRegistry) -> None:
        """Test listing definitions when registry is empty."""
        definitions = workflow_registry.list_definitions()
        assert definitions == []

    def test_list_definitions_multiple(self, workflow_registry: WorkflowRegistry, sample_workflow_class: type) -> None:
        """Test listing multiple workflow definitions."""
        from litestar_workflows.core.definition import WorkflowDefinition
        from litestar_workflows.steps.base import BaseMachineStep
        from tests.conftest import make_workflow_class

        class SimpleStep(BaseMachineStep):
            async def execute(self, context):
                return {}

        # Register first workflow
        workflow_registry.register(sample_workflow_class)

        # Register second workflow
        workflow2 = WorkflowDefinition(
            name="another_workflow",
            version="1.0.0",
            description="Another workflow",
            steps={"simple": SimpleStep(name="simple", description="Simple step")},
            edges=[],
            initial_step="simple",
            terminal_steps={"simple"},
        )
        workflow_registry.register(make_workflow_class(workflow2))

        definitions = workflow_registry.list_definitions()

        assert len(definitions) == 2
        names = {d.name for d in definitions}
        assert names == {"test_workflow", "another_workflow"}

    def test_unregister_workflow(self, workflow_registry: WorkflowRegistry, sample_workflow_class: type) -> None:
        """Test unregistering a workflow."""
        workflow_registry.register(sample_workflow_class)

        # Verify it's registered
        assert workflow_registry.get_definition("test_workflow") is not None

        # Unregister
        workflow_registry.unregister("test_workflow", version="1.0.0")

        # Should no longer be found
        with pytest.raises(KeyError):
            workflow_registry.get_definition("test_workflow")

    def test_unregister_specific_version(
        self, workflow_registry: WorkflowRegistry, sample_workflow_definition: WorkflowDefinition
    ) -> None:
        """Test unregistering specific version keeps other versions."""
        from litestar_workflows.core.definition import WorkflowDefinition
        from tests.conftest import make_workflow_class

        # Register two versions
        workflow_registry.register(make_workflow_class(sample_workflow_definition))  # 1.0.0

        v2 = WorkflowDefinition(
            name="test_workflow",
            version="2.0.0",
            description="Version 2",
            steps=sample_workflow_definition.steps,
            edges=sample_workflow_definition.edges,
            initial_step=sample_workflow_definition.initial_step,
            terminal_steps=sample_workflow_definition.terminal_steps,
        )
        workflow_registry.register(make_workflow_class(v2))

        # Unregister v1
        workflow_registry.unregister("test_workflow", version="1.0.0")

        # v2 should still exist
        assert workflow_registry.get_definition("test_workflow").version == "2.0.0"

    def test_has_workflow(self, workflow_registry: WorkflowRegistry, sample_workflow_class: type) -> None:
        """Test checking if workflow exists."""
        assert workflow_registry.has_workflow("test_workflow") is False

        workflow_registry.register(sample_workflow_class)

        assert workflow_registry.has_workflow("test_workflow") is True
        assert workflow_registry.has_workflow("test_workflow", version="1.0.0") is True
        assert workflow_registry.has_workflow("test_workflow", version="9.9.9") is False

    def test_get_workflow_versions(
        self, workflow_registry: WorkflowRegistry, sample_workflow_definition: WorkflowDefinition
    ) -> None:
        """Test getting all versions of a workflow."""
        from litestar_workflows.core.definition import WorkflowDefinition
        from tests.conftest import make_workflow_class

        # Register multiple versions
        workflow_registry.register(make_workflow_class(sample_workflow_definition))  # 1.0.0

        v2 = WorkflowDefinition(
            name="test_workflow",
            version="2.0.0",
            description="Version 2",
            steps=sample_workflow_definition.steps,
            edges=sample_workflow_definition.edges,
            initial_step=sample_workflow_definition.initial_step,
            terminal_steps=sample_workflow_definition.terminal_steps,
        )
        workflow_registry.register(make_workflow_class(v2))

        versions = workflow_registry.get_versions("test_workflow")

        assert len(versions) == 2
        assert set(versions) == {"1.0.0", "2.0.0"}
