Core Concepts
=============

This section explains the fundamental concepts that power litestar-workflows.
Understanding these concepts will help you design effective workflows and
troubleshoot issues.

.. toctree::
   :maxdepth: 2

   workflows
   steps
   context
   execution


Overview
--------

litestar-workflows is built around four core concepts:

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Concept
     - Description
   * - :doc:`workflows`
     - The blueprint that defines steps and their connections
   * - :doc:`steps`
     - Individual units of work (machine, human, gateway, etc.)
   * - :doc:`context`
     - Shared state that flows through the workflow
   * - :doc:`execution`
     - The engine that runs workflow instances


Design Philosophy
-----------------

litestar-workflows follows several key design principles:


Async-First
~~~~~~~~~~~

Every execution API is ``async``. This aligns with Litestar's async-first design
and provides excellent performance for I/O-bound workflows. Human tasks are
naturally async since they wait for user input.

.. code-block:: python

   async def execute(self, context: WorkflowContext) -> None:
       # Async operations are natural
       result = await external_api.fetch_data()
       context.set("result", result)


Lean Automation
~~~~~~~~~~~~~~~

Inspired by Joeflow, the philosophy is: "Automate the common path, allow human
intervention for exceptions." Rather than trying to handle every edge case in
code, workflows pause for human decision when needed.

.. code-block:: python

   class ReviewException(BaseHumanStep):
       """When automation fails, humans can take over."""
       name = "review_exception"
       title = "Review Failed Processing"
       form_schema = {...}


Protocol-Based Interfaces
~~~~~~~~~~~~~~~~~~~~~~~~~

Core interfaces use Python Protocols rather than deep inheritance hierarchies.
This enables duck typing with full type checker support:

.. code-block:: python

   from typing import Protocol

   class Step(Protocol):
       name: str
       async def execute(self, context: WorkflowContext) -> None: ...

   # Any class matching this signature works as a Step


Composable Primitives
~~~~~~~~~~~~~~~~~~~~~

Complex workflows are built from simple, reusable pieces:

- **Steps**: Individual units of work
- **Edges**: Connections between steps
- **Groups**: Combine steps (sequential, parallel, conditional)

.. code-block:: python

   # Build complex workflows from simple parts
   definition = WorkflowDefinition(
       steps={...},
       edges=[
           Edge("a", "b"),
           Edge("b", "c"),
           Edge("b", "d"),  # Parallel branches
       ],
   )


Conceptual Model
----------------

Here's how the concepts relate:

.. code-block:: text

                        WorkflowDefinition
                              |
          +-------------------+-------------------+
          |                   |                   |
        Steps               Edges              Metadata
     (what to do)     (how they connect)    (name, version)
          |                   |
          +-------------------+
                   |
            WorkflowInstance
          (running workflow)
                   |
             +-----+-----+
             |           |
         Context      Engine
       (shared data)  (executor)


Next Steps
----------

Start with :doc:`workflows` to understand workflow definitions, then proceed
through the other concept pages.
