Installation
============

This guide covers how to install litestar-workflows and its optional dependencies.


Basic Installation
------------------

Install the core package using pip:

.. code-block:: bash

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

- SQLAlchemy models for workflow persistence
- Repository implementations
- Alembic migration support


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

For contributing to litestar-workflows:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/JacobCoffee/litestar-workflows.git
   cd litestar-workflows

   # Create a virtual environment (recommended)
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate

   # Install with development dependencies
   pip install -e ".[dev-lint,dev-test]"

   # Install pre-commit hooks
   pre-commit install


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
   :widths: 30 40 30
   :header-rows: 1

   * - Extra
     - Dependencies
     - Purpose
   * - ``db``
     - SQLAlchemy, Alembic
     - Database persistence
   * - ``ui``
     - Jinja2
     - Web UI templates


Next Steps
----------

Now that you have litestar-workflows installed, head over to the
:doc:`quickstart` guide to build your first workflow!
