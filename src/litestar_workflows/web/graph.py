"""Graph visualization utilities for workflows.

This module provides utilities for generating visual representations of
workflow graphs, primarily using MermaidJS format.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from litestar_workflows.core.definition import WorkflowDefinition

__all__ = ["generate_mermaid_graph", "parse_graph_to_dict"]


def generate_mermaid_graph(definition: WorkflowDefinition) -> str:
    """Generate a MermaidJS graph representation of a workflow definition.

    This function creates a Mermaid flowchart diagram that visualizes the
    workflow's steps and transitions. Different step types are represented
    with different node shapes.

    Args:
        definition: The workflow definition to visualize.

    Returns:
        A MermaidJS flowchart definition as a string.

    Example:
        >>> mermaid = generate_mermaid_graph(definition)
        >>> print(mermaid)
        graph TD
            submit[Submit]
            review{{Review}}
            approve[Approve]
            submit --> review
            review --> approve
    """
    return definition.to_mermaid()


def generate_mermaid_graph_with_state(
    definition: WorkflowDefinition,
    current_step: str | None = None,
    completed_steps: list[str] | None = None,
    failed_steps: list[str] | None = None,
) -> str:
    """Generate a MermaidJS graph with execution state highlighting.

    This function creates a Mermaid flowchart that includes visual styling
    to highlight the current step, completed steps, and failed steps.

    Args:
        definition: The workflow definition to visualize.
        current_step: Name of the currently executing step.
        completed_steps: List of successfully completed step names.
        failed_steps: List of failed step names.

    Returns:
        A MermaidJS flowchart definition with state styling.

    Example:
        >>> mermaid = generate_mermaid_graph_with_state(
        ...     definition,
        ...     current_step="review",
        ...     completed_steps=["submit"],
        ...     failed_steps=[],
        ... )
    """
    return definition.to_mermaid_with_state(
        current_step=current_step,
        completed_steps=completed_steps,
        failed_steps=failed_steps,
    )


def parse_graph_to_dict(definition: WorkflowDefinition) -> dict[str, Any]:
    """Parse a workflow definition into a dictionary representation.

    This function extracts nodes and edges from a workflow definition
    into a structured dictionary format suitable for JSON serialization.

    Args:
        definition: The workflow definition to parse.

    Returns:
        A dictionary containing nodes and edges lists.

    Example:
        >>> graph_dict = parse_graph_to_dict(definition)
        >>> print(graph_dict["nodes"])
        [{"id": "submit", "label": "Submit", "type": "machine"}, ...]
    """
    from litestar_workflows.core.types import StepType

    nodes = []
    for step_name, step in definition.steps.items():
        step_type = "machine"  # default
        if hasattr(step, "step_type"):
            if step.step_type == StepType.HUMAN:
                step_type = "human"
            elif step.step_type == StepType.GATEWAY:
                step_type = "gateway"
            elif step.step_type == StepType.TIMER:
                step_type = "timer"
            elif step.step_type == StepType.WEBHOOK:
                step_type = "webhook"

        node = {
            "id": step_name,
            "label": step_name.replace("_", " ").title(),
            "type": step_type,
            "is_initial": step_name == definition.initial_step,
            "is_terminal": step_name in definition.terminal_steps,
        }
        nodes.append(node)

    edges = []
    for edge in definition.edges:
        edge_dict = {
            "source": edge.get_source_name(),
            "target": edge.get_target_name(),
        }
        if edge.condition is not None:
            if callable(edge.condition):
                edge_dict["condition"] = "conditional"
            else:
                edge_dict["condition"] = str(edge.condition)
        edges.append(edge_dict)

    return {
        "nodes": nodes,
        "edges": edges,
    }
