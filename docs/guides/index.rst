How-To Guides
=============

These guides provide step-by-step instructions for common workflow patterns
and tasks. Unlike tutorials, they assume familiarity with the basics and
focus on achieving specific goals.

.. toctree::
   :maxdepth: 2

   simple-workflow
   human-tasks
   parallel-execution
   conditional-logic


Guide Overview
--------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Guide
     - What You'll Learn
   * - :doc:`simple-workflow`
     - Build a complete workflow from scratch
   * - :doc:`human-tasks`
     - Implement approval workflows with human decision points
   * - :doc:`parallel-execution`
     - Run multiple steps simultaneously
   * - :doc:`conditional-logic`
     - Add branching and decision points with gateways


Choosing a Pattern
------------------

Use this decision tree to find the right pattern:

**Do you need human approval?**

- Yes: See :doc:`human-tasks`
- No: Continue below

**Do steps need to run simultaneously?**

- Yes: See :doc:`parallel-execution`
- No: Continue below

**Do you need conditional branching?**

- Yes: See :doc:`conditional-logic`
- No: See :doc:`simple-workflow`


Common Patterns Quick Reference
-------------------------------


Sequential Workflow
~~~~~~~~~~~~~~~~~~~

Steps execute one after another:

.. code-block:: python

   edges = [
       Edge("step1", "step2"),
       Edge("step2", "step3"),
   ]


Approval Workflow
~~~~~~~~~~~~~~~~~

Automated steps with human decision points:

.. code-block:: python

   edges = [
       Edge("submit", "review"),      # Human step
       Edge("review", "process"),
   ]


Parallel Notifications
~~~~~~~~~~~~~~~~~~~~~~

Multiple steps at once:

.. code-block:: python

   edges = [
       Edge("process", "email"),
       Edge("process", "slack"),
       Edge("process", "sms"),
       Edge("email", "complete"),
       Edge("slack", "complete"),
       Edge("sms", "complete"),
   ]


Conditional Branching
~~~~~~~~~~~~~~~~~~~~~

Different paths based on conditions:

.. code-block:: python

   edges = [
       Edge("check", "approve", condition="ctx.get('amount') < 1000"),
       Edge("check", "escalate", condition="ctx.get('amount') >= 1000"),
   ]
