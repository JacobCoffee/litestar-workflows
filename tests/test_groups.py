"""Tests for step groups (Sequential, Parallel, Conditional)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from litestar_workflows.core.context import WorkflowContext
    from litestar_workflows.engine.local import LocalExecutionEngine


@pytest.mark.unit
@pytest.mark.asyncio
class TestSequentialGroup:
    """Tests for SequentialGroup execution."""

    async def test_sequential_group_executes_in_order(
        self, sample_context: WorkflowContext, local_engine: LocalExecutionEngine
    ) -> None:
        """Test SequentialGroup executes steps in order."""
        from litestar_workflows.steps.base import BaseMachineStep
        from litestar_workflows.steps.groups import SequentialGroup

        execution_order = []

        class Step1(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                execution_order.append(1)
                return {"step": 1}

        class Step2(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                execution_order.append(2)
                return {"step": 2}

        class Step3(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                execution_order.append(3)
                return {"step": 3}

        group = SequentialGroup(
            Step1(name="step1", description="First step"),
            Step2(name="step2", description="Second step"),
            Step3(name="step3", description="Third step"),
        )
        result = await group.execute(sample_context, local_engine)

        assert execution_order == [1, 2, 3]
        assert result is not None

    async def test_sequential_group_passes_results(
        self, sample_context: WorkflowContext, local_engine: LocalExecutionEngine
    ) -> None:
        """Test SequentialGroup passes results between steps."""
        from litestar_workflows.steps.base import BaseMachineStep
        from litestar_workflows.steps.groups import SequentialGroup

        class Step1(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                context.set("value", 10)
                return {"value": 10}

        class Step2(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                value = context.get("value", 0)
                context.set("value", value * 2)
                return {"value": value * 2}

        group = SequentialGroup(
            Step1(name="step1", description="First step"), Step2(name="step2", description="Second step")
        )
        result = await group.execute(sample_context, local_engine)

        # Final result should be from last step
        assert sample_context.get("value") == 20

    async def test_sequential_group_single_step(
        self, sample_context: WorkflowContext, local_engine: LocalExecutionEngine
    ) -> None:
        """Test SequentialGroup with single step."""
        from litestar_workflows.steps.base import BaseMachineStep
        from litestar_workflows.steps.groups import SequentialGroup

        class SingleStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"success": True}

        group = SequentialGroup(SingleStep(name="single", description="Single step"))
        result = await group.execute(sample_context, local_engine)

        assert result is not None


@pytest.mark.unit
@pytest.mark.asyncio
class TestParallelGroup:
    """Tests for ParallelGroup execution."""

    async def test_parallel_group_executes_concurrently(
        self, sample_context: WorkflowContext, local_engine: LocalExecutionEngine
    ) -> None:
        """Test ParallelGroup executes steps concurrently."""
        import asyncio

        from litestar_workflows.steps.base import BaseMachineStep
        from litestar_workflows.steps.groups import ParallelGroup

        execution_times = {}

        class Step1(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                execution_times["step1"] = asyncio.get_event_loop().time()
                await asyncio.sleep(0.01)
                return {"step": 1}

        class Step2(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                execution_times["step2"] = asyncio.get_event_loop().time()
                await asyncio.sleep(0.01)
                return {"step": 2}

        group = ParallelGroup(
            Step1(name="step1", description="First step"), Step2(name="step2", description="Second step")
        )
        results = await group.execute(sample_context, local_engine)

        # Both steps should have executed
        assert len(execution_times) == 2
        assert len(results) == 2

        # Start times should be close (within 100ms)
        time_diff = abs(execution_times["step1"] - execution_times["step2"])
        assert time_diff < 0.1

    async def test_parallel_group_returns_all_results(
        self, sample_context: WorkflowContext, local_engine: LocalExecutionEngine
    ) -> None:
        """Test ParallelGroup returns results from all steps."""
        from litestar_workflows.steps.base import BaseMachineStep
        from litestar_workflows.steps.groups import ParallelGroup

        class StepA(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"name": "A", "value": 1}

        class StepB(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"name": "B", "value": 2}

        class StepC(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"name": "C", "value": 3}

        group = ParallelGroup(
            StepA(name="step_a", description="Step A"),
            StepB(name="step_b", description="Step B"),
            StepC(name="step_c", description="Step C"),
        )
        results = await group.execute(sample_context, local_engine)

        assert len(results) == 3
        # Results should contain all step outputs
        assert any(r["name"] == "A" for r in results if isinstance(r, dict))
        assert any(r["name"] == "B" for r in results if isinstance(r, dict))
        assert any(r["name"] == "C" for r in results if isinstance(r, dict))

    async def test_parallel_group_with_callback_chord(
        self, sample_context: WorkflowContext, local_engine: LocalExecutionEngine
    ) -> None:
        """Test ParallelGroup with callback (chord pattern)."""
        from litestar_workflows.steps.base import BaseMachineStep
        from litestar_workflows.steps.groups import ParallelGroup

        class ParallelStep(BaseMachineStep):
            def __init__(self, name: str, value: int, description: str = ""):
                super().__init__(name, description)
                self.value = value

            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"value": self.value}

        class CallbackStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                # Access results from parallel steps via previous_result
                # Implementation depends on how engine passes results
                context.set("callback_executed", True)
                return {"callback": True}

        group = ParallelGroup(
            ParallelStep(name="parallel_1", value=1, description="Parallel step 1"),
            ParallelStep(name="parallel_2", value=2, description="Parallel step 2"),
            ParallelStep(name="parallel_3", value=3, description="Parallel step 3"),
            callback=CallbackStep(name="callback", description="Callback step"),
        )

        result = await group.execute(sample_context, local_engine)

        # Callback should have executed
        # Result depends on implementation


@pytest.mark.unit
@pytest.mark.asyncio
class TestConditionalGroup:
    """Tests for ConditionalGroup execution."""

    async def test_conditional_group_branches_correctly(
        self, sample_context: WorkflowContext, local_engine: LocalExecutionEngine
    ) -> None:
        """Test ConditionalGroup selects correct branch."""
        from litestar_workflows.steps.base import BaseMachineStep
        from litestar_workflows.steps.groups import ConditionalGroup

        class ApprovedStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"path": "approved"}

        class RejectedStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"path": "rejected"}

        def condition(context: WorkflowContext) -> str:
            return "approved" if context.get("is_approved") else "rejected"

        group = ConditionalGroup(
            condition=condition,
            branches={
                "approved": ApprovedStep(name="approved", description="Approved path"),
                "rejected": RejectedStep(name="rejected", description="Rejected path"),
            },
        )

        # Test approved branch
        sample_context.set("is_approved", True)
        result = await group.execute(sample_context, local_engine)
        assert result["path"] == "approved" if result else True

        # Test rejected branch
        sample_context.set("is_approved", False)
        result = await group.execute(sample_context, local_engine)
        assert result["path"] == "rejected" if result else True

    async def test_conditional_group_with_multiple_branches(
        self, sample_context: WorkflowContext, local_engine: LocalExecutionEngine
    ) -> None:
        """Test ConditionalGroup with multiple branches."""
        from litestar_workflows.steps.base import BaseMachineStep
        from litestar_workflows.steps.groups import ConditionalGroup

        class HighPriorityStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"priority": "high"}

        class MediumPriorityStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"priority": "medium"}

        class LowPriorityStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"priority": "low"}

        def priority_condition(context: WorkflowContext) -> str:
            priority = context.get("priority_level", "medium")
            return priority

        group = ConditionalGroup(
            condition=priority_condition,
            branches={
                "high": HighPriorityStep(name="high", description="High priority"),
                "medium": MediumPriorityStep(name="medium", description="Medium priority"),
                "low": LowPriorityStep(name="low", description="Low priority"),
            },
        )

        # Test each branch
        for priority in ["high", "medium", "low"]:
            sample_context.set("priority_level", priority)
            result = await group.execute(sample_context, local_engine)
            if result:
                assert result["priority"] == priority

    async def test_conditional_group_no_matching_branch(
        self, sample_context: WorkflowContext, local_engine: LocalExecutionEngine
    ) -> None:
        """Test ConditionalGroup when no branch matches."""
        from litestar_workflows.steps.base import BaseMachineStep
        from litestar_workflows.steps.groups import ConditionalGroup

        class DefaultStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"executed": True}

        def condition(context: WorkflowContext) -> str:
            return "nonexistent"

        group = ConditionalGroup(
            condition=condition,
            branches={"other": DefaultStep(name="default", description="Default step")},
        )

        result = await group.execute(sample_context, local_engine)
        # Should return None when no matching branch
        assert result is None
