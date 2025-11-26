"""Local in-memory async execution engine.

This module provides a local, in-process execution engine suitable for
development, testing, and single-instance deployments.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from litestar_workflows.core.context import StepExecution, WorkflowContext
from litestar_workflows.core.models import WorkflowInstanceData
from litestar_workflows.core.types import StepStatus, StepType, WorkflowStatus
from litestar_workflows.engine.graph import WorkflowGraph

if TYPE_CHECKING:
    from litestar_workflows.core.protocols import Step, Workflow
    from litestar_workflows.engine.registry import WorkflowRegistry

__all__ = ["LocalExecutionEngine"]


class LocalExecutionEngine:
    """In-memory async execution engine for workflows.

    This engine executes workflows in the same process using asyncio tasks.
    It's suitable for development, testing, and single-instance production
    deployments where distributed execution is not required.

    Attributes:
        registry: The workflow registry for looking up definitions.
        persistence: Optional persistence layer for saving state.
        event_bus: Optional event bus for emitting workflow events.
        _instances: In-memory storage of workflow instances.
        _running: Map of instance IDs to their running asyncio tasks.
    """

    def __init__(
        self,
        registry: WorkflowRegistry,
        persistence: Any | None = None,
        event_bus: Any | None = None,
    ) -> None:
        """Initialize the local execution engine.

        Args:
            registry: The workflow registry.
            persistence: Optional persistence layer implementing save/load methods.
            event_bus: Optional event bus implementing emit method.
        """
        self.registry = registry
        self.persistence = persistence
        self.event_bus = event_bus
        self._instances: dict[UUID, WorkflowInstanceData] = {}
        self._running: dict[UUID, asyncio.Task[None]] = {}

    async def start_workflow(
        self,
        workflow: type[Workflow],
        initial_data: dict[str, Any] | None = None,
    ) -> WorkflowInstanceData:
        """Start a new workflow instance.

        Creates a new workflow instance and begins execution from the initial step.

        Args:
            workflow: The workflow class to execute.
            initial_data: Optional initial data for the workflow context.

        Returns:
            The created WorkflowInstanceData.

        Example:
            >>> engine = LocalExecutionEngine(registry)
            >>> instance = await engine.start_workflow(
            ...     ApprovalWorkflow, initial_data={"document_id": "doc_123"}
            ... )
        """
        # Get workflow definition
        definition = workflow.get_definition()

        # Create unique IDs
        instance_id = uuid4()
        workflow_id = uuid4()

        # Create execution context
        context = WorkflowContext(
            workflow_id=workflow_id,
            instance_id=instance_id,
            data=initial_data or {},
            metadata={
                "workflow_name": definition.name,
                "workflow_version": definition.version,
            },
            current_step=definition.initial_step,
            step_history=[],
            started_at=datetime.now(timezone.utc),
        )

        # Create workflow instance
        instance = WorkflowInstanceData(
            id=instance_id,
            workflow_name=definition.name,
            workflow_version=definition.version,
            status=WorkflowStatus.RUNNING,
            context=context,
            current_step=definition.initial_step,
            error=None,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
        )

        # Store instance
        self._instances[instance_id] = instance

        # Persist if persistence layer available
        if self.persistence:
            await self.persistence.save_instance(instance)

        # Emit workflow started event
        if self.event_bus:
            await self.event_bus.emit("workflow.started", instance_id=instance_id)

        # Start execution in background
        self._running[instance_id] = asyncio.create_task(self._run_workflow(instance, definition))

        return instance

    async def _run_workflow(
        self,
        instance: WorkflowInstanceData,
        definition: Any,
    ) -> None:
        """Main workflow execution loop.

        Executes workflow steps in sequence, handling transitions, parallel execution,
        and human task pauses.

        Args:
            instance: The workflow instance to execute.
            definition: The workflow definition.
        """
        graph = WorkflowGraph.from_definition(definition)

        while instance.status == WorkflowStatus.RUNNING:
            current_step_name = instance.context.current_step

            # Get current step
            if current_step_name not in definition.steps:
                instance.status = WorkflowStatus.FAILED
                instance.error = f"Step '{current_step_name}' not found in definition"
                instance.completed_at = datetime.now(timezone.utc)
                break

            step = definition.steps[current_step_name]

            # Check if it's a human task - pause and wait
            if step.step_type == StepType.HUMAN:
                instance.status = WorkflowStatus.WAITING
                instance.current_step = current_step_name

                if self.persistence:
                    await self.persistence.save_instance(instance)

                if self.event_bus:
                    await self.event_bus.emit(
                        "workflow.waiting",
                        instance_id=instance.id,
                        step_name=current_step_name,
                    )

                # Human task will be completed via complete_human_task
                return

            # Execute machine step
            try:
                result = await self._execute_single_step(step, instance.context)

                # Record execution
                execution = StepExecution(
                    step_name=current_step_name,
                    status=result["status"],
                    result=result.get("result"),
                    error=result.get("error"),
                    started_at=result["started_at"],
                    completed_at=result["completed_at"],
                )
                instance.context.step_history.append(execution)

                # If step failed, fail the workflow
                if result["status"] == StepStatus.FAILED:
                    instance.status = WorkflowStatus.FAILED
                    instance.error = result.get("error")
                    instance.completed_at = datetime.now(timezone.utc)
                    break

            except Exception as e:
                instance.status = WorkflowStatus.FAILED
                instance.error = str(e)
                instance.completed_at = datetime.now(timezone.utc)

                # Record failed execution
                instance.context.step_history.append(
                    StepExecution(
                        step_name=current_step_name,
                        status=StepStatus.FAILED,
                        error=str(e),
                        started_at=datetime.now(timezone.utc),
                        completed_at=datetime.now(timezone.utc),
                    )
                )
                break

            # Check if this was a terminal step (after executing it)
            if graph.is_terminal(current_step_name):
                instance.status = WorkflowStatus.COMPLETED
                instance.completed_at = datetime.now(timezone.utc)
                break

            # Find next steps
            next_steps = graph.get_next_steps(current_step_name, instance.context)

            if not next_steps:
                # No more steps - workflow complete
                instance.status = WorkflowStatus.COMPLETED
                instance.completed_at = datetime.now(timezone.utc)
                break
            if len(next_steps) == 1:
                # Single next step - continue loop
                instance.context.current_step = next_steps[0]
                instance.current_step = next_steps[0]
            else:
                # Multiple next steps - parallel execution
                await self._execute_parallel_steps(
                    next_steps,
                    definition,
                    instance,
                    graph,
                )
                # After parallel execution, check if workflow is complete
                if instance.status != WorkflowStatus.RUNNING:
                    break

            # Persist progress
            if self.persistence:
                await self.persistence.save_instance(instance)

        # Workflow finished
        instance.current_step = None

        if self.persistence:
            await self.persistence.save_instance(instance)

        if self.event_bus:
            event_type = "workflow.completed" if instance.status == WorkflowStatus.COMPLETED else "workflow.failed"
            await self.event_bus.emit(
                event_type,
                instance_id=instance.id,
                status=instance.status,
            )

        # Clean up running task
        if instance.id in self._running:
            del self._running[instance.id]

    async def _execute_single_step(
        self,
        step: Step[Any],
        context: WorkflowContext,
    ) -> dict[str, Any]:
        """Execute a single step with lifecycle hooks.

        Args:
            step: The step to execute.
            context: The workflow context.

        Returns:
            Dict containing execution results and metadata.
        """
        started_at = datetime.now(timezone.utc)

        try:
            # Check if step can execute
            if not await step.can_execute(context):
                return {
                    "status": StepStatus.SKIPPED,
                    "started_at": started_at,
                    "completed_at": datetime.now(timezone.utc),
                }

            # Execute the step
            result = await step.execute(context)

            # Call success hook
            await step.on_success(context, result)

            return {
                "status": StepStatus.SUCCEEDED,
                "result": result,
                "started_at": started_at,
                "completed_at": datetime.now(timezone.utc),
            }

        except Exception as e:
            # Call failure hook
            await step.on_failure(context, e)

            return {
                "status": StepStatus.FAILED,
                "error": str(e),
                "started_at": started_at,
                "completed_at": datetime.now(timezone.utc),
            }

    async def _execute_parallel_steps(
        self,
        step_names: list[str],
        definition: Any,
        instance: WorkflowInstanceData,
        graph: WorkflowGraph,
    ) -> None:
        """Execute multiple steps in parallel.

        Args:
            step_names: List of step names to execute in parallel.
            definition: The workflow definition.
            instance: The workflow instance.
            graph: The workflow graph.
        """
        # Create tasks for each step
        tasks = []
        for step_name in step_names:
            if step_name not in definition.steps:
                continue

            step = definition.steps[step_name]

            # Create a copy of context for this parallel branch
            branch_context = instance.context.with_step(step_name)

            tasks.append(self._execute_single_step(step, branch_context))

        # Execute all in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Record all executions
        for i, step_name in enumerate(step_names):
            result = results[i]

            if isinstance(result, BaseException):
                execution = StepExecution(
                    step_name=step_name,
                    status=StepStatus.FAILED,
                    error=str(result),
                    started_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                )
            else:
                execution = StepExecution(
                    step_name=step_name,
                    status=result["status"],
                    result=result.get("result"),
                    error=result.get("error"),
                    started_at=result["started_at"],
                    completed_at=result["completed_at"],
                )

            instance.context.step_history.append(execution)

            # If any step failed, fail the workflow
            if execution.status == StepStatus.FAILED:
                instance.status = WorkflowStatus.FAILED
                instance.error = execution.error
                instance.completed_at = datetime.now(timezone.utc)
                return

        # After parallel execution, find the next step
        # For simplicity, we'll just mark as complete if all steps succeeded
        instance.status = WorkflowStatus.COMPLETED
        instance.completed_at = datetime.now(timezone.utc)

    async def execute_step(
        self,
        step: Step[Any],
        context: WorkflowContext,
        previous_result: Any = None,
    ) -> Any:
        """Execute a single step with the given context.

        Args:
            step: The step to execute.
            context: The workflow context.
            previous_result: Optional result from previous step.

        Returns:
            The result of the step execution.
        """
        # Store previous result in context if provided
        if previous_result is not None:
            context.set("_previous_result", previous_result)

        result = await self._execute_single_step(step, context)

        if result["status"] == StepStatus.FAILED:
            raise Exception(result.get("error", "Step execution failed"))

        return result.get("result")

    async def schedule_step(
        self,
        instance_id: UUID,
        step_name: str,
        delay: timedelta | None = None,
    ) -> None:
        """Schedule a step for execution.

        Args:
            instance_id: The workflow instance ID.
            step_name: Name of the step to schedule.
            delay: Optional delay before execution.
        """
        if delay:
            await asyncio.sleep(delay.total_seconds())

        # For local engine, we just resume the workflow at this step
        instance = await self.get_instance(instance_id)
        instance.context.current_step = step_name
        instance.current_step = step_name

        # Get the definition
        definition = self.registry.get_definition(instance.workflow_name)

        # Resume execution
        if instance_id not in self._running:
            self._running[instance_id] = asyncio.create_task(self._run_workflow(instance, definition))

    async def complete_human_task(
        self,
        instance_id: UUID,
        step_name: str,
        user_id: str,
        data: dict[str, Any],
    ) -> None:
        """Complete a human task with user-provided data.

        Args:
            instance_id: The workflow instance ID.
            step_name: Name of the human task step.
            user_id: ID of the user completing the task.
            data: User-provided data to merge into context.
        """
        instance = await self.get_instance(instance_id)

        # Verify the instance is waiting at this step
        if instance.status != WorkflowStatus.WAITING:
            msg = f"Instance {instance_id} is not waiting (status: {instance.status})"
            raise ValueError(msg)

        if instance.current_step != step_name:
            msg = f"Instance is waiting at step '{instance.current_step}', not '{step_name}'"
            raise ValueError(msg)

        # Merge user data into context
        instance.context.data.update(data)
        instance.context.user_id = user_id

        # Record the human task execution
        instance.context.step_history.append(
            StepExecution(
                step_name=step_name,
                status=StepStatus.SUCCEEDED,
                result=data,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                output_data=data,
            )
        )

        # Resume workflow
        instance.status = WorkflowStatus.RUNNING

        # Get definition
        definition = self.registry.get_definition(instance.workflow_name)
        graph = WorkflowGraph.from_definition(definition)

        # Find next steps
        next_steps = graph.get_next_steps(step_name, instance.context)

        if next_steps:
            instance.context.current_step = next_steps[0]
            instance.current_step = next_steps[0]

        # Save state
        if self.persistence:
            await self.persistence.save_instance(instance)

        # Resume execution
        if instance_id not in self._running:
            self._running[instance_id] = asyncio.create_task(self._run_workflow(instance, definition))

    async def cancel_workflow(self, instance_id: UUID, reason: str) -> None:
        """Cancel a running workflow.

        Args:
            instance_id: The workflow instance ID.
            reason: Reason for cancellation.
        """
        instance = await self.get_instance(instance_id)

        # Update instance status
        instance.status = WorkflowStatus.CANCELED
        instance.error = f"Canceled: {reason}"
        instance.completed_at = datetime.now(timezone.utc)

        # Cancel the running task
        if instance_id in self._running:
            self._running[instance_id].cancel()
            del self._running[instance_id]

        # Save state
        if self.persistence:
            await self.persistence.save_instance(instance)

        # Emit event
        if self.event_bus:
            await self.event_bus.emit(
                "workflow.canceled",
                instance_id=instance_id,
                reason=reason,
            )

    async def get_instance(self, instance_id: UUID) -> WorkflowInstanceData:
        """Retrieve a workflow instance by ID.

        Args:
            instance_id: The workflow instance ID.

        Returns:
            The WorkflowInstanceData.

        Raises:
            KeyError: If the instance is not found.
        """
        if instance_id not in self._instances:
            # Try loading from persistence
            if self.persistence:
                instance = await self.persistence.load_instance(instance_id)
                if instance:
                    self._instances[instance_id] = instance
                    return instance

            msg = f"Workflow instance {instance_id} not found"
            raise KeyError(msg)

        return self._instances[instance_id]

    def get_running_instances(self) -> list[WorkflowInstanceData]:
        """Get all currently running workflow instances.

        Returns:
            List of running WorkflowInstanceData objects.
        """
        return [
            instance
            for instance in self._instances.values()
            if instance.status in (WorkflowStatus.RUNNING, WorkflowStatus.WAITING)
        ]

    def get_all_instances(self) -> list[WorkflowInstanceData]:
        """Get all workflow instances (running and completed).

        Returns:
            List of all WorkflowInstanceData objects.
        """
        return list(self._instances.values())
