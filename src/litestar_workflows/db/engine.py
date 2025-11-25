"""Persistent execution engine with database storage.

This module provides a persistence-aware execution engine that stores
workflow state in a database using SQLAlchemy.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from litestar_workflows.core.context import StepExecution, WorkflowContext
from litestar_workflows.core.models import WorkflowInstanceData
from litestar_workflows.core.types import StepStatus, StepType, WorkflowStatus
from litestar_workflows.db.models import (
    HumanTaskModel,
    StepExecutionModel,
    WorkflowDefinitionModel,
    WorkflowInstanceModel,
)
from litestar_workflows.db.repositories import (
    HumanTaskRepository,
    StepExecutionRepository,
    WorkflowDefinitionRepository,
    WorkflowInstanceRepository,
)
from litestar_workflows.engine.graph import WorkflowGraph

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from litestar_workflows.core.definition import WorkflowDefinition
    from litestar_workflows.core.protocols import Step, Workflow
    from litestar_workflows.engine.registry import WorkflowRegistry

__all__ = ["PersistentExecutionEngine"]


class PersistentExecutionEngine:
    """Execution engine with database persistence.

    This engine persists all workflow state to a database, enabling
    durability, recovery, and querying of workflow history.

    Attributes:
        registry: The workflow registry for looking up definitions.
        session: SQLAlchemy async session for database operations.
        event_bus: Optional event bus for emitting workflow events.
    """

    def __init__(
        self,
        registry: WorkflowRegistry,
        session: AsyncSession,
        event_bus: Any | None = None,
    ) -> None:
        """Initialize the persistent execution engine.

        Args:
            registry: The workflow registry.
            session: SQLAlchemy async session.
            event_bus: Optional event bus for events.
        """
        self.registry = registry
        self.session = session
        self.event_bus = event_bus

        # Initialize repositories
        self._definition_repo = WorkflowDefinitionRepository(session=session)
        self._instance_repo = WorkflowInstanceRepository(session=session)
        self._step_repo = StepExecutionRepository(session=session)
        self._task_repo = HumanTaskRepository(session=session)

        # Track running tasks in memory
        self._running: dict[UUID, asyncio.Task[None]] = {}

    async def _get_or_create_definition(
        self,
        workflow: type[Workflow],
    ) -> WorkflowDefinitionModel:
        """Get or create a workflow definition in the database.

        Args:
            workflow: The workflow class.

        Returns:
            The database definition model.
        """
        definition = workflow.get_definition()

        # Check if definition exists
        existing = await self._definition_repo.get_by_name(
            definition.name,
            definition.version,
        )

        if existing:
            return existing

        # Create new definition
        model = WorkflowDefinitionModel(
            name=definition.name,
            version=definition.version,
            description=definition.description,
            definition_json=self._serialize_definition(definition),
            is_active=True,
        )
        return await self._definition_repo.add(model, auto_commit=True)

    def _serialize_definition(self, definition: WorkflowDefinition) -> dict[str, Any]:
        """Serialize a workflow definition to JSON-compatible dict.

        Args:
            definition: The workflow definition.

        Returns:
            JSON-serializable dictionary.
        """
        return {
            "name": definition.name,
            "version": definition.version,
            "description": definition.description,
            "steps": list(definition.steps.keys()),
            "edges": [
                {
                    "source": e.get_source_name(),
                    "target": e.get_target_name(),
                    "condition": e.condition,
                }
                for e in definition.edges
            ],
            "initial_step": definition.initial_step,
            "terminal_steps": list(definition.terminal_steps),
        }

    async def start_workflow(
        self,
        workflow: type[Workflow],
        initial_data: dict[str, Any] | None = None,
        *,
        tenant_id: str | None = None,
        created_by: str | None = None,
    ) -> WorkflowInstanceData:
        """Start a new workflow instance with persistence.

        Args:
            workflow: The workflow class to execute.
            initial_data: Optional initial data for the workflow.
            tenant_id: Optional tenant ID for multi-tenancy.
            created_by: Optional user ID who started the workflow.

        Returns:
            The created WorkflowInstanceData.
        """
        # Get or create definition in database
        definition_model = await self._get_or_create_definition(workflow)
        definition = workflow.get_definition()

        # Create instance ID
        instance_id = uuid4()
        workflow_id = uuid4()
        now = datetime.now(timezone.utc)

        # Create workflow context
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
            started_at=now,
            tenant_id=tenant_id,
        )

        # Create instance model
        instance_model = WorkflowInstanceModel(
            id=instance_id,
            definition_id=definition_model.id,
            workflow_name=definition.name,
            workflow_version=definition.version,
            status=WorkflowStatus.RUNNING,
            current_step=definition.initial_step,
            context_data=initial_data or {},
            metadata_={
                "workflow_id": str(workflow_id),
            },
            started_at=now,
            tenant_id=tenant_id,
            created_by=created_by,
        )

        # Persist instance
        await self._instance_repo.add(instance_model, auto_commit=True)

        # Emit event
        if self.event_bus:
            await self.event_bus.emit("workflow.started", instance_id=instance_id)

        # Create in-memory instance data for return
        instance_data = WorkflowInstanceData(
            id=instance_id,
            workflow_name=definition.name,
            workflow_version=definition.version,
            status=WorkflowStatus.RUNNING,
            context=context,
            current_step=definition.initial_step,
            error=None,
            started_at=now,
            completed_at=None,
        )

        # Start execution in background
        self._running[instance_id] = asyncio.create_task(
            self._run_workflow(instance_id, definition)
        )

        return instance_data

    async def _run_workflow(
        self,
        instance_id: UUID,
        definition: WorkflowDefinition,
    ) -> None:
        """Main workflow execution loop with persistence.

        Args:
            instance_id: The workflow instance ID.
            definition: The workflow definition.
        """
        graph = WorkflowGraph.from_definition(definition)

        # Load instance from database
        instance = await self._instance_repo.get(instance_id)
        if not instance:
            return

        while instance.status == WorkflowStatus.RUNNING:
            current_step_name = instance.current_step

            if not current_step_name:
                break

            # Get current step
            if current_step_name not in definition.steps:
                instance.status = WorkflowStatus.FAILED
                instance.error = f"Step '{current_step_name}' not found"
                instance.completed_at = datetime.now(timezone.utc)
                await self.session.commit()
                break

            step = definition.steps[current_step_name]

            # Check if it's a human task
            if step.step_type == StepType.HUMAN:
                instance.status = WorkflowStatus.WAITING
                await self.session.commit()

                # Create human task record
                await self._create_human_task(instance_id, step)

                if self.event_bus:
                    await self.event_bus.emit(
                        "workflow.waiting",
                        instance_id=instance_id,
                        step_name=current_step_name,
                    )
                return

            # Execute machine step
            now = datetime.now(timezone.utc)
            step_execution = StepExecutionModel(
                instance_id=instance_id,
                step_name=current_step_name,
                step_type=step.step_type,
                status=StepStatus.RUNNING,
                started_at=now,
            )
            await self._step_repo.add(step_execution, auto_commit=False)

            try:
                # Build context from database state
                context = self._build_context(instance)

                # Check if step can execute
                if not await step.can_execute(context):
                    step_execution.status = StepStatus.SKIPPED
                    step_execution.completed_at = datetime.now(timezone.utc)
                    await self.session.commit()
                else:
                    # Execute the step
                    result = await step.execute(context)
                    await step.on_success(context, result)

                    # Update step execution
                    step_execution.status = StepStatus.SUCCEEDED
                    step_execution.output_data = result if isinstance(result, dict) else {"result": result}
                    step_execution.completed_at = datetime.now(timezone.utc)

                    # Update instance context
                    instance.context_data = context.data
                    await self.session.commit()

            except Exception as e:
                await step.on_failure(context, e)
                step_execution.status = StepStatus.FAILED
                step_execution.error = str(e)
                step_execution.completed_at = datetime.now(timezone.utc)

                instance.status = WorkflowStatus.FAILED
                instance.error = str(e)
                instance.completed_at = datetime.now(timezone.utc)
                await self.session.commit()
                break

            # Check if terminal step (after execution)
            if graph.is_terminal(current_step_name):
                instance.status = WorkflowStatus.COMPLETED
                instance.completed_at = datetime.now(timezone.utc)
                instance.current_step = None
                await self.session.commit()
                break

            # Find next steps
            next_steps = graph.get_next_steps(current_step_name, context)

            if not next_steps:
                instance.status = WorkflowStatus.COMPLETED
                instance.completed_at = datetime.now(timezone.utc)
                instance.current_step = None
                await self.session.commit()
                break

            # Update to next step
            instance.current_step = next_steps[0]
            await self.session.commit()

            # Reload instance for next iteration
            await self.session.refresh(instance)

        # Emit completion event
        if self.event_bus:
            event_type = "workflow.completed" if instance.status == WorkflowStatus.COMPLETED else "workflow.failed"
            await self.event_bus.emit(event_type, instance_id=instance_id)

        # Cleanup
        if instance_id in self._running:
            del self._running[instance_id]

    def _build_context(self, instance: WorkflowInstanceModel) -> WorkflowContext:
        """Build a WorkflowContext from a database instance.

        Args:
            instance: The database instance model.

        Returns:
            A WorkflowContext for step execution.
        """
        return WorkflowContext(
            workflow_id=UUID(instance.metadata_.get("workflow_id", str(instance.id))),
            instance_id=instance.id,
            data=instance.context_data or {},
            metadata=instance.metadata_ or {},
            current_step=instance.current_step or "",
            step_history=[],  # Could load from step_executions if needed
            started_at=instance.started_at,
            tenant_id=instance.tenant_id,
        )

    async def _create_human_task(
        self,
        instance_id: UUID,
        step: Step[Any],
    ) -> HumanTaskModel:
        """Create a human task record for a human step.

        Args:
            instance_id: The workflow instance ID.
            step: The human step.

        Returns:
            The created human task model.
        """
        # Get the step execution record
        step_exec = await self._step_repo.find_by_step_name(instance_id, step.name)

        # Create if doesn't exist
        if not step_exec:
            step_exec = StepExecutionModel(
                instance_id=instance_id,
                step_name=step.name,
                step_type=StepType.HUMAN,
                status=StepStatus.WAITING,
                started_at=datetime.now(timezone.utc),
            )
            await self._step_repo.add(step_exec, auto_commit=True)

        # Get form schema if available
        form_schema = None
        if hasattr(step, "form_schema"):
            form_schema = step.form_schema

        # Get title
        title = getattr(step, "title", step.name)

        task = HumanTaskModel(
            instance_id=instance_id,
            step_execution_id=step_exec.id,
            step_name=step.name,
            title=title,
            description=step.description,
            form_schema=form_schema,
            status="pending",
        )

        return await self._task_repo.add(task, auto_commit=True)

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
        # Get instance
        instance = await self._instance_repo.get(instance_id)
        if not instance:
            msg = f"Instance {instance_id} not found"
            raise ValueError(msg)

        if instance.status != WorkflowStatus.WAITING:
            msg = f"Instance {instance_id} is not waiting"
            raise ValueError(msg)

        if instance.current_step != step_name:
            msg = f"Instance is at step '{instance.current_step}', not '{step_name}'"
            raise ValueError(msg)

        # Update step execution
        step_exec = await self._step_repo.find_by_step_name(instance_id, step_name)
        if step_exec:
            step_exec.status = StepStatus.SUCCEEDED
            step_exec.output_data = data
            step_exec.completed_at = datetime.now(timezone.utc)
            step_exec.completed_by = user_id

        # Complete the human task record
        tasks = await self._task_repo.find_by_instance(instance_id)
        for task in tasks:
            if task.step_name == step_name and task.status == "pending":
                await self._task_repo.complete_task(task.id, user_id)
                break

        # Merge data into context
        context_data = instance.context_data or {}
        context_data.update(data)
        instance.context_data = context_data

        # Resume workflow
        instance.status = WorkflowStatus.RUNNING
        await self.session.commit()

        # Get definition and find next step
        definition = self.registry.get_definition(instance.workflow_name)
        graph = WorkflowGraph.from_definition(definition)
        context = self._build_context(instance)

        next_steps = graph.get_next_steps(step_name, context)
        if next_steps:
            instance.current_step = next_steps[0]
        await self.session.commit()

        # Resume execution
        if instance_id not in self._running:
            self._running[instance_id] = asyncio.create_task(
                self._run_workflow(instance_id, definition)
            )

    async def cancel_workflow(self, instance_id: UUID, reason: str) -> None:
        """Cancel a running workflow.

        Args:
            instance_id: The workflow instance ID.
            reason: Reason for cancellation.
        """
        instance = await self._instance_repo.get(instance_id)
        if not instance:
            msg = f"Instance {instance_id} not found"
            raise ValueError(msg)

        instance.status = WorkflowStatus.CANCELED
        instance.error = f"Canceled: {reason}"
        instance.completed_at = datetime.now(timezone.utc)
        await self.session.commit()

        # Cancel any pending human tasks
        tasks = await self._task_repo.find_by_instance(instance_id)
        for task in tasks:
            if task.status == "pending":
                await self._task_repo.cancel_task(task.id)

        # Cancel running task
        if instance_id in self._running:
            self._running[instance_id].cancel()
            del self._running[instance_id]

        if self.event_bus:
            await self.event_bus.emit(
                "workflow.canceled",
                instance_id=instance_id,
                reason=reason,
            )

    async def get_instance(self, instance_id: UUID) -> WorkflowInstanceData:
        """Get a workflow instance by ID.

        Args:
            instance_id: The workflow instance ID.

        Returns:
            The WorkflowInstanceData.

        Raises:
            KeyError: If instance not found.
        """
        instance = await self._instance_repo.get(instance_id)
        if not instance:
            msg = f"Instance {instance_id} not found"
            raise KeyError(msg)

        # Load step history
        step_executions = await self._step_repo.find_by_instance(instance_id)
        step_history = [
            StepExecution(
                step_name=se.step_name,
                status=se.status,
                started_at=se.started_at,
                completed_at=se.completed_at,
                result=se.output_data,
                error=se.error,
            )
            for se in step_executions
        ]

        context = WorkflowContext(
            workflow_id=UUID(instance.metadata_.get("workflow_id", str(instance.id))),
            instance_id=instance.id,
            data=instance.context_data or {},
            metadata=instance.metadata_ or {},
            current_step=instance.current_step or "",
            step_history=step_history,
            started_at=instance.started_at,
            tenant_id=instance.tenant_id,
        )

        return WorkflowInstanceData(
            id=instance.id,
            workflow_name=instance.workflow_name,
            workflow_version=instance.workflow_version,
            status=instance.status,
            context=context,
            current_step=instance.current_step,
            error=instance.error,
            started_at=instance.started_at,
            completed_at=instance.completed_at,
        )

    def get_running_instances(self) -> list[UUID]:
        """Get IDs of currently running instances.

        Returns:
            List of running instance IDs.
        """
        return list(self._running.keys())
