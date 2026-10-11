Workflows
=========

A **workflow** is a blueprint that defines a series of steps and how they connect.
Think of it as a directed graph where nodes are steps and edges are transitions.


What is a Workflow?
-------------------

At its core, a workflow is:

1. A collection of **steps** (things to do)
2. A set of **edges** (connections between steps)
3. A designated **starting point**
4. One or more **terminal points** (where execution ends)

Here's a visual representation:

.. code-block:: text

   [Start] --> [Step A] --> [Step B] --> [End]
                  |
                  +--> [Step C] --> [End]

This workflow starts at "Start", then goes to "Step A", which can lead to either
"Step B" or "Step C", both of which are terminal steps.


WorkflowDefinition
------------------

The ``WorkflowDefinition`` class captures this blueprint:

.. code-block:: python

   from litestar_workflows import WorkflowDefinition, Edge

   definition = WorkflowDefinition(
       name="my_workflow",
       version="1.0.0",
       description="A sample workflow",
       steps={
           "start": StartStep(),
           "step_a": StepA(),
           "step_b": StepB(),
           "step_c": StepC(),
       },
       edges=[
           Edge(source="start", target="step_a"),
           Edge(source="step_a", target="step_b"),
           Edge(source="step_a", target="step_c"),
       ],
       initial_step="start",
       terminal_steps={"step_b", "step_c"},
   )


Definition Properties
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Property
     - Description
   * - ``name``
     - Unique identifier for the workflow type
   * - ``version``
     - Semantic version string (e.g., "1.0.0")
   * - ``description``
     - Human-readable description
   * - ``steps``
     - Dictionary mapping step names to step instances
   * - ``edges``
     - List of Edge objects defining transitions
   * - ``initial_step``
     - Name of the first step to execute
   * - ``terminal_steps``
     - Set of step names that end the workflow


Edges
-----

Edges define how steps connect. An ``Edge`` has:

- **source**: The step to transition from
- **target**: The step to transition to
- **condition** (optional): Expression that must be true for this edge

.. code-block:: python

   from litestar_workflows import Edge

   # Simple edge - always taken
   Edge(source="submit", target="review")

   # Conditional edge - only taken if condition is met
   Edge(
       source="review",
       target="approve",
       condition="context.get('score') >= 80"
   )

When a step completes, the engine evaluates all outgoing edges to determine
the next step(s).


Workflow vs WorkflowInstance
----------------------------

It's important to distinguish between:

- **WorkflowDefinition**: The template/blueprint (like a class)
- **WorkflowInstance**: A running execution (like an object)

.. code-block:: python

   # Definition - defined once
   definition = WorkflowDefinition(name="approval", ...)

   # Instance - created for each execution
   instance1 = await engine.start_workflow("approval", data={"user": "alice"})
   instance2 = await engine.start_workflow("approval", data={"user": "bob"})

Each instance has its own:

- Unique ID
- Current step position
- Context data
- Execution history
- Status (running, waiting, completed, failed)


Workflow Status
---------------

A workflow instance can be in one of these states:

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Status
     - Description
   * - ``PENDING``
     - Created but not started
   * - ``RUNNING``
     - Actively executing steps
   * - ``WAITING``
     - Paused at a human task
   * - ``COMPLETED``
     - Finished successfully
   * - ``FAILED``
     - Stopped due to error
   * - ``CANCELED``
     - Manually canceled


Versioning
----------

Workflows support versioning for safe updates:

.. code-block:: python

   # Version 1.0.0 - original workflow
   workflow_v1 = WorkflowDefinition(
       name="approval",
       version="1.0.0",
       steps={"review": ReviewStep()},
       ...
   )

   # Version 2.0.0 - updated workflow
   workflow_v2 = WorkflowDefinition(
       name="approval",
       version="2.0.0",
       steps={"review": ReviewStep(), "audit": AuditStep()},  # New step
       ...
   )

   # Register both versions
   registry.register_definition(workflow_v1)
   registry.register_definition(workflow_v2)

   # Start with specific version
   await engine.start_workflow("approval", version="1.0.0")
   await engine.start_workflow("approval", version="2.0.0")

Running instances continue with their original version, even after you register
a new version.


Graph Visualization
-------------------

Workflows can generate visual representations:

.. code-block:: python

   # Generate MermaidJS diagram
   mermaid_code = definition.to_mermaid()
   print(mermaid_code)

   # Output:
   # graph TD
   #     start[Start]
   #     step_a[Step A]
   #     step_b[Step B]
   #     start --> step_a
   #     step_a --> step_b

This is useful for documentation and debugging. The web plugin can render these
diagrams in the browser.


Best Practices
--------------


Name Steps Clearly
~~~~~~~~~~~~~~~~~~

Use descriptive, action-oriented names:

.. code-block:: python

   # Good - clear what each step does
   steps = {
       "validate_request": ValidateStep(),
       "notify_manager": NotifyStep(),
       "process_approval": ProcessStep(),
   }

   # Avoid - vague or generic names
   steps = {
       "step1": ValidateStep(),
       "step2": NotifyStep(),
   }


Keep Workflows Focused
~~~~~~~~~~~~~~~~~~~~~~

A workflow should represent a single logical process. If a workflow grows too
complex, consider splitting it into sub-workflows:

.. code-block:: python

   # Instead of one massive workflow
   big_workflow = WorkflowDefinition(steps={...50 steps...})

   # Break into focused workflows
   intake_workflow = WorkflowDefinition(name="intake", ...)
   review_workflow = WorkflowDefinition(name="review", ...)
   fulfillment_workflow = WorkflowDefinition(name="fulfillment", ...)


Version Carefully
~~~~~~~~~~~~~~~~~

When updating workflows:

1. **Minor changes**: Increment patch version (1.0.0 -> 1.0.1)
2. **New steps**: Increment minor version (1.0.0 -> 1.1.0)
3. **Breaking changes**: Increment major version (1.0.0 -> 2.0.0)

Breaking changes include removing steps, changing step names, or modifying
edge logic in ways that affect running instances.


See Also
--------

- :doc:`steps` - Learn about different step types
- :doc:`context` - Understand workflow data sharing
- :doc:`execution` - How workflows are executed
