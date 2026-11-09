litestar-workflows
==================

.. rst-class:: lead

   Workflow automation for Litestar with human approval chains, automated pipelines,
   and web-based workflow management.

----

**litestar-workflows** is a flexible, async-first workflow automation framework built
specifically for the `Litestar <https://litestar.dev>`_ ecosystem. It enables you to
define complex business processes as code, combining automated steps with human
approval checkpoints.

.. grid:: 1 1 2 2
   :gutter: 2

   .. grid-item-card:: Getting Started
      :link: getting-started/index
      :link-type: doc

      New to litestar-workflows? Start here for installation and your first workflow.

   .. grid-item-card:: Core Concepts
      :link: concepts/index
      :link-type: doc

      Understand the fundamental concepts: workflows, steps, context, and execution.

   .. grid-item-card:: How-To Guides
      :link: guides/index
      :link-type: doc

      Practical guides for common tasks: approvals, parallel execution, and more.

   .. grid-item-card:: API Reference
      :link: api/index
      :link-type: doc

      Complete API documentation for all public classes and functions.

   .. grid-item-card:: Cookbook
      :link: cookbook/index
      :link-type: doc

      Real-world workflow recipes: expense approval, document review, onboarding, and more.


Key Features
------------

- **Async-First Design**: Native ``async/await`` throughout, leveraging Litestar's async foundation
- **Human + Machine Tasks**: Combine automated processing with human approval checkpoints
- **Composable Workflows**: Build complex workflows from simple, reusable primitives
- **Type-Safe**: Full typing with Protocol-based interfaces for IDE support
- **Litestar Integration**: Deep integration with Litestar's DI, guards, and plugin system
- **Flexible Execution**: Local execution engine with optional distributed backends
- **Database Persistence**: SQLAlchemy-backed storage with multi-tenancy support (``[db]`` extra)
- **REST API Plugin**: Production-ready web API with OpenAPI docs and MermaidJS visualization (``[web]`` extra)


Quick Example
-------------

Here's a taste of what a workflow looks like:

.. code-block:: python

   from litestar_workflows import (
       WorkflowDefinition,
       Edge,
       BaseMachineStep,
       BaseHumanStep,
       LocalExecutionEngine,
       WorkflowRegistry,
       WorkflowContext,
   )

   class SubmitRequest(BaseMachineStep):
       name = "submit"

       async def execute(self, context: WorkflowContext) -> None:
           context.set("submitted", True)

   class ManagerApproval(BaseHumanStep):
       name = "manager_approval"
       title = "Approve Request"
       form_schema = {"type": "object", "properties": {"approved": {"type": "boolean"}}}

   # Define and run workflow
   definition = WorkflowDefinition(
       name="approval",
       version="1.0.0",
       steps={"submit": SubmitRequest(), "approve": ManagerApproval()},
       edges=[Edge("submit", "approve")],
       initial_step="submit",
       terminal_steps={"approve"},
   )


Installation
------------

.. code-block:: bash

   pip install litestar-workflows

   # With optional extras
   pip install litestar-workflows[db]  # SQLAlchemy persistence
   pip install litestar-workflows[ui]  # Web UI templates


.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Learn

   getting-started/index
   concepts/index
   guides/index
   cookbook/index

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Reference

   api/index
   architecture/index
   changelog

.. toctree::
   :hidden:
   :caption: Project

   GitHub <https://github.com/JacobCoffee/litestar-workflows>
   Discord <https://discord.gg/litestar-919193495116337154>


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
