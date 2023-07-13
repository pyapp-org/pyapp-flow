"""Builtin flow steps."""
from .datastructures import WorkflowContext
from .nodes import step, Step
from .errors import StepFailedError


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
