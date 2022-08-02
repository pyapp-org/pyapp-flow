from unittest.mock import Mock, call, ANY

import pytest
from sphinx.ext.autodoc.directive import DocumenterBridge, Options

import pyapp_flow as flow
from pyapp_flow.ext import sphinx


@flow.step(name="Sample Step", output="arg_d")
def sample_step(arg_a: int, *, arg_b: str, arg_c) -> bool:
    """
    This is a sample step that just outputs false
    """
    return False


@flow.step(name="Simple Step")
def simple_step(arg_a: int, *, arg_b: str, arg_c):
    """
    This is a sample step that has no output
    """


def not_a_step():
    """
    This is not, and I repeat not a step
    """


class TestStepDocumenter:
    @pytest.fixture
    def target(self):
        directive = DocumenterBridge(
            Mock(),
            Mock(),
            Options(),
            15,
            state=Mock(document=Mock(settings=Mock(tab_width=4))),
        )
        target = sphinx.StepDocumenter(directive, "Test")
        target.object = sample_step
        target.name = "ext.test_sphinx.sample_step"
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

        assert target.directive.result.data == [
            ".. py:function:: ext.test_sphinx.sample_step",
            "",
            "**Sample Step**",
        ]

    def test_add_directive_header__with_no_name_option(self, target):
        target.options["noname"] = True
        target.add_directive_header("")

        assert target.directive.result.data == [
            ".. py:function:: ext.test_sphinx.sample_step",
        ]

    def test_get_doc(self, target):
        actual = target.get_doc()

        assert actual == [["This is a sample step that just outputs false", ""]]

    def test_document_members(self, target):
        target.document_members()

        assert target.directive.result.data == [
            "",
            "**Input Variable(s)**",
            "",
            "* *arg_a*: *int*",
            "* *arg_b*: *str*",
            "* *arg_c*",
            "",
            "**Output Variable**",
            "",
            "* *arg_d*: *bool*",
            "",
        ]

    def test_document_members__with_no_outputs(self, target):
        target.object = simple_step
        target.document_members()

        assert target.directive.result.data == [
            "",
            "**Input Variable(s)**",
            "",
            "* *arg_a*: *int*",
            "* *arg_b*: *str*",
            "* *arg_c*",
            "",
        ]


sample_workflow = flow.Workflow(
    name="Sample workflow",
    description="This is a sample workflow that just runs a simple operation",
).nodes(
    flow.SetVar(samples=["a", "b", "c"]),
    flow.ForEach("sample", in_var="samples").loop(
        flow.LogMessage("Reviewing sample {sample}")
    ),
    sample_step,
)

not_a_workflow = object()


class TestWorkflowDocumenter:
    @pytest.fixture
    def target(self):
        mock_directive = Mock(
            result=Mock(), state=Mock(document=Mock(settings=Mock(tab_width=4)))
        )
        target = sphinx.WorkflowDocumenter(mock_directive, "Test")
        target.object = sample_workflow
        target.name = "ext.test_sphinx.sample_workflow"
        return target

    @pytest.mark.parametrize(
        "step, expected",
        (
            (sample_workflow, True),
            (not_a_workflow, False),
        ),
    )
    def test_can_document_member(self, step, expected):
        actual = sphinx.WorkflowDocumenter.can_document_member(step)

        assert actual is expected

    def test_add_directive_header(self, target):
        target.add_directive_header("")

        assert target.directive.result.append.mock_calls == [
            call(".. py:function:: ext.test_sphinx.sample_workflow", ANY),
            call("", ANY),
            call("**Sample workflow**", ANY),
        ]

    def test_get_doc(self, target):
        actual = target.get_doc()

        assert actual == [
            ["This is a sample workflow that just runs a simple operation", ""]
        ]

    def test_document_members(self, target):
        target.document_members()

        assert target.directive.result.append.mock_calls == [
            call("", ANY),
        ]
