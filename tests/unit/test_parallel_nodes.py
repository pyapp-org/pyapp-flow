from unittest.mock import patch, Mock

import pytest

from pyapp_flow import parallel_nodes, WorkflowContext
from pyapp_flow.errors import FatalError


@patch("importlib.import_module")
def test_import_node(mock_import_module):
    mock_node_test = Mock()
    mock_import_module.return_value = Mock(NodeTest=mock_node_test)

    actual = parallel_nodes.import_node("this.is.a.test:NodeTest")

    assert actual is mock_node_test
    mock_import_module.assert_called_once_with("this.is.a.test")


@patch("importlib.import_module")
def test_call_parallel_node(mock_import_module):
    mock_node_test = Mock(return_value=[])
    mock_import_module.return_value = Mock(NodeTest=mock_node_test)

    actual = parallel_nodes._call_parallel_node(
        "this.is.a.test:NodeTest",
        {"foo": "bar"},
        ["foo"],
    )

    assert actual == ("bar",)


@patch("importlib.import_module")
def test_call_parallel_node__import_failure(mock_import_module):
    mock_import_module.side_effect = ImportError("Boom!")

    with pytest.raises(FatalError, match="Unable to import parallel node: Boom!"):
        parallel_nodes._call_parallel_node(
            "this.is.a.test:NodeTest",
            {"foo": "bar"},
            ["foo"],
        )


class TestMapNodes:
    @pytest.fixture
    def target(self):
        target = parallel_nodes.MapNode("message", in_var="messages")
        target.pool_type = Mock(
            starmap=Mock(
                lambda node_id, context_data, return_vars: (
                    node_id,
                    context_data,
                    return_vars,
                )
            )
        )
        # target.loop()
        return target

    def test_call(self, target):
        context = WorkflowContext(messages=["foo", "bar", "baz"])

        target(context)
