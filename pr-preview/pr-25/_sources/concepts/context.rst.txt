Workflow Context
================

The **WorkflowContext** is the shared state that flows through a workflow.
It carries data between steps, tracks execution history, and provides
identity information.


What is WorkflowContext?
------------------------

Think of the context as a shared workspace that all steps can read from
and write to:

.. code-block:: text

   Step A           Step B           Step C
     |                |                |
     +------> Context <-------+--------+
              |  data        |
              |  metadata    |
              |  history     |


The context holds:

- **data**: Mutable dictionary of workflow state
- **metadata**: Immutable information set at creation
- **identity**: Workflow and instance IDs
- **history**: Record of executed steps


Basic Usage
-----------

Steps interact with context through simple get/set operations:

.. code-block:: python

   from litestar_workflows import BaseMachineStep, WorkflowContext

   class ProcessOrder(BaseMachineStep):
       name = "process_order"

       async def execute(self, context: WorkflowContext) -> None:
           # Read values
           order_id = context.get("order_id")
           items = context.get("items", [])  # With default

           # Process the order
           total = sum(item["price"] for item in items)
           tax = total * 0.08

           # Write values
           context.set("subtotal", total)
           context.set("tax", tax)
           context.set("total", total + tax)


Context Properties
------------------

The ``WorkflowContext`` provides access to:


Identity
~~~~~~~~

.. code-block:: python

   context.workflow_id   # UUID of the workflow definition
   context.instance_id   # UUID of this specific execution


Data Access
~~~~~~~~~~~

.. code-block:: python

   # Get a value with optional default
   value = context.get("key", default=None)

   # Set a value
   context.set("key", value)

   # Access the full data dictionary
   all_data = context.data

   # Check if key exists
   if "key" in context.data:
       ...


Metadata
~~~~~~~~

Metadata is set when the workflow starts and cannot be modified:

.. code-block:: python

   # Set during workflow start
   instance = await engine.start_workflow(
       "my_workflow",
       initial_data={"order_id": "123"},
       metadata={
           "triggered_by": "api",
           "source_system": "web_app",
           "correlation_id": "abc-123",
       }
   )

   # Access in steps (read-only)
   source = context.metadata.get("source_system")


User Context
~~~~~~~~~~~~

For human tasks and audit trails:

.. code-block:: python

   context.user_id     # Current user (for human tasks)
   context.tenant_id   # Multi-tenancy support


Execution Info
~~~~~~~~~~~~~~

.. code-block:: python

   context.current_step   # Name of the currently executing step
   context.started_at     # When the workflow instance started
   context.step_history   # List of completed step executions


Step History
------------

The context maintains a complete history of step executions:

.. code-block:: python

   for execution in context.step_history:
       print(f"Step: {execution.step_name}")
       print(f"Status: {execution.status}")
       print(f"Started: {execution.started_at}")
       print(f"Completed: {execution.completed_at}")
       print(f"Result: {execution.result}")

This is useful for:

- Debugging workflow execution
- Building audit trails
- Conditional logic based on past steps


Data Patterns
-------------


Passing Data Between Steps
~~~~~~~~~~~~~~~~~~~~~~~~~~

Steps communicate by reading and writing context data:

.. code-block:: python

   class StepA(BaseMachineStep):
       async def execute(self, context: WorkflowContext) -> None:
           result = await process_something()
           context.set("step_a_result", result)

   class StepB(BaseMachineStep):
       async def execute(self, context: WorkflowContext) -> None:
           # Read data from previous step
           previous_result = context.get("step_a_result")
           final_result = await process_more(previous_result)
           context.set("step_b_result", final_result)


Structured Data
~~~~~~~~~~~~~~~

Store complex objects as nested dictionaries:

.. code-block:: python

   # Store structured data
   context.set("customer", {
       "id": "cust-123",
       "name": "Alice Smith",
       "tier": "premium",
       "preferences": {
           "notifications": True,
           "format": "html",
       }
   })

   # Access nested values
   customer = context.get("customer", {})
   tier = customer.get("tier")


Accumulating Results
~~~~~~~~~~~~~~~~~~~~

Build up results across multiple steps:

.. code-block:: python

   class ValidationStep(BaseMachineStep):
       async def execute(self, context: WorkflowContext) -> None:
           errors = context.get("errors", [])

           if not context.get("name"):
               errors.append("Name is required")
           if context.get("age", 0) < 18:
               errors.append("Must be 18 or older")

           context.set("errors", errors)
           context.set("is_valid", len(errors) == 0)


Typed Access
------------

For better type safety, define typed accessors:

.. code-block:: python

   from dataclasses import dataclass
   from typing import TypeVar

   @dataclass
   class OrderData:
       order_id: str
       items: list[dict]
       total: float = 0.0

   class OrderContext:
       """Type-safe wrapper around WorkflowContext."""

       def __init__(self, context: WorkflowContext):
           self._context = context

       @property
       def order(self) -> OrderData:
           data = self._context.get("order", {})
           return OrderData(**data)

       @order.setter
       def order(self, value: OrderData) -> None:
           self._context.set("order", {
               "order_id": value.order_id,
               "items": value.items,
               "total": value.total,
           })

   # Use in steps
   class ProcessOrder(BaseMachineStep):
       async def execute(self, context: WorkflowContext) -> None:
           order_ctx = OrderContext(context)
           order = order_ctx.order

           order.total = sum(item["price"] for item in order.items)
           order_ctx.order = order


Context Isolation
-----------------

Each workflow instance has its own isolated context:

.. code-block:: python

   # Instance 1
   instance1 = await engine.start_workflow("order", {"order_id": "001"})

   # Instance 2 - completely separate context
   instance2 = await engine.start_workflow("order", {"order_id": "002"})

   # Changes to instance1 don't affect instance2


Within a workflow, all steps share the same context. This is intentional
for communication, but be mindful of naming collisions in complex workflows.


Best Practices
--------------


Use Meaningful Keys
~~~~~~~~~~~~~~~~~~~

Choose clear, descriptive key names:

.. code-block:: python

   # Good - clear purpose
   context.set("approved_by", "alice@example.com")
   context.set("approval_timestamp", datetime.now())
   context.set("requires_second_approval", True)

   # Avoid - unclear or too generic
   context.set("flag", True)
   context.set("data", result)
   context.set("x", value)


Namespace Related Data
~~~~~~~~~~~~~~~~~~~~~~

Group related data under common prefixes:

.. code-block:: python

   # Group approval-related data
   context.set("approval.status", "pending")
   context.set("approval.reviewer", "bob@example.com")
   context.set("approval.comments", "Looks good")

   # Or use nested dictionaries
   context.set("approval", {
       "status": "pending",
       "reviewer": "bob@example.com",
       "comments": "Looks good",
   })


Provide Defaults
~~~~~~~~~~~~~~~~

Always use defaults when reading optional values:

.. code-block:: python

   # Good - safe with default
   retries = context.get("retry_count", 0)
   items = context.get("items", [])
   config = context.get("config", {})

   # Risky - might be None
   retries = context.get("retry_count")  # Could be None!


Don't Store Secrets
~~~~~~~~~~~~~~~~~~~

Never store sensitive data directly in context:

.. code-block:: python

   # Bad - secret in context
   context.set("api_key", "sk-xxx")
   context.set("password", "secret123")

   # Good - reference to secrets manager
   context.set("api_key_reference", "vault/path/to/key")

Context data may be persisted, logged, or exposed through APIs.


Serialization
-------------

Context data is serialized for persistence. Ensure your data is JSON-serializable:

.. code-block:: python

   # Good - serializable types
   context.set("timestamp", datetime.now().isoformat())  # String
   context.set("amount", 123.45)                          # Number
   context.set("items", [{"id": 1}, {"id": 2}])          # List of dicts

   # Bad - not JSON serializable
   context.set("timestamp", datetime.now())  # datetime object
   context.set("user", User(id=1))           # Custom object

If you need to store complex objects, serialize them first:

.. code-block:: python

   import json

   # Serialize custom objects
   context.set("config", json.dumps(config_object.to_dict()))

   # Or use dataclasses with asdict
   from dataclasses import asdict
   context.set("order", asdict(order))


See Also
--------

- :doc:`steps` - How steps use context
- :doc:`execution` - Context during execution
- :doc:`/guides/simple-workflow` - Practical context usage
