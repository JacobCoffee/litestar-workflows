Cookbook
========

Real-world workflow recipes you can adapt and use in your applications.
Each recipe is a complete, working example that demonstrates best practices
for common workflow patterns.

Unlike the :doc:`/guides/index`, which teach concepts step-by-step, these
recipes are ready-to-use solutions. Copy, paste, and customize to fit your
needs.


.. toctree::
   :maxdepth: 2

   expense-approval
   document-review
   onboarding
   integration-patterns


Recipe Quick Reference
----------------------

Use this table to find the recipe that matches your use case:

.. list-table::
   :widths: 25 35 40
   :header-rows: 1

   * - Recipe
     - Use Case
     - Key Features
   * - :doc:`expense-approval`
     - Financial approvals, purchase requests
     - Multi-level approval chain, conditional routing, JSON Schema forms
   * - :doc:`document-review`
     - Content review, contract approval
     - Submit-review-revise cycle, parallel reviewers, rejection handling
   * - :doc:`onboarding`
     - Employee onboarding, customer setup
     - Parallel setup tasks, timer steps for deadlines, task coordination
   * - :doc:`integration-patterns`
     - External APIs, notifications
     - Error handling, retry strategies, event hooks, testing


What You Need
-------------

Before using these recipes, you should:

1. Have litestar-workflows installed (see :doc:`/getting-started/installation`)
2. Understand basic workflow concepts (see :doc:`/concepts/index`)
3. Be familiar with Litestar dependency injection


Recipe Structure
----------------

Each recipe follows a consistent structure:

**Overview**
    What the workflow does and when to use it

**Complete Code**
    Full working implementation with imports and type hints

**Key Concepts**
    Important patterns demonstrated in the recipe

**Customization Points**
    Where and how to adapt the recipe for your needs

**Testing**
    How to test the workflow

**Common Variations**
    Alternative approaches and extensions


Running the Examples
--------------------

All recipes are designed to run with the REST API. Start a workflow:

.. code-block:: bash

   # Start a workflow instance
   curl -X POST http://localhost:8000/workflows/instances \
     -H "Content-Type: application/json" \
     -d '{
       "definition_name": "expense_approval",
       "input_data": {"amount": 5000, "requester": "alice@example.com"}
     }'

   # List pending tasks
   curl http://localhost:8000/workflows/tasks

   # Complete a human task
   curl -X POST http://localhost:8000/workflows/tasks/{task_id}/complete \
     -H "Content-Type: application/json" \
     -d '{"output_data": {"approved": true}, "completed_by": "manager@example.com"}'


See Also
--------

- :doc:`/guides/index` - Step-by-step guides for learning concepts
- :doc:`/concepts/index` - Core concepts and terminology
- :doc:`/api/index` - Complete API reference
