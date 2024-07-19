import pytest
from pyapp_flow import nodes, steps
from pyapp_flow.errors import FatalError, StepFailedError
from pyapp_flow.testing import call_node


def test_failed():
    target = steps.failed("Failed as {my_var} is not set")

    with pytest.raises(StepFailedError, match="Failed as test is not set"):
        call_node(target, my_var="test")


def test_fatal():
    target = steps.fatal("Fatal error as {my_var} is not set")

    with pytest.raises(FatalError, match="Fatal error as test is not set"):
        call_node(target, my_var="test")


def test_alias():
    target = nodes.SetVar(new_var=steps.alias("old_var"))

    context = call_node(target, old_var="foo")

    actual = context.state.new_var

    assert actual == "foo"
