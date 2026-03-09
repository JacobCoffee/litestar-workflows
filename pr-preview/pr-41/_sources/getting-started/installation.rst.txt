Installation
============

This guide covers how to install litestar-workflows and its optional dependencies.


Basic Installation
------------------

Install the core package using uv (recommended) or pip:

.. code-block:: bash

   # Using uv (recommended)
   uv add litestar-workflows

   # Using pip
   pip install litestar-workflows

This installs the core library with:

- Workflow definition classes
- Step types (machine, human, gateway, etc.)
- Local execution engine
- In-memory workflow registry


Optional Extras
---------------

litestar-workflows provides several optional extras for additional functionality:


Database Persistence (``[db]``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For persistent workflow storage with SQLAlchemy:

.. code-block:: bash

   pip install litestar-workflows[db]

This adds:

- **advanced-alchemy**: Async SQLAlchemy repository pattern for database operations
- **alembic**: Database migration management for version-controlled schema changes

With the ``[db]`` extra, you get:

- ``PersistentExecutionEngine`` - Drop-in replacement for ``LocalExecutionEngine`` with database persistence
- SQLAlchemy models for workflows, instances, step executions, and human tasks
- Repository classes with powerful query capabilities
- Multi-tenancy support with ``tenant_id`` filtering
- Alembic migrations for production deployments

Quick setup:

.. code-block:: python

   from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
   from litestar_workflows import WorkflowRegistry
   from litestar_workflows.db import PersistentExecutionEngine

   engine = create_async_engine("sqlite+aiosqlite:///workflows.db")
   session_factory = async_sessionmaker(engine, expire_on_commit=False)

   registry = WorkflowRegistry()
   # ... register workflows ...

   async with session_factory() as session:
       persistent_engine = PersistentExecutionEngine(
           registry=registry,
           session=session,
       )
       instance = await persistent_engine.start_workflow(MyWorkflow)

See :doc:`/guides/persistence` for a complete guide on database persistence


Web UI (``[ui]``)
~~~~~~~~~~~~~~~~~

For Jinja2-based workflow management templates:

.. code-block:: bash

   pip install litestar-workflows[ui]

This adds:

- Pre-built HTML templates for workflow management
- Task list and detail views
- Form rendering for human tasks


All Extras
~~~~~~~~~~

Install everything at once:

.. code-block:: bash

   pip install litestar-workflows[db,ui]


Development Installation
------------------------

For contributing to litestar-workflows, we recommend using `uv <https://docs.astral.sh/uv/>`_:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/JacobCoffee/litestar-workflows.git
   cd litestar-workflows

   # Install with all development dependencies using uv
   uv sync --all-groups

   # Run tests
   uv run pytest

   # Run linters
   uv run ruff check .
   uv run ty

   # Or use make targets
   make ci  # Run all CI checks (lint + fmt + test)

Version Bumping (uv 0.7+)
~~~~~~~~~~~~~~~~~~~~~~~~~

If using uv 0.7+, you can easily manage package versions:

.. code-block:: bash

   # Show current version
   uv version                 # e.g., "litestar-workflows 0.2.0"

   # Bump versions
   uv version --bump patch    # 0.2.0 => 0.2.1
   uv version --bump minor    # 0.2.1 => 0.3.0
   uv version --bump major    # 0.3.0 => 1.0.0

   # Show uv version
   uv self version


Verify Installation
-------------------

Verify your installation by checking the version:

.. code-block:: python

   >>> import litestar_workflows
   >>> print(litestar_workflows.__version__)
   0.1.0

Or from the command line:

.. code-block:: bash

   python -c "import litestar_workflows; print(litestar_workflows.__version__)"


Requirements
------------

litestar-workflows requires:

- Python 3.9 or later
- Litestar 2.0 or later

The following are optional dependencies installed with extras:

.. list-table:: Optional Dependencies
   :widths: 20 50 30
   :header-rows: 1

   * - Extra
     - Dependencies
     - Purpose
   * - ``db``
     - advanced-alchemy (>=0.20.0), alembic (>=1.13.0)
     - Database persistence with SQLAlchemy
   * - ``ui``
     - litestar[jinja]
     - Web UI templates
   * - ``web``
     - litestar-workflows[db]
     - REST API plugin (includes db)
   * - ``all``
     - All of the above
     - Complete installation


Next Steps
----------

Now that you have litestar-workflows installed, head over to the
:doc:`quickstart` guide to build your first workflow!
