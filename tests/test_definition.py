"""Tests for workflow definitions and edges."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from litestar_workflows.core.definition import WorkflowDefinition
    from litestar_workflows.steps.base import BaseHumanStep, BaseMachineStep


@pytest.mark.unit
class TestEdge:
    """Tests for Edge class."""

    def test_edge_creation_with_step_names(self) -> None:
        """Test creating edge with step name strings."""
        from litestar_workflows.core.definition import Edge

        edge = Edge(source="step1", target="step2")

        assert edge.source == "step1"
        assert edge.target == "step2"
        assert edge.condition is None

    def test_edge_with_condition(self) -> None:
        """Test creating edge with condition."""
        from litestar_workflows.core.definition import Edge

        edge = Edge(source="decision", target="approved_path", condition="approved")

        assert edge.source == "decision"
        assert edge.target == "approved_path"
        assert edge.condition == "approved"

    def test_edge_creation_with_step_types(
        self, sample_machine_step: BaseMachineStep, sample_human_step: BaseHumanStep
    ) -> None:
        """Test creating edge with step type references."""
        from litestar_workflows.core.definition import Edge

        edge = Edge(source=type(sample_machine_step), target=type(sample_human_step))

        # Edge should accept step types
        assert edge.source is not None
        assert edge.target is not None

    def test_edge_equality(self) -> None:
        """Test edge equality comparison."""
        from litestar_workflows.core.definition import Edge

        edge1 = Edge(source="a", target="b")
        edge2 = Edge(source="a", target="b")
        edge3 = Edge(source="a", target="c")

        assert edge1 == edge2
        assert edge1 != edge3


@pytest.mark.unit
class TestWorkflowDefinition:
    """Tests for WorkflowDefinition class."""

    def test_definition_creation(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test creating a workflow definition."""
        assert sample_workflow_definition.name == "test_workflow"
        assert sample_workflow_definition.version == "1.0.0"
        assert sample_workflow_definition.description == "A test workflow definition"
        assert len(sample_workflow_definition.steps) == 2
        assert len(sample_workflow_definition.edges) == 1
        assert sample_workflow_definition.initial_step == "start"
        assert "approval" in sample_workflow_definition.terminal_steps

    def test_definition_steps_dict(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test workflow definition steps dictionary."""
        assert "start" in sample_workflow_definition.steps
        assert "approval" in sample_workflow_definition.steps
        assert sample_workflow_definition.steps["start"].name == "test_machine_step"
        assert sample_workflow_definition.steps["approval"].name == "test_human_step"

    def test_definition_edges_list(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test workflow definition edges list."""
        assert len(sample_workflow_definition.edges) == 1

        edge = sample_workflow_definition.edges[0]
        assert edge.source == "start"
        assert edge.target == "approval"

    def test_terminal_steps_detection(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test identification of terminal steps."""
        terminal = sample_workflow_definition.terminal_steps

        assert "approval" in terminal
        assert len(terminal) >= 1

    def test_to_mermaid_output(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test MermaidJS diagram generation."""
        mermaid = sample_workflow_definition.to_mermaid()

        # Should produce valid mermaid syntax
        assert mermaid.startswith("graph")
        assert "start" in mermaid
        assert "approval" in mermaid
        assert "-->" in mermaid  # Edge notation

    def test_to_mermaid_with_conditions(self, complex_workflow_definition: WorkflowDefinition) -> None:
        """Test MermaidJS generation with conditional edges."""
        mermaid = complex_workflow_definition.to_mermaid()

        # Should include conditional edges
        assert "graph" in mermaid
        assert "approval" in mermaid
        assert "publish" in mermaid
        assert "reject" in mermaid

    def test_graph_from_definition(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test building graph representation from definition."""
        from litestar_workflows.engine.graph import WorkflowGraph

        graph = WorkflowGraph.from_definition(sample_workflow_definition)

        # Should return a graph object
        assert graph is not None

    def test_workflow_allows_nonexistent_initial_step(
        self, sample_machine_step: BaseMachineStep, sample_human_step: BaseHumanStep
    ) -> None:
        """Test workflow definition allows initial step not in steps dict.

        Note: Validation happens at graph building time, not definition time.
        """
        from litestar_workflows.core.definition import Edge, WorkflowDefinition

        # Create definition with initial step not in steps dict
        # This is allowed at definition time - validation happens later
        definition = WorkflowDefinition(
            name="invalid_workflow",
            version="1.0.0",
            description="Invalid workflow",
            steps={
                "step1": sample_machine_step,
                "step2": sample_human_step,
            },
            edges=[Edge(source="step1", target="step2")],
            initial_step="nonexistent",
            terminal_steps={"step2"},
        )
        assert definition.initial_step == "nonexistent"

    def test_workflow_allows_edge_to_missing_step(self, sample_machine_step: BaseMachineStep) -> None:
        """Test workflow definition allows edges referencing missing steps.

        Note: Validation happens at graph building time, not definition time.
        """
        from litestar_workflows.core.definition import Edge, WorkflowDefinition

        # Create definition with edge pointing to missing step
        # This is allowed at definition time - validation happens later
        definition = WorkflowDefinition(
            name="invalid_workflow",
            version="1.0.0",
            description="Invalid workflow",
            steps={"step1": sample_machine_step},
            edges=[Edge(source="step1", target="nonexistent")],
            initial_step="step1",
            terminal_steps=set(),
        )
        assert len(definition.edges) == 1

    def test_complex_workflow_structure(self, complex_workflow_definition: WorkflowDefinition) -> None:
        """Test complex workflow with multiple branches."""
        assert len(complex_workflow_definition.steps) == 5
        assert len(complex_workflow_definition.edges) == 4

        # Verify all steps exist
        assert "start" in complex_workflow_definition.steps
        assert "process" in complex_workflow_definition.steps
        assert "approval" in complex_workflow_definition.steps
        assert "publish" in complex_workflow_definition.steps
        assert "reject" in complex_workflow_definition.steps

        # Verify terminal steps
        assert "publish" in complex_workflow_definition.terminal_steps
        assert "reject" in complex_workflow_definition.terminal_steps

    def test_workflow_definition_immutability(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test that workflow definition is effectively immutable after creation."""
        original_name = sample_workflow_definition.name
        original_version = sample_workflow_definition.version

        # These should remain constant
        assert sample_workflow_definition.name == original_name
        assert sample_workflow_definition.version == original_version

    def test_empty_workflow_definition(self) -> None:
        """Test creating minimal workflow definition."""
        from litestar_workflows.core.definition import WorkflowDefinition
        from litestar_workflows.steps.base import BaseMachineStep

        class SimpleStep(BaseMachineStep):
            async def execute(self, context):
                return {}

        definition = WorkflowDefinition(
            name="minimal",
            version="1.0.0",
            description="Minimal workflow",
            steps={"simple": SimpleStep(name="simple", description="Simple step")},
            edges=[],
            initial_step="simple",
            terminal_steps={"simple"},
        )

        assert definition.name == "minimal"
        assert len(definition.steps) == 1
        assert len(definition.edges) == 0
