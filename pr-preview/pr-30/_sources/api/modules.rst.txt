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

The core module provides fundamental building blocks for workflow automation.

.. automodule:: litestar_workflows.core
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.core.types
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.core.context
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.core.definition
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.core.events
   :members:
   :undoc-members:
   :show-inheritance:


Public API
~~~~~~~~~~

The following is available from the top-level package:

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


Engine Module
-------------

Execution engines and workflow registry.

.. automodule:: litestar_workflows.engine
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.engine.local
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.engine.registry
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.engine.graph
   :members:
   :undoc-members:
   :show-inheritance:


Steps Module
------------

Built-in step implementations.

.. automodule:: litestar_workflows.steps
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.steps.base
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.steps.groups
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.steps.gateway
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.steps.timer
   :members:
   :undoc-members:
   :show-inheritance:


Database Module
---------------

Available with the ``[db]`` extra: ``pip install litestar-workflows[db]``

.. automodule:: litestar_workflows.db
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.db.models
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.db.repositories
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.db.engine
   :members:
   :undoc-members:
   :show-inheritance:


Database API
~~~~~~~~~~~~

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

The web module provides REST API controllers and DTOs. The REST API is built into
the main ``WorkflowPlugin`` and enabled by default.

.. automodule:: litestar_workflows.web
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.web.controllers
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.web.dto
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.web.graph
   :members:
   :undoc-members:
   :show-inheritance:


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

Optional integration modules for distributed execution (stub implementations for Phase 6).

.. automodule:: litestar_workflows.contrib
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.contrib.celery
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.contrib.saq
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: litestar_workflows.contrib.arq
   :members:
   :undoc-members:
   :show-inheritance:

.. note::

   The contrib engines are stub implementations. Full implementations are planned for Phase 6 (v0.7.0).


Contrib API
~~~~~~~~~~~

.. code-block:: python

   # Celery execution engine
   from litestar_workflows.contrib.celery import CeleryExecutionEngine

   # SAQ execution engine
   from litestar_workflows.contrib.saq import SAQExecutionEngine

   # ARQ execution engine
   from litestar_workflows.contrib.arq import ARQExecutionEngine
