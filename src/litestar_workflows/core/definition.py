"""Workflow definition and edge structures.

This module provides the data structures for defining workflow graphs, including
edges (transitions) and the complete workflow definition.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from litestar_workflows.core.context import WorkflowContext
    from litestar_workflows.core.protocols import Step

__all__ = ["Edge", "WorkflowDefinition"]


@dataclass
class Edge:
    """Defines a transition between workflow steps.

    An edge represents a directed connection from one step to another, optionally
    conditioned on a predicate function or expression.

    Attributes:
        source: Name of the source step or the Step class itself.
        target: Name of the target step or the Step class itself.
        condition: Optional condition for edge traversal. Can be a callable that
            takes WorkflowContext and returns bool, or a string expression.

    Example:
        >>> edge = Edge(
        ...     source="submit",
        ...     target="review",
        ...     condition=lambda ctx: ctx.get("auto_approve") is False,
        ... )
        >>> conditional_edge = Edge(
        ...     source="review", target="approve", condition="context.get('approved') == True"
        ... )
    """

    source: str | type[Step]
    target: str | type[Step]
    condition: str | Callable[[WorkflowContext], bool] | None = None

    def evaluate_condition(self, context: WorkflowContext) -> bool:
        """Evaluate the edge condition against the workflow context.

        Args:
            context: The current workflow execution context.

        Returns:
            True if the condition is met or if no condition exists, False otherwise.

        Example:
            >>> edge = Edge(source="a", target="b", condition=lambda ctx: ctx.get("value") > 10)
            >>> context.set("value", 15)
            >>> edge.evaluate_condition(context)
            True
        """
        if self.condition is None:
            return True

        if callable(self.condition):
            return self.condition(context)

        # For string expressions, could implement SpEL-like evaluation
        # For now, we'll just return True (future enhancement)
        return True

    def get_source_name(self) -> str:
        """Get the name of the source step.

        Returns:
            The source step name as a string.
        """
        if isinstance(self.source, str):
            return self.source
        return self.source.name

    def get_target_name(self) -> str:
        """Get the name of the target step.

        Returns:
            The target step name as a string.
        """
        if isinstance(self.target, str):
            return self.target
        return self.target.name


@dataclass
class WorkflowDefinition:
    """Declarative workflow structure.

    The WorkflowDefinition captures the complete structure of a workflow including
    all steps, edges, and metadata. It serves as the blueprint for workflow execution.

    Attributes:
        name: Unique identifier for the workflow.
        version: Version string for workflow versioning.
        description: Human-readable description of the workflow's purpose.
        steps: Dictionary mapping step names to Step instances.
        edges: List of Edge instances defining the workflow graph.
        initial_step: Name of the step to execute first.
        terminal_steps: Set of step names that mark workflow completion.

    Example:
        >>> from litestar_workflows.core.types import StepType
        >>> definition = WorkflowDefinition(
        ...     name="approval_flow",
        ...     version="1.0.0",
        ...     description="Document approval workflow",
        ...     steps={
        ...         "submit": SubmitStep(),
        ...         "review": ReviewStep(),
        ...         "approve": ApproveStep(),
        ...     },
        ...     edges=[
        ...         Edge(source="submit", target="review"),
        ...         Edge(source="review", target="approve"),
        ...     ],
        ...     initial_step="submit",
        ...     terminal_steps={"approve"},
        ... )
    """

    name: str
    version: str
    description: str
    steps: dict[str, Step[Any]]
    edges: list[Edge]
    initial_step: str
    terminal_steps: set[str] = field(default_factory=set)

    def validate(self) -> list[str]:
        """Validate the workflow definition for common issues.

        Returns:
            List of validation error messages. Empty list if valid.

        Example:
            >>> errors = definition.validate()
            >>> if errors:
            ...     print("Validation errors:", errors)
        """
        errors: list[str] = []

        # Check initial step exists
        if self.initial_step not in self.steps:
            errors.append(f"Initial step '{self.initial_step}' not found in steps")

        # Check terminal steps exist
        for terminal in self.terminal_steps:
            if terminal not in self.steps:
                errors.append(f"Terminal step '{terminal}' not found in steps")

        # Check edge validity
        for i, edge in enumerate(self.edges):
            source_name = edge.get_source_name()
            target_name = edge.get_target_name()

            if source_name not in self.steps:
                errors.append(f"Edge {i}: source step '{source_name}' not found")

            if target_name not in self.steps:
                errors.append(f"Edge {i}: target step '{target_name}' not found")

        # Check for unreachable steps (excluding terminal steps)
        reachable = {self.initial_step}
        changed = True
        while changed:
            changed = False
            for edge in self.edges:
                source = edge.get_source_name()
                target = edge.get_target_name()
                if source in reachable and target not in reachable:
                    reachable.add(target)
                    changed = True

        unreachable = set(self.steps.keys()) - reachable
        for step_name in unreachable:
            if step_name not in self.terminal_steps:
                errors.append(f"Step '{step_name}' is unreachable from initial step")

        return errors

    def get_next_steps(self, current_step: str, context: WorkflowContext) -> list[str]:
        """Get the list of next steps from the current step based on edge conditions.

        Args:
            current_step: Name of the current step.
            context: The workflow execution context for condition evaluation.

        Returns:
            List of step names that should be executed next.

        Example:
            >>> next_steps = definition.get_next_steps("review", context)
            >>> if "approve" in next_steps:
            ...     print("Moving to approval")
        """
        next_steps = []
        for edge in self.edges:
            if edge.get_source_name() == current_step and edge.evaluate_condition(context):
                next_steps.append(edge.get_target_name())
        return next_steps

    def to_mermaid(self) -> str:
        """Generate a MermaidJS graph representation of the workflow.

        Returns:
            MermaidJS graph definition as a string.

        Example:
            >>> mermaid = definition.to_mermaid()
            >>> print(mermaid)
            graph TD
                submit[Submit]
                review{Review}
                approve[Approve]
                submit --> review
                review --> approve
        """
        lines = ["graph TD"]

        # Add nodes with shapes based on step type
        for step_name, step in self.steps.items():
            shape_start = "["
            shape_end = "]"

            # Use different shapes for different step types
            if hasattr(step, "step_type"):
                from litestar_workflows.core.types import StepType

                if step.step_type == StepType.HUMAN:
                    shape_start = "{{"
                    shape_end = "}}"
                elif step.step_type == StepType.GATEWAY:
                    shape_start = "{"
                    shape_end = "}"
                elif step.step_type == StepType.TIMER:
                    shape_start = "([["
                    shape_end = "]])"

            # Mark initial and terminal steps
            prefix = ""
            if step_name == self.initial_step:
                prefix = "START: "
            elif step_name in self.terminal_steps:
                prefix = "END: "

            lines.append(f"    {step_name}{shape_start}{prefix}{step_name.replace('_', ' ').title()}{shape_end}")

        # Add edges
        for edge in self.edges:
            source = edge.get_source_name()
            target = edge.get_target_name()
            label = ""
            if edge.condition is not None:
                if isinstance(edge.condition, str):
                    # Remove quotes for mermaid compatibility (they break syntax)
                    safe_condition = edge.condition.replace("'", "").replace('"', "")
                    label = f"|{safe_condition}|"
                else:
                    label = "|conditional|"
            lines.append(f"    {source} -->{label} {target}")

        return "\n".join(lines)

    def to_mermaid_with_state(
        self,
        current_step: str | None = None,
        completed_steps: list[str] | None = None,
        failed_steps: list[str] | None = None,
    ) -> str:
        """Generate a MermaidJS graph with execution state highlighting.

        Args:
            current_step: Name of the currently executing step.
            completed_steps: List of successfully completed step names.
            failed_steps: List of failed step names.

        Returns:
            MermaidJS graph definition with state styling.

        Example:
            >>> mermaid = definition.to_mermaid_with_state(
            ...     current_step="review", completed_steps=["submit"], failed_steps=[]
            ... )
        """
        completed_steps = completed_steps or []
        failed_steps = failed_steps or []

        base_graph = self.to_mermaid()
        lines = base_graph.split("\n")

        # Add styling
        style_lines = []
        for step_name in completed_steps:
            style_lines.append(f"    style {step_name} fill:#90EE90,stroke:#006400,stroke-width:2px")

        for step_name in failed_steps:
            style_lines.append(f"    style {step_name} fill:#FFB6C1,stroke:#8B0000,stroke-width:2px")

        if current_step:
            style_lines.append(f"    style {current_step} fill:#FFD700,stroke:#FFA500,stroke-width:3px")

        lines.extend(style_lines)
        return "\n".join(lines)
