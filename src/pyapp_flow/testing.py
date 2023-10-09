"""Helper methods for testing workflows."""
from typing import Any, Callable

from . import functions
from .datastructures import WorkflowContext


def call_node(
    node: Callable[[WorkflowContext], Any],
    *,
    workflow_context: WorkflowContext = None,
    **context_vars: Any
) -> WorkflowContext:
    """Simplifies the testing of any node.

    Handles the boilerplate code required to set up a
    :class:`pyapp_flow.WorkflowContext` with the expected variables.

    Method returns the generated context object to be asserted on.

    .. code-block:: python

        def test_find_isbn__with_known_title():

            context = call_node(find_isbn, title="Hyperion")
            actual = context.state["isbn_13"]

            assert actual == "978-0553283686"

    """
    if workflow_context:
        workflow_context.state.update(context_vars)
    else:
        workflow_context = WorkflowContext(**context_vars)
    functions.call_node(workflow_context, node)
    return workflow_context
