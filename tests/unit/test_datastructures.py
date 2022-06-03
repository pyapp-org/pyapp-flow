import pytest

from pyapp_flow import datastructures


class TestWorkflowContext:
    @pytest.mark.parametrize(
        "message, expected",
        (
            ("Foo", "Foo"),
            ("Foo {var_a}", "Foo Bar"),
            ("Foo {var_b:03d}", "Foo 042"),
            # Bad
            ("Foo {var_c}", "Foo {var_c}"),
            ("Foo {var_b:03z}", "Foo {var_b:03z}"),
        ),
    )
    def test_format(self, message, expected):
        target = datastructures.WorkflowContext(var_a="Bar", var_b=42)

        actual = target.format(message)

        assert actual == expected
