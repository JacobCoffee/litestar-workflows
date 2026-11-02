Working with Human Tasks
========================

This guide covers implementing approval workflows and other patterns that
require human interaction. You'll learn how to create human steps, handle
task assignment, and process user input.


Goal
----

Build workflows that pause for human decisions and resume when users
complete their tasks.


Understanding Human Tasks
-------------------------

Human tasks are steps that require user interaction:

- **Approvals**: Approve/reject decisions
- **Form submissions**: Data entry by users
- **Reviews**: Content or document review
- **Assignments**: Manual task routing

When a workflow reaches a human step:

1. Execution pauses
2. A task is created for the assignee
3. The workflow waits until the task is completed
4. User input is added to the context
5. Execution resumes


Basic Human Step
----------------

Create a simple approval step:

.. code-block:: python

   from litestar_workflows import BaseHumanStep

   class ManagerApproval(BaseHumanStep):
       """Manager reviews and approves request."""

       name = "manager_approval"
       title = "Manager Approval Required"
       description = "Please review this request and make a decision"

       form_schema = {
           "type": "object",
           "properties": {
               "approved": {
                   "type": "boolean",
                   "title": "Approve this request?",
                   "default": False,
               },
               "comments": {
                   "type": "string",
                   "title": "Comments",
                   "description": "Optional feedback for the requester",
               },
           },
           "required": ["approved"],
       }


Form Schema Design
------------------

Human steps use `JSON Schema <https://json-schema.org/>`_ for form definitions.


Boolean Approval
~~~~~~~~~~~~~~~~

.. code-block:: python

   form_schema = {
       "type": "object",
       "properties": {
           "approved": {
               "type": "boolean",
               "title": "Approve?",
               "default": False,
           },
       },
       "required": ["approved"],
   }


Multiple Choice
~~~~~~~~~~~~~~~

.. code-block:: python

   form_schema = {
       "type": "object",
       "properties": {
           "decision": {
               "type": "string",
               "title": "Your Decision",
               "enum": ["approve", "reject", "defer"],
               "enumNames": ["Approve", "Reject", "Defer to next week"],
           },
       },
       "required": ["decision"],
   }


Numeric Input
~~~~~~~~~~~~~

.. code-block:: python

   form_schema = {
       "type": "object",
       "properties": {
           "adjustment_amount": {
               "type": "number",
               "title": "Adjustment Amount",
               "minimum": -1000,
               "maximum": 1000,
           },
           "reason": {
               "type": "string",
               "title": "Reason for Adjustment",
               "minLength": 10,
           },
       },
       "required": ["adjustment_amount", "reason"],
   }


Rich Text Input
~~~~~~~~~~~~~~~

.. code-block:: python

   form_schema = {
       "type": "object",
       "properties": {
           "feedback": {
               "type": "string",
               "title": "Detailed Feedback",
               "format": "textarea",
               "minLength": 50,
               "maxLength": 2000,
           },
       },
       "required": ["feedback"],
   }


Complete Approval Workflow
--------------------------

Here's a full example with multiple approval levels:

.. code-block:: python

   from datetime import datetime
   from litestar_workflows import (
       WorkflowDefinition,
       Edge,
       BaseMachineStep,
       BaseHumanStep,
       LocalExecutionEngine,
       WorkflowRegistry,
       WorkflowContext,
   )


   # Machine step - automatic submission
   class SubmitRequest(BaseMachineStep):
       name = "submit"
       description = "Record the initial request"

       async def execute(self, context: WorkflowContext) -> None:
           context.set("submitted_at", datetime.now().isoformat())
           context.set("status", "pending_approval")


   # Human step - manager approval
   class ManagerApproval(BaseHumanStep):
       name = "manager_approval"
       title = "Manager Approval"
       description = "Review and approve this expense request"

       form_schema = {
           "type": "object",
           "properties": {
               "approved": {"type": "boolean", "title": "Approve?"},
               "comments": {"type": "string", "title": "Comments"},
           },
           "required": ["approved"],
       }


   # Human step - finance approval (for high amounts)
   class FinanceApproval(BaseHumanStep):
       name = "finance_approval"
       title = "Finance Approval"
       description = "Finance review for high-value requests"

       form_schema = {
           "type": "object",
           "properties": {
               "approved": {"type": "boolean", "title": "Approve?"},
               "budget_code": {"type": "string", "title": "Budget Code"},
               "comments": {"type": "string", "title": "Comments"},
           },
           "required": ["approved", "budget_code"],
       }


   # Machine step - process result
   class ProcessResult(BaseMachineStep):
       name = "process"
       description = "Process the final decision"

       async def execute(self, context: WorkflowContext) -> None:
           # Check all approvals
           manager_approved = context.get("approved", False)
           finance_approved = context.get("finance_approved", True)  # Default True if skipped

           if manager_approved and finance_approved:
               context.set("status", "approved")
               context.set("approved_at", datetime.now().isoformat())
           else:
               context.set("status", "rejected")
               context.set("rejected_at", datetime.now().isoformat())


   # Workflow definition
   expense_workflow = WorkflowDefinition(
       name="expense_approval",
       version="1.0.0",
       description="Multi-level expense approval",
       steps={
           "submit": SubmitRequest(),
           "manager_approval": ManagerApproval(),
           "finance_approval": FinanceApproval(),
           "process": ProcessResult(),
       },
       edges=[
           Edge("submit", "manager_approval"),
           Edge("manager_approval", "finance_approval"),
           Edge("finance_approval", "process"),
       ],
       initial_step="submit",
       terminal_steps={"process"},
   )


Completing Human Tasks
----------------------

When a user is ready to complete their task:

.. code-block:: python

   # Start the workflow
   instance = await engine.start_workflow(
       "expense_approval",
       initial_data={
           "requester": "alice@example.com",
           "amount": 2500.00,
           "description": "Conference attendance",
       }
   )

   # Workflow is now waiting at manager_approval
   assert instance.current_step == "manager_approval"

   # Manager completes their task
   await engine.complete_human_task(
       instance_id=instance.id,
       step_name="manager_approval",
       user_id="manager@example.com",
       data={
           "approved": True,
           "comments": "Approved for Q4 budget",
       }
   )

   # Workflow continues to finance_approval
   # ...then finance completes their task
   await engine.complete_human_task(
       instance_id=instance.id,
       step_name="finance_approval",
       user_id="finance@example.com",
       data={
           "approved": True,
           "budget_code": "CONF-2024",
           "comments": "Within budget",
       }
   )


Task Assignment
---------------

Assign tasks to specific users or groups:

.. code-block:: python

   class DynamicApproval(BaseHumanStep):
       name = "dynamic_approval"
       title = "Approval Required"

       form_schema = {...}

       async def get_assignee(self, context: WorkflowContext) -> str | None:
           """Dynamically determine the assignee."""
           department = context.get("department")
           amount = context.get("amount", 0)

           # Route based on business logic
           if amount > 10000:
               return await get_department_director(department)
           else:
               return await get_department_manager(department)

       async def get_assignee_group(self, context: WorkflowContext) -> str | None:
           """Assign to a group instead of individual."""
           return "finance-approvers"


Task Deadlines
--------------

Set deadlines for human tasks:

.. code-block:: python

   from datetime import datetime, timedelta

   class UrgentApproval(BaseHumanStep):
       name = "urgent_approval"
       title = "Urgent Approval Required"

       form_schema = {...}

       async def get_due_date(self, context: WorkflowContext) -> datetime:
           """Task must be completed within 24 hours."""
           return datetime.now() + timedelta(hours=24)

       async def get_reminder_date(self, context: WorkflowContext) -> datetime:
           """Send reminder after 12 hours."""
           return datetime.now() + timedelta(hours=12)


Conditional Approval Chains
---------------------------

Skip approvals based on conditions:

.. code-block:: python

   # Define edges with conditions
   edges = [
       Edge("submit", "manager_approval"),
       # Skip finance for small amounts
       Edge(
           "manager_approval",
           "process",
           condition="context.get('amount', 0) < 1000"
       ),
       # Require finance for large amounts
       Edge(
           "manager_approval",
           "finance_approval",
           condition="context.get('amount', 0) >= 1000"
       ),
       Edge("finance_approval", "process"),
   ]


Handling Rejections
-------------------

Route rejected requests appropriately:

.. code-block:: python

   class HandleRejection(BaseMachineStep):
       name = "handle_rejection"
       description = "Process rejected request"

       async def execute(self, context: WorkflowContext) -> None:
           rejection_reason = context.get("comments", "No reason provided")
           requester = context.get("requester")

           # Notify requester
           await send_notification(
               to=requester,
               subject="Request Rejected",
               body=f"Your request was rejected: {rejection_reason}",
           )

           context.set("status", "rejected")
           context.set("rejection_notified", True)


   # Add rejection path
   edges = [
       Edge("submit", "manager_approval"),
       Edge(
           "manager_approval",
           "process_approval",
           condition="context.get('approved') == True"
       ),
       Edge(
           "manager_approval",
           "handle_rejection",
           condition="context.get('approved') == False"
       ),
   ]


Building a Task Inbox API
-------------------------

Create an API for users to view and complete their tasks:

.. code-block:: python

   from litestar import Controller, get, post
   from litestar.params import Parameter


   class TaskController(Controller):
       path = "/tasks"

       @get("/")
       async def list_my_tasks(
           self,
           request: Request,
           engine: LocalExecutionEngine,
       ) -> list[dict]:
           """List pending tasks for current user."""
           user_id = request.user.id
           tasks = await engine.get_pending_tasks(user_id=user_id)

           return [
               {
                   "id": task.id,
                   "instance_id": task.instance_id,
                   "step_name": task.step_name,
                   "title": task.title,
                   "description": task.description,
                   "form_schema": task.form_schema,
                   "due_at": task.due_at,
               }
               for task in tasks
           ]

       @get("/{task_id:uuid}")
       async def get_task(
           self,
           task_id: UUID,
           engine: LocalExecutionEngine,
       ) -> dict:
           """Get task details including workflow context."""
           task = await engine.get_task(task_id)
           return {
               "id": task.id,
               "title": task.title,
               "form_schema": task.form_schema,
               "context": task.context.data,  # Relevant data for decision
           }

       @post("/{task_id:uuid}/complete")
       async def complete_task(
           self,
           task_id: UUID,
           data: dict,
           request: Request,
           engine: LocalExecutionEngine,
       ) -> dict:
           """Complete a task with form data."""
           task = await engine.get_task(task_id)

           await engine.complete_human_task(
               instance_id=task.instance_id,
               step_name=task.step_name,
               user_id=request.user.id,
               data=data,
           )

           return {"status": "completed"}


Best Practices
--------------


Provide Context to Approvers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Include relevant information in task descriptions:

.. code-block:: python

   class InformedApproval(BaseHumanStep):
       name = "informed_approval"

       async def get_description(self, context: WorkflowContext) -> str:
           amount = context.get("amount")
           requester = context.get("requester")
           description = context.get("description")

           return f"""
           **Expense Request**

           - Requester: {requester}
           - Amount: ${amount:,.2f}
           - Description: {description}

           Please review and approve or reject.
           """


Validate Form Submissions
~~~~~~~~~~~~~~~~~~~~~~~~~

Add server-side validation:

.. code-block:: python

   class ValidatedApproval(BaseHumanStep):
       name = "validated_approval"
       form_schema = {...}

       async def validate_submission(
           self,
           context: WorkflowContext,
           data: dict
       ) -> list[str]:
           """Return list of validation errors."""
           errors = []

           if data.get("approved") and not data.get("budget_code"):
               errors.append("Budget code required for approvals")

           if data.get("adjustment_amount", 0) > context.get("max_adjustment", 0):
               errors.append("Adjustment exceeds maximum allowed")

           return errors


Keep Forms Simple
~~~~~~~~~~~~~~~~~

Request only essential information:

.. code-block:: python

   # Good - focused form
   form_schema = {
       "type": "object",
       "properties": {
           "approved": {"type": "boolean", "title": "Approve?"},
           "comments": {"type": "string", "title": "Comments"},
       },
       "required": ["approved"],
   }

   # Avoid - overwhelming form
   form_schema = {
       "type": "object",
       "properties": {
           "approved": {...},
           "comments": {...},
           "risk_assessment": {...},
           "compliance_check": {...},
           "budget_impact": {...},
           "timeline_impact": {...},
           # ... too many fields
       },
   }


Next Steps
----------

- Add parallel approvals: See :doc:`parallel-execution`
- Add conditional routing: See :doc:`conditional-logic`
