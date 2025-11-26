"""UI views controller for workflow management.

This module provides HTML template views for the workflow management UI.
It requires the [ui] extra to be installed (litestar[jinja]).

The views provide:
- Dashboard with workflow statistics
- Workflow definition list and detail views
- Instance list and detail views with graph visualization
- Human task list, detail, and form submission views
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, ClassVar
from uuid import UUID

from litestar import Controller, get, post
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.exceptions import NotFoundException
from litestar.response import Redirect, Template
from litestar.template import TemplateConfig

# These imports must be available at runtime for Litestar's dependency injection
from litestar_workflows.db.repositories import HumanTaskRepository, WorkflowInstanceRepository  # noqa: TC001
from litestar_workflows.engine.local import LocalExecutionEngine  # noqa: TC001
from litestar_workflows.engine.registry import WorkflowRegistry  # noqa: TC001
from litestar_workflows.web.graph import generate_mermaid_graph, generate_mermaid_graph_with_state

if TYPE_CHECKING:
    from litestar import Request

__all__ = ["WorkflowUIController", "get_template_config"]


def get_template_config() -> TemplateConfig:
    """Get the template configuration for the workflow UI.

    Returns:
        TemplateConfig configured for the workflow templates directory.
    """
    import importlib.resources
    from pathlib import Path

    # Get the templates directory path
    templates_path = importlib.resources.files("litestar_workflows.web") / "templates"

    return TemplateConfig(
        directory=Path(str(templates_path)),
        engine=JinjaTemplateEngine,
    )


class WorkflowUIController(Controller):
    """UI controller for workflow management views.

    Provides HTML template views for managing workflows, instances, and tasks.
    All views render Jinja templates with Tailwind CSS styling.
    """

    path = "/ui"
    tags: ClassVar[list[str]] = ["Workflow UI"]
    include_in_schema: ClassVar[bool] = False  # Don't include UI routes in OpenAPI

    # Dashboard
    @get("/", name="workflow_ui:index")
    async def index(
        self,
        request: Request,
        workflow_registry: WorkflowRegistry,
    ) -> Template:
        """Render the workflow dashboard.

        Shows statistics and quick access to registered workflows.
        """
        definitions = workflow_registry.list_definitions()

        # Build stats (in a real app, these would come from the database)
        stats = {
            "workflow_count": len(definitions),
            "active_instances": 0,  # Would query from DB
            "pending_tasks": 0,  # Would query from DB
        }

        return Template(
            template_name="index.html",
            context={
                "request": request,
                "stats": stats,
                "recent_workflows": definitions[:4],
                "api_base_url": str(request.base_url).rstrip("/"),
            },
        )

    # Workflow Definition Views
    @get("/workflows", name="workflow_ui:workflow_list")
    async def workflow_list(
        self,
        request: Request,
        workflow_registry: WorkflowRegistry,
    ) -> Template:
        """List all registered workflow definitions."""
        definitions = workflow_registry.list_definitions()

        workflows = [
            {
                "name": d.name,
                "version": d.version,
                "description": d.description,
                "steps": list(d.steps.keys()),
                "initial_step": d.initial_step,
                "terminal_steps": list(d.terminal_steps),
            }
            for d in definitions
        ]

        return Template(
            template_name="workflow_list.html",
            context={
                "request": request,
                "workflows": workflows,
                "api_base_url": str(request.base_url).rstrip("/"),
            },
        )

    @get("/workflows/{workflow_name:str}", name="workflow_ui:workflow_detail")
    async def workflow_detail(
        self,
        request: Request,
        workflow_name: str,
        workflow_registry: WorkflowRegistry,
    ) -> Template:
        """Show workflow definition details with graph visualization."""
        try:
            definition = workflow_registry.get_definition(workflow_name)
        except KeyError as e:
            raise NotFoundException(detail=f"Workflow '{workflow_name}' not found") from e

        # Generate graph
        mermaid_source = generate_mermaid_graph(definition)

        workflow = {
            "name": definition.name,
            "version": definition.version,
            "description": definition.description,
            "steps": list(definition.steps.keys()),
            "edges": [
                {
                    "source": edge.get_source_name(),
                    "target": edge.get_target_name(),
                    "condition": str(edge.condition) if edge.condition else None,
                }
                for edge in definition.edges
            ],
            "initial_step": definition.initial_step,
            "terminal_steps": list(definition.terminal_steps),
        }

        return Template(
            template_name="workflow_detail.html",
            context={
                "request": request,
                "workflow": workflow,
                "graph": {"mermaid_source": mermaid_source},
                "api_base_url": str(request.base_url).rstrip("/"),
            },
        )

    @get("/workflows/{workflow_name:str}/start", name="workflow_ui:start_workflow_form")
    async def start_workflow_form(
        self,
        request: Request,
        workflow_name: str,
        workflow_registry: WorkflowRegistry,
    ) -> Template:
        """Show form to start a new workflow instance."""
        try:
            definition = workflow_registry.get_definition(workflow_name)
        except KeyError as e:
            raise NotFoundException(detail=f"Workflow '{workflow_name}' not found") from e

        workflow = {
            "name": definition.name,
            "version": definition.version,
            "description": definition.description,
            "steps": list(definition.steps.keys()),
            "initial_step": definition.initial_step,
        }

        return Template(
            template_name="start_workflow.html",
            context={
                "request": request,
                "workflow": workflow,
                "current_user": None,  # Would come from auth
                "api_base_url": str(request.base_url).rstrip("/"),
            },
        )

    @post("/workflows/{workflow_name:str}/start", name="workflow_ui:start_workflow")
    async def start_workflow(
        self,
        request: Request,
        workflow_name: str,
        workflow_engine: LocalExecutionEngine,
        workflow_registry: WorkflowRegistry,
    ) -> Redirect | Template:
        """Start a new workflow instance from form submission."""
        try:
            workflow_class = workflow_registry.get_workflow_class(workflow_name)
        except KeyError as e:
            raise NotFoundException(detail=f"Workflow '{workflow_name}' not found") from e

        # Parse form data
        form_data = await request.form()
        input_data_str = form_data.get("input_data", "{}")
        # user_id could be used for audit logging in the future
        _ = form_data.get("user_id", "anonymous")

        try:
            input_data = json.loads(input_data_str) if input_data_str else {}
        except json.JSONDecodeError:
            # Return to form with error message
            try:
                definition = workflow_registry.get_definition(workflow_name)
            except KeyError as e:
                raise NotFoundException(detail=f"Workflow '{workflow_name}' not found") from e

            return Template(
                template_name="start_workflow.html",
                context={
                    "request": request,
                    "workflow": {
                        "name": definition.name,
                        "version": definition.version,
                        "description": definition.description,
                        "steps": list(definition.steps.keys()),
                        "initial_step": definition.initial_step,
                    },
                    "current_user": None,
                    "api_base_url": str(request.base_url).rstrip("/"),
                    "error": "Invalid JSON in input data. Please check your JSON syntax.",
                },
            )

        # Start the workflow
        instance = await workflow_engine.start_workflow(
            workflow_class,
            initial_data=input_data,
        )

        # Redirect to instance detail
        return Redirect(path=f"/ui/instances/{instance.id}")

    # Instance Views
    @get("/instances", name="workflow_ui:instance_list")
    async def instance_list(  # noqa: PLR0913
        self,
        request: Request,
        workflow_registry: WorkflowRegistry,
        workflow_instance_repo: WorkflowInstanceRepository,
        status: str | None = None,
        workflow: str | None = None,
        page: int = 1,
    ) -> Template:
        """List workflow instances with filtering."""
        from litestar_workflows.core.types import WorkflowStatus

        # Get instances from repository
        workflow_status = WorkflowStatus(status) if status else None

        if workflow:
            instances, total = await workflow_instance_repo.find_by_workflow(
                workflow_name=workflow,
                status=workflow_status,
                limit=20,
                offset=(page - 1) * 20,
            )
        else:
            instances = await workflow_instance_repo.list()
            total = len(instances)

        # Get available workflows for filter dropdown
        definitions = workflow_registry.list_definitions()

        # Build pagination info
        per_page = 20
        total_pages = (total + per_page - 1) // per_page
        pagination = {
            "page": page,
            "total": total,
            "total_pages": total_pages,
            "start": (page - 1) * per_page + 1,
            "end": min(page * per_page, total),
        }

        # Convert instances to template-friendly format
        instance_list = [
            {
                "id": str(inst.id),
                "definition_name": inst.workflow_name,
                "status": inst.status.value if hasattr(inst.status, "value") else inst.status,
                "current_step": inst.current_step,
                "started_at": inst.started_at,
                "completed_at": inst.completed_at,
                "created_by": inst.created_by,
            }
            for inst in instances[:per_page]
        ]

        return Template(
            template_name="instance_list.html",
            context={
                "request": request,
                "instances": instance_list,
                "available_workflows": [{"name": d.name} for d in definitions],
                "filters": {"status": status, "workflow": workflow},
                "pagination": pagination,
                "api_base_url": str(request.base_url).rstrip("/"),
            },
        )

    @get("/instances/{instance_id:uuid}", name="workflow_ui:instance_detail")
    async def instance_detail(
        self,
        request: Request,
        instance_id: UUID,
        workflow_registry: WorkflowRegistry,
        workflow_instance_repo: WorkflowInstanceRepository,
    ) -> Template:
        """Show workflow instance details with execution graph."""
        instance = await workflow_instance_repo.get(instance_id)
        if not instance:
            raise NotFoundException(detail=f"Instance {instance_id} not found")

        # Get workflow definition for graph
        try:
            definition = workflow_registry.get_definition(instance.workflow_name)
        except KeyError:
            definition = None

        # Build step history
        step_history = []
        completed_steps = []
        failed_steps = []

        if hasattr(instance, "step_executions") and instance.step_executions:
            from litestar_workflows.core.types import StepStatus

            for step_exec in instance.step_executions:
                step_history.append(
                    {
                        "step_name": step_exec.step_name,
                        "status": step_exec.status.value if hasattr(step_exec.status, "value") else step_exec.status,
                        "started_at": step_exec.started_at,
                        "completed_at": step_exec.completed_at,
                        "error": step_exec.error,
                    }
                )
                if step_exec.status == StepStatus.SUCCEEDED:
                    completed_steps.append(step_exec.step_name)
                elif step_exec.status == StepStatus.FAILED:
                    failed_steps.append(step_exec.step_name)

        # Generate graph with state
        if definition:
            mermaid_source = generate_mermaid_graph_with_state(
                definition,
                current_step=instance.current_step,
                completed_steps=completed_steps,
                failed_steps=failed_steps,
            )
        else:
            mermaid_source = "graph TD\n    A[Workflow definition not found]"

        instance_data = {
            "id": str(instance.id),
            "definition_name": instance.workflow_name,
            "status": instance.status.value if hasattr(instance.status, "value") else instance.status,
            "current_step": instance.current_step,
            "started_at": instance.started_at,
            "completed_at": instance.completed_at,
            "created_by": instance.created_by,
            "error": instance.error,
            "context_data": instance.context_data or {},
            "step_history": step_history,
        }

        return Template(
            template_name="instance_detail.html",
            context={
                "request": request,
                "instance": instance_data,
                "graph": {"mermaid_source": mermaid_source},
                "api_base_url": str(request.base_url).rstrip("/"),
            },
        )

    @post("/instances/{instance_id:uuid}/cancel", name="workflow_ui:cancel_instance")
    async def cancel_instance(
        self,
        request: Request,
        instance_id: UUID,
        workflow_engine: LocalExecutionEngine,
    ) -> Redirect:
        """Cancel a running workflow instance."""
        await workflow_engine.cancel_workflow(instance_id, reason="Canceled via UI")
        return Redirect(path=f"/ui/instances/{instance_id}")

    # Task Views
    @get("/tasks", name="workflow_ui:task_list")
    async def task_list(
        self,
        request: Request,
        human_task_repo: HumanTaskRepository,
    ) -> Template:
        """List pending human tasks."""
        # Get pending tasks
        tasks = await human_task_repo.find_pending()

        # Build stats
        now = datetime.now(tz=timezone.utc)
        overdue_count = sum(1 for t in tasks if t.due_at and t.due_at < now)

        stats = {
            "pending": len(tasks),
            "overdue": overdue_count,
            "completed_today": 0,  # Would need to query completed tasks
        }

        # Convert to template-friendly format
        task_list = []
        for task in tasks:
            is_overdue = task.due_at and task.due_at < now if task.due_at else False
            task_list.append(
                {
                    "id": str(task.id),
                    "instance_id": str(task.instance_id),
                    "workflow_name": task.instance.workflow_name if hasattr(task, "instance") else "Unknown",
                    "step_name": task.step_name,
                    "title": task.title,
                    "description": task.description,
                    "assignee": task.assignee_id,
                    "status": task.status,
                    "due_date": task.due_at,
                    "is_overdue": is_overdue,
                    "created_at": task.created_at,
                }
            )

        return Template(
            template_name="task_list.html",
            context={
                "request": request,
                "tasks": task_list,
                "stats": stats,
                "api_base_url": str(request.base_url).rstrip("/"),
            },
        )

    @get("/tasks/{task_id:uuid}", name="workflow_ui:task_detail")
    async def task_detail(
        self,
        request: Request,
        task_id: UUID,
        human_task_repo: HumanTaskRepository,
    ) -> Template:
        """Show human task details with form."""
        task = await human_task_repo.get(task_id)
        if not task:
            raise NotFoundException(detail=f"Task {task_id} not found")

        now = datetime.now(tz=timezone.utc)
        is_overdue = task.due_at and task.due_at < now if task.due_at else False

        task_data = {
            "id": str(task.id),
            "instance_id": str(task.instance_id),
            "workflow_name": task.instance.workflow_name if hasattr(task, "instance") else "Unknown",
            "step_name": task.step_name,
            "title": task.title,
            "description": task.description,
            "assignee": task.assignee_id,
            "status": task.status,
            "due_date": task.due_at,
            "is_overdue": is_overdue,
            "created_at": task.created_at,
            "form_schema": task.form_schema or {},
        }

        return Template(
            template_name="task_detail.html",
            context={
                "request": request,
                "task": task_data,
                "current_user": None,  # Would come from auth
                "api_base_url": str(request.base_url).rstrip("/"),
            },
        )

    @post("/tasks/{task_id:uuid}/complete", name="workflow_ui:complete_task")
    async def complete_task(
        self,
        request: Request,
        task_id: UUID,
        workflow_engine: LocalExecutionEngine,
        human_task_repo: HumanTaskRepository,
    ) -> Redirect:
        """Complete a human task with form data."""
        task = await human_task_repo.get(task_id)
        if not task:
            raise NotFoundException(detail=f"Task {task_id} not found")

        # Parse form data
        form_data = await request.form()
        completed_by = form_data.get("completed_by", "anonymous")

        # Build output data from form fields (excluding completed_by)
        output_data = {}
        for key, value in form_data.items():
            if key != "completed_by":
                # Convert checkbox values
                if value == "true":
                    output_data[key] = True
                elif value == "false":
                    output_data[key] = False
                else:
                    output_data[key] = value

        # Complete the task
        await human_task_repo.complete_task(task_id, completed_by=completed_by)

        # Resume the workflow
        await workflow_engine.complete_human_task(
            instance_id=task.instance_id,
            step_name=task.step_name,
            user_id=completed_by,
            data=output_data,
        )

        # Redirect to instance detail
        return Redirect(path=f"/ui/instances/{task.instance_id}")

    @post("/tasks/{task_id:uuid}/reassign", name="workflow_ui:reassign_task")
    async def reassign_task(
        self,
        request: Request,
        task_id: UUID,
        human_task_repo: HumanTaskRepository,
    ) -> Redirect:
        """Reassign a task to another user."""
        task = await human_task_repo.get(task_id)
        if not task:
            raise NotFoundException(detail=f"Task {task_id} not found")

        # Get new assignee from form
        form_data = await request.form()
        new_assignee = form_data.get("new_assignee")

        if new_assignee:
            task.assignee_id = new_assignee
            await human_task_repo.session.flush()

        return Redirect(path=f"/ui/tasks/{task_id}")
