Employee Onboarding Workflow
============================

A complete employee onboarding system with parallel setup tasks,
timer steps for deadline reminders, and coordinated task management
across departments.

This recipe demonstrates:

- Parallel execution of independent setup tasks
- Timer steps for deadline enforcement
- Cross-department task coordination (IT, HR, Manager)
- Progress tracking and status updates
- Escalation handling for overdue tasks


Overview
--------

New employee onboarding requires coordination across multiple departments:

.. code-block:: text

   [Start Onboarding]
         |
         v
   [Parallel Setup] --+--> [IT Setup]      --> [Equipment Delivered]
                      |                           |
                      +--> [HR Paperwork]  --> [Paperwork Complete]
                      |                           |
                      +--> [Manager Prep]  --> [Training Scheduled]
                      |                           |
                      v                           v
               [Wait All Complete]      [Deadline Timer]
                      |                      |
                      v                      v
              [Orientation]         [Escalate if Overdue]
                      |
                      v
              [First Day Complete]

**Key Tasks:**

- **IT Setup**: Account creation, equipment provisioning
- **HR Paperwork**: Tax forms, benefits enrollment
- **Manager Preparation**: Workspace setup, training schedule
- **Orientation**: First-day walkthrough


Complete Implementation
-----------------------

.. code-block:: python

   """Employee onboarding workflow with parallel tasks and deadline tracking.

   Run with:
       uv run python -m employee_onboarding
   """

   from __future__ import annotations

   from datetime import datetime, timedelta, timezone
   from typing import TYPE_CHECKING, Any

   from litestar import Litestar, get
   from litestar.di import Provide
   from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

   from litestar_workflows import (
       BaseMachineStep,
       BaseHumanStep,
       Edge,
       ExclusiveGateway,
       ParallelGroup,
       TimerStep,
       WorkflowContext,
       WorkflowDefinition,
       WorkflowPlugin,
       WorkflowPluginConfig,
       WorkflowRegistry,
   )
   from litestar_workflows.db import PersistentExecutionEngine

   if TYPE_CHECKING:
       pass


   # =============================================================================
   # Step Definitions
   # =============================================================================

   class InitiateOnboarding(BaseMachineStep):
       """Initialize the onboarding process."""

       name = "initiate_onboarding"
       description = "Start onboarding and calculate deadlines"

       async def execute(self, context: WorkflowContext) -> dict[str, Any]:
           """Set up onboarding context with employee info and deadlines."""
           start_date_str = context.get("start_date")
           if not start_date_str:
               # Default to 5 business days from now
               start_date = datetime.now(timezone.utc) + timedelta(days=7)
           else:
               start_date = datetime.fromisoformat(start_date_str)

           context.set("start_date", start_date.isoformat())

           # Calculate deadlines
           # IT setup must be done 2 days before start
           it_deadline = start_date - timedelta(days=2)
           context.set("it_deadline", it_deadline.isoformat())

           # HR paperwork due 1 day before
           hr_deadline = start_date - timedelta(days=1)
           context.set("hr_deadline", hr_deadline.isoformat())

           # Manager prep due on start date
           manager_deadline = start_date
           context.set("manager_deadline", manager_deadline.isoformat())

           context.set("onboarding_status", "in_progress")
           context.set("tasks_completed", [])
           context.set("initiated_at", datetime.now(timezone.utc).isoformat())

           return {
               "initiated": True,
               "employee": context.get("employee_name"),
               "start_date": start_date.isoformat(),
           }


   class ITSetup(BaseHumanStep):
       """IT provisions accounts and equipment."""

       name = "it_setup"
       title = "IT Setup Required"
       description = "Create accounts and prepare equipment for new employee"

       form_schema = {
           "type": "object",
           "title": "IT Onboarding Setup",
           "properties": {
               "email_created": {
                   "type": "boolean",
                   "title": "Email Account Created",
                   "default": False,
               },
               "email_address": {
                   "type": "string",
                   "title": "Email Address",
                   "format": "email",
               },
               "ad_account": {
                   "type": "boolean",
                   "title": "Active Directory Account Created",
                   "default": False,
               },
               "vpn_access": {
                   "type": "boolean",
                   "title": "VPN Access Configured",
                   "default": False,
               },
               "laptop_model": {
                   "type": "string",
                   "title": "Laptop Model",
                   "enum": ["MacBook Pro 14", "MacBook Pro 16", "Dell XPS 15", "ThinkPad X1"],
               },
               "laptop_asset_tag": {
                   "type": "string",
                   "title": "Asset Tag",
                   "pattern": "^[A-Z]{2}[0-9]{6}$",
               },
               "software_installed": {
                   "type": "array",
                   "title": "Software Installed",
                   "items": {
                       "type": "string",
                       "enum": ["Office 365", "Slack", "Zoom", "IDE", "VPN Client"],
                   },
                   "uniqueItems": True,
               },
               "notes": {
                   "type": "string",
                   "title": "Setup Notes",
               },
           },
           "required": ["email_created", "email_address", "ad_account", "laptop_model", "laptop_asset_tag"],
       }

       async def get_description(self, context: WorkflowContext) -> str:
           """Provide employee details for IT team."""
           name = context.get("employee_name", "New Employee")
           department = context.get("department", "Unknown")
           role = context.get("job_title", "Unknown")
           start_date = context.get("start_date", "TBD")
           deadline = context.get("it_deadline", "TBD")

           return f"""
   **IT Setup for New Employee**

   - **Name:** {name}
   - **Department:** {department}
   - **Role:** {role}
   - **Start Date:** {start_date}
   - **Setup Deadline:** {deadline}

   Please create all necessary accounts and prepare equipment.
   """

       async def get_assignee_group(self, context: WorkflowContext) -> str | None:
           """Route to IT team."""
           return "it-support"

       async def get_due_date(self, context: WorkflowContext) -> datetime:
           """Return IT deadline from context."""
           deadline_str = context.get("it_deadline")
           if deadline_str:
               return datetime.fromisoformat(deadline_str)
           return datetime.now(timezone.utc) + timedelta(days=5)


   class HRPaperwork(BaseHumanStep):
       """HR processes required documentation."""

       name = "hr_paperwork"
       title = "HR Documentation Required"
       description = "Process new hire paperwork and benefits enrollment"

       form_schema = {
           "type": "object",
           "title": "HR Onboarding",
           "properties": {
               "i9_verified": {
                   "type": "boolean",
                   "title": "I-9 Verified",
                   "default": False,
               },
               "w4_completed": {
                   "type": "boolean",
                   "title": "W-4 Completed",
                   "default": False,
               },
               "direct_deposit": {
                   "type": "boolean",
                   "title": "Direct Deposit Setup",
                   "default": False,
               },
               "benefits_enrolled": {
                   "type": "boolean",
                   "title": "Benefits Enrollment Complete",
                   "default": False,
               },
               "benefits_package": {
                   "type": "string",
                   "title": "Benefits Package",
                   "enum": ["Basic", "Standard", "Premium", "Executive"],
               },
               "emergency_contact_provided": {
                   "type": "boolean",
                   "title": "Emergency Contact Provided",
                   "default": False,
               },
               "handbook_acknowledged": {
                   "type": "boolean",
                   "title": "Employee Handbook Acknowledged",
                   "default": False,
               },
               "background_check_status": {
                   "type": "string",
                   "title": "Background Check Status",
                   "enum": ["pending", "passed", "review_required"],
               },
               "notes": {
                   "type": "string",
                   "title": "HR Notes",
               },
           },
           "required": ["i9_verified", "w4_completed", "direct_deposit", "background_check_status"],
       }

       async def get_assignee_group(self, context: WorkflowContext) -> str | None:
           """Route to HR team."""
           return "hr-team"

       async def get_due_date(self, context: WorkflowContext) -> datetime:
           """Return HR deadline."""
           deadline_str = context.get("hr_deadline")
           if deadline_str:
               return datetime.fromisoformat(deadline_str)
           return datetime.now(timezone.utc) + timedelta(days=6)


   class ManagerPreparation(BaseHumanStep):
       """Manager prepares for new team member."""

       name = "manager_preparation"
       title = "Manager Preparation Required"
       description = "Prepare workspace and training plan for new hire"

       form_schema = {
           "type": "object",
           "title": "Manager Preparation",
           "properties": {
               "workspace_ready": {
                   "type": "boolean",
                   "title": "Workspace Prepared",
                   "default": False,
               },
               "workspace_location": {
                   "type": "string",
                   "title": "Workspace Location",
                   "description": "Desk/office assignment",
               },
               "buddy_assigned": {
                   "type": "boolean",
                   "title": "Onboarding Buddy Assigned",
                   "default": False,
               },
               "buddy_name": {
                   "type": "string",
                   "title": "Buddy Name",
               },
               "training_plan_created": {
                   "type": "boolean",
                   "title": "Training Plan Created",
                   "default": False,
               },
               "first_week_schedule": {
                   "type": "string",
                   "title": "First Week Schedule",
                   "format": "textarea",
                   "description": "Outline of first week activities",
               },
               "team_notified": {
                   "type": "boolean",
                   "title": "Team Notified",
                   "default": False,
               },
               "initial_projects": {
                   "type": "array",
                   "title": "Initial Projects/Tasks",
                   "items": {
                       "type": "string",
                   },
               },
               "notes": {
                   "type": "string",
                   "title": "Manager Notes",
               },
           },
           "required": ["workspace_ready", "buddy_assigned", "training_plan_created", "team_notified"],
       }

       async def get_assignee(self, context: WorkflowContext) -> str | None:
           """Route to the hiring manager."""
           return context.get("manager_email")

       async def get_due_date(self, context: WorkflowContext) -> datetime:
           """Return manager deadline."""
           deadline_str = context.get("manager_deadline")
           if deadline_str:
               return datetime.fromisoformat(deadline_str)
           return datetime.now(timezone.utc) + timedelta(days=7)


   class CheckAllTasksComplete(BaseMachineStep):
       """Verify all setup tasks are complete."""

       name = "check_all_complete"
       description = "Verify all onboarding tasks completed successfully"

       async def execute(self, context: WorkflowContext) -> dict[str, Any]:
           """Check completion status of all parallel tasks."""
           it_complete = context.get("it_setup_email_created", False)
           hr_complete = context.get("hr_paperwork_i9_verified", False)
           manager_complete = context.get("manager_preparation_workspace_ready", False)

           all_complete = it_complete and hr_complete and manager_complete

           context.set("all_tasks_complete", all_complete)
           context.set(
               "tasks_completed",
               [
                   "it_setup" if it_complete else None,
                   "hr_paperwork" if hr_complete else None,
                   "manager_preparation" if manager_complete else None,
               ],
           )

           # Compile summary
           summary = {
               "employee_email": context.get("it_setup_email_address"),
               "laptop": context.get("it_setup_laptop_model"),
               "benefits": context.get("hr_paperwork_benefits_package"),
               "workspace": context.get("manager_preparation_workspace_location"),
               "buddy": context.get("manager_preparation_buddy_name"),
           }
           context.set("onboarding_summary", summary)

           return {
               "all_complete": all_complete,
               "summary": summary,
           }


   class OnboardingRouter(ExclusiveGateway):
       """Route based on task completion status."""

       name = "onboarding_router"
       description = "Determine next step based on completion status"

       async def evaluate(self, context: WorkflowContext) -> str:
           """Route to orientation or handle incomplete tasks."""
           all_complete = context.get("all_tasks_complete", False)

           if all_complete:
               return "orientation"
           else:
               return "handle_incomplete"


   class HandleIncomplete(BaseMachineStep):
       """Handle case when not all tasks are complete."""

       name = "handle_incomplete"
       description = "Escalate or wait for incomplete tasks"

       async def execute(self, context: WorkflowContext) -> dict[str, Any]:
           """Identify and escalate incomplete tasks."""
           tasks_completed = context.get("tasks_completed", [])
           incomplete = [t for t in ["it_setup", "hr_paperwork", "manager_preparation"]
                        if t not in tasks_completed]

           context.set("incomplete_tasks", incomplete)
           context.set("onboarding_status", "blocked")

           # In a real app: send escalation emails
           return {
               "escalated": True,
               "incomplete_tasks": incomplete,
           }


   class Orientation(BaseHumanStep):
       """First day orientation session."""

       name = "orientation"
       title = "Conduct Orientation"
       description = "Complete first-day orientation with new employee"

       form_schema = {
           "type": "object",
           "title": "Orientation Checklist",
           "properties": {
               "welcome_completed": {
                   "type": "boolean",
                   "title": "Welcome Session Completed",
                   "default": False,
               },
               "tour_completed": {
                   "type": "boolean",
                   "title": "Office Tour Completed",
                   "default": False,
               },
               "team_introductions": {
                   "type": "boolean",
                   "title": "Team Introductions Done",
                   "default": False,
               },
               "systems_access_verified": {
                   "type": "boolean",
                   "title": "Systems Access Verified",
                   "default": False,
               },
               "security_training": {
                   "type": "boolean",
                   "title": "Security Training Completed",
                   "default": False,
               },
               "questions_addressed": {
                   "type": "boolean",
                   "title": "Initial Questions Addressed",
                   "default": False,
               },
               "employee_feedback": {
                   "type": "string",
                   "title": "Employee First Day Feedback",
                   "format": "textarea",
               },
               "issues_noted": {
                   "type": "string",
                   "title": "Any Issues Noted",
               },
           },
           "required": ["welcome_completed", "tour_completed", "team_introductions", "systems_access_verified"],
       }

       async def get_assignee(self, context: WorkflowContext) -> str | None:
           """Route to hiring manager for orientation."""
           return context.get("manager_email")

       async def get_due_date(self, context: WorkflowContext) -> datetime:
           """Due on start date."""
           start_date_str = context.get("start_date")
           if start_date_str:
               return datetime.fromisoformat(start_date_str)
           return datetime.now(timezone.utc) + timedelta(days=7)


   class CompleteOnboarding(BaseMachineStep):
       """Finalize the onboarding process."""

       name = "complete_onboarding"
       description = "Mark onboarding as complete"

       async def execute(self, context: WorkflowContext) -> dict[str, Any]:
           """Finalize onboarding and create summary."""
           context.set("onboarding_status", "completed")
           context.set("completed_at", datetime.now(timezone.utc).isoformat())

           summary = context.get("onboarding_summary", {})
           summary["orientation_complete"] = True
           summary["first_day_feedback"] = context.get("orientation_employee_feedback")

           context.set("final_summary", summary)

           # In a real app: update HRIS, send welcome email, create 30/60/90 day check-ins
           return {
               "completed": True,
               "employee": context.get("employee_name"),
               "summary": summary,
           }


   # =============================================================================
   # Timer Step for Deadline Reminders
   # =============================================================================

   def calculate_reminder_delay(context: WorkflowContext) -> timedelta:
       """Calculate when to send deadline reminder."""
       start_date_str = context.get("start_date")
       if start_date_str:
           start_date = datetime.fromisoformat(start_date_str)
           # Remind 3 days before start date
           reminder_date = start_date - timedelta(days=3)
           now = datetime.now(timezone.utc)
           if reminder_date > now:
               return reminder_date - now
       return timedelta(days=2)  # Default 2 day delay


   deadline_reminder = TimerStep(
       name="deadline_reminder",
       duration=calculate_reminder_delay,
       description="Wait until deadline reminder time",
   )


   class SendDeadlineReminder(BaseMachineStep):
       """Send reminder for approaching deadlines."""

       name = "send_reminder"
       description = "Send deadline reminder notifications"

       async def execute(self, context: WorkflowContext) -> dict[str, Any]:
           """Check and send reminders for incomplete tasks."""
           tasks_completed = context.get("tasks_completed", [])
           reminders_sent = []

           if "it_setup" not in tasks_completed:
               # In real app: send reminder to IT
               reminders_sent.append("it_setup")

           if "hr_paperwork" not in tasks_completed:
               # In real app: send reminder to HR
               reminders_sent.append("hr_paperwork")

           if "manager_preparation" not in tasks_completed:
               # In real app: send reminder to manager
               reminders_sent.append("manager_preparation")

           context.set("reminders_sent", reminders_sent)

           return {
               "reminders_sent": reminders_sent,
               "reminder_count": len(reminders_sent),
           }


   # =============================================================================
   # Workflow Definition
   # =============================================================================

   # Create parallel setup group
   parallel_setup = ParallelGroup(
       ITSetup(),
       HRPaperwork(),
       ManagerPreparation(),
   )


   onboarding_workflow = WorkflowDefinition(
       name="employee_onboarding",
       version="1.0.0",
       description="Employee onboarding with parallel setup and deadline tracking",
       steps={
           "initiate_onboarding": InitiateOnboarding(),
           "parallel_setup": parallel_setup,
           "check_all_complete": CheckAllTasksComplete(),
           "onboarding_router": OnboardingRouter(),
           "handle_incomplete": HandleIncomplete(),
           "orientation": Orientation(),
           "complete_onboarding": CompleteOnboarding(),
           "deadline_reminder": deadline_reminder,
           "send_reminder": SendDeadlineReminder(),
       },
       edges=[
           # Main flow
           Edge("initiate_onboarding", "parallel_setup"),
           Edge("parallel_setup", "check_all_complete"),
           Edge("check_all_complete", "onboarding_router"),

           # Success path
           Edge(
               "onboarding_router",
               "orientation",
               condition="context.get('all_tasks_complete') == True"
           ),
           Edge("orientation", "complete_onboarding"),

           # Incomplete path
           Edge(
               "onboarding_router",
               "handle_incomplete",
               condition="context.get('all_tasks_complete') == False"
           ),

           # Timer-based reminder (runs in parallel with setup)
           Edge("initiate_onboarding", "deadline_reminder"),
           Edge("deadline_reminder", "send_reminder"),
       ],
       initial_step="initiate_onboarding",
       terminal_steps={"complete_onboarding", "handle_incomplete"},
   )


   # =============================================================================
   # Application Setup
   # =============================================================================

   def create_app() -> Litestar:
       """Create the Litestar application with onboarding workflow."""
       db_engine = create_async_engine(
           "sqlite+aiosqlite:///onboarding.db",
           echo=False,
       )
       session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

       registry = WorkflowRegistry()
       registry.register_definition(onboarding_workflow)

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

Parallel Task Execution
~~~~~~~~~~~~~~~~~~~~~~~

Multiple departments work simultaneously:

.. code-block:: python

   from litestar_workflows import ParallelGroup

   parallel_setup = ParallelGroup(
       ITSetup(),
       HRPaperwork(),
       ManagerPreparation(),
   )

All three tasks are created at once, and the workflow waits until all
are completed before proceeding to verification.


Timer Steps for Deadlines
~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``TimerStep`` to schedule future actions:

.. code-block:: python

   from datetime import timedelta
   from litestar_workflows import TimerStep

   # Static duration
   reminder = TimerStep(
       name="reminder",
       duration=timedelta(days=2),
       description="Wait 2 days before reminder",
   )

   # Dynamic duration based on context
   def calculate_delay(context: WorkflowContext) -> timedelta:
       deadline = datetime.fromisoformat(context.get("deadline"))
       reminder_time = deadline - timedelta(days=1)
       return reminder_time - datetime.now(timezone.utc)

   dynamic_reminder = TimerStep(
       name="dynamic_reminder",
       duration=calculate_delay,
       description="Wait until day before deadline",
   )


Cross-Department Coordination
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Route tasks to different teams using groups:

.. code-block:: python

   class ITSetup(BaseHumanStep):
       async def get_assignee_group(self, context: WorkflowContext) -> str:
           return "it-support"

   class HRPaperwork(BaseHumanStep):
       async def get_assignee_group(self, context: WorkflowContext) -> str:
           return "hr-team"

   class ManagerPreparation(BaseHumanStep):
       async def get_assignee(self, context: WorkflowContext) -> str:
           # Route to specific manager
           return context.get("manager_email")


Customization Points
--------------------

**Add More Setup Tasks**
    Add steps to the ``ParallelGroup`` (e.g., security badge, parking)

**Adjust Deadlines**
    Modify deadline calculations in ``InitiateOnboarding``

**Change Reminder Frequency**
    Add multiple timer steps for periodic reminders

**Add Department-Specific Fields**
    Customize ``form_schema`` for each department's needs


Usage Example
-------------

Start an onboarding workflow:

.. code-block:: bash

   curl -X POST http://localhost:8000/api/workflows/instances \
     -H "Content-Type: application/json" \
     -d '{
       "definition_name": "employee_onboarding",
       "input_data": {
         "employee_name": "Alice Johnson",
         "employee_email": "alice.johnson@example.com",
         "department": "Engineering",
         "job_title": "Senior Developer",
         "manager_email": "bob.smith@example.com",
         "start_date": "2025-12-15T09:00:00Z"
       }
     }'

View pending tasks for IT team:

.. code-block:: bash

   curl "http://localhost:8000/api/workflows/tasks?assignee_group=it-support&status=pending"


Testing
-------

.. code-block:: python

   import pytest
   from datetime import datetime, timedelta, timezone
   from litestar_workflows import WorkflowContext

   from employee_onboarding import InitiateOnboarding, calculate_reminder_delay


   @pytest.mark.asyncio
   async def test_deadline_calculation():
       """Verify deadline calculation logic."""
       context = WorkflowContext()
       start_date = datetime.now(timezone.utc) + timedelta(days=7)
       context.set("start_date", start_date.isoformat())

       step = InitiateOnboarding()
       await step.execute(context)

       it_deadline = datetime.fromisoformat(context.get("it_deadline"))
       expected = start_date - timedelta(days=2)

       # IT deadline should be 2 days before start
       assert it_deadline.date() == expected.date()


   def test_reminder_delay_calculation():
       """Verify reminder timing."""
       context = WorkflowContext()
       start_date = datetime.now(timezone.utc) + timedelta(days=7)
       context.set("start_date", start_date.isoformat())

       delay = calculate_reminder_delay(context)

       # Should remind 3 days before start (so ~4 days from now)
       assert delay > timedelta(days=3)
       assert delay < timedelta(days=5)


Common Variations
-----------------

**Add Security Badge Processing**

.. code-block:: python

   class SecurityBadge(BaseHumanStep):
       name = "security_badge"
       title = "Security Badge Setup"

       form_schema = {
           "properties": {
               "photo_taken": {"type": "boolean"},
               "badge_number": {"type": "string"},
               "access_level": {"type": "string", "enum": ["standard", "restricted", "full"]},
           },
       }

       async def get_assignee_group(self, context):
           return "security-team"

   # Add to parallel group
   parallel_setup = ParallelGroup(
       ITSetup(),
       HRPaperwork(),
       ManagerPreparation(),
       SecurityBadge(),
   )


**Recurring Check-in Reminders**

Schedule 30/60/90 day check-ins:

.. code-block:: python

   thirty_day_checkin = TimerStep(
       name="thirty_day_timer",
       duration=timedelta(days=30),
       description="Wait for 30-day check-in",
   )

   class ThirtyDayCheckin(BaseHumanStep):
       name = "thirty_day_checkin"
       title = "30-Day Check-in"
       form_schema = {
           "properties": {
               "settling_in_well": {"type": "boolean"},
               "training_on_track": {"type": "boolean"},
               "concerns": {"type": "string"},
           },
       }


See Also
--------

- :doc:`/guides/parallel-execution` - Parallel step patterns
- :doc:`/guides/human-tasks` - Human task configuration
- :doc:`expense-approval` - Multi-level approval patterns
- :doc:`integration-patterns` - External API integration
