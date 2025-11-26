"""Tests for web graph visualization utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from litestar_workflows.core.definition import WorkflowDefinition


@pytest.mark.unit
class TestWebGraphVisualization:
    """Tests for web graph visualization functions."""

    def test_generate_mermaid_graph_basic(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test basic Mermaid graph generation."""
        from litestar_workflows.web.graph import generate_mermaid_graph

        mermaid = generate_mermaid_graph(sample_workflow_definition)

        # Should contain graph declaration
        assert "graph" in mermaid.lower() or "flowchart" in mermaid.lower()

        # Should contain step names
        assert "start" in mermaid.lower()
        assert "approval" in mermaid.lower()

        # Should contain connection
        assert "-->" in mermaid

    def test_generate_mermaid_graph_complex(self, complex_workflow_definition: WorkflowDefinition) -> None:
        """Test Mermaid graph generation with complex workflow."""
        from litestar_workflows.web.graph import generate_mermaid_graph

        mermaid = generate_mermaid_graph(complex_workflow_definition)

        # Should contain all steps
        assert "start" in mermaid.lower()
        assert "process" in mermaid.lower()
        assert "approval" in mermaid.lower()
        assert "publish" in mermaid.lower()
        assert "reject" in mermaid.lower()

        # Should contain edges
        assert "-->" in mermaid

    def test_generate_mermaid_graph_with_parallel_steps(self) -> None:
        """Test Mermaid graph generation with parallel execution paths."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.steps.base import BaseMachineStep
        from litestar_workflows.web.graph import generate_mermaid_graph

        class StartStep(BaseMachineStep):
            async def execute(self, context):
                return {}

        class ParallelA(BaseMachineStep):
            async def execute(self, context):
                return {}

        class ParallelB(BaseMachineStep):
            async def execute(self, context):
                return {}

        class JoinStep(BaseMachineStep):
            async def execute(self, context):
                return {}

        definition = WorkflowDefinition(
            name="parallel_workflow",
            version="1.0.0",
            description="Workflow with parallel paths",
            steps={
                "start": StartStep(name="start", description="Start"),
                "parallel_a": ParallelA(name="parallel_a", description="Path A"),
                "parallel_b": ParallelB(name="parallel_b", description="Path B"),
                "join": JoinStep(name="join", description="Join"),
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

        mermaid = generate_mermaid_graph(definition)

        # Should contain all steps
        assert "start" in mermaid.lower()
        assert "parallel_a" in mermaid.lower()
        assert "parallel_b" in mermaid.lower()
        assert "join" in mermaid.lower()

        # Should contain multiple edges from start
        assert "-->" in mermaid

    def test_generate_mermaid_graph_with_conditions(self, complex_workflow_definition: WorkflowDefinition) -> None:
        """Test Mermaid graph generation with conditional edges."""
        from litestar_workflows.web.graph import generate_mermaid_graph

        mermaid = generate_mermaid_graph(complex_workflow_definition)

        # Should contain conditional branches
        assert "approval" in mermaid.lower()
        assert "publish" in mermaid.lower() or "reject" in mermaid.lower()

    def test_generate_mermaid_graph_with_state_no_state(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test Mermaid graph with state highlighting - no state."""
        from litestar_workflows.web.graph import generate_mermaid_graph_with_state

        mermaid = generate_mermaid_graph_with_state(
            sample_workflow_definition,
            current_step=None,
            completed_steps=None,
            failed_steps=None,
        )

        # Should still generate valid mermaid
        assert "graph" in mermaid.lower() or "flowchart" in mermaid.lower()
        assert "start" in mermaid.lower()

    def test_generate_mermaid_graph_with_state_current_step(
        self, sample_workflow_definition: WorkflowDefinition
    ) -> None:
        """Test Mermaid graph with current step highlighted."""
        from litestar_workflows.web.graph import generate_mermaid_graph_with_state

        mermaid = generate_mermaid_graph_with_state(
            sample_workflow_definition,
            current_step="approval",
            completed_steps=["start"],
            failed_steps=None,
        )

        # Should contain graph and steps
        assert "approval" in mermaid.lower()
        assert "start" in mermaid.lower()

    def test_generate_mermaid_graph_with_state_completed_steps(
        self, complex_workflow_definition: WorkflowDefinition
    ) -> None:
        """Test Mermaid graph with completed steps highlighted."""
        from litestar_workflows.web.graph import generate_mermaid_graph_with_state

        mermaid = generate_mermaid_graph_with_state(
            complex_workflow_definition,
            current_step="approval",
            completed_steps=["start", "process"],
            failed_steps=None,
        )

        # Should contain all relevant steps
        assert "start" in mermaid.lower()
        assert "process" in mermaid.lower()
        assert "approval" in mermaid.lower()

    def test_generate_mermaid_graph_with_state_failed_steps(
        self, complex_workflow_definition: WorkflowDefinition
    ) -> None:
        """Test Mermaid graph with failed steps highlighted."""
        from litestar_workflows.web.graph import generate_mermaid_graph_with_state

        mermaid = generate_mermaid_graph_with_state(
            complex_workflow_definition,
            current_step=None,
            completed_steps=["start"],
            failed_steps=["process"],
        )

        # Should contain graph
        assert "start" in mermaid.lower()
        assert "process" in mermaid.lower()

    def test_generate_mermaid_graph_with_state_all_states(
        self, complex_workflow_definition: WorkflowDefinition
    ) -> None:
        """Test Mermaid graph with all state types highlighted."""
        from litestar_workflows.web.graph import generate_mermaid_graph_with_state

        mermaid = generate_mermaid_graph_with_state(
            complex_workflow_definition,
            current_step="publish",
            completed_steps=["start", "process", "approval"],
            failed_steps=["reject"],
        )

        # Should generate valid mermaid
        assert "graph" in mermaid.lower() or "flowchart" in mermaid.lower()


@pytest.mark.unit
class TestParseGraphToDict:
    """Tests for parse_graph_to_dict function."""

    def test_parse_graph_to_dict_basic(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test parsing workflow to dictionary."""
        from litestar_workflows.web.graph import parse_graph_to_dict

        result = parse_graph_to_dict(sample_workflow_definition)

        # Should have nodes and edges
        assert "nodes" in result
        assert "edges" in result

        # Should have correct number of nodes
        assert len(result["nodes"]) == 2

        # Should have node information
        nodes = result["nodes"]
        node_ids = {node["id"] for node in nodes}
        assert "start" in node_ids
        assert "approval" in node_ids

        # Each node should have required fields
        for node in nodes:
            assert "id" in node
            assert "label" in node
            assert "type" in node
            assert "is_initial" in node
            assert "is_terminal" in node

        # Should have edges
        assert len(result["edges"]) == 1
        edge = result["edges"][0]
        assert edge["source"] == "start"
        assert edge["target"] == "approval"

    def test_parse_graph_to_dict_complex(self, complex_workflow_definition: WorkflowDefinition) -> None:
        """Test parsing complex workflow to dictionary."""
        from litestar_workflows.web.graph import parse_graph_to_dict

        result = parse_graph_to_dict(complex_workflow_definition)

        # Should have all nodes
        assert len(result["nodes"]) == 5

        node_ids = {node["id"] for node in result["nodes"]}
        assert node_ids == {"start", "process", "approval", "publish", "reject"}

        # Should have all edges
        assert len(result["edges"]) == 4

    def test_parse_graph_to_dict_node_types(self) -> None:
        """Test that different step types are correctly identified."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.steps.base import BaseHumanStep, BaseMachineStep
        from litestar_workflows.steps.gateway import ExclusiveGateway
        from litestar_workflows.steps.timer import TimerStep
        from litestar_workflows.steps.webhook import WebhookStep
        from litestar_workflows.web.graph import parse_graph_to_dict

        class MachineStep(BaseMachineStep):
            async def execute(self, context):
                return {}

        class HumanStep(BaseHumanStep):
            async def execute(self, context):
                return {}

        from datetime import timedelta

        def gateway_condition(context):
            return "timer"

        definition = WorkflowDefinition(
            name="type_test_workflow",
            version="1.0.0",
            description="Test different step types",
            steps={
                "machine": MachineStep(name="machine", description="Machine"),
                "human": HumanStep(name="human", title="Human Task", description="Human", form_schema={}),
                "gateway": ExclusiveGateway(name="gateway", description="Gateway", condition=gateway_condition),
                "timer": TimerStep(name="timer", description="Timer", duration=timedelta(seconds=60)),
                "webhook": WebhookStep(name="webhook", description="Webhook"),
            },
            edges=[
                Edge(source="machine", target="human"),
                Edge(source="human", target="gateway"),
                Edge(source="gateway", target="timer"),
                Edge(source="timer", target="webhook"),
            ],
            initial_step="machine",
            terminal_steps={"webhook"},
        )

        result = parse_graph_to_dict(definition)

        # Find each node and check its type
        nodes_by_id = {node["id"]: node for node in result["nodes"]}

        assert nodes_by_id["machine"]["type"] == "machine"
        assert nodes_by_id["human"]["type"] == "human"
        assert nodes_by_id["gateway"]["type"] == "gateway"
        assert nodes_by_id["timer"]["type"] == "timer"
        assert nodes_by_id["webhook"]["type"] == "webhook"

    def test_parse_graph_to_dict_initial_and_terminal_markers(
        self, sample_workflow_definition: WorkflowDefinition
    ) -> None:
        """Test that initial and terminal steps are correctly marked."""
        from litestar_workflows.web.graph import parse_graph_to_dict

        result = parse_graph_to_dict(sample_workflow_definition)

        nodes_by_id = {node["id"]: node for node in result["nodes"]}

        # Start should be initial
        assert nodes_by_id["start"]["is_initial"] is True
        assert nodes_by_id["start"]["is_terminal"] is False

        # Approval should be terminal
        assert nodes_by_id["approval"]["is_initial"] is False
        assert nodes_by_id["approval"]["is_terminal"] is True

    def test_parse_graph_to_dict_edge_conditions_callable(self) -> None:
        """Test that callable edge conditions are handled correctly."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.steps.base import BaseMachineStep
        from litestar_workflows.web.graph import parse_graph_to_dict

        class Step1(BaseMachineStep):
            async def execute(self, context):
                return {}

        class Step2(BaseMachineStep):
            async def execute(self, context):
                return {}

        def condition_func(context):
            return context.get("approved", False)

        definition = WorkflowDefinition(
            name="condition_workflow",
            version="1.0.0",
            description="Workflow with callable condition",
            steps={
                "step1": Step1(name="step1", description="Step 1"),
                "step2": Step2(name="step2", description="Step 2"),
            },
            edges=[
                Edge(source="step1", target="step2", condition=condition_func),
            ],
            initial_step="step1",
            terminal_steps={"step2"},
        )

        result = parse_graph_to_dict(definition)

        # Edge should have condition marked as "conditional"
        edge = result["edges"][0]
        assert "condition" in edge
        assert edge["condition"] == "conditional"

    def test_parse_graph_to_dict_edge_conditions_string(self) -> None:
        """Test that string edge conditions are preserved."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.steps.base import BaseMachineStep
        from litestar_workflows.web.graph import parse_graph_to_dict

        class Step1(BaseMachineStep):
            async def execute(self, context):
                return {}

        class Step2(BaseMachineStep):
            async def execute(self, context):
                return {}

        definition = WorkflowDefinition(
            name="string_condition_workflow",
            version="1.0.0",
            description="Workflow with string condition",
            steps={
                "step1": Step1(name="step1", description="Step 1"),
                "step2": Step2(name="step2", description="Step 2"),
            },
            edges=[
                Edge(source="step1", target="step2", condition="approved"),
            ],
            initial_step="step1",
            terminal_steps={"step2"},
        )

        result = parse_graph_to_dict(definition)

        # Edge should have condition as string
        edge = result["edges"][0]
        assert "condition" in edge
        assert edge["condition"] == "approved"

    def test_parse_graph_to_dict_edge_no_condition(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test that edges without conditions don't have condition key."""
        from litestar_workflows.web.graph import parse_graph_to_dict

        result = parse_graph_to_dict(sample_workflow_definition)

        # Edge should not have condition key
        edge = result["edges"][0]
        assert "condition" not in edge

    def test_parse_graph_to_dict_parallel_edges(self) -> None:
        """Test parsing workflow with parallel execution paths."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.steps.base import BaseMachineStep
        from litestar_workflows.web.graph import parse_graph_to_dict

        class StartStep(BaseMachineStep):
            async def execute(self, context):
                return {}

        class PathA(BaseMachineStep):
            async def execute(self, context):
                return {}

        class PathB(BaseMachineStep):
            async def execute(self, context):
                return {}

        definition = WorkflowDefinition(
            name="parallel_workflow",
            version="1.0.0",
            description="Workflow with parallel paths",
            steps={
                "start": StartStep(name="start", description="Start"),
                "path_a": PathA(name="path_a", description="Path A"),
                "path_b": PathB(name="path_b", description="Path B"),
            },
            edges=[
                Edge(source="start", target="path_a"),
                Edge(source="start", target="path_b"),
            ],
            initial_step="start",
            terminal_steps={"path_a", "path_b"},
        )

        result = parse_graph_to_dict(definition)

        # Should have 2 edges from start
        edges_from_start = [e for e in result["edges"] if e["source"] == "start"]
        assert len(edges_from_start) == 2

        targets = {e["target"] for e in edges_from_start}
        assert targets == {"path_a", "path_b"}

    def test_parse_graph_to_dict_node_labels(self, sample_workflow_definition: WorkflowDefinition) -> None:
        """Test that node labels are correctly formatted."""
        from litestar_workflows.web.graph import parse_graph_to_dict

        result = parse_graph_to_dict(sample_workflow_definition)

        nodes_by_id = {node["id"]: node for node in result["nodes"]}

        # Labels should be title case with underscores converted to spaces
        assert nodes_by_id["start"]["label"] == "Start"
        # Note: "approval" becomes "Approval" (single word, title case)
        assert nodes_by_id["approval"]["label"] == "Approval"
