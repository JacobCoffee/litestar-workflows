Quickstart
==========

This tutorial walks you through creating your first workflow with litestar-workflows.
In about 10 minutes, you'll build a complete approval workflow that combines automated
processing with human decision points.


What We're Building
-------------------

We'll create a simple expense approval workflow with three steps:

1. **Submit Request** (Machine Step): Automatically validates and records the submission
2. **Manager Approval** (Human Step): Waits for a manager to approve or reject
3. **Process Result** (Machine Step): Handles the approved/rejected request

Here's what the workflow looks like visually:

.. code-block:: text

   [Submit Request] --> [Manager Approval] --> [Process Result]
        (auto)              (human)              (auto)


Step 1: Define Your Steps
-------------------------

First, let's create the steps that make up our workflow.

Machine Steps
~~~~~~~~~~~~~

Machine steps run automatically without human intervention. They inherit from
``BaseMachineStep`` and implement an ``execute`` method:

.. code-block:: python

   from litestar_workflows import BaseMachineStep, WorkflowContext

   class SubmitRequest(BaseMachineStep):
       """Automatically process the initial submission."""

       name = "submit_request"
       description = "Validate and record the expense submission"

       async def execute(self, context: WorkflowContext) -> None:
           # Access workflow data
           amount = context.get("amount", 0)
           description = context.get("description", "")

           # Validate the request
           if amount <= 0:
               raise ValueError("Amount must be positive")

           # Store computed values in context
           context.set("submitted", True)
           context.set("submitted_at", datetime.now().isoformat())
           context.set("requires_vp_approval", amount > 5000)

The ``WorkflowContext`` provides access to workflow data:

- ``context.get(key, default)`` - Retrieve a value
- ``context.set(key, value)`` - Store a value
- ``context.data`` - Access the full data dictionary


Human Steps
~~~~~~~~~~~

Human steps pause the workflow until a person takes action. They inherit from
``BaseHumanStep`` and define a form schema:

.. code-block:: python

   from litestar_workflows import BaseHumanStep

   class ManagerApproval(BaseHumanStep):
       """Wait for manager to approve or reject the request."""

       name = "manager_approval"
       title = "Approve Expense Request"
       description = "Review and approve or reject this expense request"

       # JSON Schema for the approval form
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
                   "description": "Optional comments for the requester",
               },
           },
           "required": ["approved"],
       }

When this step is reached, the workflow pauses and creates a task for the assigned
person. Once they submit the form, the data is added to the context and execution
continues.


Processing Step
~~~~~~~~~~~~~~~

Let's add the final step that handles the result:

.. code-block:: python

   class ProcessResult(BaseMachineStep):
       """Process the approved or rejected request."""

       name = "process_result"
       description = "Handle the final outcome"

       async def execute(self, context: WorkflowContext) -> None:
           if context.get("approved"):
               # Request was approved - process it
               context.set("status", "approved")
               context.set("processed_at", datetime.now().isoformat())
               # Trigger payment, notification, etc.
           else:
               # Request was rejected
               context.set("status", "rejected")
               context.set("rejection_reason", context.get("comments", "No reason provided"))


Step 2: Create the Workflow Definition
--------------------------------------

Now we connect our steps with edges to form a workflow:

.. code-block:: python

   from litestar_workflows import WorkflowDefinition, Edge

   # Create step instances
   submit_step = SubmitRequest()
   approval_step = ManagerApproval()
   process_step = ProcessResult()

   # Define the workflow
   expense_workflow = WorkflowDefinition(
       name="expense_approval",
       version="1.0.0",
       description="Expense request approval workflow",
       steps={
           "submit_request": submit_step,
           "manager_approval": approval_step,
           "process_result": process_step,
       },
       edges=[
           Edge(source="submit_request", target="manager_approval"),
           Edge(source="manager_approval", target="process_result"),
       ],
       initial_step="submit_request",
       terminal_steps={"process_result"},
   )

Key concepts:

- **steps**: Dictionary mapping step names to step instances
- **edges**: List of transitions between steps
- **initial_step**: Where execution begins
- **terminal_steps**: Steps that mark workflow completion


Step 3: Register and Run
------------------------

With our workflow defined, we can register it and start instances:

.. code-block:: python

   from litestar_workflows import WorkflowRegistry, LocalExecutionEngine

   # Create registry and register our workflow
   registry = WorkflowRegistry()
   registry.register_definition(expense_workflow)

   # Create execution engine
   engine = LocalExecutionEngine(registry)

   # Start a new workflow instance
   async def submit_expense(user_id: str, amount: float, description: str):
       instance = await engine.start_workflow(
           workflow_name="expense_approval",
           initial_data={
               "requester_id": user_id,
               "amount": amount,
               "description": description,
           },
       )
       return instance

The workflow will:

1. Execute ``submit_request`` automatically
2. Pause at ``manager_approval``, waiting for human input
3. Create a pending task for the manager


Step 4: Complete Human Tasks
----------------------------

When a manager is ready to approve or reject, complete the human task:

.. code-block:: python

   async def approve_expense(instance_id: str, manager_id: str, approved: bool, comments: str = ""):
       await engine.complete_human_task(
           instance_id=instance_id,
           step_name="manager_approval",
           user_id=manager_id,
           data={
               "approved": approved,
               "comments": comments,
           },
       )

After the task is completed:

1. The form data is added to the workflow context
2. Execution continues to ``process_result``
3. The workflow completes


Complete Example
----------------

Here's everything together:

.. code-block:: python

   """Complete expense approval workflow example."""

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


   # Step 1: Define Steps
   class SubmitRequest(BaseMachineStep):
       name = "submit_request"
       description = "Validate and record the expense submission"

       async def execute(self, context: WorkflowContext) -> None:
           amount = context.get("amount", 0)
           if amount <= 0:
               raise ValueError("Amount must be positive")
           context.set("submitted", True)
           context.set("submitted_at", datetime.now().isoformat())


   class ManagerApproval(BaseHumanStep):
       name = "manager_approval"
       title = "Approve Expense Request"
       form_schema = {
           "type": "object",
           "properties": {
               "approved": {"type": "boolean", "title": "Approve?"},
               "comments": {"type": "string", "title": "Comments"},
           },
           "required": ["approved"],
       }


   class ProcessResult(BaseMachineStep):
       name = "process_result"
       description = "Handle the final outcome"

       async def execute(self, context: WorkflowContext) -> None:
           status = "approved" if context.get("approved") else "rejected"
           context.set("status", status)
           context.set("completed_at", datetime.now().isoformat())


   # Step 2: Create Workflow Definition
   expense_workflow = WorkflowDefinition(
       name="expense_approval",
       version="1.0.0",
       description="Expense request approval workflow",
       steps={
           "submit_request": SubmitRequest(),
           "manager_approval": ManagerApproval(),
           "process_result": ProcessResult(),
       },
       edges=[
           Edge("submit_request", "manager_approval"),
           Edge("manager_approval", "process_result"),
       ],
       initial_step="submit_request",
       terminal_steps={"process_result"},
   )


   # Step 3: Register and Run
   registry = WorkflowRegistry()
   registry.register_definition(expense_workflow)
   engine = LocalExecutionEngine(registry)


   async def main():
       # Start a new expense request
       instance = await engine.start_workflow(
           "expense_approval",
           initial_data={
               "requester_id": "alice@example.com",
               "amount": 250.00,
               "description": "Conference registration fee",
           },
       )
       print(f"Workflow started: {instance.id}")
       print(f"Current step: {instance.current_step}")  # manager_approval

       # Manager approves the request
       await engine.complete_human_task(
           instance_id=instance.id,
           step_name="manager_approval",
           user_id="bob@example.com",
           data={"approved": True, "comments": "Approved for Q4 budget"},
       )
       print(f"Workflow completed with status: {instance.context.get('status')}")


   if __name__ == "__main__":
       import asyncio
       asyncio.run(main())


Next Steps
----------

Congratulations! You've built your first workflow. Here's where to go next:

- :doc:`/concepts/index` - Understand the core concepts in depth
- :doc:`/guides/human-tasks` - Learn more about human task patterns
- :doc:`/guides/conditional-logic` - Add conditional branching with gateways
- :doc:`/guides/parallel-execution` - Execute steps in parallel
