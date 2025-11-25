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

Available with the ``[db]`` extra.

.. py:class:: WorkflowDefinitionModel

   SQLAlchemy model for persisted workflow definitions.


.. py:class:: WorkflowInstanceModel

   SQLAlchemy model for workflow instances.


.. py:class:: StepExecutionModel

   SQLAlchemy model for step execution records.


.. py:class:: HumanTaskModel

   SQLAlchemy model for pending human tasks.


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
