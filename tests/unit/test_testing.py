from __future__ import annotations

from pyapp_flow import step, WorkflowContext
from pyapp_flow import testing


@step(output="isbn_13")
def find_isbn(*, title: str) -> None | str:
    """
    Mock step that returns the ISBN of a known book
    """
    return {
        "Hyperion": "978-0553283686",
        "The Fall of Hyperion": "978-0553288209",
    }.get(title)


def test_call_step__where_value_is_returned():
    context = testing.call_node(find_isbn, title="Hyperion")

    assert isinstance(context, WorkflowContext)
    assert context.state["title"] == "Hyperion"
    assert context.state["isbn_13"] == "978-0553283686"


def test_call_step__where_none_is_returned():
    context = testing.call_node(find_isbn, title="Endymion")

    assert isinstance(context, WorkflowContext)
    assert context.state["title"] == "Endymion"
    assert context.state["isbn_13"] is None
