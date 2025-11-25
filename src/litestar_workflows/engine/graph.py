"""Workflow graph operations and navigation.

This module provides graph-based operations for workflow definitions,
including step navigation, validation, and path finding.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litestar_workflows.core.context import WorkflowContext
    from litestar_workflows.core.definition import Edge, WorkflowDefinition

__all__ = ["WorkflowGraph"]


class WorkflowGraph:
    """Graph representation of a workflow for navigation and validation.

    The graph provides methods to navigate between steps, validate structure,
    and determine execution paths based on workflow state.

    Attributes:
        definition: The workflow definition this graph represents.
        _adjacency: Adjacency list mapping step names to outgoing edges.
        _reverse_adjacency: Reverse adjacency list for finding predecessors.
    """

    def __init__(self, definition: WorkflowDefinition) -> None:
        """Initialize a workflow graph from a definition.

        Args:
            definition: The workflow definition to represent as a graph.
        """
        self.definition = definition
        self._adjacency: dict[str, list[Edge]] = {}
        self._reverse_adjacency: dict[str, list[str]] = {}
        self._build_adjacency()

    def _build_adjacency(self) -> None:
        """Build adjacency lists from workflow edges."""
        # Initialize adjacency lists for all steps
        for step_name in self.definition.steps:
            self._adjacency[step_name] = []
            self._reverse_adjacency[step_name] = []

        # Build adjacency lists from edges
        for edge in self.definition.edges:
            source = edge.source if isinstance(edge.source, str) else edge.source.name
            target = edge.target if isinstance(edge.target, str) else edge.target.name

            self._adjacency[source].append(edge)
            if target not in self._reverse_adjacency:
                self._reverse_adjacency[target] = []
            self._reverse_adjacency[target].append(source)

    @classmethod
    def from_definition(cls, definition: WorkflowDefinition) -> WorkflowGraph:
        """Create a workflow graph from a definition.

        Args:
            definition: The workflow definition.

        Returns:
            A WorkflowGraph instance.

        Example:
            >>> graph = WorkflowGraph.from_definition(my_definition)
        """
        return cls(definition)

    def get_next_steps(
        self,
        current: str,
        context: WorkflowContext,
    ) -> list[str]:
        """Get the next steps from the current step.

        Evaluates edge conditions to determine which steps should execute next.
        If multiple unconditional edges exist, all targets are returned (parallel).

        Args:
            current: Name of the current step.
            context: The workflow context for condition evaluation.

        Returns:
            List of next step names. Empty list if current step is terminal.

        Example:
            >>> next_steps = graph.get_next_steps("approval", context)
            >>> if len(next_steps) > 1:
            ...     print("Parallel execution required")
        """
        if current not in self._adjacency:
            return []

        next_steps = []

        for edge in self._adjacency[current]:
            target = edge.target if isinstance(edge.target, str) else edge.target.name

            # If edge has a condition, evaluate it
            if edge.condition is not None:
                # Use the edge's evaluate_condition method for proper type handling
                if edge.evaluate_condition(context):
                    next_steps.append(target)
            else:
                # Unconditional edge
                next_steps.append(target)

        return next_steps

    def get_previous_steps(self, current: str) -> list[str]:
        """Get the steps that lead to the current step.

        Args:
            current: Name of the current step.

        Returns:
            List of predecessor step names.

        Example:
            >>> predecessors = graph.get_previous_steps("final_step")
        """
        return self._reverse_adjacency.get(current, [])

    def is_terminal(self, step_name: str) -> bool:
        """Check if a step is a terminal (end) step.

        Args:
            step_name: Name of the step to check.

        Returns:
            True if the step has no outgoing edges or is in terminal_steps.

        Example:
            >>> if graph.is_terminal("approval"):
            ...     print("Workflow ends here")
        """
        # Explicitly marked as terminal
        if step_name in self.definition.terminal_steps:
            return True

        # No outgoing edges
        return not self._adjacency.get(step_name, [])

    def validate(self) -> list[str]:
        """Validate the workflow graph structure.

        Checks for common graph issues:
        - Unreachable steps (not connected to initial step)
        - Disconnected components
        - Steps with no outgoing edges that aren't marked terminal
        - Invalid edge references

        Returns:
            List of validation error messages. Empty list if valid.

        Example:
            >>> errors = graph.validate()
            >>> if errors:
            ...     for error in errors:
            ...         print(f"Validation error: {error}")
        """
        errors = []

        # Check that initial step exists
        if self.definition.initial_step not in self.definition.steps:
            errors.append(f"Initial step '{self.definition.initial_step}' not found in steps")

        # Check for invalid edge references
        for edge in self.definition.edges:
            source = edge.source if isinstance(edge.source, str) else edge.source.name
            target = edge.target if isinstance(edge.target, str) else edge.target.name

            if source not in self.definition.steps:
                errors.append(f"Edge source '{source}' not found in steps")
            if target not in self.definition.steps:
                errors.append(f"Edge target '{target}' not found in steps")

        # Check for unreachable steps
        reachable = self._get_reachable_steps()
        for step_name in self.definition.steps:
            if step_name not in reachable and step_name != self.definition.initial_step:
                errors.append(f"Step '{step_name}' is unreachable from initial step")

        # Check for steps with no outgoing edges that aren't terminal
        for step_name in self.definition.steps:
            if not self._adjacency.get(step_name) and step_name not in self.definition.terminal_steps:
                errors.append(f"Step '{step_name}' has no outgoing edges but is not marked as terminal")

        return errors

    def _get_reachable_steps(self) -> set[str]:
        """Get all steps reachable from the initial step.

        Returns:
            Set of step names that can be reached.
        """
        if self.definition.initial_step not in self.definition.steps:
            return set()

        reachable = set()
        to_visit = [self.definition.initial_step]

        while to_visit:
            current = to_visit.pop()
            if current in reachable:
                continue

            reachable.add(current)

            # Add all targets of outgoing edges
            for edge in self._adjacency.get(current, []):
                target = edge.target if isinstance(edge.target, str) else edge.target.name
                if target not in reachable:
                    to_visit.append(target)

        return reachable

    def get_all_paths(
        self,
        start: str,
        end: str,
        max_paths: int = 100,
    ) -> list[list[str]]:
        """Find all paths from start step to end step.

        Args:
            start: Starting step name.
            end: Ending step name.
            max_paths: Maximum number of paths to find (prevents infinite loops).

        Returns:
            List of paths, where each path is a list of step names.

        Example:
            >>> paths = graph.get_all_paths("start", "end")
            >>> for path in paths:
            ...     print(" -> ".join(path))
        """
        paths: list[list[str]] = []
        self._find_paths(start, end, [], paths, max_paths)
        return paths

    def _find_paths(
        self,
        current: str,
        end: str,
        path: list[str],
        paths: list[list[str]],
        max_paths: int,
    ) -> None:
        """Recursive helper for finding all paths.

        Args:
            current: Current step being visited.
            end: Target step.
            path: Current path being explored.
            paths: Accumulated list of complete paths.
            max_paths: Maximum paths to find.
        """
        # Prevent infinite loops and limit results
        if len(paths) >= max_paths or current in path:
            return

        path = [*path, current]

        if current == end:
            paths.append(path)
            return

        for edge in self._adjacency.get(current, []):
            target = edge.target if isinstance(edge.target, str) else edge.target.name
            self._find_paths(target, end, path, paths, max_paths)

    def get_step_depth(self, step_name: str) -> int:
        """Get the minimum depth from initial step to the given step.

        Args:
            step_name: Name of the step.

        Returns:
            Minimum number of steps from initial to this step. Returns -1 if unreachable.

        Example:
            >>> depth = graph.get_step_depth("final_approval")
            >>> print(f"Step is at depth {depth}")
        """
        if step_name == self.definition.initial_step:
            return 0

        visited = {self.definition.initial_step: 0}
        queue = [self.definition.initial_step]

        while queue:
            current = queue.pop(0)
            current_depth = visited[current]

            for edge in self._adjacency.get(current, []):
                target = edge.target if isinstance(edge.target, str) else edge.target.name

                if target == step_name:
                    return current_depth + 1

                if target not in visited:
                    visited[target] = current_depth + 1
                    queue.append(target)

        return -1  # Unreachable
