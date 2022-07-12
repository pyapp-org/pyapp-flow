"""
Helper methods for testing workflows and steps
"""
from typing import Any, Callable

from .datastructures import WorkflowContext


def call_node(
    step: Callable[[WorkflowContext], Any], **context_vars: Any
) -> WorkflowContext:
    """
    Simplify testing of steps by providing a step and the required context variables.

    Method returns the generated context object to be asserted on.

    .. code-block:: python

        def test_find_isbn__with_known_title():
            context = call_node(find_isbn, title="Hyperion")
            actual = context.state["isbn_13"]

            assert actual == "978-0553283686"

    """
    context = WorkflowContext(**context_vars)
    step(context)
    return context
