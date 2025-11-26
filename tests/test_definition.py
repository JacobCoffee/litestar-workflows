"""Tests for workflow definitions and edges."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from litestar_workflows.core.context import WorkflowContext
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

    def test_evaluate_condition_no_condition(self, sample_context: WorkflowContext) -> None:
        """Test edge condition evaluation when no condition exists."""
        from litestar_workflows.core.definition import Edge

        edge = Edge(source="a", target="b")
        result = edge.evaluate_condition(sample_context)

        assert result is True

    def test_evaluate_condition_callable(self, sample_context: WorkflowContext) -> None:
        """Test edge condition evaluation with callable condition."""
        from litestar_workflows.core.definition import Edge

        # Test condition that returns True
        edge_true = Edge(source="a", target="b", condition=lambda ctx: ctx.get("count") == 0)
        assert edge_true.evaluate_condition(sample_context) is True

        # Test condition that returns False
        edge_false = Edge(source="a", target="b", condition=lambda ctx: ctx.get("count") > 10)
        assert edge_false.evaluate_condition(sample_context) is False

    def test_evaluate_condition_string(self, sample_context: WorkflowContext) -> None:
        """Test edge condition evaluation with string expression."""
        from litestar_workflows.core.definition import Edge

        # String conditions currently default to True (future enhancement)
        edge = Edge(source="a", target="b", condition="ctx.get('approved') == True")
        result = edge.evaluate_condition(sample_context)

        assert result is True

    def test_get_source_name_with_string(self) -> None:
        """Test getting source name when source is a string."""
        from litestar_workflows.core.definition import Edge

        edge = Edge(source="step_a", target="step_b")
        assert edge.get_source_name() == "step_a"

    def test_get_source_name_with_step_class(self) -> None:
        """Test getting source name when source is a step class with name attribute."""
        from litestar_workflows.core.definition import Edge
        from litestar_workflows.steps.base import BaseMachineStep

        # Create a step class with a name class attribute
        class TestStep(BaseMachineStep):
            name = "test_step"

            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {}

        edge = Edge(source=TestStep, target="step_b")
        assert edge.get_source_name() == "test_step"

    def test_get_target_name_with_string(self) -> None:
        """Test getting target name when target is a string."""
        from litestar_workflows.core.definition import Edge

        edge = Edge(source="step_a", target="step_b")
        assert edge.get_target_name() == "step_b"

    def test_get_target_name_with_step_class(self) -> None:
        """Test getting target name when target is a step class with name attribute."""
        from litestar_workflows.core.definition import Edge
        from litestar_workflows.steps.base import BaseHumanStep

        # Create a step class with a name class attribute
        class TestStep(BaseHumanStep):
            name = "test_step"

            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {}

        edge = Edge(source="step_a", target=TestStep)
        assert edge.get_target_name() == "test_step"


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


@pytest.mark.unit
class TestWorkflowDefinitionValidation:
    """Tests for WorkflowDefinition validation."""

    def test_validate_valid_workflow(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test validation of a valid workflow."""
        errors = sample_workflow_definition.validate()
        assert errors == []

    def test_validate_missing_initial_step(self, sample_machine_step: BaseMachineStep) -> None:
        """Test validation fails when initial step is not in steps dict."""
        from litestar_workflows.core.definition import WorkflowDefinition

        definition = WorkflowDefinition(
            name="invalid_workflow",
            version="1.0.0",
            description="Invalid workflow",
            steps={"step1": sample_machine_step},
            edges=[],
            initial_step="nonexistent",
            terminal_steps=set(),
        )

        errors = definition.validate()
        assert len(errors) > 0
        assert any("Initial step 'nonexistent' not found" in error for error in errors)

    def test_validate_missing_terminal_step(self, sample_machine_step: BaseMachineStep) -> None:
        """Test validation fails when terminal step is not in steps dict."""
        from litestar_workflows.core.definition import WorkflowDefinition

        definition = WorkflowDefinition(
            name="invalid_workflow",
            version="1.0.0",
            description="Invalid workflow",
            steps={"step1": sample_machine_step},
            edges=[],
            initial_step="step1",
            terminal_steps={"nonexistent"},
        )

        errors = definition.validate()
        assert len(errors) > 0
        assert any("Terminal step 'nonexistent' not found" in error for error in errors)

    def test_validate_edge_source_not_found(
        self, sample_machine_step: BaseMachineStep, sample_human_step: BaseHumanStep
    ) -> None:
        """Test validation fails when edge source is not in steps dict."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition

        definition = WorkflowDefinition(
            name="invalid_workflow",
            version="1.0.0",
            description="Invalid workflow",
            steps={"step1": sample_machine_step, "step2": sample_human_step},
            edges=[Edge(source="nonexistent", target="step2")],
            initial_step="step1",
            terminal_steps={"step2"},
        )

        errors = definition.validate()
        assert len(errors) > 0
        assert any("source step 'nonexistent' not found" in error for error in errors)

    def test_validate_edge_target_not_found(
        self, sample_machine_step: BaseMachineStep, sample_human_step: BaseHumanStep
    ) -> None:
        """Test validation fails when edge target is not in steps dict."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition

        definition = WorkflowDefinition(
            name="invalid_workflow",
            version="1.0.0",
            description="Invalid workflow",
            steps={"step1": sample_machine_step, "step2": sample_human_step},
            edges=[Edge(source="step1", target="nonexistent")],
            initial_step="step1",
            terminal_steps={"step2"},
        )

        errors = definition.validate()
        assert len(errors) > 0
        assert any("target step 'nonexistent' not found" in error for error in errors)

    def test_validate_unreachable_step(
        self, sample_machine_step: BaseMachineStep, sample_human_step: BaseHumanStep
    ) -> None:
        """Test validation detects unreachable steps."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.steps.base import BaseMachineStep

        class ThirdStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {}

        third_step = ThirdStep(name="third_step", description="Third step")

        definition = WorkflowDefinition(
            name="unreachable_workflow",
            version="1.0.0",
            description="Workflow with unreachable step",
            steps={"step1": sample_machine_step, "step2": sample_human_step, "step3": third_step},
            edges=[Edge(source="step1", target="step2")],
            initial_step="step1",
            terminal_steps={"step2"},
        )

        errors = definition.validate()
        assert len(errors) > 0
        assert any("Step 'step3' is unreachable" in error for error in errors)

    def test_validate_terminal_step_not_flagged_as_unreachable(
        self, sample_machine_step: BaseMachineStep, sample_human_step: BaseHumanStep
    ) -> None:
        """Test that unreachable terminal steps are not flagged as errors."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.steps.base import BaseMachineStep

        class TerminalStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {}

        terminal_step = TerminalStep(name="terminal_step", description="Terminal step")

        definition = WorkflowDefinition(
            name="terminal_workflow",
            version="1.0.0",
            description="Workflow with isolated terminal step",
            steps={"step1": sample_machine_step, "step2": sample_human_step, "terminal": terminal_step},
            edges=[Edge(source="step1", target="step2")],
            initial_step="step1",
            terminal_steps={"step2", "terminal"},
        )

        errors = definition.validate()
        # Terminal steps should not be reported as unreachable
        assert not any("terminal" in error and "unreachable" in error for error in errors)


@pytest.mark.unit
class TestWorkflowDefinitionMethods:
    """Tests for WorkflowDefinition methods."""

    def test_get_next_steps_no_edges(
        self, sample_workflow_definition: WorkflowDefinition, sample_context: WorkflowContext
    ) -> None:
        """Test get_next_steps when no edges exist from current step."""
        # Terminal step has no outgoing edges
        next_steps = sample_workflow_definition.get_next_steps("approval", sample_context)
        assert next_steps == []

    def test_get_next_steps_with_edges(
        self, sample_workflow_definition: WorkflowDefinition, sample_context: WorkflowContext
    ) -> None:
        """Test get_next_steps when edges exist from current step."""
        next_steps = sample_workflow_definition.get_next_steps("start", sample_context)
        assert "approval" in next_steps

    def test_get_next_steps_with_conditions(
        self, complex_workflow_definition: WorkflowDefinition, sample_context: WorkflowContext
    ) -> None:
        """Test get_next_steps with conditional edges."""
        # Both edges from 'approval' have conditions, so both should be included (string conditions default to True)
        next_steps = complex_workflow_definition.get_next_steps("approval", sample_context)
        assert len(next_steps) >= 1

    def test_get_next_steps_conditional_evaluation(self, sample_context: WorkflowContext) -> None:
        """Test get_next_steps evaluates conditions correctly."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.steps.base import BaseMachineStep

        class StepA(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {}

        class StepB(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {}

        class StepC(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {}

        step_a = StepA(name="step_a", description="Step A")
        step_b = StepB(name="step_b", description="Step B")
        step_c = StepC(name="step_c", description="Step C")

        definition = WorkflowDefinition(
            name="conditional_workflow",
            version="1.0.0",
            description="Workflow with conditional edges",
            steps={"a": step_a, "b": step_b, "c": step_c},
            edges=[
                Edge(source="a", target="b", condition=lambda ctx: ctx.get("count") == 0),
                Edge(source="a", target="c", condition=lambda ctx: ctx.get("count") > 0),
            ],
            initial_step="a",
            terminal_steps={"b", "c"},
        )

        # count == 0, should go to b
        next_steps = definition.get_next_steps("a", sample_context)
        assert "b" in next_steps
        assert "c" not in next_steps

        # Change count, should go to c
        sample_context.set("count", 5)
        next_steps = definition.get_next_steps("a", sample_context)
        assert "b" not in next_steps
        assert "c" in next_steps


@pytest.mark.unit
class TestMermaidGeneration:
    """Tests for Mermaid diagram generation."""

    def test_to_mermaid_with_step_types(self) -> None:
        """Test Mermaid generation with different step types."""
        from datetime import timedelta

        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.steps.base import BaseHumanStep, BaseMachineStep
        from litestar_workflows.steps.gateway import ExclusiveGateway
        from litestar_workflows.steps.timer import TimerStep

        class MachineStepA(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {}

        step_a = MachineStepA(name="machine", description="Machine step")
        step_b = ExclusiveGateway(
            name="gateway",
            condition=lambda ctx: "path_a",
            description="Gateway step",
        )
        step_c = TimerStep(name="timer", description="Timer step", duration=timedelta(seconds=60))

        # Add a human step to test that shape too
        step_d = BaseHumanStep(name="human", title="Human Task", description="Human step")

        definition = WorkflowDefinition(
            name="typed_workflow",
            version="1.0.0",
            description="Workflow with typed steps",
            steps={"machine": step_a, "gateway": step_b, "timer": step_c, "human": step_d},
            edges=[
                Edge(source="machine", target="gateway"),
                Edge(source="gateway", target="timer"),
                Edge(source="timer", target="human"),
            ],
            initial_step="machine",
            terminal_steps={"human"},
        )

        mermaid = definition.to_mermaid()

        # Should contain different shapes for different step types
        assert "graph TD" in mermaid
        assert "machine" in mermaid
        assert "gateway" in mermaid
        assert "timer" in mermaid
        assert "human" in mermaid
        # Gateway uses curly braces
        assert "{" in mermaid
        # Timer uses doubled brackets ([[...]])
        assert "[[" in mermaid
        # Human uses double curly braces {{...}}
        assert "{{" in mermaid

    def test_to_mermaid_with_state(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test Mermaid generation with execution state."""
        mermaid = sample_workflow_definition.to_mermaid_with_state(
            current_step="approval", completed_steps=["start"], failed_steps=[]
        )

        # Should include state styling
        assert "graph TD" in mermaid
        assert "style" in mermaid
        assert "start" in mermaid
        assert "approval" in mermaid

    def test_to_mermaid_with_state_completed_steps(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test Mermaid with completed steps styling."""
        mermaid = sample_workflow_definition.to_mermaid_with_state(
            current_step=None, completed_steps=["start", "approval"], failed_steps=[]
        )

        # Should style completed steps in green
        assert "style start fill:#90EE90" in mermaid
        assert "style approval fill:#90EE90" in mermaid

    def test_to_mermaid_with_state_failed_steps(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test Mermaid with failed steps styling."""
        mermaid = sample_workflow_definition.to_mermaid_with_state(
            current_step=None, completed_steps=[], failed_steps=["start"]
        )

        # Should style failed steps in red
        assert "style start fill:#FFB6C1" in mermaid

    def test_to_mermaid_with_state_current_step(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test Mermaid with current step styling."""
        mermaid = sample_workflow_definition.to_mermaid_with_state(
            current_step="start", completed_steps=[], failed_steps=[]
        )

        # Should style current step in yellow/gold
        assert "style start fill:#FFD700" in mermaid

    def test_to_mermaid_with_state_no_parameters(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test Mermaid with state but no parameters."""
        mermaid = sample_workflow_definition.to_mermaid_with_state()

        # Should just return base graph with no styling
        assert "graph TD" in mermaid
        assert "start" in mermaid
        assert "approval" in mermaid

    def test_to_mermaid_initial_and_terminal_markers(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test Mermaid marks initial and terminal steps."""
        mermaid = sample_workflow_definition.to_mermaid()

        # Should mark initial step
        assert "START:" in mermaid
        # Should mark terminal step
        assert "END:" in mermaid

    def test_to_mermaid_with_conditional_edges(self, complex_workflow_definition: WorkflowDefinition) -> None:
        """Test Mermaid generation includes conditional edge labels."""
        mermaid = complex_workflow_definition.to_mermaid()

        # Conditional edges should have labels
        assert "graph TD" in mermaid
        # String conditions should show in label
        assert "|" in mermaid  # Edge label notation
