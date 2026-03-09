Parallel Execution
==================

This guide covers executing multiple steps simultaneously. You'll learn
how to run steps in parallel, wait for all to complete, and use the
chord pattern for aggregating results.


Goal
----

Execute multiple independent steps at the same time to improve throughput
and reduce total workflow duration.


When to Use Parallel Execution
------------------------------

Parallel execution is ideal for:

- **Notifications**: Send email, Slack, and SMS simultaneously
- **Multi-party approvals**: Request approval from multiple stakeholders
- **Data fetching**: Retrieve data from multiple sources
- **Validation**: Run independent validation checks


Basic Parallel Pattern
----------------------

Create parallel branches by defining multiple edges from one step:

.. code-block:: python

   from litestar_workflows import WorkflowDefinition, Edge, BaseMachineStep

   # Steps that will run in parallel
   class SendEmail(BaseMachineStep):
       name = "send_email"

       async def execute(self, context):
           await email_service.send(...)
           context.set("email_sent", True)


   class SendSlack(BaseMachineStep):
       name = "send_slack"

       async def execute(self, context):
           await slack_service.send(...)
           context.set("slack_sent", True)


   class SendSMS(BaseMachineStep):
       name = "send_sms"

       async def execute(self, context):
           await sms_service.send(...)
           context.set("sms_sent", True)


   # Define parallel edges
   notification_workflow = WorkflowDefinition(
       name="parallel_notify",
       steps={
           "process": ProcessStep(),
           "send_email": SendEmail(),
           "send_slack": SendSlack(),
           "send_sms": SendSMS(),
           "complete": CompleteStep(),
       },
       edges=[
           # Fork: one step to many
           Edge("process", "send_email"),
           Edge("process", "send_slack"),
           Edge("process", "send_sms"),
           # Join: many steps to one
           Edge("send_email", "complete"),
           Edge("send_slack", "complete"),
           Edge("send_sms", "complete"),
       ],
       initial_step="process",
       terminal_steps={"complete"},
   )

The engine will:

1. Execute ``process``
2. Start ``send_email``, ``send_slack``, ``send_sms`` simultaneously
3. Wait for all three to complete
4. Execute ``complete``


Using ParallelGroup
-------------------

For cleaner code, use ``ParallelGroup``:

.. code-block:: python

   from litestar_workflows import ParallelGroup

   # Define the parallel group
   notification_group = ParallelGroup(
       SendEmail(),
       SendSlack(),
       SendSMS(),
   )

   # Use in workflow definition
   workflow = WorkflowDefinition(
       name="parallel_notify",
       steps={
           "process": ProcessStep(),
           "notify": notification_group,
           "complete": CompleteStep(),
       },
       edges=[
           Edge("process", "notify"),
           Edge("notify", "complete"),
       ],
       initial_step="process",
       terminal_steps={"complete"},
   )


Chord Pattern: Parallel with Callback
-------------------------------------

Use a callback to aggregate results from parallel steps:

.. code-block:: python

   from litestar_workflows import ParallelGroup, BaseMachineStep


   class FetchFromAPI1(BaseMachineStep):
       name = "fetch_api1"

       async def execute(self, context):
           data = await api1.fetch()
           context.set("api1_data", data)


   class FetchFromAPI2(BaseMachineStep):
       name = "fetch_api2"

       async def execute(self, context):
           data = await api2.fetch()
           context.set("api2_data", data)


   class FetchFromAPI3(BaseMachineStep):
       name = "fetch_api3"

       async def execute(self, context):
           data = await api3.fetch()
           context.set("api3_data", data)


   class AggregateResults(BaseMachineStep):
       name = "aggregate"

       async def execute(self, context):
           # Combine all fetched data
           combined = {
               "api1": context.get("api1_data"),
               "api2": context.get("api2_data"),
               "api3": context.get("api3_data"),
           }
           context.set("combined_data", combined)


   # Create chord: parallel steps + callback
   data_fetch_group = ParallelGroup(
       FetchFromAPI1(),
       FetchFromAPI2(),
       FetchFromAPI3(),
       callback=AggregateResults(),  # Runs after all complete
   )


Parallel Human Tasks
--------------------

Request approval from multiple stakeholders simultaneously:

.. code-block:: python

   from litestar_workflows import BaseHumanStep, ParallelGroup


   class LegalApproval(BaseHumanStep):
       name = "legal_approval"
       title = "Legal Review Required"
       form_schema = {
           "type": "object",
           "properties": {
               "approved": {"type": "boolean", "title": "Legal Approved?"},
               "concerns": {"type": "string", "title": "Legal Concerns"},
           },
           "required": ["approved"],
       }


   class FinanceApproval(BaseHumanStep):
       name = "finance_approval"
       title = "Finance Review Required"
       form_schema = {
           "type": "object",
           "properties": {
               "approved": {"type": "boolean", "title": "Finance Approved?"},
               "budget_code": {"type": "string", "title": "Budget Code"},
           },
           "required": ["approved"],
       }


   class SecurityApproval(BaseHumanStep):
       name = "security_approval"
       title = "Security Review Required"
       form_schema = {
           "type": "object",
           "properties": {
               "approved": {"type": "boolean", "title": "Security Approved?"},
               "risk_level": {
                   "type": "string",
                   "enum": ["low", "medium", "high"],
               },
           },
           "required": ["approved", "risk_level"],
       }


   class CheckAllApprovals(BaseMachineStep):
       name = "check_approvals"

       async def execute(self, context):
           # All three must approve
           legal = context.get("legal_approval.approved", False)
           finance = context.get("finance_approval.approved", False)
           security = context.get("security_approval.approved", False)

           all_approved = legal and finance and security
           context.set("all_approved", all_approved)


   # Parallel approval workflow
   parallel_approvals = ParallelGroup(
       LegalApproval(),
       FinanceApproval(),
       SecurityApproval(),
       callback=CheckAllApprovals(),
   )


Handling Partial Failures
-------------------------

When parallel steps might fail, handle errors gracefully:

.. code-block:: python

   class ResilientFetch(BaseMachineStep):
       name = "resilient_fetch"

       async def execute(self, context):
           try:
               data = await external_api.fetch()
               context.set(f"{self.name}_data", data)
               context.set(f"{self.name}_success", True)
           except Exception as e:
               context.set(f"{self.name}_error", str(e))
               context.set(f"{self.name}_success", False)


   class HandlePartialResults(BaseMachineStep):
       name = "handle_results"

       async def execute(self, context):
           successful = []
           failed = []

           for source in ["api1", "api2", "api3"]:
               if context.get(f"fetch_{source}_success"):
                   successful.append(source)
               else:
                   failed.append(source)

           context.set("successful_fetches", successful)
           context.set("failed_fetches", failed)

           # Proceed if at least one succeeded
           if not successful:
               raise ValueError("All data fetches failed")


Timeout Handling
----------------

Set timeouts for parallel operations:

.. code-block:: python

   import asyncio

   class TimedFetch(BaseMachineStep):
       name = "timed_fetch"
       timeout_seconds = 30

       async def execute(self, context):
           try:
               data = await asyncio.wait_for(
                   self.fetch_data(),
                   timeout=self.timeout_seconds
               )
               context.set("data", data)
           except asyncio.TimeoutError:
               context.set("timed_out", True)
               context.set("data", None)

       async def fetch_data(self):
           # Actual fetch logic
           ...


Race Pattern
------------

Execute parallel steps but proceed when the first one completes:

.. code-block:: python

   from litestar_workflows import RaceGroup


   class FastSource(BaseMachineStep):
       name = "fast_source"

       async def execute(self, context):
           # Usually responds quickly
           data = await fast_api.fetch()
           context.set("data", data)
           context.set("source", "fast")


   class ReliableSource(BaseMachineStep):
       name = "reliable_source"

       async def execute(self, context):
           # Slower but more reliable
           data = await reliable_api.fetch()
           context.set("data", data)
           context.set("source", "reliable")


   # First to complete wins
   race_group = RaceGroup(
       FastSource(),
       ReliableSource(),
   )


Complete Example: Parallel Notifications
----------------------------------------

.. code-block:: python

   """Parallel notification workflow example."""

   import asyncio
   from litestar_workflows import (
       WorkflowDefinition,
       Edge,
       BaseMachineStep,
       ParallelGroup,
       LocalExecutionEngine,
       WorkflowRegistry,
       WorkflowContext,
   )


   class ProcessOrder(BaseMachineStep):
       name = "process_order"

       async def execute(self, context: WorkflowContext) -> None:
           order_id = context.get("order_id")
           context.set("processed", True)
           context.set("order_status", "completed")


   class SendEmailNotification(BaseMachineStep):
       name = "send_email"

       async def execute(self, context: WorkflowContext) -> None:
           await asyncio.sleep(0.1)  # Simulate API call
           context.set("email_sent", True)
           context.set("email_timestamp", datetime.now().isoformat())


   class SendSlackNotification(BaseMachineStep):
       name = "send_slack"

       async def execute(self, context: WorkflowContext) -> None:
           await asyncio.sleep(0.1)  # Simulate API call
           context.set("slack_sent", True)
           context.set("slack_timestamp", datetime.now().isoformat())


   class SendWebhook(BaseMachineStep):
       name = "send_webhook"

       async def execute(self, context: WorkflowContext) -> None:
           await asyncio.sleep(0.1)  # Simulate API call
           context.set("webhook_sent", True)
           context.set("webhook_timestamp", datetime.now().isoformat())


   class LogNotifications(BaseMachineStep):
       name = "log_notifications"

       async def execute(self, context: WorkflowContext) -> None:
           sent = []
           if context.get("email_sent"):
               sent.append("email")
           if context.get("slack_sent"):
               sent.append("slack")
           if context.get("webhook_sent"):
               sent.append("webhook")

           context.set("notifications_sent", sent)
           context.set("notification_count", len(sent))


   # Create parallel notification group
   notification_group = ParallelGroup(
       SendEmailNotification(),
       SendSlackNotification(),
       SendWebhook(),
       callback=LogNotifications(),
   )


   # Define workflow
   workflow = WorkflowDefinition(
       name="order_with_notifications",
       version="1.0.0",
       description="Process order and send parallel notifications",
       steps={
           "process_order": ProcessOrder(),
           "notify": notification_group,
       },
       edges=[
           Edge("process_order", "notify"),
       ],
       initial_step="process_order",
       terminal_steps={"notify"},
   )


   # Run
   async def main():
       registry = WorkflowRegistry()
       registry.register_definition(workflow)
       engine = LocalExecutionEngine(registry)

       instance = await engine.start_workflow(
           "order_with_notifications",
           initial_data={"order_id": "ORD-123"}
       )

       print(f"Notifications sent: {instance.context.get('notifications_sent')}")
       print(f"Count: {instance.context.get('notification_count')}")


Best Practices
--------------


Keep Parallel Steps Independent
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parallel steps should not depend on each other:

.. code-block:: python

   # Good - independent steps
   parallel = ParallelGroup(
       FetchFromAPI1(),  # No dependency on other fetches
       FetchFromAPI2(),
       FetchFromAPI3(),
   )

   # Bad - steps depend on each other
   parallel = ParallelGroup(
       FetchInitialData(),
       ProcessFetchedData(),  # Depends on FetchInitialData!
   )


Handle All Failure Modes
~~~~~~~~~~~~~~~~~~~~~~~~

Account for timeouts, errors, and partial failures:

.. code-block:: python

   class RobustCallback(BaseMachineStep):
       name = "robust_callback"

       async def execute(self, context):
           results = {}
           errors = {}

           for step in ["step1", "step2", "step3"]:
               if context.get(f"{step}_success"):
                   results[step] = context.get(f"{step}_data")
               else:
                   errors[step] = context.get(f"{step}_error", "Unknown error")

           context.set("results", results)
           context.set("errors", errors)
           context.set("partial_success", len(results) > 0)


Limit Parallelism
~~~~~~~~~~~~~~~~~

Don't overwhelm external services:

.. code-block:: python

   import asyncio

   class ThrottledGroup:
       """Limit concurrent executions."""

       def __init__(self, *steps, max_concurrent: int = 5):
           self.steps = steps
           self.semaphore = asyncio.Semaphore(max_concurrent)

       async def execute(self, context, engine):
           async def run_with_limit(step):
               async with self.semaphore:
                   return await engine.execute_step(step, context)

           await asyncio.gather(*[run_with_limit(s) for s in self.steps])


Next Steps
----------

- Add conditional logic: See :doc:`conditional-logic`
- Learn about human tasks: See :doc:`human-tasks`
