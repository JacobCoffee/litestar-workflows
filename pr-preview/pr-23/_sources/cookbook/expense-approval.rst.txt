Expense Approval Workflow
=========================

A complete expense approval system with multi-level approval chains,
conditional routing based on amount, and full REST API integration.

This recipe demonstrates:

- Multi-level approval chains (Manager -> Finance -> CFO)
- Conditional routing based on expense amount
- Human task forms with JSON Schema validation
- Rejection handling and notifications
- Full Litestar integration with the web plugin


Overview
--------

The workflow routes expense requests through appropriate approval levels:

.. code-block:: text

   [Submit] --> [Route by Amount] --> [Manager Approval] --> [Route by Amount]
                     |                                            |
                     +---(< $1,000)--> [Auto Approve] -----+      +---(< $5,000)--> [Process]
                     |                                     |      |
                     +---(>= $1,000)---> [Manager] --------+      +---(>= $5,000)--> [Finance]
                     |                                            |
                     +---(>= $10,000)-> [Manager] -> [Finance] ---+--(>= $10,000)--> [CFO]
                                                                  |
                                                                  v
                                                              [Process]

**Approval Thresholds:**

- Under $1,000: Auto-approved
- $1,000 - $4,999: Manager approval only
- $5,000 - $9,999: Manager + Finance approval
- $10,000+: Manager + Finance + CFO approval


Complete Implementation
-----------------------

.. code-block:: python

   """Expense approval workflow with multi-level approval chain.

   Run with:
       uv run python -m expense_approval
   """

   from __future__ import annotations

   from datetime import datetime, timezone
   from typing import TYPE_CHECKING, Any

   from litestar import Litestar, get
   from litestar.di import Provide
   from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

   from litestar_workflows import (
       BaseMachineStep,
       BaseHumanStep,
       Edge,
       ExclusiveGateway,
       LocalExecutionEngine,
       WorkflowContext,
       WorkflowDefinition,
       WorkflowPlugin,
       WorkflowPluginConfig,
       WorkflowRegistry,
   )
   from litestar_workflows.db import PersistentExecutionEngine

   if TYPE_CHECKING:
       from litestar_workflows.core import WorkflowContext


   # =============================================================================
   # Step Definitions
   # =============================================================================

   class SubmitExpense(BaseMachineStep):
       """Record the expense submission with metadata."""

       name = "submit_expense"
       description = "Record expense submission and prepare for routing"

       async def execute(self, context: WorkflowContext) -> dict[str, Any]:
           """Initialize the expense request in the workflow context."""
           context.set("submitted_at", datetime.now(timezone.utc).isoformat())
           context.set("status", "pending")
           context.set("approval_chain", [])

           # Validate required fields
           amount = context.get("amount")
           if amount is None or amount <= 0:
               raise ValueError("Amount must be a positive number")

           requester = context.get("requester")
           if not requester:
               raise ValueError("Requester email is required")

           return {
               "submitted": True,
               "amount": amount,
               "requester": requester,
           }


   class AmountRouter(ExclusiveGateway):
       """Route expense to appropriate approval level based on amount."""

       name = "amount_router"
       description = "Determine required approval level"

       async def evaluate(self, context: WorkflowContext) -> str:
           """Return the next step based on amount and current approval state."""
           amount = context.get("amount", 0)
           approval_chain: list[str] = context.get("approval_chain", [])

           # Determine required approvals
           required_approvals = self._get_required_approvals(amount)

           # Find next unobtained approval
           for approval_level in required_approvals:
               if approval_level not in approval_chain:
                   return f"{approval_level}_approval"

           # All required approvals obtained
           return "process_approved"

       def _get_required_approvals(self, amount: float) -> list[str]:
           """Determine which approvals are needed based on amount."""
           if amount < 1000:
               return []  # Auto-approve
           elif amount < 5000:
               return ["manager"]
           elif amount < 10000:
               return ["manager", "finance"]
           else:
               return ["manager", "finance", "cfo"]


   class AutoApprove(BaseMachineStep):
       """Automatically approve small expenses."""

       name = "auto_approve"
       description = "Auto-approve expenses under threshold"

       async def execute(self, context: WorkflowContext) -> dict[str, Any]:
           """Mark expense as auto-approved."""
           context.set("approved", True)
           context.set("approved_by", "system")
           context.set("approved_at", datetime.now(timezone.utc).isoformat())
           context.set("status", "approved")

           approval_chain = context.get("approval_chain", [])
           approval_chain.append("auto")
           context.set("approval_chain", approval_chain)

           return {"auto_approved": True}


   class ManagerApproval(BaseHumanStep):
       """Manager reviews and approves/rejects the expense."""

       name = "manager_approval"
       title = "Manager Approval Required"
       description = "Review expense request and approve or reject"

       form_schema = {
           "type": "object",
           "title": "Expense Approval",
           "properties": {
               "decision": {
                   "type": "string",
                   "title": "Decision",
                   "enum": ["approve", "reject", "request_info"],
                   "enumNames": ["Approve", "Reject", "Request More Information"],
                   "description": "Your decision on this expense request",
               },
               "comments": {
                   "type": "string",
                   "title": "Comments",
                   "description": "Feedback for the requester (required for rejection)",
                   "maxLength": 1000,
               },
               "cost_center": {
                   "type": "string",
                   "title": "Cost Center",
                   "description": "Assign to cost center (optional)",
                   "pattern": "^[A-Z]{2}-[0-9]{4}$",
               },
           },
           "required": ["decision"],
           "if": {
               "properties": {"decision": {"const": "reject"}}
           },
           "then": {
               "required": ["decision", "comments"]
           },
       }

       async def get_description(self, context: WorkflowContext) -> str:
           """Generate a dynamic description with expense details."""
           amount = context.get("amount", 0)
           requester = context.get("requester", "Unknown")
           description = context.get("description", "No description provided")

           return f"""
   **Expense Request**

   - **Requester:** {requester}
   - **Amount:** ${amount:,.2f}
   - **Description:** {description}

   Please review and approve or reject this expense request.
   """

       async def get_assignee(self, context: WorkflowContext) -> str | None:
           """Route to the requester's manager."""
           requester = context.get("requester")
           # In a real application, look up the manager
           # For demo, use a pattern
           return f"manager-of-{requester}"


   class FinanceApproval(BaseHumanStep):
       """Finance team reviews larger expenses."""

       name = "finance_approval"
       title = "Finance Approval Required"
       description = "Finance review for expenses over $5,000"

       form_schema = {
           "type": "object",
           "title": "Finance Review",
           "properties": {
               "decision": {
                   "type": "string",
                   "title": "Decision",
                   "enum": ["approve", "reject"],
               },
               "budget_code": {
                   "type": "string",
                   "title": "Budget Code",
                   "description": "Assign expense to budget",
                   "pattern": "^BUD-[0-9]{6}$",
               },
               "fiscal_year": {
                   "type": "string",
                   "title": "Fiscal Year",
                   "enum": ["FY2024", "FY2025"],
               },
               "comments": {
                   "type": "string",
                   "title": "Comments",
               },
           },
           "required": ["decision", "budget_code", "fiscal_year"],
       }

       async def get_assignee_group(self, context: WorkflowContext) -> str | None:
           """Assign to finance approvers group."""
           return "finance-approvers"


   class CFOApproval(BaseHumanStep):
       """CFO reviews high-value expenses."""

       name = "cfo_approval"
       title = "CFO Approval Required"
       description = "Executive approval for expenses over $10,000"

       form_schema = {
           "type": "object",
           "title": "Executive Approval",
           "properties": {
               "decision": {
                   "type": "string",
                   "title": "Decision",
                   "enum": ["approve", "reject", "defer"],
                   "enumNames": ["Approve", "Reject", "Defer to Board"],
               },
               "strategic_alignment": {
                   "type": "boolean",
                   "title": "Strategically Aligned",
                   "description": "Does this expense align with company strategy?",
               },
               "comments": {
                   "type": "string",
                   "title": "Executive Notes",
                   "format": "textarea",
               },
           },
           "required": ["decision"],
       }

       async def get_assignee(self, context: WorkflowContext) -> str | None:
           """Route to CFO."""
           return "cfo@company.com"


   class RecordApproval(BaseMachineStep):
       """Record approval from a human step and route to next."""

       name = "record_approval"
       description = "Process approval decision and update chain"

       async def execute(self, context: WorkflowContext) -> dict[str, Any]:
           """Record the approval decision and prepare for routing."""
           decision = context.get("decision")
           approval_chain: list[str] = context.get("approval_chain", [])

           if decision == "approve":
               # Determine which approval was just completed
               current_step = context.get("_current_step", "")
               if "manager" in current_step:
                   approval_chain.append("manager")
               elif "finance" in current_step:
                   approval_chain.append("finance")
               elif "cfo" in current_step:
                   approval_chain.append("cfo")

               context.set("approval_chain", approval_chain)
               context.set("last_approved_at", datetime.now(timezone.utc).isoformat())
               return {"recorded": True, "chain": approval_chain}

           elif decision == "reject":
               context.set("status", "rejected")
               context.set("rejected_at", datetime.now(timezone.utc).isoformat())
               return {"rejected": True}

           else:
               # Request info or defer - keep status as pending
               context.set("status", "awaiting_info")
               return {"pending_info": True}


   class ProcessApproved(BaseMachineStep):
       """Finalize approved expense."""

       name = "process_approved"
       description = "Process fully approved expense"

       async def execute(self, context: WorkflowContext) -> dict[str, Any]:
           """Finalize the approved expense."""
           context.set("status", "approved")
           context.set("approved", True)
           context.set("processed_at", datetime.now(timezone.utc).isoformat())

           # In a real app: trigger payment, update accounting system, etc.
           return {
               "processed": True,
               "expense_id": context.get("expense_id"),
               "amount": context.get("amount"),
               "approval_chain": context.get("approval_chain"),
           }


   class ProcessRejected(BaseMachineStep):
       """Handle rejected expense."""

       name = "process_rejected"
       description = "Process rejected expense"

       async def execute(self, context: WorkflowContext) -> dict[str, Any]:
           """Handle rejection and notify requester."""
           context.set("status", "rejected")
           context.set("processed_at", datetime.now(timezone.utc).isoformat())

           # In a real app: send notification email to requester
           return {
               "processed": True,
               "rejected": True,
               "reason": context.get("comments"),
           }


   # =============================================================================
   # Workflow Definition
   # =============================================================================

   expense_approval_workflow = WorkflowDefinition(
       name="expense_approval",
       version="1.0.0",
       description="Multi-level expense approval with conditional routing",
       steps={
           "submit_expense": SubmitExpense(),
           "amount_router": AmountRouter(),
           "auto_approve": AutoApprove(),
           "manager_approval": ManagerApproval(),
           "finance_approval": FinanceApproval(),
           "cfo_approval": CFOApproval(),
           "record_approval": RecordApproval(),
           "process_approved": ProcessApproved(),
           "process_rejected": ProcessRejected(),
       },
       edges=[
           # Initial submission and routing
           Edge("submit_expense", "amount_router"),

           # Auto-approve path for small expenses
           Edge(
               "amount_router",
               "auto_approve",
               condition="context.get('amount', 0) < 1000"
           ),
           Edge("auto_approve", "process_approved"),

           # Manager approval path
           Edge(
               "amount_router",
               "manager_approval",
               condition="context.get('amount', 0) >= 1000 and 'manager' not in context.get('approval_chain', [])"
           ),

           # Finance approval path
           Edge(
               "amount_router",
               "finance_approval",
               condition="context.get('amount', 0) >= 5000 and 'manager' in context.get('approval_chain', []) and 'finance' not in context.get('approval_chain', [])"
           ),

           # CFO approval path
           Edge(
               "amount_router",
               "cfo_approval",
               condition="context.get('amount', 0) >= 10000 and 'finance' in context.get('approval_chain', []) and 'cfo' not in context.get('approval_chain', [])"
           ),

           # After any human approval, record and re-route
           Edge(
               "manager_approval",
               "record_approval",
               condition="context.get('decision') == 'approve'"
           ),
           Edge(
               "manager_approval",
               "process_rejected",
               condition="context.get('decision') == 'reject'"
           ),

           Edge(
               "finance_approval",
               "record_approval",
               condition="context.get('decision') == 'approve'"
           ),
           Edge(
               "finance_approval",
               "process_rejected",
               condition="context.get('decision') == 'reject'"
           ),

           Edge(
               "cfo_approval",
               "record_approval",
               condition="context.get('decision') == 'approve'"
           ),
           Edge(
               "cfo_approval",
               "process_rejected",
               condition="context.get('decision') == 'reject'"
           ),

           # After recording, check if more approvals needed
           Edge("record_approval", "amount_router"),

           # Final approval when all required approvals obtained
           Edge(
               "amount_router",
               "process_approved",
               condition="len([a for a in context.get('approval_chain', []) if a in ['manager', 'finance', 'cfo']]) >= len([a for a in ['manager', 'finance', 'cfo'][:max(0, (context.get('amount', 0) >= 10000 and 3) or (context.get('amount', 0) >= 5000 and 2) or (context.get('amount', 0) >= 1000 and 1) or 0)]])"
           ),
       ],
       initial_step="submit_expense",
       terminal_steps={"process_approved", "process_rejected"},
   )


   # =============================================================================
   # Application Setup
   # =============================================================================

   def create_app() -> Litestar:
       """Create the Litestar application with expense workflow."""
       # Database setup
       db_engine = create_async_engine(
           "sqlite+aiosqlite:///expenses.db",
           echo=False,
       )
       session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

       # Workflow registry
       registry = WorkflowRegistry()
       registry.register_definition(expense_approval_workflow)

       async def provide_session() -> AsyncSession:
           async with session_factory() as session:
               yield session

       async def provide_engine(session: AsyncSession) -> PersistentExecutionEngine:
           return PersistentExecutionEngine(registry=registry, session=session)

       async def provide_registry() -> WorkflowRegistry:
           return registry

       @get("/health")
       async def health() -> dict[str, str]:
           return {"status": "healthy"}

       return Litestar(
           route_handlers=[health],
           plugins=[
               WorkflowPlugin(
                   config=WorkflowPluginConfig(
                       enable_api=True,
                       api_path_prefix="/api/workflows",
                   )
               ),
           ],
           dependencies={
               "session": Provide(provide_session),
               "workflow_engine": Provide(provide_engine),
               "workflow_registry": Provide(provide_registry),
           },
       )


   app = create_app()


   if __name__ == "__main__":
       import uvicorn
       uvicorn.run(app, host="0.0.0.0", port=8000)


Key Concepts
------------

Multi-Level Approval Chain
~~~~~~~~~~~~~~~~~~~~~~~~~~

The workflow tracks completed approvals in the ``approval_chain`` context variable:

.. code-block:: python

   # Check which approvals have been obtained
   approval_chain = context.get("approval_chain", [])  # ["manager", "finance"]

   # Add a new approval
   approval_chain.append("cfo")
   context.set("approval_chain", approval_chain)

This pattern allows the gateway to determine which approval is needed next.


Conditional Routing
~~~~~~~~~~~~~~~~~~~

Edges use conditions to route based on amount thresholds:

.. code-block:: python

   Edge(
       "amount_router",
       "finance_approval",
       condition="context.get('amount', 0) >= 5000 and 'manager' in context.get('approval_chain', [])"
   )

The condition checks both the amount and the current approval state.


JSON Schema Forms
~~~~~~~~~~~~~~~~~

Human steps define form schemas with validation:

.. code-block:: python

   form_schema = {
       "type": "object",
       "properties": {
           "decision": {
               "type": "string",
               "enum": ["approve", "reject"],
           },
           "budget_code": {
               "type": "string",
               "pattern": "^BUD-[0-9]{6}$",  # Regex validation
           },
       },
       "required": ["decision", "budget_code"],
   }


Customization Points
--------------------

**Approval Thresholds**
    Modify the ``_get_required_approvals`` method in ``AmountRouter``

**Form Fields**
    Update the ``form_schema`` in each human step

**Assignee Logic**
    Override ``get_assignee`` or ``get_assignee_group`` methods

**Notifications**
    Add email/Slack integration in ``ProcessApproved`` and ``ProcessRejected``


Testing the Workflow
--------------------

.. code-block:: python

   """Test the expense approval workflow."""

   import pytest
   from litestar.testing import AsyncTestClient

   from expense_approval import app, expense_approval_workflow


   @pytest.fixture
   def test_client():
       return AsyncTestClient(app)


   @pytest.mark.asyncio
   async def test_small_expense_auto_approved(test_client):
       """Expenses under $1,000 should be auto-approved."""
       response = await test_client.post(
           "/api/workflows/instances",
           json={
               "definition_name": "expense_approval",
               "input_data": {
                   "amount": 500,
                   "requester": "alice@example.com",
                   "description": "Office supplies",
               },
           },
       )
       assert response.status_code == 200
       instance = response.json()

       # Should be completed immediately (auto-approved)
       response = await test_client.get(
           f"/api/workflows/instances/{instance['id']}"
       )
       assert response.json()["status"] == "completed"


   @pytest.mark.asyncio
   async def test_medium_expense_requires_manager(test_client):
       """Expenses $1,000-$4,999 require manager approval."""
       response = await test_client.post(
           "/api/workflows/instances",
           json={
               "definition_name": "expense_approval",
               "input_data": {
                   "amount": 2500,
                   "requester": "bob@example.com",
                   "description": "Conference registration",
               },
           },
       )
       instance = response.json()

       # Should be waiting for manager approval
       response = await test_client.get(
           f"/api/workflows/instances/{instance['id']}"
       )
       assert response.json()["status"] == "waiting"
       assert response.json()["current_step"] == "manager_approval"


Common Variations
-----------------

**Add Email Notifications**

.. code-block:: python

   class ProcessApproved(BaseMachineStep):
       async def execute(self, context: WorkflowContext) -> dict:
           # Existing logic...

           # Send notification
           await email_service.send(
               to=context.get("requester"),
               subject="Expense Approved",
               body=f"Your expense request for ${context.get('amount'):,.2f} has been approved.",
           )

           return {"processed": True}


**Parallel Finance Review**

For higher amounts, require multiple finance approvers in parallel.
See :doc:`/guides/parallel-execution` for the pattern.


**Delegation Support**

Allow approvers to delegate to others:

.. code-block:: python

   class DelegableApproval(BaseHumanStep):
       form_schema = {
           "properties": {
               "action": {
                   "type": "string",
                   "enum": ["approve", "reject", "delegate"],
               },
               "delegate_to": {
                   "type": "string",
                   "title": "Delegate To",
                   "format": "email",
               },
           },
       }


See Also
--------

- :doc:`/guides/human-tasks` - Human task patterns
- :doc:`/guides/conditional-logic` - Gateway and routing patterns
- :doc:`/guides/persistence` - Database persistence setup
- :doc:`/guides/web-plugin` - REST API configuration
