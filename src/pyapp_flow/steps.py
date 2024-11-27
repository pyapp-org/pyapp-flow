"""Builtin flow steps."""

from .datastructures import WorkflowContext
from .errors import FatalError, StepFailedError
from .nodes import Step, step


def failed(message: str) -> Step:
    """Step that will always fail.

    Useful if a branch should always fail.

    :param message: The message to provide to failed error; can include context
        variables.

    .. code-block:: python

        failed("Failed as {my_var} is not set")

    """

    @step
    def _step(context: WorkflowContext):
        raise StepFailedError(context.format(message))

    return _step


def fatal(message: str) -> Step:
    """Step that will raise a Fatal error.

    Useful if a branch should always fatally fail.

    :param message: The message to provide to fatal error; can include context
        variables.

    .. code-block:: python

        fatal("Fatal error as {my_var} is not set")

    """

    @step
    def _step(context: WorkflowContext):
        raise FatalError(context.format(message))

    return _step


def alias(variable: str) -> Step:
    """Read a variable from the context.

    Simplifies aliasing variables using ``set_var``

    ..code-block:: python

        SetVar(new_var=alias("old_var"))

    """

    @step
    def _step(context: WorkflowContext):
        return context.state[variable]

    return _step
