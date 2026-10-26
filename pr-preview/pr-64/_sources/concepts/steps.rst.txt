Steps
=====

**Steps** are the building blocks of workflows. Each step represents a single
unit of work, whether automated or requiring human interaction.


Step Types
----------

litestar-workflows provides five step types, each designed for specific use cases:

.. list-table::
   :widths: 15 25 60
   :header-rows: 1

   * - Type
     - Class
     - Purpose
   * - MACHINE
     - ``BaseMachineStep``
     - Automated execution without human intervention
   * - HUMAN
     - ``BaseHumanStep``
     - Requires user interaction (forms, approvals)
   * - GATEWAY
     - ``BaseGateway``
     - Decision points for conditional branching
   * - TIMER
     - ``TimerStep``
     - Delays or scheduled execution
   * - WEBHOOK
     - ``WebhookStep``
     - Waits for external callbacks


Machine Steps
-------------

Machine steps execute automatically when reached. They're used for:

- Data processing
- API calls
- Calculations
- Notifications
- File operations

.. code-block:: python

   from litestar_workflows import BaseMachineStep, WorkflowContext

   class SendNotification(BaseMachineStep):
       """Send an email notification."""

       name = "send_notification"
       description = "Notify stakeholders of the request"

       async def execute(self, context: WorkflowContext) -> None:
           recipient = context.get("requester_email")
           status = context.get("status")

           await email_service.send(
               to=recipient,
               subject=f"Request {status}",
               body=f"Your request has been {status}.",
           )

           context.set("notification_sent", True)


Machine Step Lifecycle
~~~~~~~~~~~~~~~~~~~~~~

1. **can_execute**: Check if the step should run (guards)
2. **execute**: Perform the actual work
3. **on_success**: Called after successful execution
4. **on_failure**: Called if execution raises an exception

.. code-block:: python

   class RobustStep(BaseMachineStep):
       name = "robust_step"

       async def can_execute(self, context: WorkflowContext) -> bool:
           """Only run if prerequisites are met."""
           return context.get("prerequisites_met", False)

       async def execute(self, context: WorkflowContext) -> None:
           """Main logic."""
           result = await do_work()
           context.set("result", result)

       async def on_success(self, context: WorkflowContext, result: None) -> None:
           """Log success metrics."""
           await metrics.record("step_completed", tags={"step": self.name})

       async def on_failure(self, context: WorkflowContext, error: Exception) -> None:
           """Handle failures gracefully."""
           await alerting.notify(f"Step failed: {error}")
           context.set("error", str(error))


Human Steps
-----------

Human steps pause execution and wait for user input. They're used for:

- Approvals and rejections
- Form submissions
- Manual data entry
- Decision points requiring human judgment

.. code-block:: python

   from litestar_workflows import BaseHumanStep

   class DocumentReview(BaseHumanStep):
       """Human reviews and approves a document."""

       name = "document_review"
       title = "Review Document"
       description = "Please review this document and provide your decision"

       form_schema = {
           "type": "object",
           "properties": {
               "decision": {
                   "type": "string",
                   "title": "Your Decision",
                   "enum": ["approve", "reject", "revise"],
                   "enumNames": ["Approve", "Reject", "Request Revisions"],
               },
               "feedback": {
                   "type": "string",
                   "title": "Feedback",
                   "description": "Comments for the author",
               },
               "priority": {
                   "type": "integer",
                   "title": "Priority Score",
                   "minimum": 1,
                   "maximum": 5,
               },
           },
           "required": ["decision"],
       }


Form Schema
~~~~~~~~~~~

Human steps use `JSON Schema <https://json-schema.org/>`_ to define their forms.
This enables:

- Automatic form generation in the UI
- Input validation
- Type safety

Common schema patterns:

.. code-block:: python

   # Boolean approval
   form_schema = {
       "type": "object",
       "properties": {
           "approved": {"type": "boolean", "title": "Approve?", "default": False},
       },
       "required": ["approved"],
   }

   # Selection from options
   form_schema = {
       "type": "object",
       "properties": {
           "status": {
               "type": "string",
               "enum": ["pending", "active", "completed"],
               "default": "pending",
           },
       },
   }

   # Numeric input with constraints
   form_schema = {
       "type": "object",
       "properties": {
           "amount": {
               "type": "number",
               "minimum": 0,
               "maximum": 10000,
               "title": "Adjustment Amount",
           },
       },
   }


Task Assignment
~~~~~~~~~~~~~~~

Human tasks can be assigned to specific users or groups:

.. code-block:: python

   class ManagerApproval(BaseHumanStep):
       name = "manager_approval"
       title = "Manager Approval Required"

       # Assignment can be dynamic based on context
       async def get_assignee(self, context: WorkflowContext) -> str:
           department = context.get("department")
           return await org_chart.get_manager(department)


Gateway Steps
-------------

Gateways are decision points that route execution based on conditions:

.. code-block:: python

   from litestar_workflows import BaseGateway, WorkflowContext

   class AmountGateway(BaseGateway):
       """Route based on request amount."""

       name = "amount_gateway"
       description = "Determine approval path based on amount"

       async def evaluate(self, context: WorkflowContext) -> str:
           """Return the name of the next step."""
           amount = context.get("amount", 0)

           if amount > 10000:
               return "vp_approval"
           elif amount > 1000:
               return "manager_approval"
           else:
               return "auto_approve"

Gateways connect to multiple outgoing edges, and the ``evaluate`` method
determines which path to take.


Timer Steps
-----------

Timer steps introduce delays or schedule execution for later:

.. code-block:: python

   from litestar_workflows import TimerStep
   from datetime import timedelta

   class WaitForBusinessHours(TimerStep):
       """Wait until next business day if outside hours."""

       name = "wait_for_business_hours"

       async def get_delay(self, context: WorkflowContext) -> timedelta:
           now = datetime.now()
           if is_business_hours(now):
               return timedelta(0)  # No delay
           return get_next_business_day() - now


Webhook Steps
-------------

Webhook steps wait for external systems to call back:

.. code-block:: python

   from litestar_workflows import WebhookStep

   class PaymentCallback(WebhookStep):
       """Wait for payment processor callback."""

       name = "payment_callback"
       description = "Waiting for payment confirmation"

       # Unique token for this webhook
       async def get_callback_token(self, context: WorkflowContext) -> str:
           return f"payment-{context.instance_id}"

The workflow pauses until an external system calls the webhook endpoint
with the matching token.


Step Groups
-----------

Steps can be composed into groups for more complex patterns:


Sequential Group
~~~~~~~~~~~~~~~~

Execute steps one after another:

.. code-block:: python

   from litestar_workflows import SequentialGroup

   validation_sequence = SequentialGroup(
       ValidateFormat(),
       ValidateContent(),
       ValidatePermissions(),
   )

   # Use in workflow definition
   steps = {
       "validation": validation_sequence,
       ...
   }


Parallel Group
~~~~~~~~~~~~~~

Execute steps simultaneously:

.. code-block:: python

   from litestar_workflows import ParallelGroup

   parallel_notifications = ParallelGroup(
       SendEmail(),
       SendSlack(),
       SendSMS(),
   )

All steps in the group run concurrently, and execution continues when all
complete.


Parallel with Callback (Chord)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute steps in parallel, then run a callback with all results:

.. code-block:: python

   from litestar_workflows import ParallelGroup

   gather_approvals = ParallelGroup(
       ManagerApproval(),
       LegalReview(),
       FinanceReview(),
       callback=AggregateDecisions(),  # Runs after all complete
   )


Creating Custom Steps
---------------------

While the base classes cover most use cases, you can create custom step types:

.. code-block:: python

   from litestar_workflows import Step, StepType

   class BatchProcessingStep(Step):
       """Custom step for batch operations."""

       name: str
       step_type = StepType.MACHINE
       batch_size: int = 100

       async def execute(self, context: WorkflowContext) -> None:
           items = context.get("items", [])

           for i in range(0, len(items), self.batch_size):
               batch = items[i:i + self.batch_size]
               await self.process_batch(batch)

           context.set("processed_count", len(items))

       async def process_batch(self, batch: list) -> None:
           """Override in subclasses."""
           raise NotImplementedError


Best Practices
--------------


Keep Steps Focused
~~~~~~~~~~~~~~~~~~

Each step should do one thing well:

.. code-block:: python

   # Good - single responsibility
   class ValidateInput(BaseMachineStep):
       async def execute(self, context):
           validate(context.get("input"))

   class TransformData(BaseMachineStep):
       async def execute(self, context):
           context.set("output", transform(context.get("input")))

   # Avoid - doing too much
   class DoEverything(BaseMachineStep):
       async def execute(self, context):
           validate(context.get("input"))
           result = transform(context.get("input"))
           await save_to_database(result)
           await send_notification(result)


Make Steps Reusable
~~~~~~~~~~~~~~~~~~~

Design steps to be configurable and reusable across workflows:

.. code-block:: python

   class SendEmail(BaseMachineStep):
       """Reusable email step."""

       name = "send_email"

       def __init__(self, template: str, recipient_key: str = "email"):
           self.template = template
           self.recipient_key = recipient_key

       async def execute(self, context: WorkflowContext) -> None:
           recipient = context.get(self.recipient_key)
           await email_service.send(recipient, template=self.template)

   # Use with different configurations
   steps = {
       "notify_requester": SendEmail("request_received", "requester_email"),
       "notify_manager": SendEmail("approval_needed", "manager_email"),
   }


Handle Errors Gracefully
~~~~~~~~~~~~~~~~~~~~~~~~

Use ``on_failure`` to handle errors without crashing the workflow:

.. code-block:: python

   class ResilientStep(BaseMachineStep):
       async def execute(self, context: WorkflowContext) -> None:
           # Main logic that might fail
           result = await risky_operation()
           context.set("result", result)

       async def on_failure(self, context: WorkflowContext, error: Exception) -> None:
           # Log the error
           logger.error(f"Step failed: {error}")

           # Set fallback values
           context.set("result", None)
           context.set("error", str(error))

           # Optionally, don't re-raise to allow workflow to continue
           # raise  # Re-raise to fail the workflow


See Also
--------

- :doc:`context` - How steps share data
- :doc:`execution` - How steps are executed
- :doc:`/guides/human-tasks` - Deep dive into human tasks
