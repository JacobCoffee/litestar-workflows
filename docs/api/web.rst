Web Plugin API Reference
========================

Complete API documentation for the ``litestar_workflows.web`` module.

.. contents:: On this page
   :local:
   :depth: 2


Installation
------------

Install with the ``[web]`` extra:

.. code-block:: bash

   pip install litestar-workflows[web]


Module Exports
--------------

The following are exported from ``litestar_workflows.web``:

.. code-block:: python

   from litestar_workflows.web import (
       # Plugin
       WorkflowWebPlugin,
       WorkflowWebConfig,

       # Controllers
       WorkflowDefinitionController,
       WorkflowInstanceController,
       HumanTaskController,

       # DTOs
       StartWorkflowDTO,
       WorkflowDefinitionDTO,
       WorkflowInstanceDTO,
       WorkflowInstanceDetailDTO,
       StepExecutionDTO,
       HumanTaskDTO,
       CompleteTaskDTO,
       ReassignTaskDTO,
       GraphDTO,

       # Graph utilities
       generate_mermaid_graph,
       generate_mermaid_graph_with_state,
       parse_graph_to_dict,
   )


Plugin Configuration
--------------------


WorkflowWebConfig
~~~~~~~~~~~~~~~~~

.. py:class:: WorkflowWebConfig

   Configuration dataclass for the WorkflowWebPlugin.

   :param path_prefix: URL path prefix for all workflow endpoints
   :type path_prefix: str
   :param include_in_schema: Include routes in OpenAPI documentation
   :type include_in_schema: bool
   :param guards: List of Litestar guards to apply to all routes
   :type guards: list[Guard]
   :param enable_graph_endpoints: Enable graph visualization endpoints
   :type enable_graph_endpoints: bool
   :param tags: OpenAPI tags for route grouping
   :type tags: list[str]

   **Defaults:**

   .. code-block:: python

      WorkflowWebConfig(
          path_prefix="/workflows",
          include_in_schema=True,
          guards=[],
          enable_graph_endpoints=True,
          tags=["Workflows"],
      )

   **Example:**

   .. code-block:: python

      from litestar_workflows.web import WorkflowWebConfig

      config = WorkflowWebConfig(
          path_prefix="/api/v1/workflows",
          guards=[require_auth],
          enable_graph_endpoints=True,
          tags=["Business Processes"],
      )


WorkflowWebPlugin
~~~~~~~~~~~~~~~~~

.. py:class:: WorkflowWebPlugin

   Litestar plugin for workflow web routes.

   Automatically registers REST API controllers for workflow management.
   Should be used alongside the base WorkflowPlugin.

   :param config: Plugin configuration
   :type config: WorkflowWebConfig | None

   **Example:**

   .. code-block:: python

      from litestar import Litestar
      from litestar_workflows import WorkflowPlugin
      from litestar_workflows.web import WorkflowWebPlugin, WorkflowWebConfig

      app = Litestar(
          plugins=[
              WorkflowPlugin(),
              WorkflowWebPlugin(
                  config=WorkflowWebConfig(
                      path_prefix="/api/workflows",
                  )
              ),
          ]
      )

   .. py:attribute:: config
      :type: WorkflowWebConfig

      The plugin configuration instance.

   .. py:method:: on_app_init(app_config: AppConfig) -> AppConfig

      Hook called during Litestar application initialization.

      Registers workflow routes under the configured path prefix:

      - ``{path_prefix}/definitions/*`` - Workflow definition endpoints
      - ``{path_prefix}/instances/*`` - Workflow instance endpoints
      - ``{path_prefix}/tasks/*`` - Human task endpoints

      :param app_config: The application configuration being built
      :returns: Modified application configuration


Controllers
-----------

The plugin registers three controller classes.


WorkflowDefinitionController
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:class:: WorkflowDefinitionController

   REST API controller for workflow definitions.

   **Path:** ``{path_prefix}/definitions``

   **Tags:** Workflow Definitions

   .. py:method:: list_definitions(workflow_registry, active_only=True) -> list[WorkflowDefinitionDTO]
      :async:

      List all registered workflow definitions.

      **Endpoint:** ``GET /definitions``

      :param workflow_registry: Injected workflow registry
      :type workflow_registry: WorkflowRegistry
      :param active_only: If True, only return active definitions
      :type active_only: bool
      :returns: List of workflow definition DTOs

      **Example Response:**

      .. code-block:: json

         [
           {
             "name": "expense_approval",
             "version": "1.0.0",
             "description": "Multi-level expense approval",
             "steps": ["submit", "manager_approval", "process"],
             "edges": [
               {"source": "submit", "target": "manager_approval", "condition": null}
             ],
             "initial_step": "submit",
             "terminal_steps": ["process"]
           }
         ]

   .. py:method:: get_definition(name, workflow_registry, version=None) -> WorkflowDefinitionDTO
      :async:

      Get a specific workflow definition by name.

      **Endpoint:** ``GET /definitions/{name}``

      :param name: Workflow name
      :type name: str
      :param workflow_registry: Injected workflow registry
      :type workflow_registry: WorkflowRegistry
      :param version: Optional specific version (defaults to latest)
      :type version: str | None
      :returns: Workflow definition DTO
      :raises NotFoundException: If workflow not found

   .. py:method:: get_definition_graph(name, workflow_registry, graph_format="mermaid") -> GraphDTO
      :async:

      Get workflow graph visualization.

      **Endpoint:** ``GET /definitions/{name}/graph``

      :param name: Workflow name
      :type name: str
      :param workflow_registry: Injected workflow registry
      :type workflow_registry: WorkflowRegistry
      :param graph_format: Output format ("mermaid" or "json")
      :type graph_format: str
      :returns: Graph DTO with MermaidJS source and node/edge data
      :raises NotFoundException: If workflow not found or unknown format

      **Example Response:**

      .. code-block:: json

         {
           "mermaid_source": "graph TD\n    submit[Submit]\n    ...",
           "nodes": [
             {"id": "submit", "label": "Submit", "type": "machine", "is_initial": true, "is_terminal": false}
           ],
           "edges": [
             {"source": "submit", "target": "manager_approval"}
           ]
         }


WorkflowInstanceController
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:class:: WorkflowInstanceController

   REST API controller for workflow instances.

   **Path:** ``{path_prefix}/instances``

   **Tags:** Workflow Instances

   .. py:method:: start_workflow(data, workflow_engine, workflow_registry) -> WorkflowInstanceDTO
      :async:

      Start a new workflow instance.

      **Endpoint:** ``POST /instances``

      :param data: Start workflow request data
      :type data: DTOData[StartWorkflowDTO]
      :param workflow_engine: Injected execution engine
      :type workflow_engine: LocalExecutionEngine
      :param workflow_registry: Injected workflow registry
      :type workflow_registry: WorkflowRegistry
      :returns: Created workflow instance DTO
      :raises NotFoundException: If workflow definition not found

      **Request Body:**

      .. code-block:: json

         {
           "definition_name": "expense_approval",
           "input_data": {
             "requester": "alice@example.com",
             "amount": 2500.00
           },
           "user_id": "alice@example.com"
         }

   .. py:method:: list_instances(workflow_instance_repo, workflow_name=None, status=None, limit=50, offset=0) -> list[WorkflowInstanceDTO]
      :async:

      List workflow instances with optional filtering.

      **Endpoint:** ``GET /instances``

      :param workflow_instance_repo: Injected instance repository
      :type workflow_instance_repo: WorkflowInstanceRepository
      :param workflow_name: Filter by workflow name
      :type workflow_name: str | None
      :param status: Filter by status
      :type status: str | None
      :param limit: Maximum results (1-100)
      :type limit: int
      :param offset: Pagination offset
      :type offset: int
      :returns: List of workflow instance DTOs

   .. py:method:: get_instance(instance_id, workflow_instance_repo) -> WorkflowInstanceDetailDTO
      :async:

      Get detailed workflow instance information.

      **Endpoint:** ``GET /instances/{instance_id}``

      :param instance_id: The workflow instance UUID
      :type instance_id: UUID
      :param workflow_instance_repo: Injected instance repository
      :type workflow_instance_repo: WorkflowInstanceRepository
      :returns: Detailed instance DTO with step history
      :raises NotFoundException: If instance not found

   .. py:method:: get_instance_graph(instance_id, workflow_instance_repo, workflow_registry) -> GraphDTO
      :async:

      Get instance graph with execution state highlighting.

      **Endpoint:** ``GET /instances/{instance_id}/graph``

      :param instance_id: The workflow instance UUID
      :type instance_id: UUID
      :param workflow_instance_repo: Injected instance repository
      :type workflow_instance_repo: WorkflowInstanceRepository
      :param workflow_registry: Injected workflow registry
      :type workflow_registry: WorkflowRegistry
      :returns: Graph DTO with state-based MermaidJS styling
      :raises NotFoundException: If instance not found

      The returned graph uses CSS styling to indicate step states:

      - Completed: ``fill:#90EE90,stroke:#006400`` (green)
      - Current: ``fill:#FFD700,stroke:#FFA500`` (yellow)
      - Failed: ``fill:#FF6B6B`` (red)

   .. py:method:: cancel_instance(instance_id, workflow_engine, workflow_instance_repo, reason="User canceled") -> WorkflowInstanceDTO
      :async:

      Cancel a running workflow instance.

      **Endpoint:** ``POST /instances/{instance_id}/cancel``

      :param instance_id: The workflow instance UUID
      :type instance_id: UUID
      :param workflow_engine: Injected execution engine
      :type workflow_engine: LocalExecutionEngine
      :param workflow_instance_repo: Injected instance repository
      :type workflow_instance_repo: WorkflowInstanceRepository
      :param reason: Cancellation reason
      :type reason: str
      :returns: Updated instance DTO
      :raises NotFoundException: If instance not found

   .. py:method:: retry_instance(instance_id, workflow_engine, workflow_instance_repo, from_step=None) -> WorkflowInstanceDTO
      :async:

      Retry a failed workflow from a specific step.

      **Endpoint:** ``POST /instances/{instance_id}/retry``

      :param instance_id: The workflow instance UUID
      :type instance_id: UUID
      :param workflow_engine: Injected execution engine
      :type workflow_engine: LocalExecutionEngine
      :param workflow_instance_repo: Injected instance repository
      :type workflow_instance_repo: WorkflowInstanceRepository
      :param from_step: Step name to retry from (defaults to failed step)
      :type from_step: str | None
      :returns: Updated instance DTO
      :raises NotFoundException: If instance not found


HumanTaskController
~~~~~~~~~~~~~~~~~~~

.. py:class:: HumanTaskController

   REST API controller for human tasks.

   **Path:** ``{path_prefix}/tasks``

   **Tags:** Human Tasks

   .. py:method:: list_tasks(human_task_repo, assignee_id=None, assignee_group=None, status="pending") -> list[HumanTaskDTO]
      :async:

      List human tasks with optional filtering.

      **Endpoint:** ``GET /tasks``

      :param human_task_repo: Injected human task repository
      :type human_task_repo: HumanTaskRepository
      :param assignee_id: Filter by assignee user ID
      :type assignee_id: str | None
      :param assignee_group: Filter by assignee group
      :type assignee_group: str | None
      :param status: Filter by task status
      :type status: str
      :returns: List of human task DTOs

   .. py:method:: get_task(task_id, human_task_repo) -> HumanTaskDTO
      :async:

      Get detailed information about a human task.

      **Endpoint:** ``GET /tasks/{task_id}``

      :param task_id: The task UUID
      :type task_id: UUID
      :param human_task_repo: Injected task repository
      :type human_task_repo: HumanTaskRepository
      :returns: Human task DTO with form schema
      :raises NotFoundException: If task not found

   .. py:method:: complete_task(task_id, data, workflow_engine, human_task_repo) -> WorkflowInstanceDTO
      :async:

      Complete a human task with form data.

      **Endpoint:** ``POST /tasks/{task_id}/complete``

      :param task_id: The task UUID
      :type task_id: UUID
      :param data: Task completion data
      :type data: DTOData[CompleteTaskDTO]
      :param workflow_engine: Injected execution engine
      :type workflow_engine: LocalExecutionEngine
      :param human_task_repo: Injected task repository
      :type human_task_repo: HumanTaskRepository
      :returns: Updated workflow instance DTO
      :raises NotFoundException: If task not found

      **Request Body:**

      .. code-block:: json

         {
           "output_data": {
             "approved": true,
             "comments": "Looks good!"
           },
           "completed_by": "manager@example.com"
         }

   .. py:method:: reassign_task(task_id, data, human_task_repo) -> HumanTaskDTO
      :async:

      Reassign a task to another user.

      **Endpoint:** ``POST /tasks/{task_id}/reassign``

      :param task_id: The task UUID
      :type task_id: UUID
      :param data: Reassignment data
      :type data: DTOData[ReassignTaskDTO]
      :param human_task_repo: Injected task repository
      :type human_task_repo: HumanTaskRepository
      :returns: Updated task DTO
      :raises NotFoundException: If task not found


Data Transfer Objects
---------------------

Request DTOs
~~~~~~~~~~~~

.. py:class:: StartWorkflowDTO

   DTO for starting a workflow instance.

   :param definition_name: Name of the workflow definition to instantiate
   :type definition_name: str
   :param input_data: Initial data to pass to the workflow context
   :type input_data: dict[str, Any] | None
   :param correlation_id: Optional correlation ID for tracking related workflows
   :type correlation_id: str | None
   :param user_id: Optional user ID who started the workflow
   :type user_id: str | None
   :param tenant_id: Optional tenant ID for multi-tenancy
   :type tenant_id: str | None


.. py:class:: CompleteTaskDTO

   DTO for completing a human task.

   :param output_data: Data submitted by the user completing the task
   :type output_data: dict[str, Any]
   :param completed_by: User ID who completed the task
   :type completed_by: str
   :param comment: Optional comment about the completion
   :type comment: str | None


.. py:class:: ReassignTaskDTO

   DTO for reassigning a human task.

   :param new_assignee: User ID to assign the task to
   :type new_assignee: str
   :param reason: Optional reason for reassignment
   :type reason: str | None


Response DTOs
~~~~~~~~~~~~~

.. py:class:: WorkflowDefinitionDTO

   DTO for workflow definition metadata.

   :param name: Workflow name
   :type name: str
   :param version: Workflow version
   :type version: str
   :param description: Human-readable description
   :type description: str
   :param steps: List of step names in the workflow
   :type steps: list[str]
   :param edges: List of edge definitions (source, target, condition)
   :type edges: list[dict[str, Any]]
   :param initial_step: Name of the starting step
   :type initial_step: str
   :param terminal_steps: List of terminal step names
   :type terminal_steps: list[str]


.. py:class:: WorkflowInstanceDTO

   DTO for workflow instance summary.

   :param id: Instance UUID
   :type id: UUID
   :param definition_name: Name of the workflow definition
   :type definition_name: str
   :param status: Current execution status
   :type status: str
   :param current_step: Currently executing step (if applicable)
   :type current_step: str | None
   :param started_at: When the workflow started
   :type started_at: datetime
   :param completed_at: When the workflow completed (if finished)
   :type completed_at: datetime | None
   :param created_by: User who started the workflow
   :type created_by: str | None


.. py:class:: WorkflowInstanceDetailDTO

   DTO for detailed workflow instance information.

   Extends WorkflowInstanceDTO with context and execution history.

   :param id: Instance UUID
   :type id: UUID
   :param definition_name: Name of the workflow definition
   :type definition_name: str
   :param status: Current execution status
   :type status: str
   :param current_step: Currently executing step
   :type current_step: str | None
   :param started_at: When the workflow started
   :type started_at: datetime
   :param completed_at: When the workflow completed
   :type completed_at: datetime | None
   :param created_by: User who started the workflow
   :type created_by: str | None
   :param context_data: Current workflow context data
   :type context_data: dict[str, Any]
   :param metadata: Workflow metadata
   :type metadata: dict[str, Any]
   :param step_history: List of step executions
   :type step_history: list[StepExecutionDTO]
   :param error: Error message if workflow failed
   :type error: str | None


.. py:class:: StepExecutionDTO

   DTO for step execution record.

   :param id: Step execution UUID
   :type id: UUID
   :param step_name: Name of the executed step
   :type step_name: str
   :param status: Execution status
   :type status: str
   :param started_at: When execution started
   :type started_at: datetime
   :param completed_at: When execution completed (if finished)
   :type completed_at: datetime | None
   :param error: Error message if execution failed
   :type error: str | None


.. py:class:: HumanTaskDTO

   DTO for human task summary.

   :param id: Task UUID
   :type id: UUID
   :param instance_id: Workflow instance UUID
   :type instance_id: UUID
   :param step_name: Name of the human task step
   :type step_name: str
   :param title: Display title for the task
   :type title: str
   :param description: Detailed task description
   :type description: str | None
   :param assignee: User ID assigned to complete the task
   :type assignee: str | None
   :param status: Task status (pending, completed, canceled)
   :type status: str
   :param due_date: Optional due date for task completion
   :type due_date: datetime | None
   :param created_at: When the task was created
   :type created_at: datetime
   :param form_schema: Optional JSON Schema for task form
   :type form_schema: dict[str, Any] | None


.. py:class:: GraphDTO

   DTO for workflow graph visualization.

   :param mermaid_source: MermaidJS graph definition
   :type mermaid_source: str
   :param nodes: List of node definitions
   :type nodes: list[dict[str, Any]]
   :param edges: List of edge definitions
   :type edges: list[dict[str, Any]]


Graph Utilities
---------------

.. py:function:: generate_mermaid_graph(definition: WorkflowDefinition) -> str

   Generate a MermaidJS graph representation of a workflow definition.

   :param definition: The workflow definition to visualize
   :type definition: WorkflowDefinition
   :returns: MermaidJS flowchart definition string

   **Example:**

   .. code-block:: python

      from litestar_workflows.web import generate_mermaid_graph

      mermaid = generate_mermaid_graph(definition)
      # Returns:
      # graph TD
      #     submit[Submit]
      #     review{{Review}}
      #     submit --> review


.. py:function:: generate_mermaid_graph_with_state(definition, current_step=None, completed_steps=None, failed_steps=None) -> str

   Generate a MermaidJS graph with execution state highlighting.

   :param definition: The workflow definition to visualize
   :type definition: WorkflowDefinition
   :param current_step: Name of the currently executing step
   :type current_step: str | None
   :param completed_steps: List of successfully completed step names
   :type completed_steps: list[str] | None
   :param failed_steps: List of failed step names
   :type failed_steps: list[str] | None
   :returns: MermaidJS flowchart with state styling

   **Example:**

   .. code-block:: python

      mermaid = generate_mermaid_graph_with_state(
          definition,
          current_step="review",
          completed_steps=["submit"],
          failed_steps=[],
      )


.. py:function:: parse_graph_to_dict(definition: WorkflowDefinition) -> dict[str, Any]

   Parse a workflow definition into a dictionary representation.

   :param definition: The workflow definition to parse
   :type definition: WorkflowDefinition
   :returns: Dictionary with ``nodes`` and ``edges`` lists

   **Example:**

   .. code-block:: python

      graph_dict = parse_graph_to_dict(definition)
      # Returns:
      # {
      #     "nodes": [
      #         {"id": "submit", "label": "Submit", "type": "machine", "is_initial": True, "is_terminal": False}
      #     ],
      #     "edges": [
      #         {"source": "submit", "target": "review"}
      #     ]
      # }


Route Summary
-------------

Complete route listing for the Web Plugin:

.. list-table::
   :widths: 10 40 50
   :header-rows: 1

   * - Method
     - Path
     - Description
   * - GET
     - ``/definitions``
     - List workflow definitions
   * - GET
     - ``/definitions/{name}``
     - Get workflow definition
   * - GET
     - ``/definitions/{name}/graph``
     - Get workflow graph
   * - POST
     - ``/instances``
     - Start new workflow
   * - GET
     - ``/instances``
     - List workflow instances
   * - GET
     - ``/instances/{id}``
     - Get instance details
   * - GET
     - ``/instances/{id}/graph``
     - Get instance graph with state
   * - POST
     - ``/instances/{id}/cancel``
     - Cancel workflow
   * - POST
     - ``/instances/{id}/retry``
     - Retry failed workflow
   * - GET
     - ``/tasks``
     - List tasks
   * - GET
     - ``/tasks/{id}``
     - Get task details
   * - POST
     - ``/tasks/{id}/complete``
     - Complete task
   * - POST
     - ``/tasks/{id}/reassign``
     - Reassign task

All paths are relative to the configured ``path_prefix`` (default: ``/workflows``).


See Also
--------

- :doc:`/guides/web-plugin` - Web Plugin integration guide
- :doc:`/guides/persistence` - Database persistence setup
- :doc:`/guides/human-tasks` - Human task patterns
- :doc:`/architecture/phase3-web` - Web plugin architecture details
