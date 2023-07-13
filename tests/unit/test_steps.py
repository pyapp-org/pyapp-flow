import pytest

from pyapp_flow import steps
from pyapp_flow.errors import StepFailedError
from pyapp_flow.testing import call_node


def test_failed():
    target = steps.failed("Failed as {my_var} is not set")

    with pytest.raises(StepFailedError, match="Failed as test is not set"):
        call_node(target, my_var="test")
