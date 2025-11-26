Module Reference
================

Auto-generated API documentation from source code.

.. note::

   This reference is automatically generated from docstrings in the source code.
   For conceptual documentation, see :doc:`/concepts/index`.


litestar_workflows
------------------

.. automodule:: litestar_workflows
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:


Core Module
-----------

.. note::

   The core module will be documented once the Phase 1 implementation is complete.
   See ``PLAN.md`` for the planned API surface.


Planned Public API
~~~~~~~~~~~~~~~~~~

The following will be available from the top-level package:

.. code-block:: python

   from litestar_workflows import (
       # Protocols
       Step,
       Workflow,
       ExecutionEngine,

       # Types
       StepType,
       StepStatus,
       WorkflowStatus,
       WorkflowContext,
       WorkflowDefinition,
       Edge,

       # Base implementations
       BaseMachineStep,
       BaseHumanStep,
       BaseGateway,

       # Groups
       SequentialGroup,
       ParallelGroup,
       ConditionalGroup,

       # Engine
       LocalExecutionEngine,
       WorkflowRegistry,

       # Exceptions
       WorkflowsError,
       WorkflowNotFoundError,
       StepExecutionError,
       InvalidTransitionError,
   )


Database Module
---------------

.. note::

   The database module will be available with the ``[db]`` extra in Phase 2.


Planned Database API
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from litestar_workflows.db import (
       WorkflowDefinitionModel,
       WorkflowInstanceModel,
       StepExecutionModel,
       HumanTaskModel,
       WorkflowInstanceRepository,
   )


Web Module
----------

.. note::

   The web module is available with the ``[web]`` extra. The REST API is built into
   the main ``WorkflowPlugin`` and enabled by default.


Web API
~~~~~~~

.. code-block:: python

   from litestar_workflows import WorkflowPlugin, WorkflowPluginConfig

   # REST API is enabled by default
   app = Litestar(
       plugins=[
           WorkflowPlugin(
               config=WorkflowPluginConfig(
                   enable_api=True,  # Default
                   api_path_prefix="/workflows",
               )
           ),
       ],
   )

   # For advanced usage, DTOs and utilities are available:
   from litestar_workflows.web import (
       WorkflowWebConfig,
       WorkflowDefinitionController,
       WorkflowInstanceController,
       HumanTaskController,
       generate_mermaid_graph,
   )


Contrib Modules
---------------

.. note::

   Contrib modules for distributed execution will be available in Phase 6.


Planned Contrib API
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Celery execution engine
   from litestar_workflows.contrib.celery import CeleryExecutionEngine

   # SAQ execution engine
   from litestar_workflows.contrib.saq import SAQExecutionEngine

   # ARQ execution engine
   from litestar_workflows.contrib.arq import ARQExecutionEngine
