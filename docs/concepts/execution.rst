Execution
=========

The **execution engine** is responsible for running workflow instances.
It schedules steps, manages state transitions, and handles both automated
and human-driven execution.


Execution Engines
-----------------

litestar-workflows provides multiple execution engine implementations:

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Engine
     - Description
   * - ``LocalExecutionEngine``
     - In-process async execution (default)
   * - ``CeleryExecutionEngine``
     - Distributed via Celery (optional extra)
   * - ``SAQExecutionEngine``
     - Redis-backed async queues (optional extra)


The Local Engine
----------------

The ``LocalExecutionEngine`` runs workflows in the current process:

.. code-block:: python

   from litestar_workflows import LocalExecutionEngine, WorkflowRegistry

   # Create registry with workflow definitions
   registry = WorkflowRegistry()
   registry.register_definition(my_workflow)

   # Create engine
   engine = LocalExecutionEngine(registry)

   # Start a workflow
   instance = await engine.start_workflow(
       "my_workflow",
       initial_data={"key": "value"}
   )


Engine Configuration
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   engine = LocalExecutionEngine(
       registry=registry,
       persistence=database_repository,  # Optional: persist state
       event_bus=event_bus,              # Optional: emit events
   )


Execution Flow
--------------

Here's how the engine executes a workflow:

.. code-block:: text

   1. Start Workflow
      |
      v
   2. Create Instance + Context
      |
      v
   3. Begin at initial_step
      |
      v
   +---> 4. Check step type
   |        |
   |        +-- MACHINE: Execute immediately
   |        |             |
   |        |             v
   |        |          on_success/on_failure
   |        |
   |        +-- HUMAN: Create task, PAUSE
   |        |          Wait for completion...
   |        |
   |        +-- GATEWAY: Evaluate condition
   |        |
   |        +-- TIMER: Schedule future execution
   |
   5. Find next step(s) via edges
      |
      +-- Has next: Return to step 4
      |
      +-- No next (terminal): Complete workflow


Starting Workflows
------------------

.. code-block:: python

   # Basic start
   instance = await engine.start_workflow("workflow_name")

   # With initial data
   instance = await engine.start_workflow(
       "workflow_name",
       initial_data={
           "customer_id": "cust-123",
           "amount": 500.00,
       }
   )

   # With specific version
   instance = await engine.start_workflow(
       "workflow_name",
       version="2.0.0",
       initial_data={...}
   )

The returned instance contains:

.. code-block:: python

   instance.id           # Unique instance identifier
   instance.status       # Current status (RUNNING, WAITING, etc.)
   instance.current_step # Name of current step
   instance.context      # WorkflowContext with data


Human Task Completion
---------------------

When a workflow reaches a human step, it pauses and waits for input:

.. code-block:: python

   # Workflow is now WAITING at "manager_approval"
   assert instance.status == WorkflowStatus.WAITING
   assert instance.current_step == "manager_approval"

   # Complete the human task
   await engine.complete_human_task(
       instance_id=instance.id,
       step_name="manager_approval",
       user_id="manager@example.com",
       data={
           "approved": True,
           "comments": "Approved for Q4 budget",
       }
   )

   # Workflow continues execution


Cancellation
------------

Cancel a running or waiting workflow:

.. code-block:: python

   await engine.cancel_workflow(
       instance_id=instance.id,
       reason="Customer requested cancellation"
   )

   # Instance is now CANCELED
   assert instance.status == WorkflowStatus.CANCELED


Retry Failed Workflows
----------------------

Retry a failed workflow from a specific step:

.. code-block:: python

   # Workflow failed at "process_payment"
   assert instance.status == WorkflowStatus.FAILED

   # Retry from the failed step
   await engine.retry(
       instance_id=instance.id,
       from_step="process_payment"  # Optional: defaults to failed step
   )


Parallel Execution
------------------

When a step has multiple outgoing edges without conditions, they execute
in parallel:

.. code-block:: python

   definition = WorkflowDefinition(
       steps={
           "start": StartStep(),
           "notify_email": NotifyEmail(),
           "notify_slack": NotifySlack(),
           "notify_sms": NotifySMS(),
           "complete": CompleteStep(),
       },
       edges=[
           Edge("start", "notify_email"),
           Edge("start", "notify_slack"),
           Edge("start", "notify_sms"),
           Edge("notify_email", "complete"),
           Edge("notify_slack", "complete"),
           Edge("notify_sms", "complete"),
       ],
       ...
   )

The engine will:

1. Execute ``start``
2. Execute ``notify_email``, ``notify_slack``, ``notify_sms`` in parallel
3. Wait for all three to complete
4. Execute ``complete``


Conditional Execution
---------------------

Edge conditions control which paths are taken:

.. code-block:: python

   edges = [
       Edge("review", "approve", condition="context.get('score') >= 80"),
       Edge("review", "reject", condition="context.get('score') < 80"),
   ]

The engine evaluates conditions and follows matching edges.


Event Emission
--------------

Configure an event bus to receive workflow events:

.. code-block:: python

   from litestar_workflows import EventBus

   class MyEventBus(EventBus):
       async def emit(self, event):
           print(f"Event: {event}")
           await event_store.save(event)

   engine = LocalExecutionEngine(
       registry=registry,
       event_bus=MyEventBus()
   )

Events include:

- ``WorkflowStarted``
- ``WorkflowCompleted``
- ``WorkflowFailed``
- ``WorkflowCanceled``
- ``StepExecuted``
- ``HumanTaskCreated``
- ``HumanTaskCompleted``


Persistence
-----------

For durable workflows, configure a persistence layer:

.. code-block:: python

   from litestar_workflows.db import WorkflowInstanceRepository

   # With SQLAlchemy persistence
   engine = LocalExecutionEngine(
       registry=registry,
       persistence=WorkflowInstanceRepository(session),
   )

With persistence:

- Workflow state survives restarts
- Human tasks can be queried
- Execution history is preserved
- Workflows can be resumed after failures


Distributed Execution
---------------------

For production workloads, use a distributed engine:


Celery Engine
~~~~~~~~~~~~~

.. code-block:: python

   from celery import Celery
   from litestar_workflows.contrib.celery import CeleryExecutionEngine

   celery_app = Celery("workflows", broker="redis://localhost:6379/0")

   engine = CeleryExecutionEngine(
       celery_app=celery_app,
       persistence=persistence,
   )

   # Steps are executed as Celery tasks
   instance = await engine.start_workflow("my_workflow")


SAQ Engine
~~~~~~~~~~

.. code-block:: python

   from saq import Queue
   from litestar_workflows.contrib.saq import SAQExecutionEngine

   queue = Queue.from_url("redis://localhost:6379/0")

   engine = SAQExecutionEngine(
       queue=queue,
       persistence=persistence,
   )


Execution Guarantees
--------------------

The execution engine provides these guarantees:


At-Least-Once Execution
~~~~~~~~~~~~~~~~~~~~~~~

Steps are guaranteed to execute at least once. With persistence, failed
workflows can be retried:

.. code-block:: python

   # Step might run multiple times in retry scenarios
   class IdempotentStep(BaseMachineStep):
       async def execute(self, context):
           # Make operations idempotent
           if not await payment_exists(context.get("payment_id")):
               await create_payment(...)


Order Preservation
~~~~~~~~~~~~~~~~~~

Steps execute in the order defined by edges. Parallel steps may complete
in any order, but the next step waits for all to finish.


Error Isolation
~~~~~~~~~~~~~~~

A failing step doesn't corrupt the workflow state. The context is preserved
at the point of failure for debugging and retry.


Workflow Registry
-----------------

The ``WorkflowRegistry`` manages workflow definitions:

.. code-block:: python

   from litestar_workflows import WorkflowRegistry

   registry = WorkflowRegistry()

   # Register definitions
   registry.register_definition(workflow_v1)
   registry.register_definition(workflow_v2)

   # Get definition
   definition = registry.get_definition("my_workflow")
   definition = registry.get_definition("my_workflow", version="1.0.0")

   # List all definitions
   all_workflows = registry.list_definitions()

   # Check if workflow exists
   if registry.has_definition("my_workflow"):
       ...


Best Practices
--------------


Use Persistence in Production
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Always configure persistence for production workloads:

.. code-block:: python

   # Development - in-memory is fine
   engine = LocalExecutionEngine(registry)

   # Production - use persistence
   engine = LocalExecutionEngine(
       registry=registry,
       persistence=database_persistence,
   )


Make Steps Idempotent
~~~~~~~~~~~~~~~~~~~~~

Design steps to be safely re-executed:

.. code-block:: python

   class CreateOrder(BaseMachineStep):
       async def execute(self, context):
           order_id = context.get("order_id")

           # Check if already created
           existing = await orders.get(order_id)
           if existing:
               context.set("order", existing)
               return

           # Create new order
           order = await orders.create(order_id, ...)
           context.set("order", order)


Handle Timeouts
~~~~~~~~~~~~~~~

Long-running steps should handle timeouts gracefully:

.. code-block:: python

   import asyncio

   class LongRunningStep(BaseMachineStep):
       async def execute(self, context):
           try:
               result = await asyncio.wait_for(
                   slow_operation(),
                   timeout=300.0  # 5 minutes
               )
               context.set("result", result)
           except asyncio.TimeoutError:
               context.set("timeout", True)
               raise


Monitor Execution
~~~~~~~~~~~~~~~~~

Use events to track workflow execution:

.. code-block:: python

   class MonitoringEventBus(EventBus):
       async def emit(self, event):
           # Record metrics
           metrics.increment(f"workflow.{event.type}")

           # Log for debugging
           logger.info(f"Workflow event: {event}")

           # Alert on failures
           if event.type == "WorkflowFailed":
               await alerting.notify(f"Workflow failed: {event.instance_id}")


See Also
--------

- :doc:`workflows` - Workflow definitions
- :doc:`steps` - Step types and lifecycle
- :doc:`/guides/parallel-execution` - Parallel execution patterns
