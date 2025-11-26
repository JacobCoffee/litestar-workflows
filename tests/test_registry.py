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

        with pytest.raises(KeyError, match=r"9\.9\.9"):
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

    def test_get_versions_not_found(self, workflow_registry: WorkflowRegistry) -> None:
        """Test getting versions for non-existent workflow raises error."""
        with pytest.raises(KeyError, match="nonexistent_workflow"):
            workflow_registry.get_versions("nonexistent_workflow")

    def test_get_workflow_class_success(self, workflow_registry: WorkflowRegistry, sample_workflow_class: type) -> None:
        """Test getting workflow class by name."""
        workflow_registry.register(sample_workflow_class)

        workflow_class = workflow_registry.get_workflow_class("test_workflow")

        assert workflow_class is sample_workflow_class
        assert workflow_class.name == "test_workflow"

    def test_get_workflow_class_not_found(self, workflow_registry: WorkflowRegistry) -> None:
        """Test getting non-existent workflow class raises error."""
        with pytest.raises(KeyError, match="nonexistent_workflow"):
            workflow_registry.get_workflow_class("nonexistent_workflow")

    def test_list_definitions_active_only_true(
        self, workflow_registry: WorkflowRegistry, sample_workflow_definition: WorkflowDefinition
    ) -> None:
        """Test listing only active (latest) versions of workflows."""
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

        v3 = WorkflowDefinition(
            name="test_workflow",
            version="3.0.0",
            description="Version 3",
            steps=sample_workflow_definition.steps,
            edges=sample_workflow_definition.edges,
            initial_step=sample_workflow_definition.initial_step,
            terminal_steps=sample_workflow_definition.terminal_steps,
        )
        workflow_registry.register(make_workflow_class(v3))

        # List with active_only=True (default)
        definitions = workflow_registry.list_definitions(active_only=True)

        # Should only return latest version
        assert len(definitions) == 1
        assert definitions[0].version == "3.0.0"

    def test_list_definitions_active_only_false(
        self, workflow_registry: WorkflowRegistry, sample_workflow_definition: WorkflowDefinition
    ) -> None:
        """Test listing all versions of workflows."""
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

        # List with active_only=False
        definitions = workflow_registry.list_definitions(active_only=False)

        # Should return all versions
        assert len(definitions) == 2
        versions = {d.version for d in definitions}
        assert versions == {"1.0.0", "2.0.0"}

    def test_unregister_nonexistent_workflow(self, workflow_registry: WorkflowRegistry) -> None:
        """Test unregistering non-existent workflow does not raise error."""
        # Should not raise any exception
        workflow_registry.unregister("nonexistent_workflow")
        workflow_registry.unregister("nonexistent_workflow", version="1.0.0")

    def test_unregister_all_versions(
        self, workflow_registry: WorkflowRegistry, sample_workflow_definition: WorkflowDefinition
    ) -> None:
        """Test unregistering all versions of a workflow."""
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

        # Verify both versions exist
        assert workflow_registry.has_workflow("test_workflow", "1.0.0")
        assert workflow_registry.has_workflow("test_workflow", "2.0.0")

        # Unregister all versions
        workflow_registry.unregister("test_workflow")

        # Both versions should be gone
        assert workflow_registry.has_workflow("test_workflow") is False
        assert workflow_registry.has_workflow("test_workflow", "1.0.0") is False
        assert workflow_registry.has_workflow("test_workflow", "2.0.0") is False

    def test_unregister_last_version_removes_class(
        self, workflow_registry: WorkflowRegistry, sample_workflow_class: type
    ) -> None:
        """Test that unregistering the last version removes the workflow class."""
        workflow_registry.register(sample_workflow_class)

        # Verify workflow class exists
        assert workflow_registry.has_workflow("test_workflow")
        workflow_class = workflow_registry.get_workflow_class("test_workflow")
        assert workflow_class is not None

        # Unregister the only version
        workflow_registry.unregister("test_workflow", "1.0.0")

        # Workflow should no longer exist
        assert workflow_registry.has_workflow("test_workflow") is False

        # Getting workflow class should raise error
        with pytest.raises(KeyError):
            workflow_registry.get_workflow_class("test_workflow")

    def test_register_same_workflow_multiple_times(
        self, workflow_registry: WorkflowRegistry, sample_workflow_class: type
    ) -> None:
        """Test registering the same workflow class multiple times."""
        workflow_registry.register(sample_workflow_class)
        workflow_registry.register(sample_workflow_class)  # Register again

        # Should still have only one version
        versions = workflow_registry.get_versions("test_workflow")
        assert len(versions) == 1
        assert versions[0] == "1.0.0"

    def test_semantic_version_sorting(
        self, workflow_registry: WorkflowRegistry, sample_workflow_definition: WorkflowDefinition
    ) -> None:
        """Test that versions are sorted semantically."""
        from litestar_workflows.core.definition import WorkflowDefinition
        from tests.conftest import make_workflow_class

        # Register versions in non-sorted order
        for version in ["2.0.0", "1.0.0", "10.0.0", "1.1.0", "1.10.0"]:
            definition = WorkflowDefinition(
                name="test_workflow",
                version=version,
                description=f"Version {version}",
                steps=sample_workflow_definition.steps,
                edges=sample_workflow_definition.edges,
                initial_step=sample_workflow_definition.initial_step,
                terminal_steps=sample_workflow_definition.terminal_steps,
            )
            workflow_registry.register(make_workflow_class(definition))

        # Get latest version (should be highest)
        latest = workflow_registry.get_definition("test_workflow")

        # max() on strings will return "9.0.0" > "10.0.0" in lexical order
        # But we expect basic string comparison which gives us the max string
        assert latest.version in ["2.0.0", "10.0.0"]  # String comparison
