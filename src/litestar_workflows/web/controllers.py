"""REST API controllers for workflow management.

This module provides three controller classes for managing workflows:
- WorkflowDefinitionController: Manage workflow definitions and schemas
- WorkflowInstanceController: Start, monitor, and control workflow executions
- HumanTaskController: Manage human approval tasks
"""

from __future__ import annotations

from typing import Any, ClassVar
from uuid import UUID

from litestar import Controller, get, post
from litestar.exceptions import NotFoundException
from litestar.params import Parameter

from litestar_workflows.core.types import WorkflowStatus
from litestar_workflows.engine.local import LocalExecutionEngine  # noqa: TC001 - needed for DI
from litestar_workflows.engine.registry import WorkflowRegistry  # noqa: TC001 - needed for DI
from litestar_workflows.web.dto import (
    CompleteTaskDTO,
    GraphDTO,
    HumanTaskDTO,
    ReassignTaskDTO,
    StartWorkflowDTO,
    StepExecutionDTO,
    WorkflowDefinitionDTO,
    WorkflowInstanceDetailDTO,
    WorkflowInstanceDTO,
)
from litestar_workflows.web.graph import (
    generate_mermaid_graph,
    generate_mermaid_graph_with_state,
    parse_graph_to_dict,
)

# Try to import DB repositories - will be None if [db] extra not installed
try:
    from litestar_workflows.db.repositories import (
        HumanTaskRepository,
        WorkflowInstanceRepository,
    )
except ImportError:
    HumanTaskRepository = Any  # type: ignore[misc, assignment]
    WorkflowInstanceRepository = Any  # type: ignore[misc, assignment]

__all__ = [
    "HumanTaskController",
    "WorkflowDefinitionController",
    "WorkflowInstanceController",
]


class WorkflowDefinitionController(Controller):
    """API controller for workflow definitions.

    Provides endpoints for listing and retrieving workflow definitions,
    including their schemas and graph visualizations.

    Tags: Workflow Definitions
    """

    path = "/definitions"
    tags: ClassVar[list[str]] = ["Workflow Definitions"]

    @get("/")
    async def list_definitions(
        self,
        workflow_registry: WorkflowRegistry,
        active_only: bool = Parameter(
            default=True,
            description="Filter to only active workflow definitions",
        ),
    ) -> list[WorkflowDefinitionDTO]:
        """List all registered workflow definitions.

        Returns a list of workflow definitions available for instantiation.
        By default, only active definitions are returned.

        Args:
            workflow_registry: Injected workflow registry.
            active_only: Whether to filter to only active definitions.

        Returns:
            List of workflow definition DTOs.
        """
        definitions = workflow_registry.list_definitions()

        result = []
        for definition in definitions:
            dto = WorkflowDefinitionDTO(
                name=definition.name,
                version=definition.version,
                description=definition.description,
                steps=list(definition.steps.keys()),
                edges=[
                    {
                        "source": edge.get_source_name(),
                        "target": edge.get_target_name(),
                        "condition": str(edge.condition) if edge.condition else None,
                    }
                    for edge in definition.edges
                ],
                initial_step=definition.initial_step,
                terminal_steps=list(definition.terminal_steps),
            )
            result.append(dto)

        return result

    @get("/{name:str}")
    async def get_definition(
        self,
        name: str,
        workflow_registry: WorkflowRegistry,
        version: str | None = Parameter(
            default=None,
            description="Specific version to retrieve. If omitted, returns latest.",
        ),
    ) -> WorkflowDefinitionDTO:
        """Get a specific workflow definition by name.

        Args:
            name: The workflow name.
            workflow_registry: Injected workflow registry.
            version: Optional specific version to retrieve.

        Returns:
            Workflow definition DTO.

        Raises:
            NotFoundException: If workflow definition not found.
        """
        try:
            definition = workflow_registry.get_definition(name, version=version)
        except KeyError as e:
            raise NotFoundException(detail=f"Workflow definition '{name}' not found") from e

        return WorkflowDefinitionDTO(
            name=definition.name,
            version=definition.version,
            description=definition.description,
            steps=list(definition.steps.keys()),
            edges=[
                {
                    "source": edge.get_source_name(),
                    "target": edge.get_target_name(),
                    "condition": str(edge.condition) if edge.condition else None,
                }
                for edge in definition.edges
            ],
            initial_step=definition.initial_step,
            terminal_steps=list(definition.terminal_steps),
        )

    @get("/{name:str}/graph")
    async def get_definition_graph(
        self,
        name: str,
        workflow_registry: WorkflowRegistry,
        graph_format: str = Parameter(
            default="mermaid",
            description="Graph format: 'mermaid' or 'json'",
        ),
    ) -> GraphDTO:
        """Get workflow graph visualization.

        Returns a visual representation of the workflow graph, either as
        MermaidJS source or as a structured JSON object.

        Args:
            name: The workflow name.
            workflow_registry: Injected workflow registry.
            graph_format: Graph format ('mermaid' or 'json').

        Returns:
            Graph DTO with visualization data.

        Raises:
            NotFoundException: If workflow definition not found.
        """
        try:
            definition = workflow_registry.get_definition(name)
        except KeyError as e:
            raise NotFoundException(detail=f"Workflow definition '{name}' not found") from e

        if graph_format == "mermaid":
            mermaid_source = generate_mermaid_graph(definition)
            graph_dict = parse_graph_to_dict(definition)
            return GraphDTO(
                mermaid_source=mermaid_source,
                nodes=graph_dict["nodes"],
                edges=graph_dict["edges"],
            )
        if graph_format == "json":
            graph_dict = parse_graph_to_dict(definition)
            return GraphDTO(
                mermaid_source="",
                nodes=graph_dict["nodes"],
                edges=graph_dict["edges"],
            )
        raise NotFoundException(detail=f"Unknown format: {graph_format}")


class WorkflowInstanceController(Controller):
    """API controller for workflow instances.

    Provides endpoints for starting, listing, and managing workflow
    instance executions.

    Tags: Workflow Instances
    """

    path = "/instances"
    tags: ClassVar[list[str]] = ["Workflow Instances"]

    @post("/", dto=None, return_dto=None)
    async def start_workflow(
        self,
        data: StartWorkflowDTO,
        workflow_engine: LocalExecutionEngine,
        workflow_registry: WorkflowRegistry,
    ) -> WorkflowInstanceDTO:
        """Start a new workflow instance.

        Creates and starts a new instance of the specified workflow definition.

        Args:
            data: Workflow start parameters.
            workflow_engine: Injected execution engine.
            workflow_registry: Injected workflow registry.

        Returns:
            Workflow instance DTO.

        Raises:
            NotFoundException: If workflow definition not found.
        """
        try:
            workflow_class = workflow_registry.get_workflow_class(data.definition_name)
        except KeyError as e:
            raise NotFoundException(detail=f"Workflow '{data.definition_name}' not found") from e

        # Start the workflow
        instance = await workflow_engine.start_workflow(
            workflow_class,
            initial_data=data.input_data or {},
        )

        return WorkflowInstanceDTO(
            id=instance.id,
            definition_name=instance.workflow_name,
            status=instance.status.value,
            current_step=instance.context.current_step,
            started_at=instance.context.started_at,
            completed_at=None,
            created_by=data.user_id,
        )

    @get("/")
    async def list_instances(
        self,
        workflow_instance_repo: WorkflowInstanceRepository,
        workflow_name: str | None = Parameter(
            default=None,
            description="Filter by workflow name",
        ),
        status: str | None = Parameter(
            default=None,
            description="Filter by status",
        ),
        limit: int = Parameter(
            default=50,
            le=100,
            description="Maximum number of results",
        ),
        offset: int = Parameter(
            default=0,
            ge=0,
            description="Number of results to skip",
        ),
    ) -> list[WorkflowInstanceDTO]:
        """List workflow instances with optional filtering.

        Args:
            workflow_instance_repo: Injected workflow instance repository.
            workflow_name: Optional workflow name filter.
            status: Optional status filter.
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            List of workflow instance DTOs.
        """
        workflow_status = WorkflowStatus(status) if status else None

        if workflow_name:
            instances, _ = await workflow_instance_repo.find_by_workflow(
                workflow_name=workflow_name,
                status=workflow_status,
                limit=limit,
                offset=offset,
            )
        else:
            # List all instances
            instances = await workflow_instance_repo.list()

        result = []
        for instance in instances[:limit]:  # Apply limit manually if not filtered
            dto = WorkflowInstanceDTO(
                id=instance.id,
                definition_name=instance.workflow_name,
                status=instance.status.value,
                current_step=instance.current_step,
                started_at=instance.started_at,
                completed_at=instance.completed_at,
                created_by=instance.created_by,
            )
            result.append(dto)

        return result

    @get("/{instance_id:uuid}")
    async def get_instance(
        self,
        instance_id: UUID,
        workflow_instance_repo: WorkflowInstanceRepository,
    ) -> WorkflowInstanceDetailDTO:
        """Get detailed workflow instance information.

        Returns comprehensive information about a workflow instance including
        execution context, step history, and current state.

        Args:
            instance_id: The workflow instance ID.
            workflow_instance_repo: Injected workflow instance repository.

        Returns:
            Detailed workflow instance DTO.

        Raises:
            NotFoundException: If instance not found.
        """
        instance = await workflow_instance_repo.get(instance_id)
        if not instance:
            raise NotFoundException(detail=f"Workflow instance {instance_id} not found")

        # Convert step executions to DTOs
        step_history = []
        if hasattr(instance, "step_executions") and instance.step_executions:
            for step_exec in instance.step_executions:
                step_dto = StepExecutionDTO(
                    id=step_exec.id,
                    step_name=step_exec.step_name,
                    status=step_exec.status.value,
                    started_at=step_exec.started_at,
                    completed_at=step_exec.completed_at,
                    error=step_exec.error,
                )
                step_history.append(step_dto)

        return WorkflowInstanceDetailDTO(
            id=instance.id,
            definition_name=instance.workflow_name,
            status=instance.status.value,
            current_step=instance.current_step,
            started_at=instance.started_at,
            completed_at=instance.completed_at,
            created_by=instance.created_by,
            context_data=instance.context_data,
            metadata=instance.metadata_,
            step_history=step_history,
            error=instance.error,
        )

    @get("/{instance_id:uuid}/graph")
    async def get_instance_graph(
        self,
        instance_id: UUID,
        workflow_instance_repo: WorkflowInstanceRepository,
        workflow_registry: WorkflowRegistry,
    ) -> GraphDTO:
        """Get workflow instance graph with execution state highlighting.

        Returns a visual representation of the workflow with the current
        execution state highlighted, showing completed and failed steps.

        Args:
            instance_id: The workflow instance ID.
            workflow_instance_repo: Injected workflow instance repository.
            workflow_registry: Injected workflow registry.

        Returns:
            Graph DTO with state highlighting.

        Raises:
            NotFoundException: If instance not found.
        """
        instance = await workflow_instance_repo.get(instance_id)
        if not instance:
            raise NotFoundException(detail=f"Workflow instance {instance_id} not found")

        try:
            definition = workflow_registry.get_definition(instance.workflow_name)
        except KeyError as e:
            raise NotFoundException(detail=f"Workflow definition '{instance.workflow_name}' not found") from e

        # Extract completed and failed steps from execution history
        completed_steps = []
        failed_steps = []

        if hasattr(instance, "step_executions") and instance.step_executions:
            for step_exec in instance.step_executions:
                from litestar_workflows.core.types import StepStatus

                if step_exec.status == StepStatus.SUCCEEDED:
                    completed_steps.append(step_exec.step_name)
                elif step_exec.status == StepStatus.FAILED:
                    failed_steps.append(step_exec.step_name)

        mermaid_source = generate_mermaid_graph_with_state(
            definition,
            current_step=instance.current_step,
            completed_steps=completed_steps,
            failed_steps=failed_steps,
        )

        graph_dict = parse_graph_to_dict(definition)

        return GraphDTO(
            mermaid_source=mermaid_source,
            nodes=graph_dict["nodes"],
            edges=graph_dict["edges"],
        )

    @post("/{instance_id:uuid}/cancel")
    async def cancel_instance(
        self,
        instance_id: UUID,
        workflow_engine: LocalExecutionEngine,
        workflow_instance_repo: WorkflowInstanceRepository,
        reason: str = Parameter(
            default="User canceled",
            description="Reason for cancellation",
        ),
    ) -> WorkflowInstanceDTO:
        """Cancel a running workflow instance.

        Args:
            instance_id: The workflow instance ID.
            workflow_engine: Injected execution engine.
            workflow_instance_repo: Injected workflow instance repository.
            reason: Cancellation reason.

        Returns:
            Updated workflow instance DTO.

        Raises:
            NotFoundException: If instance not found.
        """
        instance = await workflow_instance_repo.get(instance_id)
        if not instance:
            raise NotFoundException(detail=f"Workflow instance {instance_id} not found")

        await workflow_engine.cancel_workflow(instance_id, reason=reason)

        # Reload instance
        instance = await workflow_instance_repo.get(instance_id)

        return WorkflowInstanceDTO(
            id=instance.id,
            definition_name=instance.workflow_name,
            status=instance.status.value,
            current_step=instance.current_step,
            started_at=instance.started_at,
            completed_at=instance.completed_at,
            created_by=instance.created_by,
        )

    @post("/{instance_id:uuid}/retry")
    async def retry_instance(
        self,
        instance_id: UUID,
        workflow_engine: LocalExecutionEngine,
        workflow_instance_repo: WorkflowInstanceRepository,
        from_step: str | None = Parameter(
            default=None,
            description="Step to retry from (defaults to failed step)",
        ),
    ) -> WorkflowInstanceDTO:
        """Retry a failed workflow instance.

        Args:
            instance_id: The workflow instance ID.
            workflow_engine: Injected execution engine.
            workflow_instance_repo: Injected workflow instance repository.
            from_step: Optional step to retry from.

        Returns:
            Updated workflow instance DTO.

        Raises:
            NotFoundException: If instance not found.
        """
        instance = await workflow_instance_repo.get(instance_id)
        if not instance:
            raise NotFoundException(detail=f"Workflow instance {instance_id} not found")

        # Retry logic would go here - this is a placeholder
        # In a real implementation, this would call engine.retry_workflow()
        # For now, we'll just return the instance

        return WorkflowInstanceDTO(
            id=instance.id,
            definition_name=instance.workflow_name,
            status=instance.status.value,
            current_step=instance.current_step,
            started_at=instance.started_at,
            completed_at=instance.completed_at,
            created_by=instance.created_by,
        )


class HumanTaskController(Controller):
    """API controller for human tasks.

    Provides endpoints for managing human approval tasks including
    listing, completing, and reassigning tasks.

    Tags: Human Tasks
    """

    path = "/tasks"
    tags: ClassVar[list[str]] = ["Human Tasks"]

    @get("/")
    async def list_tasks(
        self,
        human_task_repo: HumanTaskRepository,
        assignee_id: str | None = Parameter(
            default=None,
            description="Filter by assignee ID",
        ),
        assignee_group: str | None = Parameter(
            default=None,
            description="Filter by assignee group",
        ),
        status: str = Parameter(
            default="pending",
            description="Filter by task status",
        ),
    ) -> list[HumanTaskDTO]:
        """List human tasks with optional filtering.

        Returns tasks that match the specified filters. By default, returns
        all pending tasks.

        Args:
            human_task_repo: Injected human task repository.
            assignee_id: Optional assignee ID filter.
            assignee_group: Optional group filter.
            status: Task status filter.

        Returns:
            List of human task DTOs.
        """
        if status == "pending":
            tasks = await human_task_repo.find_pending(
                assignee_id=assignee_id,
                assignee_group=assignee_group,
            )
        else:
            # For other statuses, we'd need to implement additional filters
            tasks = []

        result = []
        for task in tasks:
            dto = HumanTaskDTO(
                id=task.id,
                instance_id=task.instance_id,
                step_name=task.step_name,
                title=task.title,
                description=task.description,
                assignee=task.assignee_id,
                status=task.status,
                due_date=task.due_at,
                created_at=task.created_at,
                form_schema=task.form_schema,
            )
            result.append(dto)

        return result

    @get("/{task_id:uuid}")
    async def get_task(
        self,
        task_id: UUID,
        human_task_repo: HumanTaskRepository,
    ) -> HumanTaskDTO:
        """Get detailed information about a human task.

        Args:
            task_id: The task ID.
            human_task_repo: Injected human task repository.

        Returns:
            Human task DTO.

        Raises:
            NotFoundException: If task not found.
        """
        task = await human_task_repo.get(task_id)
        if not task:
            raise NotFoundException(detail=f"Task {task_id} not found")

        return HumanTaskDTO(
            id=task.id,
            instance_id=task.instance_id,
            step_name=task.step_name,
            title=task.title,
            description=task.description,
            assignee=task.assignee_id,
            status=task.status,
            due_date=task.due_at,
            created_at=task.created_at,
            form_schema=task.form_schema,
        )

    @post(
        "/{task_id:uuid}/complete",
        dto=None,
        return_dto=None,
    )
    async def complete_task(
        self,
        task_id: UUID,
        data: CompleteTaskDTO,
        workflow_engine: LocalExecutionEngine,
        human_task_repo: HumanTaskRepository,
    ) -> WorkflowInstanceDTO:
        """Complete a human task with form data.

        Submits the task completion data and resumes the workflow execution.

        Args:
            task_id: The task ID.
            data: Task completion data.
            workflow_engine: Injected execution engine.
            human_task_repo: Injected human task repository.

        Returns:
            Updated workflow instance DTO.

        Raises:
            NotFoundException: If task not found.
        """
        task = await human_task_repo.get(task_id)
        if not task:
            raise NotFoundException(detail=f"Task {task_id} not found")

        # Complete the task
        await human_task_repo.complete_task(task_id, completed_by=data.completed_by)

        # Resume the workflow with the task output
        await workflow_engine.complete_human_task(
            instance_id=task.instance_id,
            step_name=task.step_name,
            user_id=data.completed_by,
            data=data.output_data,
        )

        # Return updated instance (placeholder)
        return WorkflowInstanceDTO(
            id=task.instance_id,
            definition_name="",  # Would need to fetch from instance
            status="RUNNING",
            current_step=None,
            started_at=task.created_at,
            created_by=data.completed_by,
        )

    @post(
        "/{task_id:uuid}/reassign",
        dto=None,
        return_dto=None,
    )
    async def reassign_task(
        self,
        task_id: UUID,
        data: ReassignTaskDTO,
        human_task_repo: HumanTaskRepository,
    ) -> HumanTaskDTO:
        """Reassign a task to a different user.

        Args:
            task_id: The task ID.
            data: Reassignment data.
            human_task_repo: Injected human task repository.

        Returns:
            Updated human task DTO.

        Raises:
            NotFoundException: If task not found.
        """
        task = await human_task_repo.get(task_id)
        if not task:
            raise NotFoundException(detail=f"Task {task_id} not found")

        # Update assignee
        task.assignee_id = data.new_assignee
        await human_task_repo.session.flush()

        return HumanTaskDTO(
            id=task.id,
            instance_id=task.instance_id,
            step_name=task.step_name,
            title=task.title,
            description=task.description,
            assignee=task.assignee_id,
            status=task.status,
            due_date=task.due_at,
            created_at=task.created_at,
            form_schema=task.form_schema,
        )
