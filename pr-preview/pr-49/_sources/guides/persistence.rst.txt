Database Persistence
====================

This guide covers how to set up database persistence for your workflows using
the ``[db]`` extra. With persistence enabled, your workflow state survives
application restarts, and you gain access to powerful querying capabilities.


Why Use Persistence?
--------------------

By default, ``LocalExecutionEngine`` keeps workflow state in memory. While this
is fine for development and testing, production workloads need durability:

**Without persistence:**

- Workflow state is lost if the application crashes
- Human tasks cannot survive restarts
- No audit trail of workflow executions
- No way to query workflow history

**With persistence:**

- Durable workflow state across restarts
- Queryable workflow history and audit trail
- Human tasks can wait indefinitely
- Multi-process and multi-instance deployment support


Installation
------------

Install the ``[db]`` extra to enable persistence:

.. code-block:: bash

   pip install litestar-workflows[db]

This adds the following dependencies:

- **advanced-alchemy**: SQLAlchemy async repository pattern
- **alembic**: Database migration management


Database Setup
--------------

The persistence layer supports any database supported by SQLAlchemy:

- **PostgreSQL** (recommended for production)
- **SQLite** (great for development and testing)
- **MySQL/MariaDB**
- **Oracle, MSSQL**, etc.


Creating Tables
~~~~~~~~~~~~~~~

There are two ways to create the required database tables:


Option 1: Using Alembic Migrations (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For production deployments, use Alembic migrations for version-controlled
schema changes:

.. code-block:: bash

   # Set your database URL
   export WORKFLOW_DATABASE_URL="postgresql+asyncpg://user:pass@localhost/workflows"

   # Run migrations
   alembic -c src/litestar_workflows/db/migrations/alembic.ini upgrade head

The migrations create four tables:

- ``workflow_definitions`` - Stores workflow definition metadata
- ``workflow_instances`` - Tracks running/completed workflow instances
- ``workflow_step_executions`` - Records individual step executions
- ``workflow_human_tasks`` - Manages pending human approval tasks


Option 2: Direct Table Creation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For quick setup or testing, you can create tables directly:

.. code-block:: python

   from sqlalchemy.ext.asyncio import create_async_engine
   from advanced_alchemy.base import UUIDAuditBase

   # Import models to register them
   from litestar_workflows.db import (
       WorkflowDefinitionModel,
       WorkflowInstanceModel,
       StepExecutionModel,
       HumanTaskModel,
   )

   async def create_tables():
       engine = create_async_engine("sqlite+aiosqlite:///workflows.db")
       async with engine.begin() as conn:
           await conn.run_sync(UUIDAuditBase.metadata.create_all)

   asyncio.run(create_tables())


Using PersistentExecutionEngine
-------------------------------

The ``PersistentExecutionEngine`` is a drop-in replacement for
``LocalExecutionEngine`` that stores all workflow state in the database.


Basic Setup
~~~~~~~~~~~

.. code-block:: python

   from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
   from litestar_workflows import WorkflowRegistry
   from litestar_workflows.db import PersistentExecutionEngine

   # Create async engine and session factory
   engine = create_async_engine(
       "postgresql+asyncpg://user:pass@localhost/workflows",
       echo=True,  # Enable SQL logging for development
   )
   session_factory = async_sessionmaker(engine, expire_on_commit=False)

   # Create registry with workflow definitions
   registry = WorkflowRegistry()
   registry.register_definition(MyWorkflow.get_definition())
   registry.register_workflow_class(MyWorkflow)

   # Create persistent engine with a session
   async with session_factory() as session:
       engine = PersistentExecutionEngine(
           registry=registry,
           session=session,
       )

       # Start a workflow - state is automatically persisted
       instance = await engine.start_workflow(
           MyWorkflow,
           initial_data={"customer_id": "cust-123"},
           tenant_id="acme-corp",  # Optional: multi-tenancy support
           created_by="user@example.com",  # Optional: audit trail
       )


Litestar Integration
~~~~~~~~~~~~~~~~~~~~

Here's how to integrate the persistent engine with a Litestar application:

.. code-block:: python

   from litestar import Litestar, get, post
   from litestar.di import Provide
   from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
   from litestar_workflows import WorkflowRegistry
   from litestar_workflows.db import PersistentExecutionEngine

   # Database setup
   engine = create_async_engine("postgresql+asyncpg://localhost/workflows")
   session_factory = async_sessionmaker(engine, expire_on_commit=False)

   # Workflow registry
   registry = WorkflowRegistry()
   registry.register_definition(ApprovalWorkflow.get_definition())
   registry.register_workflow_class(ApprovalWorkflow)


   async def provide_session() -> AsyncSession:
       """Provide database session for dependency injection."""
       async with session_factory() as session:
           yield session


   async def provide_engine(session: AsyncSession) -> PersistentExecutionEngine:
       """Provide persistent workflow engine."""
       return PersistentExecutionEngine(
           registry=registry,
           session=session,
       )


   @post("/workflows/{name}/start")
   async def start_workflow(
       name: str,
       data: dict,
       engine: PersistentExecutionEngine,
   ) -> dict:
       """Start a new workflow instance with persistence."""
       workflow_class = registry.get_workflow_class(name)
       instance = await engine.start_workflow(workflow_class, initial_data=data)
       return {"instance_id": str(instance.id), "status": instance.status.value}


   app = Litestar(
       route_handlers=[start_workflow],
       dependencies={
           "session": Provide(provide_session),
           "engine": Provide(provide_engine),
       },
   )


Working with Repositories
-------------------------

The ``[db]`` extra provides four repository classes for direct database access:


WorkflowDefinitionRepository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Manage workflow definitions with versioning:

.. code-block:: python

   from litestar_workflows.db import WorkflowDefinitionRepository

   async with session_factory() as session:
       repo = WorkflowDefinitionRepository(session=session)

       # Get latest active version of a workflow
       definition = await repo.get_latest_version("approval_workflow")

       # Get specific version
       definition = await repo.get_by_name("approval_workflow", version="1.0.0")

       # List all active definitions
       all_definitions = await repo.list_active()

       # Deactivate an old version
       await repo.deactivate_version("approval_workflow", "1.0.0")


WorkflowInstanceRepository
~~~~~~~~~~~~~~~~~~~~~~~~~~

Query and manage workflow instances:

.. code-block:: python

   from litestar_workflows.db import WorkflowInstanceRepository
   from litestar_workflows import WorkflowStatus

   async with session_factory() as session:
       repo = WorkflowInstanceRepository(session=session)

       # Find instances by workflow name
       instances, total = await repo.find_by_workflow(
           workflow_name="approval_workflow",
           status=WorkflowStatus.RUNNING,
           limit=50,
           offset=0,
       )

       # Find instances by user
       my_instances = await repo.find_by_user("user@example.com")

       # Find instances by tenant (multi-tenancy)
       tenant_instances, total = await repo.find_by_tenant(
           tenant_id="acme-corp",
           status=WorkflowStatus.COMPLETED,
       )

       # Find all running or waiting instances
       active_instances = await repo.find_running()

       # Update instance status
       await repo.update_status(
           instance_id=instance.id,
           status=WorkflowStatus.FAILED,
           error="External service unavailable",
       )


StepExecutionRepository
~~~~~~~~~~~~~~~~~~~~~~~

Access step execution history:

.. code-block:: python

   from litestar_workflows.db import StepExecutionRepository

   async with session_factory() as session:
       repo = StepExecutionRepository(session=session)

       # Get all step executions for an instance
       executions = await repo.find_by_instance(instance_id)

       # Find a specific step execution
       step = await repo.find_by_step_name(instance_id, "approval_step")

       # Find all failed steps (for debugging/monitoring)
       failed_steps = await repo.find_failed(instance_id=instance_id)


HumanTaskRepository
~~~~~~~~~~~~~~~~~~~

Manage pending human tasks:

.. code-block:: python

   from litestar_workflows.db import HumanTaskRepository

   async with session_factory() as session:
       repo = HumanTaskRepository(session=session)

       # Find pending tasks for a user
       my_tasks = await repo.find_pending(assignee_id="user@example.com")

       # Find pending tasks for a group
       team_tasks = await repo.find_pending(assignee_group="managers")

       # Find all tasks for an instance
       instance_tasks = await repo.find_by_instance(instance_id)

       # Find overdue tasks
       overdue = await repo.find_overdue()

       # Complete a task
       await repo.complete_task(task_id, completed_by="user@example.com")

       # Cancel a task
       await repo.cancel_task(task_id)


Human Task Management
---------------------

The persistence layer excels at managing human approval workflows. When a
workflow reaches a human step, the engine:

1. Creates a ``StepExecutionModel`` record with status ``WAITING``
2. Creates a ``HumanTaskModel`` record with task details
3. Sets the workflow instance status to ``WAITING``
4. Persists all state and returns control

When the task is completed:

.. code-block:: python

   # Complete a human task
   await engine.complete_human_task(
       instance_id=instance_id,
       step_name="manager_approval",
       user_id="manager@example.com",
       data={
           "approved": True,
           "comments": "Looks good!",
       },
   )

   # The workflow automatically resumes execution


Building a Task Inbox
~~~~~~~~~~~~~~~~~~~~~

Here's how to build a task inbox for users:

.. code-block:: python

   from litestar import get
   from litestar_workflows.db import HumanTaskRepository

   @get("/tasks")
   async def get_my_tasks(
       session: AsyncSession,
       current_user: str,  # From auth middleware
   ) -> list[dict]:
       """Get pending tasks for current user."""
       repo = HumanTaskRepository(session=session)
       tasks = await repo.find_pending(assignee_id=current_user)

       return [
           {
               "id": str(task.id),
               "title": task.title,
               "description": task.description,
               "workflow_instance_id": str(task.instance_id),
               "form_schema": task.form_schema,
               "due_at": task.due_at.isoformat() if task.due_at else None,
               "created_at": task.created_at.isoformat(),
           }
           for task in tasks
       ]


Multi-Tenancy
-------------

The persistence layer supports multi-tenancy out of the box. Specify a
``tenant_id`` when starting workflows:

.. code-block:: python

   instance = await engine.start_workflow(
       workflow_class,
       initial_data=data,
       tenant_id="tenant-123",  # Tenant isolation
   )

   # Query by tenant
   repo = WorkflowInstanceRepository(session=session)
   tenant_workflows, total = await repo.find_by_tenant(
       tenant_id="tenant-123",
       limit=100,
   )


Database Schema
---------------

The persistence layer creates four tables:


workflow_definitions
~~~~~~~~~~~~~~~~~~~~

Stores workflow definition metadata:

.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * - Column
     - Type
     - Description
   * - id
     - UUID
     - Primary key
   * - name
     - VARCHAR(255)
     - Workflow name (indexed)
   * - version
     - VARCHAR(50)
     - Semantic version
   * - description
     - TEXT
     - Human-readable description
   * - definition_json
     - JSON/JSONB
     - Serialized workflow definition
   * - is_active
     - BOOLEAN
     - Active for new instances
   * - created_at
     - TIMESTAMP
     - Creation timestamp
   * - updated_at
     - TIMESTAMP
     - Last update timestamp


workflow_instances
~~~~~~~~~~~~~~~~~~

Stores workflow execution state:

.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * - Column
     - Type
     - Description
   * - id
     - UUID
     - Primary key
   * - definition_id
     - UUID
     - FK to workflow_definitions
   * - workflow_name
     - VARCHAR(255)
     - Denormalized workflow name
   * - workflow_version
     - VARCHAR(50)
     - Denormalized version
   * - status
     - VARCHAR(50)
     - Current status (indexed)
   * - current_step
     - VARCHAR(255)
     - Current step name
   * - context_data
     - JSON/JSONB
     - Workflow context data
   * - metadata
     - JSON/JSONB
     - Instance metadata
   * - error
     - TEXT
     - Error message (if failed)
   * - started_at
     - TIMESTAMP
     - Execution start time
   * - completed_at
     - TIMESTAMP
     - Completion time (nullable)
   * - tenant_id
     - VARCHAR(255)
     - Tenant ID (indexed, nullable)
   * - created_by
     - VARCHAR(255)
     - Creator user ID (indexed)


workflow_step_executions
~~~~~~~~~~~~~~~~~~~~~~~~

Records individual step executions:

.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * - Column
     - Type
     - Description
   * - id
     - UUID
     - Primary key
   * - instance_id
     - UUID
     - FK to workflow_instances
   * - step_name
     - VARCHAR(255)
     - Step name (indexed)
   * - step_type
     - VARCHAR(50)
     - Step type (MACHINE, HUMAN, etc.)
   * - status
     - VARCHAR(50)
     - Execution status (indexed)
   * - input_data
     - JSON/JSONB
     - Step input data (nullable)
   * - output_data
     - JSON/JSONB
     - Step output data (nullable)
   * - error
     - TEXT
     - Error message (nullable)
   * - started_at
     - TIMESTAMP
     - Step start time
   * - completed_at
     - TIMESTAMP
     - Step completion time
   * - assigned_to
     - VARCHAR(255)
     - Assigned user (human tasks)
   * - completed_by
     - VARCHAR(255)
     - Completing user (human tasks)


workflow_human_tasks
~~~~~~~~~~~~~~~~~~~~

Tracks pending human approval tasks:

.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * - Column
     - Type
     - Description
   * - id
     - UUID
     - Primary key
   * - instance_id
     - UUID
     - FK to workflow_instances
   * - step_execution_id
     - UUID
     - FK to workflow_step_executions
   * - step_name
     - VARCHAR(255)
     - Step name
   * - title
     - VARCHAR(500)
     - Task display title
   * - description
     - TEXT
     - Task description
   * - form_schema
     - JSON/JSONB
     - JSON Schema for task form
   * - assignee_id
     - VARCHAR(255)
     - Assigned user (indexed)
   * - assignee_group
     - VARCHAR(255)
     - Assigned group (indexed)
   * - due_at
     - TIMESTAMP
     - Due date (indexed, nullable)
   * - reminder_at
     - TIMESTAMP
     - Reminder time (nullable)
   * - status
     - VARCHAR(50)
     - Task status (indexed)
   * - completed_at
     - TIMESTAMP
     - Completion time (nullable)
   * - completed_by
     - VARCHAR(255)
     - Completing user


Best Practices
--------------


Use Connection Pooling
~~~~~~~~~~~~~~~~~~~~~~

For production, configure connection pooling:

.. code-block:: python

   from sqlalchemy.ext.asyncio import create_async_engine

   engine = create_async_engine(
       "postgresql+asyncpg://localhost/workflows",
       pool_size=20,
       max_overflow=10,
       pool_timeout=30,
       pool_recycle=1800,
   )


Handle Session Scope Carefully
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each workflow execution should have its own session to avoid conflicts:

.. code-block:: python

   # Good: Session per request
   @post("/workflows/{name}/start")
   async def start_workflow(
       name: str,
       session: AsyncSession,  # Injected per-request
   ) -> dict:
       engine = PersistentExecutionEngine(registry=registry, session=session)
       instance = await engine.start_workflow(...)
       return {...}


Monitor Pending Tasks
~~~~~~~~~~~~~~~~~~~~~

Set up monitoring for overdue tasks:

.. code-block:: python

   from datetime import datetime, timezone

   async def check_overdue_tasks():
       """Alert on overdue human tasks."""
       async with session_factory() as session:
           repo = HumanTaskRepository(session=session)
           overdue = await repo.find_overdue()

           for task in overdue:
               hours_overdue = (datetime.now(timezone.utc) - task.due_at).total_seconds() / 3600
               logger.warning(
                   f"Task {task.id} is {hours_overdue:.1f}h overdue",
                   extra={"task_id": str(task.id), "title": task.title},
               )


See Also
--------

- :doc:`/concepts/execution` - Execution engine concepts
- :doc:`human-tasks` - Human task workflows
- :doc:`/api/index` - Complete API reference
