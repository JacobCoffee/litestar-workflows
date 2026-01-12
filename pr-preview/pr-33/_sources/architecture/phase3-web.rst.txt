Phase 3: Web Plugin Architecture
=================================

.. contents:: Table of Contents
   :depth: 3
   :local:


Executive Summary
-----------------

This document defines the architecture for the ``litestar-workflows[web]`` extra,
which provides REST API endpoints, DTOs, and Litestar integration for managing
workflow definitions, instances, and human tasks. The REST API is built into the
main ``WorkflowPlugin`` and enabled by default via ``enable_api=True``. It builds
on the Phase 2 persistence layer and follows Litestar best practices for controllers,
dependency injection, and OpenAPI schema generation.


Design Goals
~~~~~~~~~~~~

1. **Zero-Configuration Default**: Works out of the box with sensible defaults
2. **Full Customization**: Every aspect configurable (routes, guards, DTOs)
3. **OpenAPI-First**: Auto-generated, comprehensive OpenAPI documentation
4. **Litestar-Native**: Deep integration with DI, guards, middleware, and plugins
5. **Type-Safe**: Full typing with DTO validation at boundaries
6. **Testable**: Easy to test with dependency injection and mocking


Module Structure
----------------

The web plugin module structure follows a layered architecture:

.. code-block:: text

   src/litestar_workflows/web/
   |-- __init__.py              # Public API exports
   |-- plugin.py                # WorkflowWebPlugin implementation
   |-- config.py                # WorkflowWebPluginConfig dataclass
   |-- dependencies.py          # DI providers for engine/repositories
   |
   |-- controllers/             # REST API controllers
   |   |-- __init__.py
   |   |-- definitions.py       # WorkflowDefinitionController
   |   |-- instances.py         # WorkflowInstanceController
   |   |-- tasks.py             # HumanTaskController
   |   |-- admin.py             # WorkflowAdminController
   |   |-- graphs.py            # GraphController (MermaidJS endpoints)
   |
   |-- dto/                     # Data Transfer Objects
   |   |-- __init__.py
   |   |-- base.py              # Base DTO classes and config
   |   |-- definitions.py       # WorkflowDefinition DTOs
   |   |-- instances.py         # WorkflowInstance DTOs
   |   |-- tasks.py             # HumanTask DTOs
   |   |-- graphs.py            # Graph visualization DTOs
   |
   |-- guards/                  # Authentication/authorization guards
   |   |-- __init__.py
   |   |-- base.py              # BaseWorkflowGuard protocol
   |   |-- auth.py              # WorkflowAuthGuard (requires user)
   |   |-- admin.py             # WorkflowAdminGuard (requires admin role)
   |   |-- task.py              # TaskAssigneeGuard (task ownership)
   |
   |-- services/                # Business logic services
   |   |-- __init__.py
   |   |-- workflow.py          # WorkflowService (orchestration)
   |   |-- graph.py             # GraphService (visualization)
   |
   |-- exceptions.py            # Web-specific exception handlers
   |-- openapi.py               # OpenAPI schema customization


Dependency Graph
~~~~~~~~~~~~~~~~

.. code-block:: text

   web/plugin.py
       |
       +-- web/config.py
       |
       +-- web/dependencies.py
       |       |
       |       +-- db/repositories.py
       |       +-- engine/registry.py
       |       +-- db/engine.py (PersistentExecutionEngine)
       |
       +-- web/controllers/*.py
       |       |
       |       +-- web/dto/*.py
       |       +-- web/services/*.py
       |       +-- web/guards/*.py
       |
       +-- web/exceptions.py
       +-- web/openapi.py


Plugin Design
-------------

WorkflowWebPluginConfig
~~~~~~~~~~~~~~~~~~~~~~~

Configuration dataclass for the web plugin:

.. code-block:: python

   from dataclasses import dataclass, field
   from typing import TYPE_CHECKING, Any

   if TYPE_CHECKING:
       from litestar.types import Guard

   @dataclass
   class WorkflowWebPluginConfig:
       """Configuration for the WorkflowWebPlugin.

       Attributes:
           path_prefix: URL prefix for all workflow routes. Defaults to "/workflows".
           enable_api: Enable REST API endpoints. Defaults to True.
           enable_admin_api: Enable admin API endpoints. Defaults to True.
           enable_graph_api: Enable graph visualization endpoints. Defaults to True.
           include_in_schema: Include routes in OpenAPI schema. Defaults to True.
           tags: OpenAPI tags for workflow routes.
           api_guards: Guards applied to API routes.
           admin_guards: Guards applied to admin routes.
           task_guards: Guards applied to task completion routes.
           dto_config: Custom DTO configuration overrides.
           dependency_key_engine: DI key for ExecutionEngine. Defaults to "workflow_engine".
           dependency_key_registry: DI key for WorkflowRegistry. Defaults to "workflow_registry".
           dependency_key_instance_repo: DI key for instance repository.
           dependency_key_task_repo: DI key for task repository.
           dependency_key_definition_repo: DI key for definition repository.
           auto_create_dependencies: Auto-create DI providers. Defaults to True.
           session_dependency_key: Key for SQLAlchemy session dependency.
       """

       # Route configuration
       path_prefix: str = "/workflows"
       enable_api: bool = True
       enable_admin_api: bool = True
       enable_graph_api: bool = True
       include_in_schema: bool = True
       tags: list[str] = field(default_factory=lambda: ["Workflows"])

       # Security configuration
       api_guards: list[Guard] = field(default_factory=list)
       admin_guards: list[Guard] = field(default_factory=list)
       task_guards: list[Guard] = field(default_factory=list)

       # DTO configuration
       dto_config: dict[str, Any] = field(default_factory=dict)

       # Dependency injection keys
       dependency_key_engine: str = "workflow_engine"
       dependency_key_registry: str = "workflow_registry"
       dependency_key_instance_repo: str = "workflow_instance_repo"
       dependency_key_task_repo: str = "workflow_task_repo"
       dependency_key_definition_repo: str = "workflow_definition_repo"

       # Auto-configuration
       auto_create_dependencies: bool = True
       session_dependency_key: str = "db_session"


WorkflowWebPlugin
~~~~~~~~~~~~~~~~~

The main plugin class implementing ``InitPluginProtocol``:

.. code-block:: python

   from litestar.plugins import InitPluginProtocol
   from litestar.config.app import AppConfig
   from litestar.router import Router

   class WorkflowWebPlugin(InitPluginProtocol):
       """Litestar plugin for workflow web routes and API.

       This plugin provides:
       - REST API endpoints for workflow management
       - Human task inbox and completion API
       - Graph visualization endpoints (MermaidJS)
       - Admin API for workflow administration
       - OpenAPI schema with full documentation

       Example:
           Basic usage::

               from litestar import Litestar
               from litestar_workflows.web import WorkflowWebPlugin, WorkflowWebPluginConfig

               app = Litestar(
                   plugins=[
                       WorkflowWebPlugin(
                           config=WorkflowWebPluginConfig(
                               path_prefix="/api/workflows",
                               admin_guards=[AdminGuard],
                           )
                       )
                   ]
               )

           With custom guards::

               from litestar_workflows.web import WorkflowWebPlugin, WorkflowWebPluginConfig

               config = WorkflowWebPluginConfig(
                   api_guards=[AuthGuard],
                   admin_guards=[AdminGuard],
                   task_guards=[AuthGuard, TaskOwnerGuard],
               )
               plugin = WorkflowWebPlugin(config=config)
       """

       __slots__ = ("_config",)

       def __init__(self, config: WorkflowWebPluginConfig | None = None) -> None:
           self._config = config or WorkflowWebPluginConfig()

       @property
       def config(self) -> WorkflowWebPluginConfig:
           """Get the plugin configuration."""
           return self._config

       def on_app_init(self, app_config: AppConfig) -> AppConfig:
           """Initialize the plugin when the Litestar app starts."""
           # Register dependencies
           if self._config.auto_create_dependencies:
               self._register_dependencies(app_config)

           # Build and register routes
           routers = self._build_routers()
           app_config.route_handlers.extend(routers)

           # Register exception handlers
           self._register_exception_handlers(app_config)

           # Add OpenAPI tags
           self._configure_openapi(app_config)

           return app_config


Plugin Initialization Flow
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   on_app_init()
       |
       +-- _register_dependencies()
       |       |-- Register engine provider
       |       |-- Register registry provider
       |       +-- Register repository providers
       |
       +-- _build_routers()
       |       |-- _create_api_router() (if enable_api)
       |       |-- _create_admin_router() (if enable_admin_api)
       |       +-- _create_graph_router() (if enable_graph_api)
       |
       +-- _register_exception_handlers()
       |       |-- WorkflowNotFoundError -> 404
       |       |-- InvalidTransitionError -> 409
       |       +-- TaskNotAssignedError -> 403
       |
       +-- _configure_openapi()
               |-- Add workflow tags
               +-- Register schema components


Route Structure
~~~~~~~~~~~~~~~

The plugin creates the following route structure:

.. code-block:: text

   {path_prefix}/                              # Configured prefix (default: /workflows)
   |
   +-- api/                                    # Public API routes
   |   |-- definitions/                        # Workflow definitions
   |   |   |-- GET     /                       # List definitions
   |   |   |-- GET     /{name}                 # Get definition by name
   |   |   +-- GET     /{name}/versions        # List versions
   |   |
   |   |-- instances/                          # Workflow instances
   |   |   |-- POST    /                       # Start new instance
   |   |   |-- GET     /                       # List instances (paginated)
   |   |   |-- GET     /{instance_id}          # Get instance detail
   |   |   |-- POST    /{instance_id}/cancel   # Cancel instance
   |   |   |-- POST    /{instance_id}/retry    # Retry failed instance
   |   |   +-- GET     /{instance_id}/history  # Get step history
   |   |
   |   +-- tasks/                              # Human tasks
   |       |-- GET     /                       # List my tasks
   |       |-- GET     /{task_id}              # Get task detail
   |       |-- POST    /{task_id}/complete     # Complete task
   |       |-- POST    /{task_id}/claim        # Claim unassigned task
   |       +-- POST    /{task_id}/reassign     # Reassign task
   |
   +-- admin/                                  # Admin API routes
   |   |-- GET     /stats                      # Workflow statistics
   |   |-- GET     /instances                  # All instances (admin view)
   |   |-- POST    /definitions                # Register new definition
   |   |-- DELETE  /definitions/{name}/{ver}   # Deactivate definition
   |   +-- POST    /instances/{id}/force-complete  # Force complete stuck workflow
   |
   +-- graphs/                                 # Graph visualization routes
       |-- GET     /definitions/{name}         # Definition graph (Mermaid)
       |-- GET     /instances/{id}             # Instance graph with state
       +-- GET     /instances/{id}/history     # Animated execution history


Controller Hierarchy
--------------------

Base Controller
~~~~~~~~~~~~~~~

All workflow controllers inherit from a base class that provides common functionality:

.. code-block:: python

   from litestar import Controller
   from typing import TYPE_CHECKING

   if TYPE_CHECKING:
       from litestar_workflows.engine.registry import WorkflowRegistry
       from litestar_workflows.db import PersistentExecutionEngine

   class BaseWorkflowController(Controller):
       """Base controller for workflow endpoints.

       Provides common dependencies and helper methods for all workflow controllers.
       """

       # Injected dependencies (configured via plugin)
       engine: PersistentExecutionEngine
       registry: WorkflowRegistry

       def _get_user_id(self, request: Request) -> str | None:
           """Extract user ID from request.

           Override this method to customize user extraction logic.
           Default implementation checks request.user.id.
           """
           if hasattr(request, "user") and request.user:
               return getattr(request.user, "id", None)
           return None

       def _get_tenant_id(self, request: Request) -> str | None:
           """Extract tenant ID from request.

           Override this method for multi-tenant applications.
           Default implementation checks request.state.tenant_id.
           """
           return getattr(request.state, "tenant_id", None)


WorkflowDefinitionController
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Controller for workflow definition management:

.. code-block:: python

   from litestar import Controller, get
   from litestar.params import Parameter

   class WorkflowDefinitionController(Controller):
       """API for workflow definitions.

       Provides endpoints for listing and retrieving workflow definitions
       registered with the workflow registry.
       """

       path = "/definitions"
       tags = ["Workflow Definitions"]

       @get(
           "/",
           summary="List workflow definitions",
           description="Returns all registered workflow definitions.",
       )
       async def list_definitions(
           self,
           workflow_registry: WorkflowRegistry,
           active_only: bool = Parameter(default=True, description="Filter to active definitions only"),
       ) -> list[WorkflowDefinitionDTO]:
           """List all registered workflow definitions."""
           ...

       @get(
           "/{name:str}",
           summary="Get workflow definition",
           description="Returns a specific workflow definition by name.",
       )
       async def get_definition(
           self,
           name: str,
           workflow_registry: WorkflowRegistry,
           version: str | None = Parameter(default=None, description="Specific version to retrieve"),
       ) -> WorkflowDefinitionDetailDTO:
           """Get a specific workflow definition."""
           ...

       @get(
           "/{name:str}/versions",
           summary="List definition versions",
           description="Returns all versions of a workflow definition.",
       )
       async def list_versions(
           self,
           name: str,
           workflow_definition_repo: WorkflowDefinitionRepository,
       ) -> list[WorkflowDefinitionVersionDTO]:
           """List all versions of a workflow definition."""
           ...


WorkflowInstanceController
~~~~~~~~~~~~~~~~~~~~~~~~~~

Controller for workflow instance management:

.. code-block:: python

   from litestar import Controller, get, post
   from litestar.params import Parameter
   from uuid import UUID

   class WorkflowInstanceController(Controller):
       """API for workflow instances.

       Provides endpoints for starting, monitoring, and controlling
       workflow executions.
       """

       path = "/instances"
       tags = ["Workflow Instances"]

       @post(
           "/",
           summary="Start workflow",
           description="Starts a new workflow instance.",
           status_code=201,
       )
       async def start_workflow(
           self,
           data: StartWorkflowDTO,
           request: Request,
           workflow_engine: PersistentExecutionEngine,
           workflow_registry: WorkflowRegistry,
       ) -> WorkflowInstanceDTO:
           """Start a new workflow instance."""
           user_id = self._get_user_id(request)
           tenant_id = self._get_tenant_id(request)

           workflow_class = workflow_registry.get_workflow_class(data.workflow_name)
           instance = await workflow_engine.start_workflow(
               workflow_class,
               initial_data=data.initial_data,
               tenant_id=tenant_id,
               created_by=user_id,
           )
           return WorkflowInstanceDTO.from_instance(instance)

       @get(
           "/",
           summary="List workflow instances",
           description="Returns paginated list of workflow instances.",
       )
       async def list_instances(
           self,
           request: Request,
           workflow_instance_repo: WorkflowInstanceRepository,
           workflow_name: str | None = None,
           status: WorkflowStatus | None = None,
           limit: int = Parameter(default=50, le=100, ge=1),
           offset: int = Parameter(default=0, ge=0),
       ) -> PaginatedResponse[WorkflowInstanceDTO]:
           """List workflow instances with filtering and pagination."""
           ...

       @get(
           "/{instance_id:uuid}",
           summary="Get workflow instance",
           description="Returns detailed information about a workflow instance.",
       )
       async def get_instance(
           self,
           instance_id: UUID,
           workflow_engine: PersistentExecutionEngine,
       ) -> WorkflowInstanceDetailDTO:
           """Get detailed workflow instance information."""
           ...

       @post(
           "/{instance_id:uuid}/cancel",
           summary="Cancel workflow",
           description="Cancels a running workflow instance.",
       )
       async def cancel_instance(
           self,
           instance_id: UUID,
           data: CancelWorkflowDTO,
           workflow_engine: PersistentExecutionEngine,
       ) -> WorkflowInstanceDTO:
           """Cancel a running workflow instance."""
           ...

       @post(
           "/{instance_id:uuid}/retry",
           summary="Retry workflow",
           description="Retries a failed workflow from the failed step.",
       )
       async def retry_instance(
           self,
           instance_id: UUID,
           data: RetryWorkflowDTO,
           workflow_engine: PersistentExecutionEngine,
       ) -> WorkflowInstanceDTO:
           """Retry a failed workflow from a specific step."""
           ...


HumanTaskController
~~~~~~~~~~~~~~~~~~~

Controller for human task management:

.. code-block:: python

   from litestar import Controller, get, post
   from uuid import UUID

   class HumanTaskController(Controller):
       """API for human tasks.

       Provides endpoints for listing, claiming, and completing
       human approval tasks in workflows.
       """

       path = "/tasks"
       tags = ["Human Tasks"]

       @get(
           "/",
           summary="List my tasks",
           description="Returns pending tasks assigned to the current user.",
       )
       async def list_my_tasks(
           self,
           request: Request,
           workflow_task_repo: HumanTaskRepository,
           status: str = Parameter(default="pending"),
           assignee_group: str | None = None,
       ) -> list[HumanTaskDTO]:
           """List human tasks assigned to current user."""
           user_id = self._get_user_id(request)
           tasks = await workflow_task_repo.find_pending(
               assignee_id=user_id,
               assignee_group=assignee_group,
           )
           return [HumanTaskDTO.from_model(t) for t in tasks]

       @get(
           "/{task_id:uuid}",
           summary="Get task detail",
           description="Returns detailed task information including form schema.",
       )
       async def get_task(
           self,
           task_id: UUID,
           workflow_task_repo: HumanTaskRepository,
       ) -> HumanTaskDetailDTO:
           """Get human task details including form schema."""
           ...

       @post(
           "/{task_id:uuid}/complete",
           summary="Complete task",
           description="Completes a human task with form data.",
       )
       async def complete_task(
           self,
           task_id: UUID,
           data: CompleteTaskDTO,
           request: Request,
           workflow_engine: PersistentExecutionEngine,
           workflow_task_repo: HumanTaskRepository,
       ) -> WorkflowInstanceDTO:
           """Complete a human task with form data."""
           user_id = self._get_user_id(request)
           task = await workflow_task_repo.get(task_id)

           # Validate task ownership
           if task.assignee_id and task.assignee_id != user_id:
               raise TaskNotAssignedError(task_id, user_id)

           await workflow_engine.complete_human_task(
               instance_id=task.instance_id,
               step_name=task.step_name,
               user_id=user_id,
               data=data.form_data,
           )
           ...

       @post(
           "/{task_id:uuid}/claim",
           summary="Claim task",
           description="Claims an unassigned task for the current user.",
       )
       async def claim_task(
           self,
           task_id: UUID,
           request: Request,
           workflow_task_repo: HumanTaskRepository,
       ) -> HumanTaskDTO:
           """Claim an unassigned task."""
           ...

       @post(
           "/{task_id:uuid}/reassign",
           summary="Reassign task",
           description="Reassigns a task to another user.",
       )
       async def reassign_task(
           self,
           task_id: UUID,
           data: ReassignTaskDTO,
           workflow_task_repo: HumanTaskRepository,
       ) -> HumanTaskDTO:
           """Reassign task to another user."""
           ...


DTO Layer Design
----------------

DTO Architecture
~~~~~~~~~~~~~~~~

The DTO layer uses ``msgspec.Struct`` for high-performance serialization with
validation. DTOs are organized by domain and follow a consistent naming pattern:

- ``*DTO``: Base response/request DTO
- ``*DetailDTO``: Extended DTO with additional fields
- ``Create*DTO``: Input DTO for creation operations
- ``Update*DTO``: Input DTO for update operations
- ``*ListDTO``: Paginated list response wrapper

.. code-block:: python

   from msgspec import Struct, field
   from typing import TypeVar, Generic
   from datetime import datetime
   from uuid import UUID

   T = TypeVar("T")

   class PaginatedResponse(Struct, Generic[T]):
       """Generic paginated response wrapper."""
       items: list[T]
       total: int
       limit: int
       offset: int
       has_more: bool = field(default=False)


Request DTOs
~~~~~~~~~~~~

Input DTOs for API operations:

.. code-block:: python

   from msgspec import Struct, field
   from typing import Any

   class StartWorkflowDTO(Struct):
       """DTO for starting a workflow instance.

       Attributes:
           workflow_name: Name of the workflow to start.
           initial_data: Optional initial context data.
           metadata: Optional metadata to attach to the instance.
       """
       workflow_name: str
       initial_data: dict[str, Any] | None = None
       metadata: dict[str, Any] | None = None

   class CancelWorkflowDTO(Struct):
       """DTO for canceling a workflow instance."""
       reason: str = field(min_length=1, max_length=1000)

   class RetryWorkflowDTO(Struct):
       """DTO for retrying a failed workflow."""
       from_step: str | None = None  # If None, retry from failed step
       clear_error: bool = True

   class CompleteTaskDTO(Struct):
       """DTO for completing a human task."""
       form_data: dict[str, Any]
       comment: str | None = None

   class ReassignTaskDTO(Struct):
       """DTO for reassigning a human task."""
       assignee_id: str | None = None
       assignee_group: str | None = None
       reason: str | None = None


Response DTOs
~~~~~~~~~~~~~

Output DTOs for API responses:

.. code-block:: python

   from msgspec import Struct, field
   from datetime import datetime
   from uuid import UUID

   class WorkflowDefinitionDTO(Struct):
       """DTO for workflow definition summary."""
       name: str
       version: str
       description: str
       is_active: bool
       step_count: int
       initial_step: str
       terminal_steps: list[str]

   class WorkflowDefinitionDetailDTO(WorkflowDefinitionDTO):
       """DTO for detailed workflow definition."""
       steps: list[StepDTO]
       edges: list[EdgeDTO]
       created_at: datetime
       updated_at: datetime

   class StepDTO(Struct):
       """DTO for workflow step."""
       name: str
       description: str
       step_type: str
       is_initial: bool = False
       is_terminal: bool = False

   class EdgeDTO(Struct):
       """DTO for workflow edge."""
       source: str
       target: str
       condition: str | None = None

   class WorkflowInstanceDTO(Struct):
       """DTO for workflow instance summary."""
       id: UUID
       workflow_name: str
       workflow_version: str
       status: str
       current_step: str | None
       started_at: datetime
       completed_at: datetime | None

   class WorkflowInstanceDetailDTO(WorkflowInstanceDTO):
       """DTO for detailed workflow instance."""
       context_data: dict[str, Any]
       metadata: dict[str, Any]
       step_history: list[StepExecutionDTO]
       error: str | None
       created_by: str | None
       tenant_id: str | None

   class StepExecutionDTO(Struct):
       """DTO for step execution record."""
       step_name: str
       step_type: str
       status: str
       started_at: datetime
       completed_at: datetime | None
       output_data: dict[str, Any] | None
       error: str | None

   class HumanTaskDTO(Struct):
       """DTO for human task summary."""
       id: UUID
       instance_id: UUID
       workflow_name: str
       step_name: str
       title: str
       description: str | None
       assignee_id: str | None
       assignee_group: str | None
       status: str
       due_at: datetime | None
       created_at: datetime

   class HumanTaskDetailDTO(HumanTaskDTO):
       """DTO for detailed human task."""
       form_schema: dict[str, Any] | None
       workflow_context: dict[str, Any]
       step_execution_id: UUID


Validation Strategy
~~~~~~~~~~~~~~~~~~~

DTOs implement validation through ``msgspec`` constraints and custom validators:

.. code-block:: python

   from msgspec import Struct, field, ValidationError
   from typing import Annotated

   class StartWorkflowDTO(Struct):
       """DTO with validation constraints."""
       workflow_name: Annotated[str, field(min_length=1, max_length=255)]
       initial_data: dict[str, Any] | None = None

       def __post_init__(self) -> None:
           """Additional validation after initialization."""
           if self.initial_data:
               # Validate initial_data doesn't exceed size limit
               import json
               data_size = len(json.dumps(self.initial_data))
               if data_size > 1_000_000:  # 1MB limit
                   raise ValidationError("initial_data exceeds maximum size of 1MB")

Custom validation decorators for complex rules:

.. code-block:: python

   from functools import wraps
   from litestar.exceptions import ValidationException

   def validate_workflow_exists(func):
       """Decorator to validate workflow exists before operation."""
       @wraps(func)
       async def wrapper(
           self,
           workflow_name: str,
           workflow_registry: WorkflowRegistry,
           **kwargs
       ):
           if not workflow_registry.has_definition(workflow_name):
               raise ValidationException(
                   detail=f"Workflow '{workflow_name}' not found"
               )
           return await func(self, workflow_name, workflow_registry, **kwargs)
       return wrapper


OpenAPI Integration
-------------------

Schema Configuration
~~~~~~~~~~~~~~~~~~~~

The plugin configures OpenAPI schema generation with comprehensive documentation:

.. code-block:: python

   from litestar.openapi.spec import Tag, ExternalDocumentation

   WORKFLOW_OPENAPI_TAGS = [
       Tag(
           name="Workflow Definitions",
           description="Endpoints for managing workflow definitions and schemas.",
           external_docs=ExternalDocumentation(
               url="https://docs.litestar-workflows.dev/concepts/workflows",
               description="Workflow Concepts Guide",
           ),
       ),
       Tag(
           name="Workflow Instances",
           description="Endpoints for starting, monitoring, and controlling workflow executions.",
           external_docs=ExternalDocumentation(
               url="https://docs.litestar-workflows.dev/guides/execution",
               description="Execution Guide",
           ),
       ),
       Tag(
           name="Human Tasks",
           description="Endpoints for managing human approval tasks and form submissions.",
           external_docs=ExternalDocumentation(
               url="https://docs.litestar-workflows.dev/guides/human-tasks",
               description="Human Tasks Guide",
           ),
       ),
       Tag(
           name="Workflow Admin",
           description="Administrative endpoints for workflow management (requires admin privileges).",
       ),
       Tag(
           name="Workflow Graphs",
           description="Endpoints for workflow visualization using MermaidJS.",
       ),
   ]

   def configure_openapi(app_config: AppConfig) -> None:
       """Configure OpenAPI schema for workflow endpoints."""
       if app_config.openapi_config:
           existing_tags = app_config.openapi_config.tags or []
           app_config.openapi_config.tags = [*existing_tags, *WORKFLOW_OPENAPI_TAGS]


Response Examples
~~~~~~~~~~~~~~~~~

DTOs include OpenAPI examples for documentation:

.. code-block:: python

   from litestar.openapi.spec import Example

   class WorkflowInstanceDTO(Struct):
       """DTO with OpenAPI examples."""

       __openapi_examples__ = {
           "running": Example(
               summary="Running Instance",
               description="A workflow instance currently executing",
               value={
                   "id": "550e8400-e29b-41d4-a716-446655440000",
                   "workflow_name": "document_approval",
                   "workflow_version": "1.0.0",
                   "status": "running",
                   "current_step": "manager_review",
                   "started_at": "2024-11-24T10:30:00Z",
                   "completed_at": None,
               },
           ),
           "completed": Example(
               summary="Completed Instance",
               description="A successfully completed workflow instance",
               value={
                   "id": "550e8400-e29b-41d4-a716-446655440001",
                   "workflow_name": "document_approval",
                   "workflow_version": "1.0.0",
                   "status": "completed",
                   "current_step": None,
                   "started_at": "2024-11-24T10:30:00Z",
                   "completed_at": "2024-11-24T11:45:00Z",
               },
           ),
       }


Guard Integration Patterns
--------------------------

Base Guard Protocol
~~~~~~~~~~~~~~~~~~~

Guards follow a consistent protocol for workflow authorization:

.. code-block:: python

   from litestar.connection import ASGIConnection
   from litestar.handlers import BaseRouteHandler
   from litestar.exceptions import NotAuthorizedException

   class BaseWorkflowGuard:
       """Base protocol for workflow guards.

       All workflow guards should implement this interface for consistent
       authorization behavior across the API.
       """

       async def __call__(
           self,
           connection: ASGIConnection,
           route_handler: BaseRouteHandler,
       ) -> None:
           """Check authorization for the request.

           Args:
               connection: The ASGI connection.
               route_handler: The route handler being accessed.

           Raises:
               NotAuthorizedException: If authorization fails.
           """
           raise NotImplementedError


Authentication Guard
~~~~~~~~~~~~~~~~~~~~

Guard requiring authenticated user:

.. code-block:: python

   class WorkflowAuthGuard(BaseWorkflowGuard):
       """Guard requiring authenticated user for workflow operations."""

       async def __call__(
           self,
           connection: ASGIConnection,
           route_handler: BaseRouteHandler,
       ) -> None:
           if not connection.user:
               raise NotAuthorizedException(
                   detail="Authentication required for workflow operations"
               )


Admin Guard
~~~~~~~~~~~

Guard requiring admin privileges:

.. code-block:: python

   class WorkflowAdminGuard(BaseWorkflowGuard):
       """Guard requiring admin role for administrative operations."""

       def __init__(self, admin_role: str = "workflow_admin") -> None:
           self.admin_role = admin_role

       async def __call__(
           self,
           connection: ASGIConnection,
           route_handler: BaseRouteHandler,
       ) -> None:
           if not connection.user:
               raise NotAuthorizedException(detail="Authentication required")

           roles = getattr(connection.user, "roles", [])
           if self.admin_role not in roles:
               raise NotAuthorizedException(
                   detail=f"Role '{self.admin_role}' required for admin operations"
               )


Task Ownership Guard
~~~~~~~~~~~~~~~~~~~~

Guard validating task assignment:

.. code-block:: python

   class TaskAssigneeGuard(BaseWorkflowGuard):
       """Guard ensuring user is assigned to the task.

       This guard validates that the current user is either:
       - Directly assigned to the task (assignee_id matches)
       - Member of the assigned group (assignee_group matches user's groups)
       - An admin (bypasses ownership check)
       """

       def __init__(
           self,
           allow_unassigned: bool = True,
           admin_role: str = "workflow_admin",
       ) -> None:
           self.allow_unassigned = allow_unassigned
           self.admin_role = admin_role

       async def __call__(
           self,
           connection: ASGIConnection,
           route_handler: BaseRouteHandler,
       ) -> None:
           # Extract task_id from path
           task_id = connection.path_params.get("task_id")
           if not task_id:
               return  # Not a task-specific route

           # Get task from database
           task_repo = connection.app.state.task_repo
           task = await task_repo.get(task_id)

           if not task:
               raise NotFoundException(detail=f"Task {task_id} not found")

           user_id = getattr(connection.user, "id", None)
           user_groups = getattr(connection.user, "groups", [])
           user_roles = getattr(connection.user, "roles", [])

           # Admin bypass
           if self.admin_role in user_roles:
               return

           # Check assignment
           is_assigned = (
               task.assignee_id == user_id
               or (task.assignee_group and task.assignee_group in user_groups)
               or (self.allow_unassigned and not task.assignee_id and not task.assignee_group)
           )

           if not is_assigned:
               raise NotAuthorizedException(
                   detail="You are not assigned to this task"
               )


MermaidJS Graph Generation
--------------------------

Graph Service
~~~~~~~~~~~~~

Service for generating MermaidJS diagrams from workflow definitions and instances:

.. code-block:: python

   from litestar_workflows.core.definition import WorkflowDefinition
   from litestar_workflows.core.types import StepType, StepStatus

   class GraphService:
       """Service for generating workflow visualizations.

       Generates MermaidJS diagrams for workflow definitions and instances
       with support for execution state highlighting.
       """

       # MermaidJS shape mappings by step type
       STEP_SHAPES: dict[StepType, tuple[str, str]] = {
           StepType.MACHINE: ("[", "]"),          # Rectangle
           StepType.HUMAN: ("{{", "}}"),          # Hexagon
           StepType.GATEWAY: ("{", "}"),          # Diamond
           StepType.TIMER: ("([", "])"),          # Stadium
           StepType.WEBHOOK: ("[[", "]]"),        # Subroutine
       }

       # Status color mappings
       STATUS_STYLES: dict[str, str] = {
           "completed": "fill:#90EE90,stroke:#006400,stroke-width:2px",
           "failed": "fill:#FFB6C1,stroke:#8B0000,stroke-width:2px",
           "running": "fill:#FFD700,stroke:#FFA500,stroke-width:3px",
           "waiting": "fill:#87CEEB,stroke:#4169E1,stroke-width:2px",
           "skipped": "fill:#D3D3D3,stroke:#808080,stroke-width:1px,stroke-dasharray:5",
       }

       def generate_definition_graph(
           self,
           definition: WorkflowDefinition,
           direction: str = "TD",
       ) -> str:
           """Generate MermaidJS graph for a workflow definition.

           Args:
               definition: The workflow definition to visualize.
               direction: Graph direction (TD, LR, BT, RL).

           Returns:
               MermaidJS graph definition string.
           """
           lines = [f"graph {direction}"]

           # Add nodes
           for step_name, step in definition.steps.items():
               shape_start, shape_end = self.STEP_SHAPES.get(
                   step.step_type, ("[", "]")
               )

               # Format label
               label = step_name.replace("_", " ").title()

               # Add markers for special steps
               if step_name == definition.initial_step:
                   label = f"[Start] {label}"
               elif step_name in definition.terminal_steps:
                   label = f"{label} [End]"

               lines.append(f"    {step_name}{shape_start}{label}{shape_end}")

           # Add edges
           for edge in definition.edges:
               source = edge.get_source_name()
               target = edge.get_target_name()

               if edge.condition:
                   # Conditional edge with label
                   condition_label = (
                       edge.condition if isinstance(edge.condition, str)
                       else "conditional"
                   )
                   lines.append(f"    {source} -->|{condition_label}| {target}")
               else:
                   lines.append(f"    {source} --> {target}")

           return "\n".join(lines)

       def generate_instance_graph(
           self,
           definition: WorkflowDefinition,
           current_step: str | None,
           step_history: list[StepExecutionDTO],
           direction: str = "TD",
       ) -> str:
           """Generate MermaidJS graph with execution state.

           Args:
               definition: The workflow definition.
               current_step: Name of the currently executing step.
               step_history: List of executed steps with status.
               direction: Graph direction.

           Returns:
               MermaidJS graph with state highlighting.
           """
           # Build base graph
           base_graph = self.generate_definition_graph(definition, direction)
           lines = base_graph.split("\n")

           # Build step status map
           step_statuses: dict[str, str] = {}
           for execution in step_history:
               status_key = "completed"
               if execution.status == StepStatus.FAILED:
                   status_key = "failed"
               elif execution.status == StepStatus.SKIPPED:
                   status_key = "skipped"
               step_statuses[execution.step_name] = status_key

           if current_step:
               step_statuses[current_step] = "running"

           # Add styling
           for step_name, status in step_statuses.items():
               if status in self.STATUS_STYLES:
                   lines.append(f"    style {step_name} {self.STATUS_STYLES[status]}")

           # Add click handlers for interactive graphs
           lines.append("")
           lines.append("    %% Click handlers for step details")
           for step_name in definition.steps:
               lines.append(f'    click {step_name} "/workflows/steps/{step_name}"')

           return "\n".join(lines)


Graph Controller
~~~~~~~~~~~~~~~~

Controller for graph visualization endpoints:

.. code-block:: python

   from litestar import Controller, get
   from litestar.response import Response
   from uuid import UUID

   class GraphController(Controller):
       """API for workflow graph visualization.

       Provides MermaidJS graph representations of workflow definitions
       and instances with execution state highlighting.
       """

       path = "/graphs"
       tags = ["Workflow Graphs"]

       @get(
           "/definitions/{name:str}",
           summary="Get definition graph",
           description="Returns MermaidJS graph for a workflow definition.",
       )
       async def get_definition_graph(
           self,
           name: str,
           workflow_registry: WorkflowRegistry,
           direction: str = "TD",
           format: str = "mermaid",
       ) -> GraphResponseDTO:
           """Get workflow definition as MermaidJS graph."""
           definition = workflow_registry.get_definition(name)
           graph_service = GraphService()
           graph = graph_service.generate_definition_graph(definition, direction)

           return GraphResponseDTO(
               graph=graph,
               format=format,
               workflow_name=name,
               workflow_version=definition.version,
           )

       @get(
           "/instances/{instance_id:uuid}",
           summary="Get instance graph",
           description="Returns MermaidJS graph with execution state.",
       )
       async def get_instance_graph(
           self,
           instance_id: UUID,
           workflow_engine: PersistentExecutionEngine,
           workflow_registry: WorkflowRegistry,
           direction: str = "TD",
       ) -> GraphResponseDTO:
           """Get workflow instance graph with execution state."""
           instance = await workflow_engine.get_instance(instance_id)
           definition = workflow_registry.get_definition(instance.workflow_name)

           graph_service = GraphService()
           graph = graph_service.generate_instance_graph(
               definition=definition,
               current_step=instance.current_step,
               step_history=[
                   StepExecutionDTO.from_model(s)
                   for s in instance.context.step_history
               ],
               direction=direction,
           )

           return GraphResponseDTO(
               graph=graph,
               format="mermaid",
               workflow_name=instance.workflow_name,
               workflow_version=instance.workflow_version,
               instance_id=instance_id,
               instance_status=instance.status.value,
           )


Graph Response DTO
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class GraphResponseDTO(Struct):
       """DTO for graph visualization response."""
       graph: str  # MermaidJS graph definition
       format: str  # "mermaid" or "svg"
       workflow_name: str
       workflow_version: str
       instance_id: UUID | None = None
       instance_status: str | None = None


Dependency Injection Patterns
-----------------------------

Repository Providers
~~~~~~~~~~~~~~~~~~~~

DI providers for repository instances:

.. code-block:: python

   from typing import TYPE_CHECKING
   from litestar.di import Provide

   if TYPE_CHECKING:
       from sqlalchemy.ext.asyncio import AsyncSession
       from litestar_workflows.db import (
           WorkflowDefinitionRepository,
           WorkflowInstanceRepository,
           HumanTaskRepository,
       )

   async def provide_definition_repo(
       db_session: AsyncSession,
   ) -> WorkflowDefinitionRepository:
       """Provide workflow definition repository."""
       return WorkflowDefinitionRepository(session=db_session)

   async def provide_instance_repo(
       db_session: AsyncSession,
   ) -> WorkflowInstanceRepository:
       """Provide workflow instance repository."""
       return WorkflowInstanceRepository(session=db_session)

   async def provide_task_repo(
       db_session: AsyncSession,
   ) -> HumanTaskRepository:
       """Provide human task repository."""
       return HumanTaskRepository(session=db_session)


Engine Provider
~~~~~~~~~~~~~~~

DI provider for the execution engine:

.. code-block:: python

   async def provide_engine(
       db_session: AsyncSession,
       workflow_registry: WorkflowRegistry,
   ) -> PersistentExecutionEngine:
       """Provide persistent execution engine.

       The engine is created per-request with the request's database session
       to ensure proper transaction management.
       """
       return PersistentExecutionEngine(
           registry=workflow_registry,
           session=db_session,
       )


Dependency Registration
~~~~~~~~~~~~~~~~~~~~~~~

The plugin registers dependencies during initialization:

.. code-block:: python

   def _register_dependencies(self, app_config: AppConfig) -> None:
       """Register dependency providers with the application."""
       config = self._config

       # Repository providers
       app_config.dependencies[config.dependency_key_definition_repo] = Provide(
           provide_definition_repo,
           sync_to_thread=False,
       )
       app_config.dependencies[config.dependency_key_instance_repo] = Provide(
           provide_instance_repo,
           sync_to_thread=False,
       )
       app_config.dependencies[config.dependency_key_task_repo] = Provide(
           provide_task_repo,
           sync_to_thread=False,
       )

       # Engine provider
       app_config.dependencies[config.dependency_key_engine] = Provide(
           provide_engine,
           sync_to_thread=False,
       )


Dependency Composition
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   Request
       |
       +-- db_session (from SQLAlchemy plugin or user config)
       |       |
       |       +-- workflow_definition_repo
       |       +-- workflow_instance_repo
       |       +-- workflow_task_repo
       |       |
       |       +-- workflow_registry (singleton)
       |               |
       |               +-- workflow_engine (per-request)


Exception Handling
------------------

Web-Specific Exceptions
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from litestar.exceptions import HTTPException

   class WorkflowWebException(HTTPException):
       """Base exception for workflow web errors."""
       pass

   class WorkflowNotFoundException(WorkflowWebException):
       """Raised when a workflow or instance is not found."""
       status_code = 404

       def __init__(self, workflow_name: str) -> None:
           super().__init__(detail=f"Workflow '{workflow_name}' not found")

   class InstanceNotFoundException(WorkflowWebException):
       """Raised when a workflow instance is not found."""
       status_code = 404

       def __init__(self, instance_id: UUID) -> None:
           super().__init__(detail=f"Workflow instance '{instance_id}' not found")

   class TaskNotFoundException(WorkflowWebException):
       """Raised when a human task is not found."""
       status_code = 404

       def __init__(self, task_id: UUID) -> None:
           super().__init__(detail=f"Task '{task_id}' not found")

   class TaskNotAssignedError(WorkflowWebException):
       """Raised when user is not assigned to a task."""
       status_code = 403

       def __init__(self, task_id: UUID, user_id: str) -> None:
           super().__init__(
               detail=f"User '{user_id}' is not assigned to task '{task_id}'"
           )

   class InvalidTransitionError(WorkflowWebException):
       """Raised when an invalid workflow transition is attempted."""
       status_code = 409

       def __init__(self, detail: str) -> None:
           super().__init__(detail=detail)

   class WorkflowInProgressError(WorkflowWebException):
       """Raised when operation requires workflow to be complete."""
       status_code = 409

       def __init__(self, instance_id: UUID, current_status: str) -> None:
           super().__init__(
               detail=f"Workflow '{instance_id}' is still in progress (status: {current_status})"
           )


Exception Handlers
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from litestar import Request, Response
   from litestar.exceptions import HTTPException
   from litestar_workflows.exceptions import (
       WorkflowNotFoundError,
       StepExecutionError,
       InvalidTransitionError as CoreInvalidTransitionError,
   )

   async def workflow_not_found_handler(
       request: Request,
       exc: WorkflowNotFoundError,
   ) -> Response:
       """Handle workflow not found errors."""
       return Response(
           content={"detail": str(exc), "type": "workflow_not_found"},
           status_code=404,
       )

   async def step_execution_handler(
       request: Request,
       exc: StepExecutionError,
   ) -> Response:
       """Handle step execution errors."""
       return Response(
           content={
               "detail": str(exc),
               "type": "step_execution_error",
               "step_name": exc.step_name if hasattr(exc, "step_name") else None,
           },
           status_code=500,
       )

   async def invalid_transition_handler(
       request: Request,
       exc: CoreInvalidTransitionError,
   ) -> Response:
       """Handle invalid workflow transition errors."""
       return Response(
           content={"detail": str(exc), "type": "invalid_transition"},
           status_code=409,
       )

   WORKFLOW_EXCEPTION_HANDLERS = {
       WorkflowNotFoundError: workflow_not_found_handler,
       StepExecutionError: step_execution_handler,
       CoreInvalidTransitionError: invalid_transition_handler,
   }


Integration Example
-------------------

Complete Application Setup
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from litestar import Litestar
   from litestar.plugins.sqlalchemy import SQLAlchemyPlugin
   from litestar_workflows import WorkflowPlugin, WorkflowPluginConfig
   from litestar_workflows.web import WorkflowWebPlugin, WorkflowWebPluginConfig

   # Workflow definitions
   from myapp.workflows import OrderApprovalWorkflow, DocumentReviewWorkflow

   # Custom guards
   from myapp.guards import AuthGuard, AdminGuard

   # Create workflow plugin
   workflow_plugin = WorkflowPlugin(
       config=WorkflowPluginConfig(
           auto_register_workflows=[
               OrderApprovalWorkflow,
               DocumentReviewWorkflow,
           ],
       )
   )

   # Create web plugin
   web_plugin = WorkflowWebPlugin(
       config=WorkflowWebPluginConfig(
           path_prefix="/api/workflows",
           api_guards=[AuthGuard],
           admin_guards=[AdminGuard],
           task_guards=[AuthGuard],
           enable_graph_api=True,
       )
   )

   # Create Litestar application
   app = Litestar(
       route_handlers=[],  # Your other routes
       plugins=[
           SQLAlchemyPlugin(config=...),
           workflow_plugin,
           web_plugin,
       ],
       openapi_config=OpenAPIConfig(
           title="My Application API",
           version="1.0.0",
       ),
   )


API Usage Examples
~~~~~~~~~~~~~~~~~~

Starting a workflow:

.. code-block:: bash

   curl -X POST http://localhost:8000/api/workflows/api/instances \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "workflow_name": "order_approval",
       "initial_data": {
         "order_id": "ORD-123",
         "amount": 1500.00,
         "customer_id": "CUST-456"
       }
     }'

Listing pending tasks:

.. code-block:: bash

   curl http://localhost:8000/api/workflows/api/tasks \
     -H "Authorization: Bearer $TOKEN"

Completing a task:

.. code-block:: bash

   curl -X POST http://localhost:8000/api/workflows/api/tasks/{task_id}/complete \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "form_data": {
         "approved": true,
         "comments": "Approved per policy guidelines"
       }
     }'

Getting workflow graph:

.. code-block:: bash

   curl http://localhost:8000/api/workflows/graphs/instances/{instance_id}


Testing Strategy
----------------

Unit Tests
~~~~~~~~~~

.. code-block:: python

   import pytest
   from litestar.testing import TestClient
   from litestar_workflows.web import WorkflowWebPlugin

   @pytest.fixture
   def client(app):
       return TestClient(app)

   class TestWorkflowDefinitionController:
       async def test_list_definitions(self, client):
           response = client.get("/api/workflows/api/definitions")
           assert response.status_code == 200
           assert isinstance(response.json(), list)

       async def test_get_definition_not_found(self, client):
           response = client.get("/api/workflows/api/definitions/nonexistent")
           assert response.status_code == 404

   class TestWorkflowInstanceController:
       async def test_start_workflow(self, client, auth_headers):
           response = client.post(
               "/api/workflows/api/instances",
               json={"workflow_name": "test_workflow", "initial_data": {}},
               headers=auth_headers,
           )
           assert response.status_code == 201
           assert "id" in response.json()

   class TestHumanTaskController:
       async def test_complete_task_unauthorized(self, client, other_user_task_id):
           response = client.post(
               f"/api/workflows/api/tasks/{other_user_task_id}/complete",
               json={"form_data": {"approved": True}},
           )
           assert response.status_code == 403


Integration Tests
~~~~~~~~~~~~~~~~~

.. code-block:: python

   @pytest.mark.integration
   async def test_full_workflow_lifecycle(client, auth_headers):
       # Start workflow
       start_response = client.post(
           "/api/workflows/api/instances",
           json={"workflow_name": "approval_workflow", "initial_data": {"value": 100}},
           headers=auth_headers,
       )
       instance_id = start_response.json()["id"]

       # Wait for human task
       import asyncio
       await asyncio.sleep(0.1)

       # Get pending tasks
       tasks_response = client.get(
           "/api/workflows/api/tasks",
           headers=auth_headers,
       )
       assert len(tasks_response.json()) > 0
       task_id = tasks_response.json()[0]["id"]

       # Complete task
       complete_response = client.post(
           f"/api/workflows/api/tasks/{task_id}/complete",
           json={"form_data": {"approved": True}},
           headers=auth_headers,
       )
       assert complete_response.status_code == 200

       # Verify workflow completed
       instance_response = client.get(
           f"/api/workflows/api/instances/{instance_id}",
           headers=auth_headers,
       )
       assert instance_response.json()["status"] == "completed"


Implementation Checklist
------------------------

Phase 3.1: Core Infrastructure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- [ ] Create ``web/`` module structure
- [ ] Implement ``WorkflowWebPluginConfig`` dataclass
- [ ] Implement ``WorkflowWebPlugin`` class with ``on_app_init``
- [ ] Create base exception hierarchy
- [ ] Register exception handlers

Phase 3.2: DTO Layer
~~~~~~~~~~~~~~~~~~~~

- [ ] Implement base DTO classes with msgspec
- [ ] Create workflow definition DTOs
- [ ] Create workflow instance DTOs
- [ ] Create human task DTOs
- [ ] Create graph response DTOs
- [ ] Add validation constraints
- [ ] Add OpenAPI examples

Phase 3.3: Controllers
~~~~~~~~~~~~~~~~~~~~~~

- [ ] Implement ``WorkflowDefinitionController``
- [ ] Implement ``WorkflowInstanceController``
- [ ] Implement ``HumanTaskController``
- [ ] Implement ``WorkflowAdminController``
- [ ] Implement ``GraphController``
- [ ] Add comprehensive docstrings for OpenAPI

Phase 3.4: Guards
~~~~~~~~~~~~~~~~~

- [ ] Implement ``BaseWorkflowGuard`` protocol
- [ ] Implement ``WorkflowAuthGuard``
- [ ] Implement ``WorkflowAdminGuard``
- [ ] Implement ``TaskAssigneeGuard``
- [ ] Document guard customization

Phase 3.5: Graph Service
~~~~~~~~~~~~~~~~~~~~~~~~

- [ ] Implement ``GraphService`` class
- [ ] Add MermaidJS generation for definitions
- [ ] Add state highlighting for instances
- [ ] Support multiple graph directions

Phase 3.6: DI Integration
~~~~~~~~~~~~~~~~~~~~~~~~~

- [ ] Create repository providers
- [ ] Create engine provider
- [ ] Implement dependency registration
- [ ] Document DI customization

Phase 3.7: Testing
~~~~~~~~~~~~~~~~~~

- [ ] Unit tests for all controllers
- [ ] Unit tests for DTOs
- [ ] Unit tests for guards
- [ ] Integration tests for full workflows
- [ ] OpenAPI schema validation tests

Phase 3.8: Documentation
~~~~~~~~~~~~~~~~~~~~~~~~

- [ ] API usage guide
- [ ] Guard customization guide
- [ ] DTO customization guide
- [ ] OpenAPI integration guide


Migration Guide
---------------

From Manual Routes
~~~~~~~~~~~~~~~~~~

If you have existing manual routes, migrate to the plugin:

**Before:**

.. code-block:: python

   @post("/workflows/start")
   async def start_workflow(data: dict, engine: Engine) -> dict:
       instance = await engine.start_workflow(MyWorkflow, data)
       return {"id": str(instance.id)}

**After:**

.. code-block:: python

   # Remove manual routes, use plugin
   app = Litestar(
       plugins=[WorkflowWebPlugin()],
   )

   # Access via: POST /workflows/api/instances


From v0.3.x
~~~~~~~~~~~

The web plugin replaces manual controller implementations:

1. Remove custom workflow controllers
2. Add ``WorkflowWebPlugin`` to your app
3. Configure guards via ``WorkflowWebPluginConfig``
4. Update frontend to use new endpoint paths


See Also
--------

- :doc:`/guides/persistence` - Database persistence setup
- :doc:`/concepts/execution` - Execution engine concepts
- :doc:`/guides/human-tasks` - Human task workflows
- :doc:`/api/index` - Complete API reference
