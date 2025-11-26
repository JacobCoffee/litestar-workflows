# litestar-workflows

<p align="center">
  <em>Workflow automation for Litestar with human approval chains, automated pipelines, and web-based workflow management.</em>
</p>

<p align="center">
  <a href="https://github.com/JacobCoffee/litestar-workflows/actions/workflows/ci.yml">
    <img src="https://github.com/JacobCoffee/litestar-workflows/actions/workflows/ci.yml/badge.svg" alt="Tests And Linting">
  </a>
  <a href="https://github.com/JacobCoffee/litestar-workflows/actions/workflows/publish.yml">
    <img src="https://github.com/JacobCoffee/litestar-workflows/actions/workflows/publish.yml/badge.svg" alt="Latest Release">
  </a>
  <a href="https://pypi.org/project/litestar-workflows/">
    <img src="https://img.shields.io/pypi/v/litestar-workflows.svg" alt="PyPI Version">
  </a>
  <a href="https://pypi.org/project/litestar-workflows/">
    <img src="https://img.shields.io/pypi/pyversions/litestar-workflows.svg" alt="Python Versions">
  </a>
  <a href="https://github.com/JacobCoffee/litestar-workflows/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/JacobCoffee/litestar-workflows.svg" alt="License">
  </a>
</p>

---

**Documentation**: [https://jacobcoffee.github.io/litestar-workflows](https://jacobcoffee.github.io/litestar-workflows)

**Source Code**: [https://github.com/JacobCoffee/litestar-workflows](https://github.com/JacobCoffee/litestar-workflows)

---

## Overview

**litestar-workflows** is a flexible, async-first workflow automation framework built specifically for the [Litestar](https://litestar.dev) ecosystem. It enables you to define complex business processes as code, combining automated steps with human approval checkpoints.

### Screenshots

<p align="center">
  <img src="https://raw.githubusercontent.com/JacobCoffee/litestar-workflows/main/docs/_static/screenshots/workflow-list.png" alt="Workflow List" width="45%">
  <img src="https://raw.githubusercontent.com/JacobCoffee/litestar-workflows/main/docs/_static/screenshots/workflow-detail.png" alt="Workflow Detail" width="45%">
</p>
<p align="center">
  <img src="https://raw.githubusercontent.com/JacobCoffee/litestar-workflows/main/docs/_static/screenshots/instance-list.png" alt="Instance List" width="45%">
  <img src="https://raw.githubusercontent.com/JacobCoffee/litestar-workflows/main/docs/_static/screenshots/tasks-list.png" alt="Tasks List" width="45%">
</p>

### Key Features

- **Async-First Design**: Native `async/await` throughout, leveraging Litestar's async foundation
- **Human + Machine Tasks**: Combine automated processing with human approval checkpoints
- **Composable Workflows**: Build complex workflows from simple, reusable primitives
- **Type-Safe**: Full typing with Protocol-based interfaces for IDE support
- **Litestar Integration**: Deep integration with Litestar's DI, guards, and plugin system
- **Flexible Execution**: Local execution engine with optional distributed backends (Celery, SAQ)
- **Visual Debugging**: MermaidJS workflow visualization support

### Use Cases

- **Approval Workflows**: Expense reports, vacation requests, document reviews
- **Multi-Stage Pipelines**: Feature releases requiring team, QA, and product approval
- **Provisioning Workflows**: VM creation, access requests with manager approval
- **Content Publishing**: Blog posts requiring editorial review before publication
- **Any Sequential Process**: Anything with an arbitrary series of steps and approvals

## Installation

Install using pip:

```bash
pip install litestar-workflows
```

Or with optional extras:

```bash
# With database persistence (SQLAlchemy)
pip install litestar-workflows[db]

# With web UI templates
pip install litestar-workflows[ui]

# All extras
pip install litestar-workflows[db,ui]
```

## Quick Start

Here's a simple approval workflow that demonstrates the core concepts:

```python
from litestar_workflows import (
    WorkflowDefinition,
    Edge,
    BaseMachineStep,
    BaseHumanStep,
    LocalExecutionEngine,
    WorkflowRegistry,
    WorkflowContext,
)


# Define automated steps
class SubmitRequest(BaseMachineStep):
    """Initial submission step - runs automatically."""

    name = "submit"
    description = "Submit a new request for processing"

    async def execute(self, context: WorkflowContext) -> None:
        # Record submission timestamp
        context.set("submitted", True)
        context.set("submitted_by", context.user_id)


# Define human approval steps
class ManagerApproval(BaseHumanStep):
    """Human task - waits for manager input."""

    name = "manager_approval"
    title = "Approve Request"
    description = "Manager reviews and approves or rejects the request"
    form_schema = {
        "type": "object",
        "properties": {
            "approved": {"type": "boolean", "title": "Approve this request?"},
            "comments": {"type": "string", "title": "Comments"},
        },
        "required": ["approved"],
    }


class ProcessRequest(BaseMachineStep):
    """Final processing step - runs after approval."""

    name = "process"
    description = "Process the approved request"

    async def execute(self, context: WorkflowContext) -> None:
        if context.get("approved"):
            context.set("status", "processed")
            # Perform actual processing here
        else:
            context.set("status", "rejected")


# Create workflow definition
definition = WorkflowDefinition(
    name="approval_workflow",
    version="1.0.0",
    description="Simple request approval workflow",
    steps={
        "submit": SubmitRequest(),
        "manager_approval": ManagerApproval(),
        "process": ProcessRequest(),
    },
    edges=[
        Edge("submit", "manager_approval"),
        Edge("manager_approval", "process"),
    ],
    initial_step="submit",
    terminal_steps={"process"},
)

# Register and run
registry = WorkflowRegistry()
registry.register_definition(definition)

engine = LocalExecutionEngine(registry)


# Start a new workflow instance
async def main():
    instance = await engine.start_workflow(
        "approval_workflow",
        initial_data={"request_id": "REQ-001", "amount": 500.00},
    )
    print(f"Workflow started: {instance.id}")
    print(f"Current step: {instance.current_step}")  # "manager_approval"

    # Later, when a manager completes the approval...
    await engine.complete_human_task(
        instance_id=instance.id,
        step_name="manager_approval",
        user_id="manager@example.com",
        data={"approved": True, "comments": "Looks good!"},
    )
```

## Documentation

For comprehensive documentation, tutorials, and API reference, visit:
[https://jacobcoffee.github.io/litestar-workflows](https://jacobcoffee.github.io/litestar-workflows)

### Quick Links

- [Getting Started Guide](https://jacobcoffee.github.io/litestar-workflows/getting-started/)
- [Core Concepts](https://jacobcoffee.github.io/litestar-workflows/concepts/)
- [How-To Guides](https://jacobcoffee.github.io/litestar-workflows/guides/)
- [API Reference](https://jacobcoffee.github.io/litestar-workflows/api/)

## Versioning

This project uses [Semantic Versioning](https://semver.org/).

- Major versions introduce breaking changes
- Major versions support the currently supported version(s) of Litestar
- See the [Litestar Versioning Policy](https://litestar.dev/about/litestar-releases#version-numbering) for details

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.rst](CONTRIBUTING.rst) for guidelines.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/JacobCoffee/litestar-workflows.git
cd litestar-workflows

# Install with development dependencies
pip install -e ".[dev-lint,dev-test]"

# Run tests
pytest tests

# Run linting
pre-commit run --all-files
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Acknowledgments

This library draws inspiration from:

- [Joeflow](https://joeflow.readthedocs.io/) - Human/machine task model and lean automation philosophy
- [Prefect](https://prefect.io/) - Dynamic execution and event-driven patterns
- [Celery Canvas](https://docs.celeryq.dev/en/stable/userguide/canvas.html) - Composable task primitives
