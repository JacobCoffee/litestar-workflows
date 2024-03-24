# litestar-workflows

[![Latest Release](https://github.com/JacobCoffee/litestar-workflows/actions/workflows/publish.yml/badge.svg)](https://github.com/JacobCoffee/litestar-workflows/actions/workflows/publish.yml)
[![Tests And Linting](https://github.com/JacobCoffee/litestar-workflows/actions/workflows/ci.yml/badge.svg)](https://github.com/JacobCoffee/litestar-workflows/actions/workflows/ci.yml)


A simple library for creating and managing workflows in Litestar.

"Workflows" are a way to define a series of steps that need to be completed to achieve a goal.
`litestar-workflows` provides a way to define workflows in code, and then execute them in a controlled manner.

Some examples of workflows that could be defined with `litestar-workflows` include:

- A user creates a new post on a blog, and the post needs to be reviewed by an editor before it can be published.
- A developer implements a new feature, and the feature must be reviewed by their team -> QA -> product owner -> ...
  before it can be reflected in the production environment.
- Approval workflows for various business processes like expense reports, vacation requests, etc.
- A user requests a new virtual machine, and the request must be approved by a manager before the VM is created.
- I need to run a command on a set of hosts, but I need approval from a manager -> directory -> VP -> ... before the command is executed.

...and many more!

## Installation

```bash
python3 -m pip install litestar-workflows
```

## Usage

Here's a simple example of how to define and execute a workflow using `litestar-workflows`:

```python
from litestar_workflows import Workflow, Step

# TODO: Define the steps of the workflow :)
```

## Versioning

This project uses [Semantic Versioning](https://semver.org/).
* Major versions introduce breaking changes.
* Major versions will support the currently supported version(s) of Litestar.
    * See the [Litestar Versioning Policy](https://litestar.dev/about/litestar-releases#version-numbering)
      for more information.

## Contributing

Contributions are welcome! For more information, please see [CONTRIBUTING.rst](CONTRIBUTING.rst).

## License

This project is licensed under the terms of the MIT license. For more information, please see [LICENSE](LICENSE).
