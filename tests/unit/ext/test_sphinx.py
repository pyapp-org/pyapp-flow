from unittest.mock import Mock

import pytest

import pyapp_flow as flow

try:
    from sphinx.ext.autodoc.directive import DocumenterBridge, Options
    from pyapp_flow.ext import sphinx
except ImportError:
    pytest.skip("Sphinx not available for tests", allow_module_level=True)
else:

    @flow.step(name="Sample Step", output="arg_d")
    def sample_step(arg_a: int, *, arg_b: str, arg_c) -> bool:
        """
        This is a sample step that just outputs false
        """
        return False

    @flow.step(name="Simple Step")
    def simple_step():
        pass

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

        def test_get_doc__where_method_has_no_docstring(self, target):
            target.object = simple_step

            actual = target.get_doc()

            assert actual == []

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

        def test_document_members__with_no_inputs_or_outputs(self, target):
            target.object = simple_step
            target.document_members()

            assert target.directive.result.data == [""]

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

    basic_workflow = flow.Workflow(name="Basic workflow").nodes(
        flow.SetVar(samples=lambda ctx: ctx.state.a.title()),
        (lambda ctx: ctx.info("Technically valid!")),
        sample_step,
    )

    not_a_workflow = object()

    class TestWorkflowDocumenter:
        @pytest.fixture
        def target(self):
            directive = DocumenterBridge(
                Mock(),
                Mock(),
                Options(),
                15,
                state=Mock(document=Mock(settings=Mock(tab_width=4))),
            )
            target = sphinx.WorkflowDocumenter(directive, "Test")
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

            assert target.directive.result.data == [
                ".. py:function:: ext.test_sphinx.sample_workflow",
                "",
                "**Sample workflow**",
            ]

        def test_add_directive_header__with_no_name_option(self, target):
            target.options["noname"] = True
            target.add_directive_header("")

            assert target.directive.result.data == [
                ".. py:function:: ext.test_sphinx.sample_workflow",
            ]

        def test_get_doc(self, target):
            actual = target.get_doc()

            assert actual == [
                ["This is a sample workflow that just runs a simple operation", ""]
            ]

        def test_get_doc__with_no_doc(self, target):
            target.object = basic_workflow
            actual = target.get_doc()

            assert actual == []

        def test_document_members(self, target):
            target.document_members()

            assert target.directive.result.data == []

        def test_document_members__with_nodes_option(self, target):
            target.options["nodes"] = True
            target.document_members()

            assert target.directive.result.data == [
                "",
                "- Set value(s) for samples",
                "",
                "- For (`sample`) in `samples`",
                "",
                "  - **loop**",
                "",
                "    - Log Message 'Reviewing sample {sample}'",
                "",
                "- Sample Step",
            ]

        def test_document_members__with_nodes_option_and_a_non_navigable(self, target):
            target.object = basic_workflow
            target.options["nodes"] = True
            target.document_members()

            assert target.directive.result.data == [
                "",
                "- Set value(s) for samples",
                "",
                "- *Unknown node*",
                "",
                "- Sample Step",
            ]
