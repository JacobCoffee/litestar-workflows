"""Tests for execution engines."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from litestar_workflows.core.context import WorkflowContext
    from litestar_workflows.core.definition import WorkflowDefinition
    from litestar_workflows.engine.local import LocalExecutionEngine
    from litestar_workflows.engine.registry import WorkflowRegistry


def make_workflow_class(definition: WorkflowDefinition) -> type:
    """Create a Workflow class from a WorkflowDefinition."""

    class _WorkflowClass:
        name = definition.name
        version = definition.version
        description = definition.description

        @classmethod
        def get_definition(cls) -> WorkflowDefinition:
            return definition

    return _WorkflowClass


@pytest.mark.unit
@pytest.mark.asyncio
class TestLocalExecutionEngine:
    """Tests for LocalExecutionEngine."""

    async def test_engine_creation(self, local_engine: LocalExecutionEngine) -> None:
        """Test creating a local execution engine."""
        assert local_engine is not None

    async def test_start_workflow(
        self,
        local_engine: LocalExecutionEngine,
        workflow_registry: WorkflowRegistry,
        sample_workflow_definition: WorkflowDefinition,
    ) -> None:
        """Test starting a workflow creates instance."""
        from litestar_workflows.core.types import WorkflowStatus

        # Create and register workflow class
        workflow_class = make_workflow_class(sample_workflow_definition)
        workflow_registry.register(workflow_class)

        # Start workflow
        instance = await local_engine.start_workflow(
            workflow_class,
            initial_data={"test": "data"},
        )

        assert instance is not None
        assert instance.workflow_name == "test_workflow"
        assert instance.status in [WorkflowStatus.RUNNING, WorkflowStatus.WAITING]
        assert instance.context.data.get("test") == "data"

    async def test_execute_step(
        self,
        local_engine: LocalExecutionEngine,
        sample_machine_step,
        sample_context: WorkflowContext,
    ) -> None:
        """Test executing a single step."""
        result = await local_engine.execute_step(sample_machine_step, sample_context)

        assert result["executed"] is True

    async def test_machine_step_execution_flow(
        self,
        local_engine: LocalExecutionEngine,
        workflow_registry: WorkflowRegistry,
        sample_context: WorkflowContext,
    ) -> None:
        """Test complete machine step execution flow."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.steps.base import BaseMachineStep

        class Step1(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                context.set("step1_completed", True)
                return {"step": 1}

        class Step2(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                context.set("step2_completed", True)
                return {"step": 2}

        # Create simple workflow
        definition = WorkflowDefinition(
            name="simple_workflow",
            version="1.0.0",
            description="Simple two-step workflow",
            steps={
                "step1": Step1(name="step1", description="First step"),
                "step2": Step2(name="step2", description="Second step"),
            },
            edges=[Edge(source="step1", target="step2")],
            initial_step="step1",
            terminal_steps={"step2"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        # Execute workflow
        instance = await local_engine.start_workflow(workflow_class)

        # Wait for completion or check status
        # Implementation depends on engine design

    async def test_human_step_pauses_workflow(
        self,
        local_engine: LocalExecutionEngine,
        workflow_registry: WorkflowRegistry,
    ) -> None:
        """Test that human step pauses workflow execution."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.core.types import WorkflowStatus
        from litestar_workflows.steps.base import BaseHumanStep, BaseMachineStep

        class Start(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"started": True}

        class Approval(BaseHumanStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"approved": context.get("approved")}

        class Finish(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"finished": True}

        definition = WorkflowDefinition(
            name="human_workflow",
            version="1.0.0",
            description="Workflow with human task",
            steps={
                "start": Start(name="start", description="Start step"),
                "approval": Approval(
                    name="approval",
                    title="Please Approve",
                    description="Approval step",
                    form_schema={"type": "object", "properties": {"approved": {"type": "boolean"}}},
                ),
                "finish": Finish(name="finish", description="Finish step"),
            },
            edges=[
                Edge(source="start", target="approval"),
                Edge(source="approval", target="finish"),
            ],
            initial_step="start",
            terminal_steps={"finish"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        instance = await local_engine.start_workflow(workflow_class)

        # Give the async task time to process and pause at human step
        import asyncio

        await asyncio.sleep(0.1)

        # Workflow should pause at human step
        updated_instance = await local_engine.get_instance(instance.id)
        assert updated_instance.status == WorkflowStatus.WAITING
        assert updated_instance.current_step == "approval"

    async def test_complete_human_task_resumes(
        self,
        local_engine: LocalExecutionEngine,
        workflow_registry: WorkflowRegistry,
    ) -> None:
        """Test completing human task resumes workflow."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.steps.base import BaseHumanStep, BaseMachineStep

        class Start(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"started": True}

        class Approval(BaseHumanStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"approved": True}

        class Finish(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"finished": True}

        definition = WorkflowDefinition(
            name="resume_workflow",
            version="1.0.0",
            description="Workflow that resumes after human task",
            steps={
                "start": Start(name="start", description="Start"),
                "approval": Approval(
                    name="approval", title="Approve", description="Approval", form_schema={"type": "object"}
                ),
                "finish": Finish(name="finish", description="Finish"),
            },
            edges=[
                Edge(source="start", target="approval"),
                Edge(source="approval", target="finish"),
            ],
            initial_step="start",
            terminal_steps={"finish"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        # Start workflow
        instance = await local_engine.start_workflow(workflow_class)

        # Wait for workflow to pause at human step
        import asyncio

        await asyncio.sleep(0.1)

        # Complete human task
        await local_engine.complete_human_task(
            instance.id,
            step_name="approval",
            user_id="test_user",
            data={"approved": True},
        )

        # Workflow should resume and potentially complete

    async def test_cancel_workflow(
        self,
        local_engine: LocalExecutionEngine,
        workflow_registry: WorkflowRegistry,
        sample_workflow_definition: WorkflowDefinition,
    ) -> None:
        """Test canceling a running workflow."""

        workflow_class = make_workflow_class(sample_workflow_definition)
        workflow_registry.register(workflow_class)

        # Start workflow
        instance = await local_engine.start_workflow(workflow_class)

        # Cancel workflow
        await local_engine.cancel_workflow(instance.id, reason="Test cancellation")

        # Check if workflow was canceled
        # Implementation depends on how engine stores state

    async def test_workflow_error_handling(
        self, local_engine: LocalExecutionEngine, workflow_registry: WorkflowRegistry
    ) -> None:
        """Test workflow handles step execution errors."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.core.types import WorkflowStatus
        from litestar_workflows.steps.base import BaseMachineStep

        class StartStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"started": True}

        class FailingStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                raise RuntimeError("Intentional failure")

        class FinalStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"finished": True}

        definition = WorkflowDefinition(
            name="failing_workflow",
            version="1.0.0",
            description="Workflow with failing step",
            steps={
                "start": StartStep(name="start", description="Start step"),
                "failing": FailingStep(name="failing_step", description="Step that fails"),
                "final": FinalStep(name="final", description="Final step"),
            },
            edges=[
                Edge(source="start", target="failing"),
                Edge(source="failing", target="final"),
            ],
            initial_step="start",
            terminal_steps={"final"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        instance = await local_engine.start_workflow(workflow_class)

        # Wait for workflow to process and fail
        import asyncio

        await asyncio.sleep(0.1)

        # Workflow should be in failed state
        updated_instance = await local_engine.get_instance(instance.id)
        assert updated_instance.status == WorkflowStatus.FAILED
        assert updated_instance.error is not None

    async def test_execute_step_with_guard(
        self, local_engine: LocalExecutionEngine, sample_context: WorkflowContext
    ) -> None:
        """Test executing step with guard condition."""
        from litestar_workflows.steps.base import BaseMachineStep

        class GuardedStep(BaseMachineStep):
            async def can_execute(self, context: WorkflowContext) -> bool:
                return context.get("allowed", False) is True

            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"executed": True}

        step = GuardedStep(name="guarded", description="Guarded step")

        # Should not execute when guard fails
        sample_context.set("allowed", False)
        can_execute = await step.can_execute(sample_context)
        assert can_execute is False

        # Should execute when guard passes
        sample_context.set("allowed", True)
        can_execute = await step.can_execute(sample_context)
        assert can_execute is True

        result = await local_engine.execute_step(step, sample_context)
        assert result["executed"] is True

    async def test_parallel_step_execution(
        self, local_engine: LocalExecutionEngine, workflow_registry: WorkflowRegistry
    ) -> None:
        """Test parallel execution of steps."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.steps.base import BaseMachineStep

        class Start(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"started": True}

        class ParallelA(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                context.set("a_executed", True)
                return {"path": "a"}

        class ParallelB(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                context.set("b_executed", True)
                return {"path": "b"}

        definition = WorkflowDefinition(
            name="parallel_workflow",
            version="1.0.0",
            description="Workflow with parallel execution",
            steps={
                "start": Start(name="start", description="Start"),
                "parallel_a": ParallelA(name="parallel_a", description="Parallel A"),
                "parallel_b": ParallelB(name="parallel_b", description="Parallel B"),
            },
            edges=[
                Edge(source="start", target="parallel_a"),
                Edge(source="start", target="parallel_b"),
            ],
            initial_step="start",
            terminal_steps={"parallel_a", "parallel_b"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        instance = await local_engine.start_workflow(workflow_class)

        # Both parallel steps should eventually execute
        # Implementation depends on engine design

    async def test_step_not_found_error(
        self, local_engine: LocalExecutionEngine, workflow_registry: WorkflowRegistry
    ) -> None:
        """Test workflow fails when step is not found in definition."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.core.types import WorkflowStatus
        from litestar_workflows.steps.base import BaseMachineStep

        class StartStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"started": True}

        # Create workflow with edge pointing to non-existent step
        definition = WorkflowDefinition(
            name="broken_workflow",
            version="1.0.0",
            description="Workflow with missing step",
            steps={
                "start": StartStep(name="start", description="Start step"),
            },
            edges=[Edge(source="start", target="non_existent_step")],
            initial_step="start",
            terminal_steps={"non_existent_step"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        instance = await local_engine.start_workflow(workflow_class)

        # Wait for workflow to fail
        import asyncio

        await asyncio.sleep(0.1)

        updated_instance = await local_engine.get_instance(instance.id)
        assert updated_instance.status == WorkflowStatus.FAILED
        assert "not found in definition" in updated_instance.error

    async def test_exception_during_step_execution(
        self, local_engine: LocalExecutionEngine, workflow_registry: WorkflowRegistry
    ) -> None:
        """Test workflow handles exceptions during step execution."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.core.types import WorkflowStatus
        from litestar_workflows.steps.base import BaseMachineStep

        class StartStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"started": True}

        class ExceptionStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                raise ValueError("Unexpected exception")

        definition = WorkflowDefinition(
            name="exception_workflow",
            version="1.0.0",
            description="Workflow with exception",
            steps={
                "start": StartStep(name="start", description="Start"),
                "exception": ExceptionStep(name="exception", description="Exception step"),
            },
            edges=[Edge(source="start", target="exception")],
            initial_step="start",
            terminal_steps={"exception"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        instance = await local_engine.start_workflow(workflow_class)

        # Wait for workflow to fail
        import asyncio

        await asyncio.sleep(0.1)

        updated_instance = await local_engine.get_instance(instance.id)
        assert updated_instance.status == WorkflowStatus.FAILED
        assert "Unexpected exception" in updated_instance.error

    async def test_workflow_with_no_next_steps(
        self, local_engine: LocalExecutionEngine, workflow_registry: WorkflowRegistry
    ) -> None:
        """Test workflow completes when no next steps are found."""
        from litestar_workflows.core.definition import WorkflowDefinition
        from litestar_workflows.core.types import WorkflowStatus
        from litestar_workflows.steps.base import BaseMachineStep

        class OnlyStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"completed": True}

        # Workflow with no edges and non-terminal step
        definition = WorkflowDefinition(
            name="no_next_steps_workflow",
            version="1.0.0",
            description="Workflow with no next steps",
            steps={
                "only": OnlyStep(name="only", description="Only step"),
            },
            edges=[],  # No edges defined
            initial_step="only",
            terminal_steps=set(),  # Not marked as terminal
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        instance = await local_engine.start_workflow(workflow_class)

        # Wait for completion
        import asyncio

        await asyncio.sleep(0.1)

        updated_instance = await local_engine.get_instance(instance.id)
        assert updated_instance.status == WorkflowStatus.COMPLETED

    async def test_complete_human_task_validation_errors(
        self, local_engine: LocalExecutionEngine, workflow_registry: WorkflowRegistry
    ) -> None:
        """Test complete_human_task validation errors."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.core.types import WorkflowStatus
        from litestar_workflows.steps.base import BaseHumanStep, BaseMachineStep

        class Start(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"started": True}

        class Approval(BaseHumanStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"approved": True}

        definition = WorkflowDefinition(
            name="validation_workflow",
            version="1.0.0",
            description="Workflow for validation testing",
            steps={
                "start": Start(name="start", description="Start"),
                "approval": Approval(
                    name="approval", title="Approve", description="Approval", form_schema={"type": "object"}
                ),
            },
            edges=[Edge(source="start", target="approval")],
            initial_step="start",
            terminal_steps={"approval"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        instance = await local_engine.start_workflow(workflow_class)

        # Wait for workflow to pause
        import asyncio

        await asyncio.sleep(0.1)

        # Test error when instance is not waiting
        instance.status = WorkflowStatus.COMPLETED
        with pytest.raises(ValueError, match="is not waiting"):
            await local_engine.complete_human_task(
                instance.id, step_name="approval", user_id="user1", data={"approved": True}
            )

        # Reset to waiting
        instance.status = WorkflowStatus.WAITING
        instance.current_step = "approval"

        # Test error when wrong step name
        with pytest.raises(ValueError, match="waiting at step"):
            await local_engine.complete_human_task(
                instance.id, step_name="wrong_step", user_id="user1", data={"approved": True}
            )

    async def test_execute_step_failure_raises_exception(
        self, local_engine: LocalExecutionEngine, sample_context: WorkflowContext
    ) -> None:
        """Test execute_step raises exception on failure."""
        from litestar_workflows.steps.base import BaseMachineStep

        class FailingStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                raise RuntimeError("Step failed")

        step = FailingStep(name="failing", description="Failing step")

        with pytest.raises(Exception, match="Step failed"):
            await local_engine.execute_step(step, sample_context)

    async def test_execute_step_with_can_execute_false(
        self, local_engine: LocalExecutionEngine, sample_context: WorkflowContext
    ) -> None:
        """Test execute_step when can_execute returns False."""
        from litestar_workflows.core.types import StepStatus
        from litestar_workflows.steps.base import BaseMachineStep

        class GuardedStep(BaseMachineStep):
            async def can_execute(self, context: WorkflowContext) -> bool:
                return False

            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"executed": True}

        step = GuardedStep(name="guarded", description="Guarded step")

        # Execute via _execute_single_step to test the guard
        result = await local_engine._execute_single_step(step, sample_context)

        assert result["status"] == StepStatus.SKIPPED

    async def test_schedule_step_with_delay(
        self, local_engine: LocalExecutionEngine, workflow_registry: WorkflowRegistry
    ) -> None:
        """Test scheduling a step with a delay."""
        from datetime import timedelta

        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.steps.base import BaseMachineStep

        class Step1(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"step": 1}

        class Step2(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"step": 2}

        definition = WorkflowDefinition(
            name="scheduled_workflow",
            version="1.0.0",
            description="Workflow with scheduled step",
            steps={
                "step1": Step1(name="step1", description="Step 1"),
                "step2": Step2(name="step2", description="Step 2"),
            },
            edges=[Edge(source="step1", target="step2")],
            initial_step="step1",
            terminal_steps={"step2"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        instance = await local_engine.start_workflow(workflow_class)

        # Wait for first step to complete
        import asyncio

        await asyncio.sleep(0.1)

        # Schedule step2 with delay
        await local_engine.schedule_step(instance.id, "step2", delay=timedelta(milliseconds=50))

    async def test_parallel_execution_with_exception(
        self, local_engine: LocalExecutionEngine, workflow_registry: WorkflowRegistry
    ) -> None:
        """Test parallel execution when one step raises an exception."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.core.types import WorkflowStatus
        from litestar_workflows.steps.base import BaseMachineStep

        class Start(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"started": True}

        class ParallelA(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"path": "a"}

        class ParallelB(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                raise RuntimeError("Parallel step failed")

        definition = WorkflowDefinition(
            name="parallel_fail_workflow",
            version="1.0.0",
            description="Parallel workflow with failure",
            steps={
                "start": Start(name="start", description="Start"),
                "parallel_a": ParallelA(name="parallel_a", description="Parallel A"),
                "parallel_b": ParallelB(name="parallel_b", description="Parallel B"),
            },
            edges=[
                Edge(source="start", target="parallel_a"),
                Edge(source="start", target="parallel_b"),
            ],
            initial_step="start",
            terminal_steps={"parallel_a", "parallel_b"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        instance = await local_engine.start_workflow(workflow_class)

        # Wait for parallel execution to fail
        import asyncio

        await asyncio.sleep(0.2)

        updated_instance = await local_engine.get_instance(instance.id)
        assert updated_instance.status == WorkflowStatus.FAILED

    async def test_parallel_execution_with_missing_step(
        self, local_engine: LocalExecutionEngine, workflow_registry: WorkflowRegistry
    ) -> None:
        """Test parallel execution when step is not in definition."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.core.types import WorkflowStatus
        from litestar_workflows.steps.base import BaseMachineStep

        class Start(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"started": True}

        class ParallelA(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"path": "a"}

        definition = WorkflowDefinition(
            name="parallel_missing_workflow",
            version="1.0.0",
            description="Parallel workflow with missing step",
            steps={
                "start": Start(name="start", description="Start"),
                "parallel_a": ParallelA(name="parallel_a", description="Parallel A"),
                # Note: parallel_b is referenced in edges but not defined
            },
            edges=[
                Edge(source="start", target="parallel_a"),
                Edge(source="start", target="parallel_b"),  # This step doesn't exist
            ],
            initial_step="start",
            terminal_steps={"parallel_a", "parallel_b"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        instance = await local_engine.start_workflow(workflow_class)

        # Wait for execution
        import asyncio

        await asyncio.sleep(0.2)

        # Workflow should complete (missing steps are skipped in parallel execution)
        updated_instance = await local_engine.get_instance(instance.id)
        assert updated_instance.status in [WorkflowStatus.COMPLETED, WorkflowStatus.RUNNING]

    async def test_get_running_instances(
        self, local_engine: LocalExecutionEngine, workflow_registry: WorkflowRegistry
    ) -> None:
        """Test getting running workflow instances."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.steps.base import BaseHumanStep, BaseMachineStep

        class Start(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"started": True}

        class Approval(BaseHumanStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"approved": True}

        definition = WorkflowDefinition(
            name="running_test_workflow",
            version="1.0.0",
            description="Workflow for testing running instances",
            steps={
                "start": Start(name="start", description="Start"),
                "approval": Approval(
                    name="approval", title="Approve", description="Approval", form_schema={"type": "object"}
                ),
            },
            edges=[Edge(source="start", target="approval")],
            initial_step="start",
            terminal_steps={"approval"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        # Start multiple workflows
        instance1 = await local_engine.start_workflow(workflow_class)
        instance2 = await local_engine.start_workflow(workflow_class)

        # Wait for workflows to pause at human step
        import asyncio

        await asyncio.sleep(0.1)

        # Get running instances
        running = local_engine.get_running_instances()

        assert len(running) == 2
        assert all(i.id in [instance1.id, instance2.id] for i in running)

    async def test_get_all_instances(
        self, local_engine: LocalExecutionEngine, workflow_registry: WorkflowRegistry
    ) -> None:
        """Test getting all workflow instances."""
        from litestar_workflows.core.definition import WorkflowDefinition
        from litestar_workflows.steps.base import BaseMachineStep

        class QuickStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"completed": True}

        definition = WorkflowDefinition(
            name="quick_workflow",
            version="1.0.0",
            description="Quick workflow",
            steps={"quick": QuickStep(name="quick", description="Quick step")},
            edges=[],
            initial_step="quick",
            terminal_steps={"quick"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        # Start workflows
        instance1 = await local_engine.start_workflow(workflow_class)
        instance2 = await local_engine.start_workflow(workflow_class)

        # Get all instances
        all_instances = local_engine.get_all_instances()

        assert len(all_instances) >= 2
        assert any(i.id == instance1.id for i in all_instances)
        assert any(i.id == instance2.id for i in all_instances)

    async def test_get_instance_not_found(self, local_engine: LocalExecutionEngine) -> None:
        """Test getting a non-existent instance raises KeyError."""
        from uuid import uuid4

        non_existent_id = uuid4()

        with pytest.raises(KeyError, match="not found"):
            await local_engine.get_instance(non_existent_id)

    async def test_execute_step_with_previous_result(
        self, local_engine: LocalExecutionEngine, sample_context: WorkflowContext
    ) -> None:
        """Test execute_step with previous_result parameter."""
        from litestar_workflows.steps.base import BaseMachineStep

        class StepWithPrevious(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                previous = context.get("_previous_result")
                return {"previous_value": previous, "current": "result"}

        step = StepWithPrevious(name="with_previous", description="Step with previous")

        result = await local_engine.execute_step(step, sample_context, previous_result={"data": "from_previous"})

        assert result["previous_value"] == {"data": "from_previous"}
        assert result["current"] == "result"

    async def test_schedule_step_when_already_running(
        self, local_engine: LocalExecutionEngine, workflow_registry: WorkflowRegistry
    ) -> None:
        """Test scheduling step when instance is already running."""
        from datetime import timedelta

        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.steps.base import BaseMachineStep

        class SlowStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                import asyncio

                await asyncio.sleep(0.5)
                return {"completed": True}

        class Step2(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"step": 2}

        definition = WorkflowDefinition(
            name="schedule_running_workflow",
            version="1.0.0",
            description="Workflow for schedule running test",
            steps={
                "slow": SlowStep(name="slow", description="Slow step"),
                "step2": Step2(name="step2", description="Step 2"),
            },
            edges=[Edge(source="slow", target="step2")],
            initial_step="slow",
            terminal_steps={"step2"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        instance = await local_engine.start_workflow(workflow_class)

        # Instance is now running, try to schedule a step
        # This should not create duplicate task
        await local_engine.schedule_step(instance.id, "step2", delay=timedelta(milliseconds=10))

        # Wait for everything to complete
        import asyncio

        await asyncio.sleep(0.7)

    async def test_exception_in_workflow_loop(self, workflow_registry: WorkflowRegistry) -> None:
        """Test exception handling in main workflow loop."""
        from unittest.mock import patch

        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.core.types import WorkflowStatus
        from litestar_workflows.engine.local import LocalExecutionEngine
        from litestar_workflows.steps.base import BaseMachineStep

        class Step1(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"step": 1}

        class Step2(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"step": 2}

        definition = WorkflowDefinition(
            name="exception_loop_workflow",
            version="1.0.0",
            description="Workflow for exception loop test",
            steps={
                "step1": Step1(name="step1", description="Step 1"),
                "step2": Step2(name="step2", description="Step 2"),
            },
            edges=[Edge(source="step1", target="step2")],
            initial_step="step1",
            terminal_steps={"step2"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        engine = LocalExecutionEngine(registry=workflow_registry)

        # Patch _execute_single_step to raise an unexpected exception
        original_execute = engine._execute_single_step

        call_count = 0

        async def mock_execute(step, context):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call succeeds
                return await original_execute(step, context)
            # Second call raises unexpected exception
            raise RuntimeError("Unexpected error in execution loop")

        with patch.object(engine, "_execute_single_step", side_effect=mock_execute):
            instance = await engine.start_workflow(workflow_class)

            # Wait for workflow to fail
            import asyncio

            await asyncio.sleep(0.2)

            updated_instance = await engine.get_instance(instance.id)
            assert updated_instance.status == WorkflowStatus.FAILED
            assert "Unexpected error in execution loop" in updated_instance.error


@pytest.mark.unit
@pytest.mark.asyncio
class TestPersistenceIntegration:
    """Tests for persistence layer integration."""

    async def test_start_workflow_saves_to_persistence(
        self,
        workflow_registry: WorkflowRegistry,
        sample_workflow_definition: WorkflowDefinition,
    ) -> None:
        """Test that starting a workflow saves to persistence."""
        from litestar_workflows.engine.local import LocalExecutionEngine
        from tests.conftest import MockPersistence, make_workflow_class

        mock_persistence = MockPersistence()
        engine = LocalExecutionEngine(registry=workflow_registry, persistence=mock_persistence)

        workflow_class = make_workflow_class(sample_workflow_definition)
        workflow_registry.register(workflow_class)

        instance = await engine.start_workflow(workflow_class)

        # Verify persistence was called
        assert mock_persistence.save_count >= 1
        assert instance.id in mock_persistence.instances

    async def test_workflow_execution_persists_progress(self, workflow_registry: WorkflowRegistry) -> None:
        """Test that workflow execution persists progress."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.engine.local import LocalExecutionEngine
        from litestar_workflows.steps.base import BaseMachineStep
        from tests.conftest import MockPersistence, make_workflow_class

        class Step1(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"step": 1}

        class Step2(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"step": 2}

        definition = WorkflowDefinition(
            name="persist_workflow",
            version="1.0.0",
            description="Workflow with persistence",
            steps={
                "step1": Step1(name="step1", description="Step 1"),
                "step2": Step2(name="step2", description="Step 2"),
            },
            edges=[Edge(source="step1", target="step2")],
            initial_step="step1",
            terminal_steps={"step2"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        mock_persistence = MockPersistence()
        engine = LocalExecutionEngine(registry=workflow_registry, persistence=mock_persistence)

        instance = await engine.start_workflow(workflow_class)

        # Wait for execution
        import asyncio

        await asyncio.sleep(0.1)

        # Should have saved multiple times (start + progress + end)
        assert mock_persistence.save_count >= 2

    async def test_get_instance_loads_from_persistence(self, workflow_registry: WorkflowRegistry) -> None:
        """Test that get_instance loads from persistence."""
        from uuid import uuid4

        from litestar_workflows.core.definition import WorkflowDefinition
        from litestar_workflows.core.models import WorkflowInstanceData
        from litestar_workflows.core.types import WorkflowStatus
        from litestar_workflows.engine.local import LocalExecutionEngine
        from litestar_workflows.steps.base import BaseMachineStep
        from tests.conftest import MockPersistence, make_workflow_class

        class QuickStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"completed": True}

        definition = WorkflowDefinition(
            name="load_workflow",
            version="1.0.0",
            description="Workflow for loading test",
            steps={"quick": QuickStep(name="quick", description="Quick step")},
            edges=[],
            initial_step="quick",
            terminal_steps={"quick"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        mock_persistence = MockPersistence()
        engine = LocalExecutionEngine(registry=workflow_registry, persistence=mock_persistence)

        # Create instance manually and save to persistence
        from datetime import datetime, timezone

        from litestar_workflows.core.context import WorkflowContext

        instance_id = uuid4()
        workflow_id = uuid4()
        context = WorkflowContext(
            workflow_id=workflow_id,
            instance_id=instance_id,
            data={},
            metadata={},
            current_step="quick",
            step_history=[],
            started_at=datetime.now(timezone.utc),
        )

        instance = WorkflowInstanceData(
            id=instance_id,
            workflow_name="load_workflow",
            workflow_version="1.0.0",
            status=WorkflowStatus.COMPLETED,
            context=context,
            current_step=None,
            error=None,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )

        await mock_persistence.save_instance(instance)

        # Now load it via engine
        loaded_instance = await engine.get_instance(instance_id)

        assert loaded_instance.id == instance_id
        assert mock_persistence.load_count == 1

    async def test_human_task_pause_saves_state(self, workflow_registry: WorkflowRegistry) -> None:
        """Test that pausing at human task saves state."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.engine.local import LocalExecutionEngine
        from litestar_workflows.steps.base import BaseHumanStep, BaseMachineStep
        from tests.conftest import MockPersistence, make_workflow_class

        class Start(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"started": True}

        class Approval(BaseHumanStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"approved": True}

        definition = WorkflowDefinition(
            name="human_persist_workflow",
            version="1.0.0",
            description="Workflow with human task and persistence",
            steps={
                "start": Start(name="start", description="Start"),
                "approval": Approval(
                    name="approval", title="Approve", description="Approval", form_schema={"type": "object"}
                ),
            },
            edges=[Edge(source="start", target="approval")],
            initial_step="start",
            terminal_steps={"approval"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        mock_persistence = MockPersistence()
        engine = LocalExecutionEngine(registry=workflow_registry, persistence=mock_persistence)

        instance = await engine.start_workflow(workflow_class)

        # Wait for pause at human step
        import asyncio

        await asyncio.sleep(0.1)

        # Should have saved state when pausing
        assert mock_persistence.save_count >= 2  # At least start + pause

    async def test_complete_human_task_saves_state(self, workflow_registry: WorkflowRegistry) -> None:
        """Test that completing human task saves state."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.engine.local import LocalExecutionEngine
        from litestar_workflows.steps.base import BaseHumanStep, BaseMachineStep
        from tests.conftest import MockPersistence, make_workflow_class

        class Start(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"started": True}

        class Approval(BaseHumanStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"approved": True}

        definition = WorkflowDefinition(
            name="complete_human_workflow",
            version="1.0.0",
            description="Workflow for complete human test",
            steps={
                "start": Start(name="start", description="Start"),
                "approval": Approval(
                    name="approval", title="Approve", description="Approval", form_schema={"type": "object"}
                ),
            },
            edges=[Edge(source="start", target="approval")],
            initial_step="start",
            terminal_steps={"approval"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        mock_persistence = MockPersistence()
        engine = LocalExecutionEngine(registry=workflow_registry, persistence=mock_persistence)

        instance = await engine.start_workflow(workflow_class)

        # Wait for pause
        import asyncio

        await asyncio.sleep(0.1)

        save_count_before = mock_persistence.save_count

        # Complete human task
        await engine.complete_human_task(instance.id, step_name="approval", user_id="user1", data={"approved": True})

        # Should have saved after completion
        assert mock_persistence.save_count > save_count_before

    async def test_cancel_workflow_saves_state(self, workflow_registry: WorkflowRegistry) -> None:
        """Test that canceling workflow saves state."""
        from litestar_workflows.core.definition import WorkflowDefinition
        from litestar_workflows.engine.local import LocalExecutionEngine
        from litestar_workflows.steps.base import BaseMachineStep
        from tests.conftest import MockPersistence, make_workflow_class

        class SlowStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                import asyncio

                await asyncio.sleep(1)
                return {"completed": True}

        definition = WorkflowDefinition(
            name="cancel_workflow",
            version="1.0.0",
            description="Workflow for cancel test",
            steps={"slow": SlowStep(name="slow", description="Slow step")},
            edges=[],
            initial_step="slow",
            terminal_steps={"slow"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        mock_persistence = MockPersistence()
        engine = LocalExecutionEngine(registry=workflow_registry, persistence=mock_persistence)

        instance = await engine.start_workflow(workflow_class)

        save_count_before = mock_persistence.save_count

        # Cancel workflow
        await engine.cancel_workflow(instance.id, reason="Test cancellation")

        # Should have saved after cancellation
        assert mock_persistence.save_count > save_count_before


@pytest.mark.unit
@pytest.mark.asyncio
class TestEventBusIntegration:
    """Tests for event bus integration."""

    async def test_workflow_started_event(self, workflow_registry: WorkflowRegistry) -> None:
        """Test that workflow.started event is emitted."""
        from litestar_workflows.core.definition import WorkflowDefinition
        from litestar_workflows.engine.local import LocalExecutionEngine
        from litestar_workflows.steps.base import BaseMachineStep
        from tests.conftest import MockEventBus, make_workflow_class

        class QuickStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"completed": True}

        definition = WorkflowDefinition(
            name="event_workflow",
            version="1.0.0",
            description="Workflow for event test",
            steps={"quick": QuickStep(name="quick", description="Quick step")},
            edges=[],
            initial_step="quick",
            terminal_steps={"quick"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        mock_event_bus = MockEventBus()
        engine = LocalExecutionEngine(registry=workflow_registry, event_bus=mock_event_bus)

        instance = await engine.start_workflow(workflow_class)

        # Check for started event
        event_types = [event[0] for event in mock_event_bus.events]
        assert "workflow.started" in event_types

        # Find the started event
        started_events = [e for e in mock_event_bus.events if e[0] == "workflow.started"]
        assert len(started_events) == 1
        assert started_events[0][1]["instance_id"] == instance.id

    async def test_workflow_completed_event(self, workflow_registry: WorkflowRegistry) -> None:
        """Test that workflow.completed event is emitted."""
        from litestar_workflows.core.definition import WorkflowDefinition
        from litestar_workflows.engine.local import LocalExecutionEngine
        from litestar_workflows.steps.base import BaseMachineStep
        from tests.conftest import MockEventBus, make_workflow_class

        class QuickStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"completed": True}

        definition = WorkflowDefinition(
            name="complete_event_workflow",
            version="1.0.0",
            description="Workflow for completion event test",
            steps={"quick": QuickStep(name="quick", description="Quick step")},
            edges=[],
            initial_step="quick",
            terminal_steps={"quick"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        mock_event_bus = MockEventBus()
        engine = LocalExecutionEngine(registry=workflow_registry, event_bus=mock_event_bus)

        instance = await engine.start_workflow(workflow_class)

        # Wait for completion
        import asyncio

        await asyncio.sleep(0.1)

        # Check for completed event
        event_types = [event[0] for event in mock_event_bus.events]
        assert "workflow.completed" in event_types

    async def test_workflow_failed_event(self, workflow_registry: WorkflowRegistry) -> None:
        """Test that workflow.failed event is emitted."""
        from litestar_workflows.core.definition import WorkflowDefinition
        from litestar_workflows.engine.local import LocalExecutionEngine
        from litestar_workflows.steps.base import BaseMachineStep
        from tests.conftest import MockEventBus, make_workflow_class

        class FailingStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                raise RuntimeError("Intentional failure")

        definition = WorkflowDefinition(
            name="fail_event_workflow",
            version="1.0.0",
            description="Workflow for failure event test",
            steps={"failing": FailingStep(name="failing", description="Failing step")},
            edges=[],
            initial_step="failing",
            terminal_steps={"failing"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        mock_event_bus = MockEventBus()
        engine = LocalExecutionEngine(registry=workflow_registry, event_bus=mock_event_bus)

        instance = await engine.start_workflow(workflow_class)

        # Wait for failure
        import asyncio

        await asyncio.sleep(0.1)

        # Check for failed event
        event_types = [event[0] for event in mock_event_bus.events]
        assert "workflow.failed" in event_types

    async def test_workflow_waiting_event(self, workflow_registry: WorkflowRegistry) -> None:
        """Test that workflow.waiting event is emitted."""
        from litestar_workflows.core.definition import Edge, WorkflowDefinition
        from litestar_workflows.engine.local import LocalExecutionEngine
        from litestar_workflows.steps.base import BaseHumanStep, BaseMachineStep
        from tests.conftest import MockEventBus, make_workflow_class

        class Start(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"started": True}

        class Approval(BaseHumanStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                return {"approved": True}

        definition = WorkflowDefinition(
            name="waiting_event_workflow",
            version="1.0.0",
            description="Workflow for waiting event test",
            steps={
                "start": Start(name="start", description="Start"),
                "approval": Approval(
                    name="approval", title="Approve", description="Approval", form_schema={"type": "object"}
                ),
            },
            edges=[Edge(source="start", target="approval")],
            initial_step="start",
            terminal_steps={"approval"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        mock_event_bus = MockEventBus()
        engine = LocalExecutionEngine(registry=workflow_registry, event_bus=mock_event_bus)

        instance = await engine.start_workflow(workflow_class)

        # Wait for pause at human step
        import asyncio

        await asyncio.sleep(0.1)

        # Check for waiting event
        event_types = [event[0] for event in mock_event_bus.events]
        assert "workflow.waiting" in event_types

        # Find the waiting event
        waiting_events = [e for e in mock_event_bus.events if e[0] == "workflow.waiting"]
        assert len(waiting_events) == 1
        assert waiting_events[0][1]["instance_id"] == instance.id
        assert waiting_events[0][1]["step_name"] == "approval"

    async def test_workflow_canceled_event(self, workflow_registry: WorkflowRegistry) -> None:
        """Test that workflow.canceled event is emitted."""
        from litestar_workflows.core.definition import WorkflowDefinition
        from litestar_workflows.engine.local import LocalExecutionEngine
        from litestar_workflows.steps.base import BaseMachineStep
        from tests.conftest import MockEventBus, make_workflow_class

        class SlowStep(BaseMachineStep):
            async def execute(self, context: WorkflowContext) -> dict[str, Any]:
                import asyncio

                await asyncio.sleep(1)
                return {"completed": True}

        definition = WorkflowDefinition(
            name="cancel_event_workflow",
            version="1.0.0",
            description="Workflow for cancel event test",
            steps={"slow": SlowStep(name="slow", description="Slow step")},
            edges=[],
            initial_step="slow",
            terminal_steps={"slow"},
        )

        workflow_class = make_workflow_class(definition)
        workflow_registry.register(workflow_class)

        mock_event_bus = MockEventBus()
        engine = LocalExecutionEngine(registry=workflow_registry, event_bus=mock_event_bus)

        instance = await engine.start_workflow(workflow_class)

        # Cancel workflow
        await engine.cancel_workflow(instance.id, reason="Test cancellation")

        # Check for canceled event
        event_types = [event[0] for event in mock_event_bus.events]
        assert "workflow.canceled" in event_types

        # Find the canceled event
        canceled_events = [e for e in mock_event_bus.events if e[0] == "workflow.canceled"]
        assert len(canceled_events) == 1
        assert canceled_events[0][1]["instance_id"] == instance.id
        assert canceled_events[0][1]["reason"] == "Test cancellation"
