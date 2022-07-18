from unittest.mock import Mock, call, ANY
import pytest

import pyapp_flow as flow
from pyapp_flow.ext import sphinx


@flow.step(name="Sample Step", output="arg_c")
def sample_step(arg_a: int, *, arg_b: str) -> bool:
    """
    This is a sample step that just outputs false
    """
    return False


def not_a_step():
    """
    This is not, and I repeat not a step
    """


class TestStepDocumenter:
    @pytest.fixture
    def target(self):
        mock_directive = Mock(
            result=Mock(), state=Mock(document=Mock(settings=Mock(tab_width=4)))
        )
        target = sphinx.StepDocumenter(mock_directive, "Test")
        target.object = sample_step
        return target

    @pytest.mark.parametrize(
        "step, expected",
        (
            (sample_step, True),
            (not_a_step, False),
        ),
    )
    def test_can_document_member(self, step, expected):
        actual = sphinx.StepDocumenter.can_document_member(step)

        assert actual is expected

    def test_add_directive_header(self, target):
        target.add_directive_header("")

        assert target.directive.result.append.mock_calls == [
            call(".. py:function:: ext.test_sphinx.sample_step", ANY),
            call("", ANY),
            call("**Sample Step**", ANY),
        ]

    def test_get_doc(self, target):
        actual = target.get_doc()

        assert actual == [["This is a sample step that just outputs false", ""]]

    def test_document_members(self, target):
        target.document_members()

        assert (
            target.directive.result.append.mock_calls
            == [
                call("", ANY),
                call("**Input Variable(s)**", ANY),
                call(
                    "These variables are resolved from the :py:class:`pyapp_flow.datastructures.WorkflowContext` at runtime",
                    ANY,
                ),
                call("", ANY),
                call("* *arg_a*: *int*", ANY),
                call("* *arg_b*: *str*", ANY),
                call("", ANY),
                call("**Output Variable(s)**", ANY),
                call(
                    "These variables are added to the :py:class:`pyapp_flow.datastructures.WorkflowContext` at runtime",
                    ANY,
                ),
                call("", ANY),
                call("* *arg_c*: *bool*", ANY),
                call("", ANY),
            ]
            != [
                call(".. py:function:: ext.test_sphinx.sample_step", ANY),
                call("", ANY),
                call("**Sample Step**", ANY),
            ]
        )
