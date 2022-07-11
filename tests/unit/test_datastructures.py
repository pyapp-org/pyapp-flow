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

    def test_state(self):
        target = datastructures.WorkflowContext(var_a=1, var_b=2)

        target.state["var_c"] = 3

        assert target.state == {"var_a": 1, "var_b": 2, "var_c": 3}
        assert target.depth == 1

        # Enter nested scope
        target.push_state()
        target.state["var_a"] = 2
        del target.state["var_b"]
        target.state["var_d"] = 4

        assert target.state == {"var_a": 2, "var_c": 3, "var_d": 4}
        assert target.depth == 2

        # Enter nested scope
        target.push_state()
        target.state["var_b"] = 2
        target.state["var_a"] = 1

        assert target.state == {"var_a": 1, "var_c": 3, "var_d": 4, "var_b": 2}
        assert target.depth == 3

        # Exit nested scope
        target.pop_state()

        assert target.state == {"var_a": 2, "var_c": 3, "var_d": 4}
        assert target.depth == 2

        # Exit nested scope
        target.pop_state()

        assert target.state == {"var_a": 1, "var_b": 2, "var_c": 3}
        assert target.depth == 1
