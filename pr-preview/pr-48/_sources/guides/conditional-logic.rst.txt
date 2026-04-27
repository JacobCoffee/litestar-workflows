Conditional Logic and Gateways
==============================

This guide covers adding decision points and conditional branching to your
workflows. You'll learn how to use gateways, conditional edges, and dynamic
routing.


Goal
----

Create workflows that take different paths based on data, user decisions,
or business rules.


Understanding Gateways
----------------------

Gateways are decision points that evaluate conditions and route execution:

.. code-block:: text

   [Submit] --> [Gateway] ---(amount < 1000)---> [Auto Approve]
                    |
                    +---(amount >= 1000)---> [Manager Approval]


There are several types of gateways:

- **Exclusive (XOR)**: One path is taken based on condition
- **Inclusive (OR)**: One or more paths may be taken
- **Parallel (AND)**: All paths are taken (covered in parallel guide)


Basic Gateway
-------------

Create a simple decision gateway:

.. code-block:: python

   from litestar_workflows import BaseGateway, WorkflowContext

   class AmountGateway(BaseGateway):
       """Route based on request amount."""

       name = "amount_gateway"
       description = "Determine approval path"

       async def evaluate(self, context: WorkflowContext) -> str:
           """Return the name of the next step."""
           amount = context.get("amount", 0)

           if amount >= 10000:
               return "executive_approval"
           elif amount >= 1000:
               return "manager_approval"
           else:
               return "auto_approve"


Using the Gateway in a Workflow
-------------------------------

.. code-block:: python

   from litestar_workflows import WorkflowDefinition, Edge

   expense_workflow = WorkflowDefinition(
       name="expense_approval",
       version="1.0.0",
       steps={
           "submit": SubmitRequest(),
           "route": AmountGateway(),
           "auto_approve": AutoApprove(),
           "manager_approval": ManagerApproval(),
           "executive_approval": ExecutiveApproval(),
           "process": ProcessResult(),
       },
       edges=[
           Edge("submit", "route"),
           # Gateway edges - one will be taken
           Edge("route", "auto_approve"),
           Edge("route", "manager_approval"),
           Edge("route", "executive_approval"),
           # All paths converge
           Edge("auto_approve", "process"),
           Edge("manager_approval", "process"),
           Edge("executive_approval", "process"),
       ],
       initial_step="submit",
       terminal_steps={"process"},
   )


Conditional Edges
-----------------

Instead of gateways, use conditional edges for simpler logic:

.. code-block:: python

   edges = [
       Edge("submit", "review"),
       # Conditional edges - condition is a Python expression
       Edge(
           source="review",
           target="approve",
           condition="context.get('approved') == True"
       ),
       Edge(
           source="review",
           target="reject",
           condition="context.get('approved') == False"
       ),
   ]

The condition is evaluated with access to ``context``.


Complex Conditions
------------------

For complex logic, use gateway steps:

.. code-block:: python

   class ComplexRoutingGateway(BaseGateway):
       name = "complex_router"

       async def evaluate(self, context: WorkflowContext) -> str:
           amount = context.get("amount", 0)
           department = context.get("department")
           is_urgent = context.get("is_urgent", False)
           requester_level = context.get("requester_level", 0)

           # Complex business rules
           if is_urgent and requester_level >= 5:
               return "fast_track"

           if department == "engineering":
               if amount > 5000:
                   return "cto_approval"
               return "eng_manager_approval"

           if department == "marketing":
               if amount > 3000:
                   return "cmo_approval"
               return "marketing_manager_approval"

           # Default path
           return "standard_approval"


Multiple Conditions (Inclusive Gateway)
---------------------------------------

When multiple paths should be taken:

.. code-block:: python

   class NotificationGateway(BaseGateway):
       """Determine which notifications to send."""

       name = "notification_gateway"
       gateway_type = "inclusive"  # Multiple paths allowed

       async def evaluate(self, context: WorkflowContext) -> list[str]:
           """Return list of next steps to execute."""
           paths = []

           if context.get("notify_email", True):
               paths.append("send_email")

           if context.get("notify_slack", False):
               paths.append("send_slack")

           if context.get("amount", 0) > 10000:
               paths.append("send_executive_alert")

           return paths if paths else ["skip_notifications"]


Conditional Approval Chains
---------------------------

Build dynamic approval chains:

.. code-block:: python

   class ApprovalChainGateway(BaseGateway):
       """Determine required approvals based on context."""

       name = "approval_chain"

       async def evaluate(self, context: WorkflowContext) -> str:
           amount = context.get("amount", 0)
           department = context.get("department")
           approval_count = context.get("approval_count", 0)

           # Define approval thresholds
           thresholds = [
               (1000, "team_lead"),
               (5000, "manager"),
               (15000, "director"),
               (50000, "vp"),
               (float("inf"), "ceo"),
           ]

           # Find required approval level
           required_level = 0
           for threshold, _ in thresholds:
               if amount <= threshold:
                   break
               required_level += 1

           # Check if all required approvals obtained
           if approval_count >= required_level:
               return "process_approved"

           # Route to next approver
           return thresholds[approval_count][1]


State Machine Pattern
---------------------

Implement state machine behavior:

.. code-block:: python

   from enum import StrEnum

   class OrderState(StrEnum):
       PENDING = "pending"
       PROCESSING = "processing"
       SHIPPED = "shipped"
       DELIVERED = "delivered"
       CANCELLED = "cancelled"

   class OrderStateGateway(BaseGateway):
       """Handle order state transitions."""

       name = "order_state"

       # Valid transitions
       TRANSITIONS = {
           OrderState.PENDING: [OrderState.PROCESSING, OrderState.CANCELLED],
           OrderState.PROCESSING: [OrderState.SHIPPED, OrderState.CANCELLED],
           OrderState.SHIPPED: [OrderState.DELIVERED],
           OrderState.DELIVERED: [],
           OrderState.CANCELLED: [],
       }

       async def evaluate(self, context: WorkflowContext) -> str:
           current_state = context.get("order_state", OrderState.PENDING)
           requested_state = context.get("requested_state")

           valid_transitions = self.TRANSITIONS.get(current_state, [])

           if requested_state in valid_transitions:
               context.set("order_state", requested_state)
               return f"handle_{requested_state}"
           else:
               context.set("transition_error", f"Cannot transition from {current_state} to {requested_state}")
               return "handle_invalid_transition"


Retry Logic with Gateways
-------------------------

Implement retry behavior:

.. code-block:: python

   class RetryGateway(BaseGateway):
       """Determine whether to retry a failed operation."""

       name = "retry_gateway"
       max_retries = 3

       async def evaluate(self, context: WorkflowContext) -> str:
           retry_count = context.get("retry_count", 0)
           last_error = context.get("last_error")

           if not last_error:
               # No error - proceed normally
               return "next_step"

           if retry_count >= self.max_retries:
               # Max retries reached - fail
               return "handle_failure"

           # Check if error is retryable
           if self.is_retryable(last_error):
               context.set("retry_count", retry_count + 1)
               return "retry_operation"
           else:
               return "handle_failure"

       def is_retryable(self, error: str) -> bool:
           retryable_patterns = ["timeout", "connection", "rate limit"]
           return any(p in error.lower() for p in retryable_patterns)


Complete Example: Multi-Level Approval
--------------------------------------

.. code-block:: python

   """Multi-level approval workflow with conditional routing."""

   from litestar_workflows import (
       WorkflowDefinition,
       Edge,
       BaseMachineStep,
       BaseHumanStep,
       BaseGateway,
       LocalExecutionEngine,
       WorkflowRegistry,
       WorkflowContext,
   )


   class SubmitRequest(BaseMachineStep):
       name = "submit"

       async def execute(self, context: WorkflowContext) -> None:
           context.set("submitted", True)
           context.set("approval_level", 0)


   class ApprovalRouter(BaseGateway):
       """Route to appropriate approver based on amount and current level."""

       name = "approval_router"

       # Approval levels: (max_amount, step_name, level)
       LEVELS = [
           (1000, "auto_approve", 0),
           (5000, "team_lead_approval", 1),
           (25000, "manager_approval", 2),
           (100000, "director_approval", 3),
           (float("inf"), "vp_approval", 4),
       ]

       async def evaluate(self, context: WorkflowContext) -> str:
           amount = context.get("amount", 0)
           current_level = context.get("approval_level", 0)

           # Find required approval level
           for max_amount, step_name, level in self.LEVELS:
               if amount <= max_amount:
                   required_level = level
                   required_step = step_name
                   break

           # Check if we've reached required level
           if current_level >= required_level:
               return "process_approved"

           # Route to next approver in chain
           for max_amount, step_name, level in self.LEVELS:
               if level == current_level + 1:
                   return step_name

           return "process_approved"


   class TeamLeadApproval(BaseHumanStep):
       name = "team_lead_approval"
       title = "Team Lead Approval"
       form_schema = {
           "type": "object",
           "properties": {
               "approved": {"type": "boolean", "title": "Approve?"},
               "escalate": {"type": "boolean", "title": "Escalate to Manager?"},
           },
           "required": ["approved"],
       }


   class ManagerApproval(BaseHumanStep):
       name = "manager_approval"
       title = "Manager Approval"
       form_schema = {
           "type": "object",
           "properties": {
               "approved": {"type": "boolean", "title": "Approve?"},
           },
           "required": ["approved"],
       }


   class UpdateApprovalLevel(BaseMachineStep):
       name = "update_level"

       async def execute(self, context: WorkflowContext) -> None:
           current = context.get("approval_level", 0)
           context.set("approval_level", current + 1)


   class AutoApprove(BaseMachineStep):
       name = "auto_approve"

       async def execute(self, context: WorkflowContext) -> None:
           context.set("approved", True)
           context.set("approved_by", "system")


   class ProcessApproved(BaseMachineStep):
       name = "process_approved"

       async def execute(self, context: WorkflowContext) -> None:
           context.set("status", "approved")
           context.set("processed", True)


   class ProcessRejected(BaseMachineStep):
       name = "process_rejected"

       async def execute(self, context: WorkflowContext) -> None:
           context.set("status", "rejected")


   # Workflow definition
   approval_workflow = WorkflowDefinition(
       name="multi_level_approval",
       version="1.0.0",
       description="Multi-level approval with conditional routing",
       steps={
           "submit": SubmitRequest(),
           "router": ApprovalRouter(),
           "auto_approve": AutoApprove(),
           "team_lead_approval": TeamLeadApproval(),
           "manager_approval": ManagerApproval(),
           "update_level": UpdateApprovalLevel(),
           "process_approved": ProcessApproved(),
           "process_rejected": ProcessRejected(),
       },
       edges=[
           Edge("submit", "router"),
           # Gateway routes to appropriate step
           Edge("router", "auto_approve"),
           Edge("router", "team_lead_approval"),
           Edge("router", "manager_approval"),
           Edge("router", "process_approved"),
           # Auto approve goes directly to processing
           Edge("auto_approve", "process_approved"),
           # Human approvals check result
           Edge(
               "team_lead_approval",
               "update_level",
               condition="context.get('approved') == True"
           ),
           Edge(
               "team_lead_approval",
               "process_rejected",
               condition="context.get('approved') == False"
           ),
           Edge(
               "manager_approval",
               "update_level",
               condition="context.get('approved') == True"
           ),
           Edge(
               "manager_approval",
               "process_rejected",
               condition="context.get('approved') == False"
           ),
           # After level update, re-evaluate routing
           Edge("update_level", "router"),
       ],
       initial_step="submit",
       terminal_steps={"process_approved", "process_rejected"},
   )


Best Practices
--------------


Keep Gateway Logic Simple
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Good - clear, simple logic
   async def evaluate(self, context):
       if context.get("approved"):
           return "next_step"
       return "rejection_handler"

   # Avoid - too complex
   async def evaluate(self, context):
       if context.get("a") and not context.get("b") or (context.get("c") > 10 and context.get("d") != "x"):
           # Hard to understand and debug
           ...


Document Decision Criteria
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class ApprovalGateway(BaseGateway):
       """Route based on amount thresholds.

       Routing Rules:
       - < $1,000: Auto-approve
       - $1,000 - $5,000: Team lead approval
       - $5,000 - $25,000: Manager approval
       - > $25,000: Director approval
       """
       ...


Test All Branches
~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pytest

   @pytest.mark.parametrize("amount,expected", [
       (500, "auto_approve"),
       (2000, "team_lead"),
       (10000, "manager"),
       (50000, "director"),
   ])
   async def test_gateway_routing(amount, expected):
       context = WorkflowContext(data={"amount": amount})
       gateway = AmountGateway()
       result = await gateway.evaluate(context)
       assert result == expected


Handle Edge Cases
~~~~~~~~~~~~~~~~~

.. code-block:: python

   class SafeGateway(BaseGateway):
       async def evaluate(self, context):
           amount = context.get("amount")

           # Handle missing data
           if amount is None:
               context.set("routing_error", "Amount is required")
               return "handle_error"

           # Handle invalid data
           if not isinstance(amount, (int, float)) or amount < 0:
               context.set("routing_error", f"Invalid amount: {amount}")
               return "handle_error"

           # Normal routing
           if amount < 1000:
               return "auto_approve"
           return "manual_review"


Next Steps
----------

- Learn about parallel execution: See :doc:`parallel-execution`
- Understand human tasks: See :doc:`human-tasks`
