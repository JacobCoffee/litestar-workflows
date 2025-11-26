"""Composable step groups for litestar-workflows."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from litestar_workflows.core import WorkflowContext
    from litestar_workflows.core.protocols import ExecutionEngine, Step


class StepGroup(ABC):
    """Base for composable step patterns.

    Step groups allow you to compose multiple steps into reusable patterns
    like sequences, parallel execution, and conditional branching.
    """

    @abstractmethod
    async def execute(self, context: WorkflowContext, engine: ExecutionEngine) -> Any:
        """Execute the step group.

        Args:
            context: The workflow execution context.
            engine: The execution engine to delegate step execution.

        Returns:
            The result of the group execution.

        Raises:
            Exception: Any exception during group execution.
        """
        ...


class SequentialGroup(StepGroup):
    """Execute steps in sequence, passing results.

    This implements the Chain pattern where each step receives the result
    of the previous step as input. The final step's result is returned.

    Example:
        >>> group = SequentialGroup(step1, step2, step3)
        >>> result = await group.execute(context, engine)
        # step1 -> step2(result1) -> step3(result2) -> result3
    """

    def __init__(self, *steps: Step[Any] | StepGroup) -> None:
        """Initialize a sequential group.

        Args:
            *steps: Steps or groups to execute in sequence.
        """
        self.steps = steps

    async def execute(self, context: WorkflowContext, engine: ExecutionEngine) -> Any:
        """Execute steps sequentially, passing results forward.

        Args:
            context: The workflow execution context.
            engine: The execution engine to delegate step execution.

        Returns:
            The result of the final step.

        Raises:
            Exception: Any exception from step execution.
        """
        result: Any = None

        for step in self.steps:
            if isinstance(step, StepGroup):
                result = await step.execute(context, engine)
            else:
                result = await engine.execute_step(step, context, previous_result=result)

        return result


class ParallelGroup(StepGroup):
    """Execute steps in parallel.

    This implements the Group pattern where multiple steps execute concurrently.
    Optionally supports a callback step (Chord pattern) that receives all results.

    Example:
        >>> # Simple parallel execution
        >>> group = ParallelGroup(step1, step2, step3)
        >>> results = await group.execute(context, engine)  # [result1, result2, result3]

        >>> # Chord pattern with callback
        >>> group = ParallelGroup(step1, step2, step3, callback=aggregate_step)
        >>> result = await group.execute(context, engine)  # aggregate_step([r1, r2, r3])
    """

    def __init__(
        self,
        *steps: Step[Any] | StepGroup,
        callback: Step[Any] | None = None,
    ) -> None:
        """Initialize a parallel group.

        Args:
            *steps: Steps or groups to execute in parallel.
            callback: Optional callback step to process results (Chord pattern).
        """
        self.steps = steps
        self.callback = callback

    async def execute(self, context: WorkflowContext, engine: ExecutionEngine) -> list[Any] | Any:
        """Execute steps in parallel using asyncio.gather.

        Args:
            context: The workflow execution context.
            engine: The execution engine to delegate step execution.

        Returns:
            List of results if no callback, otherwise callback result.

        Raises:
            Exception: Any exception from step execution.
        """
        tasks = []

        for step in self.steps:
            if isinstance(step, StepGroup):
                tasks.append(step.execute(context, engine))
            else:
                tasks.append(engine.execute_step(step, context))

        results = await asyncio.gather(*tasks)

        if self.callback:
            return await engine.execute_step(self.callback, context, previous_result=results)

        return results


class ConditionalGroup(StepGroup):
    """Execute one of multiple branches based on condition.

    This implements the Gateway pattern where a condition function determines
    which branch to execute. Similar to if/else or switch statements.

    Example:
        >>> def check_status(ctx: WorkflowContext) -> str:
        ...     return "approved" if ctx.get("approved") else "rejected"
        >>> group = ConditionalGroup(
        ...     condition=check_status,
        ...     branches={
        ...         "approved": approve_step,
        ...         "rejected": reject_step,
        ...     },
        ... )
        >>> result = await group.execute(context, engine)
    """

    def __init__(
        self,
        condition: Callable[[WorkflowContext], str],
        branches: dict[str, Step[Any] | StepGroup],
    ) -> None:
        """Initialize a conditional group.

        Args:
            condition: Function that evaluates context and returns branch key.
            branches: Map of branch keys to steps or groups.
        """
        self.condition = condition
        self.branches = branches

    async def execute(self, context: WorkflowContext, engine: ExecutionEngine) -> Any:
        """Execute the branch selected by the condition.

        Args:
            context: The workflow execution context.
            engine: The execution engine to delegate step execution.

        Returns:
            The result of the selected branch, or None if no match.

        Raises:
            Exception: Any exception from step execution.
        """
        branch_key = self.condition(context)

        if branch_key not in self.branches:
            return None

        branch = self.branches[branch_key]

        if isinstance(branch, StepGroup):
            return await branch.execute(context, engine)

        return await engine.execute_step(branch, context)
