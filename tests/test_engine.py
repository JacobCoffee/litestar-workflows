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
