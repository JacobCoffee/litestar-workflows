"""Base definitions for the library."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, ParamSpec, Protocol, TypeAlias, TypeVar

P = ParamSpec("P")
T = TypeVar("T")

StepType = TypeVar("StepType", bound="Step")
WorkflowType = TypeVar("WorkflowType", bound="Workflow")

Context: TypeAlias = dict[str, Any]
StepExecutor: TypeAlias = Callable[P, None]


class Step(Protocol):
    """Protocol to define a step in a `~.base.Workflow`.

    Inherit from this class to create a new step.
    """

    def execute(self, context: Context, *args: P.args, **kwargs: P.kwargs) -> None:
        """Method that, when ran, should execute the step.

        Args:
            context: The context of the workflow.
            *args: Positional arguments to pass to the step
            **kwargs: Keyword arguments to pass to the step
        """
        ...


class Workflow(ABC):
    """Base class for workflows.

    Inherit from this class to create a new workflow.
    You can add steps so long as they are of type `~.base.Step`.
    """

    @abstractmethod
    def run(self: WorkflowType, *args: P.args, **kwargs: P.kwargs) -> T:
        """Abstract method that, when implemented, should run the workflow.

        Args:
            *args: Positional arguments to pass to the workflow.
            **kwargs: Keyword arguments to pass to the workflow.

        Returns:
            The result of the workflow.
        """

    @abstractmethod
    def add_step(self: WorkflowType, step: Step) -> None:
        """Abstract method that, when implemented, should add a step to the workflow.

        Args:
            step: The step to add to the workflow.
        """

    @abstractmethod
    def remove_step(self: WorkflowType, step: Step) -> None:
        """Abstract method that, when implemented, should remove a step from the workflow.

        Args:
            step: The step to remove from the workflow.
        """
