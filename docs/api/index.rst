API Reference
=============

Complete API documentation for litestar-workflows.

.. contents:: On this page
   :local:
   :depth: 2


Core API
--------

The core API provides the fundamental building blocks for workflows.


Workflow Definition
~~~~~~~~~~~~~~~~~~~

.. py:class:: WorkflowDefinition

   Declarative workflow structure defining steps and their connections.

   :param name: Unique identifier for the workflow
   :type name: str
   :param version: Semantic version string (e.g., "1.0.0")
   :type version: str
   :param description: Human-readable description
   :type description: str
   :param steps: Dictionary mapping step names to step instances
   :type steps: dict[str, Step]
   :param edges: List of Edge objects defining transitions
   :type edges: list[Edge]
   :param initial_step: Name of the first step to execute
   :type initial_step: str
   :param terminal_steps: Set of step names that end the workflow
   :type terminal_steps: set[str]

   **Example:**

   .. code-block:: python

      definition = WorkflowDefinition(
          name="approval",
          version="1.0.0",
          description="Simple approval workflow",
          steps={"submit": SubmitStep(), "review": ReviewStep()},
          edges=[Edge("submit", "review")],
          initial_step="submit",
          terminal_steps={"review"},
      )

   .. py:method:: get_graph() -> WorkflowGraph

      Build and return the graph representation of the workflow.

   .. py:method:: to_mermaid() -> str

      Generate a MermaidJS diagram of the workflow.

   .. py:method:: validate() -> list[str]

      Validate the workflow definition and return any errors.


.. py:class:: Edge

   Defines a transition between steps.

   :param source: The step to transition from
   :type source: str
   :param target: The step to transition to
   :type target: str
   :param condition: Optional condition expression for this edge
   :type condition: str | None

   **Example:**

   .. code-block:: python

      # Simple edge
      Edge("step_a", "step_b")

      # Conditional edge
      Edge("review", "approve", condition="context.get('score') >= 80")


Workflow Context
~~~~~~~~~~~~~~~~

.. py:class:: WorkflowContext

   Execution context passed between steps.

   :param workflow_id: UUID of the workflow definition
   :type workflow_id: UUID
   :param instance_id: UUID of this specific execution
   :type instance_id: UUID
   :param data: Mutable workflow data dictionary
   :type data: dict[str, Any]
   :param metadata: Immutable metadata dictionary
   :type metadata: dict[str, Any]
   :param current_step: Name of the currently executing step
   :type current_step: str
   :param step_history: List of completed step executions
   :type step_history: list[StepExecution]
   :param started_at: Workflow start timestamp
   :type started_at: datetime
   :param user_id: Current user ID (for human tasks)
   :type user_id: str | None
   :param tenant_id: Tenant ID for multi-tenancy
   :type tenant_id: str | None

   .. py:method:: get(key: str, default: Any = None) -> Any

      Get a value from the data dictionary.

      :param key: The key to look up
      :param default: Default value if key not found
      :returns: The value or default

   .. py:method:: set(key: str, value: Any) -> None

      Set a value in the data dictionary.

      :param key: The key to set
      :param value: The value to store


Step Types
~~~~~~~~~~

.. py:class:: Step

   Protocol defining a workflow step.

   :param name: Unique identifier for the step
   :type name: str
   :param description: Human-readable description
   :type description: str

   .. py:method:: execute(context: WorkflowContext) -> Any
      :async:

      Execute the step with the given context.

   .. py:method:: can_execute(context: WorkflowContext) -> bool
      :async:

      Check if step can execute (guards/validators).

   .. py:method:: on_success(context: WorkflowContext, result: Any) -> None
      :async:

      Hook called after successful execution.

   .. py:method:: on_failure(context: WorkflowContext, error: Exception) -> None
      :async:

      Hook called after failed execution.


.. py:class:: BaseMachineStep

   Base class for automated (machine) steps.

   Inherits from :py:class:`Step` with ``step_type = StepType.MACHINE``.

   **Example:**

   .. code-block:: python

      class ProcessData(BaseMachineStep):
          name = "process_data"
          description = "Process incoming data"

          async def execute(self, context: WorkflowContext) -> None:
              data = context.get("input")
              result = transform(data)
              context.set("output", result)


.. py:class:: BaseHumanStep

   Base class for human interaction steps.

   :param title: Display title for the task
   :type title: str
   :param form_schema: JSON Schema for the input form
   :type form_schema: dict[str, Any]

   **Example:**

   .. code-block:: python

      class ApprovalStep(BaseHumanStep):
          name = "approval"
          title = "Approval Required"
          form_schema = {
              "type": "object",
              "properties": {
                  "approved": {"type": "boolean"},
              },
          }


.. py:class:: BaseGateway

   Base class for decision/branching steps.

   .. py:method:: evaluate(context: WorkflowContext) -> str | list[str]
      :async:

      Evaluate conditions and return the next step name(s).


Step Groups
~~~~~~~~~~~

.. py:class:: SequentialGroup

   Execute steps in sequence, passing results.

   :param steps: Steps to execute in order
   :type steps: tuple[Step | StepGroup, ...]

   **Example:**

   .. code-block:: python

      validation = SequentialGroup(
          ValidateFormat(),
          ValidateContent(),
          ValidatePermissions(),
      )


.. py:class:: ParallelGroup

   Execute steps in parallel.

   :param steps: Steps to execute simultaneously
   :type steps: tuple[Step | StepGroup, ...]
   :param callback: Optional step to run after all complete
   :type callback: Step | None

   **Example:**

   .. code-block:: python

      notifications = ParallelGroup(
          SendEmail(),
          SendSlack(),
          callback=LogNotifications(),
      )


Enums
~~~~~

.. py:class:: StepType

   Classification of step types.

   .. py:attribute:: MACHINE
      :value: "machine"

      Automated execution

   .. py:attribute:: HUMAN
      :value: "human"

      Requires user interaction

   .. py:attribute:: WEBHOOK
      :value: "webhook"

      Waits for external callback

   .. py:attribute:: TIMER
      :value: "timer"

      Waits for time condition

   .. py:attribute:: GATEWAY
      :value: "gateway"

      Decision/branching point


.. py:class:: StepStatus

   Step execution status.

   .. py:attribute:: PENDING
   .. py:attribute:: SCHEDULED
   .. py:attribute:: RUNNING
   .. py:attribute:: WAITING
   .. py:attribute:: SUCCEEDED
   .. py:attribute:: FAILED
   .. py:attribute:: CANCELED
   .. py:attribute:: SKIPPED


.. py:class:: WorkflowStatus

   Workflow instance status.

   .. py:attribute:: PENDING
   .. py:attribute:: RUNNING
   .. py:attribute:: WAITING
   .. py:attribute:: COMPLETED
   .. py:attribute:: FAILED
   .. py:attribute:: CANCELED


Execution Engine
----------------

.. py:class:: ExecutionEngine

   Protocol for workflow execution engines.

   .. py:method:: start_workflow(workflow_name: str, initial_data: dict = None, version: str = None) -> WorkflowInstance
      :async:

      Start a new workflow instance.

      :param workflow_name: Name of the workflow to start
      :param initial_data: Initial data for the workflow context
      :param version: Specific version to use (latest if None)
      :returns: The created workflow instance

   .. py:method:: execute_step(step: Step, context: WorkflowContext, previous_result: Any = None) -> Any
      :async:

      Execute a single step.

   .. py:method:: complete_human_task(instance_id: UUID, step_name: str, user_id: str, data: dict) -> None
      :async:

      Complete a human task with user input.

      :param instance_id: The workflow instance ID
      :param step_name: Name of the human step
      :param user_id: ID of the user completing the task
      :param data: Form data submitted by the user

   .. py:method:: cancel_workflow(instance_id: UUID, reason: str) -> None
      :async:

      Cancel a running workflow.

   .. py:method:: retry(instance_id: UUID, from_step: str = None) -> None
      :async:

      Retry a failed workflow from a specific step.


.. py:class:: LocalExecutionEngine

   In-process async execution engine.

   :param registry: Workflow registry containing definitions
   :type registry: WorkflowRegistry
   :param persistence: Optional persistence layer
   :type persistence: WorkflowPersistence | None
   :param event_bus: Optional event bus for notifications
   :type event_bus: EventBus | None

   **Example:**

   .. code-block:: python

      registry = WorkflowRegistry()
      registry.register_definition(my_workflow)

      engine = LocalExecutionEngine(registry)
      instance = await engine.start_workflow("my_workflow")


Registry
--------

.. py:class:: WorkflowRegistry

   Registry for managing workflow definitions.

   .. py:method:: register_definition(definition: WorkflowDefinition) -> None

      Register a workflow definition.

   .. py:method:: get_definition(name: str, version: str = None) -> WorkflowDefinition

      Get a workflow definition by name and optional version.

   .. py:method:: list_definitions(active_only: bool = True) -> list[WorkflowDefinition]

      List all registered workflow definitions.

   .. py:method:: has_definition(name: str) -> bool

      Check if a workflow definition exists.


Exceptions
----------

.. py:exception:: WorkflowsError

   Base exception for all litestar-workflows errors.


.. py:exception:: WorkflowNotFoundError

   Raised when a requested workflow definition is not found.


.. py:exception:: StepExecutionError

   Raised when a step fails during execution.


.. py:exception:: InvalidTransitionError

   Raised when an invalid state transition is attempted.


.. py:exception:: ValidationError

   Raised when workflow or step validation fails.


Database Models (Optional)
--------------------------

Available with the ``[db]`` extra. Install with:

.. code-block:: bash

   pip install litestar-workflows[db]


PersistentExecutionEngine
~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:class:: PersistentExecutionEngine

   Execution engine with database persistence.

   A drop-in replacement for ``LocalExecutionEngine`` that persists all workflow
   state to a database, enabling durability, recovery, and querying.

   :param registry: The workflow registry containing definitions
   :type registry: WorkflowRegistry
   :param session: SQLAlchemy async session for database operations
   :type session: AsyncSession
   :param event_bus: Optional event bus for emitting workflow events
   :type event_bus: Any | None

   **Example:**

   .. code-block:: python

      from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
      from litestar_workflows import WorkflowRegistry
      from litestar_workflows.db import PersistentExecutionEngine

      engine = create_async_engine("postgresql+asyncpg://localhost/db")
      session_factory = async_sessionmaker(engine, expire_on_commit=False)

      registry = WorkflowRegistry()
      registry.register_definition(MyWorkflow.get_definition())
      registry.register_workflow_class(MyWorkflow)

      async with session_factory() as session:
          engine = PersistentExecutionEngine(registry=registry, session=session)
          instance = await engine.start_workflow(MyWorkflow, initial_data={"key": "value"})

   .. py:method:: start_workflow(workflow, initial_data=None, *, tenant_id=None, created_by=None) -> WorkflowInstanceData
      :async:

      Start a new workflow instance with persistence.

      :param workflow: The workflow class to execute
      :type workflow: type[Workflow]
      :param initial_data: Optional initial data for the workflow context
      :type initial_data: dict[str, Any] | None
      :param tenant_id: Optional tenant ID for multi-tenancy support
      :type tenant_id: str | None
      :param created_by: Optional user ID who started the workflow
      :type created_by: str | None
      :returns: The created workflow instance data

   .. py:method:: complete_human_task(instance_id, step_name, user_id, data) -> None
      :async:

      Complete a human task with user-provided data.

      :param instance_id: The workflow instance ID
      :type instance_id: UUID
      :param step_name: Name of the human task step
      :type step_name: str
      :param user_id: ID of the user completing the task
      :type user_id: str
      :param data: User-provided data to merge into context
      :type data: dict[str, Any]
      :raises ValueError: If instance not found or not in WAITING status

   .. py:method:: cancel_workflow(instance_id, reason) -> None
      :async:

      Cancel a running workflow.

      :param instance_id: The workflow instance ID
      :type instance_id: UUID
      :param reason: Reason for cancellation
      :type reason: str

   .. py:method:: get_instance(instance_id) -> WorkflowInstanceData
      :async:

      Get a workflow instance by ID.

      :param instance_id: The workflow instance ID
      :type instance_id: UUID
      :returns: The workflow instance data
      :raises KeyError: If instance not found

   .. py:method:: get_running_instances() -> list[UUID]

      Get IDs of currently running instances (in-memory tracking).

      :returns: List of running instance IDs


SQLAlchemy Models
~~~~~~~~~~~~~~~~~

.. py:class:: WorkflowDefinitionModel

   SQLAlchemy model for persisted workflow definitions.

   Stores the serialized workflow definition along with metadata for
   querying and managing workflow versions.

   :param name: Unique name identifier for the workflow (indexed)
   :type name: str
   :param version: Semantic version string (e.g., "1.0.0")
   :type version: str
   :param description: Human-readable description
   :type description: str | None
   :param definition_json: Serialized WorkflowDefinition as JSON
   :type definition_json: dict[str, Any]
   :param is_active: Whether this version is active for new instances
   :type is_active: bool
   :param instances: Related workflow instances (relationship)
   :type instances: list[WorkflowInstanceModel]


.. py:class:: WorkflowInstanceModel

   SQLAlchemy model for workflow instances.

   Stores the current state of a workflow execution including context data,
   current step, and execution history.

   :param definition_id: Foreign key to the workflow definition
   :type definition_id: UUID
   :param workflow_name: Denormalized workflow name for quick queries
   :type workflow_name: str
   :param workflow_version: Denormalized workflow version
   :type workflow_version: str
   :param status: Current execution status
   :type status: WorkflowStatus
   :param current_step: Name of the currently executing step
   :type current_step: str | None
   :param context_data: Mutable workflow context data as JSON
   :type context_data: dict[str, Any]
   :param metadata_: Immutable metadata about the execution
   :type metadata_: dict[str, Any]
   :param error: Error message if workflow failed
   :type error: str | None
   :param started_at: Timestamp when execution began
   :type started_at: datetime
   :param completed_at: Timestamp when execution finished
   :type completed_at: datetime | None
   :param tenant_id: Optional tenant identifier for multi-tenancy (indexed)
   :type tenant_id: str | None
   :param created_by: Optional user who started the workflow (indexed)
   :type created_by: str | None


.. py:class:: StepExecutionModel

   SQLAlchemy model for step execution records.

   Tracks the execution of each step including timing, status, and
   input/output data for debugging and audit purposes.

   :param instance_id: Foreign key to the workflow instance
   :type instance_id: UUID
   :param step_name: Name of the executed step (indexed)
   :type step_name: str
   :param step_type: Type of step (MACHINE, HUMAN, etc.)
   :type step_type: StepType
   :param status: Execution status of the step (indexed)
   :type status: StepStatus
   :param input_data: Input data passed to the step
   :type input_data: dict[str, Any] | None
   :param output_data: Output data produced by the step
   :type output_data: dict[str, Any] | None
   :param error: Error message if step failed
   :type error: str | None
   :param started_at: Timestamp when step execution began
   :type started_at: datetime
   :param completed_at: Timestamp when step execution finished
   :type completed_at: datetime | None
   :param assigned_to: User ID assigned to human tasks
   :type assigned_to: str | None
   :param completed_by: User ID who completed human tasks
   :type completed_by: str | None


.. py:class:: HumanTaskModel

   SQLAlchemy model for pending human tasks.

   Provides a denormalized view of pending human approval tasks for
   efficient querying by assignee, due date, and status.

   :param instance_id: Foreign key to the workflow instance
   :type instance_id: UUID
   :param step_execution_id: Foreign key to the step execution
   :type step_execution_id: UUID
   :param step_name: Name of the human task step
   :type step_name: str
   :param title: Display title for the task
   :type title: str
   :param description: Detailed description of the task
   :type description: str | None
   :param form_schema: JSON Schema defining the task form
   :type form_schema: dict[str, Any] | None
   :param assignee_id: User ID assigned to complete the task (indexed)
   :type assignee_id: str | None
   :param assignee_group: Group/role that can complete the task (indexed)
   :type assignee_group: str | None
   :param due_at: Deadline for task completion (indexed)
   :type due_at: datetime | None
   :param reminder_at: When to send a reminder
   :type reminder_at: datetime | None
   :param status: Current task status (pending, completed, canceled)
   :type status: str
   :param completed_at: When the task was completed
   :type completed_at: datetime | None
   :param completed_by: User who completed the task
   :type completed_by: str | None


Repository Classes
~~~~~~~~~~~~~~~~~~

.. py:class:: WorkflowDefinitionRepository

   Repository for workflow definition CRUD operations.

   :param session: SQLAlchemy async session
   :type session: AsyncSession

   .. py:method:: get_by_name(name, version=None, *, active_only=True) -> WorkflowDefinitionModel | None
      :async:

      Get a workflow definition by name and optional version.

      :param name: The workflow name
      :param version: Optional specific version. If None, returns the latest active version.
      :param active_only: If True, only return active definitions
      :returns: The workflow definition or None

   .. py:method:: get_latest_version(name) -> WorkflowDefinitionModel | None
      :async:

      Get the latest active version of a workflow definition.

   .. py:method:: list_active() -> Sequence[WorkflowDefinitionModel]
      :async:

      List all active workflow definitions.

   .. py:method:: deactivate_version(name, version) -> bool
      :async:

      Deactivate a specific workflow version.


.. py:class:: WorkflowInstanceRepository

   Repository for workflow instance CRUD operations.

   :param session: SQLAlchemy async session
   :type session: AsyncSession

   .. py:method:: find_by_workflow(workflow_name, status=None, limit=100, offset=0) -> tuple[Sequence[WorkflowInstanceModel], int]
      :async:

      Find instances by workflow name with optional status filter.

      :returns: Tuple of (instances, total_count)

   .. py:method:: find_by_user(user_id, status=None) -> Sequence[WorkflowInstanceModel]
      :async:

      Find instances created by a specific user.

   .. py:method:: find_by_tenant(tenant_id, status=None, limit=100, offset=0) -> tuple[Sequence[WorkflowInstanceModel], int]
      :async:

      Find instances by tenant ID for multi-tenancy support.

   .. py:method:: find_running() -> Sequence[WorkflowInstanceModel]
      :async:

      Find all running or waiting workflow instances.

   .. py:method:: update_status(instance_id, status, *, current_step=None, error=None) -> WorkflowInstanceModel | None
      :async:

      Update the status of a workflow instance.


.. py:class:: StepExecutionRepository

   Repository for step execution record CRUD operations.

   :param session: SQLAlchemy async session
   :type session: AsyncSession

   .. py:method:: find_by_instance(instance_id) -> Sequence[StepExecutionModel]
      :async:

      Find all step executions for an instance, ordered by start time.

   .. py:method:: find_by_step_name(instance_id, step_name) -> StepExecutionModel | None
      :async:

      Find the most recent execution record for a specific step.

   .. py:method:: find_failed(instance_id=None) -> Sequence[StepExecutionModel]
      :async:

      Find failed step executions, optionally filtered by instance.


.. py:class:: HumanTaskRepository

   Repository for human task CRUD operations.

   :param session: SQLAlchemy async session
   :type session: AsyncSession

   .. py:method:: find_pending(assignee_id=None, assignee_group=None) -> Sequence[HumanTaskModel]
      :async:

      Find pending human tasks, optionally filtered by assignee or group.

      :param assignee_id: If provided, includes tasks assigned to this user or unassigned
      :param assignee_group: If provided, includes tasks for this group or unassigned

   .. py:method:: find_by_instance(instance_id) -> Sequence[HumanTaskModel]
      :async:

      Find all human tasks for an instance.

   .. py:method:: find_overdue() -> Sequence[HumanTaskModel]
      :async:

      Find overdue pending human tasks (due_at < now).

   .. py:method:: complete_task(task_id, completed_by) -> HumanTaskModel | None
      :async:

      Mark a human task as completed.

      :param task_id: The task ID
      :param completed_by: User ID who completed the task

   .. py:method:: cancel_task(task_id) -> HumanTaskModel | None
      :async:

      Cancel a pending human task


Web Plugin (Optional)
---------------------

Available with the ``[web]`` extra.

.. py:class:: WorkflowWebPlugin

   Litestar plugin for workflow web routes.

   :param path_prefix: URL prefix for workflow routes (default: "/workflows")
   :param enable_admin: Enable admin API routes
   :param enable_api: Enable REST API routes
   :param enable_ui: Enable web UI routes
   :param auth_guard: Guard class for authentication
   :param admin_guard: Guard class for admin routes

   **Example:**

   .. code-block:: python

      from litestar import Litestar
      from litestar_workflows.web import WorkflowWebPlugin

      app = Litestar(
          plugins=[
              WorkflowWebPlugin(
                  path_prefix="/api/workflows",
                  enable_admin=True,
              )
          ]
      )


Full Module Reference
---------------------

.. toctree::
   :maxdepth: 2

   modules


See Also
--------

- :doc:`/concepts/index` - Core concepts explained
- :doc:`/guides/index` - Practical how-to guides
