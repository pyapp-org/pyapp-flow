import logging

import pytest

from pyapp_flow import datastructures


class TestState:
    def test_set_attr__where_var_is_new(self):
        target = datastructures.State(var_a=1, var_b=2)

        target.var_c = 3

        assert target == {"var_a": 1, "var_b": 2, "var_c": 3}

    def test_set_attr__where_var_exists(self):
        target = datastructures.State(var_a=1, var_b=2)

        target.var_a = 2

        assert target == {"var_a": 2, "var_b": 2}

    def test_get_attr__where_var_exists(self):
        target = datastructures.State(var_a=1, var_b=2)

        actual = target.var_b

        assert actual == 2

    def test_get_attr__where_var_missing(self):
        target = datastructures.State(var_a=1, var_b=2)

        with pytest.raises(AttributeError):
            target.var_c

    def test_del_attr__where_var_exists(self):
        target = datastructures.State(var_a=1, var_b=2)

        del target.var_b

        assert target == {"var_a": 1}

    def test_del_attr__where_var_missing(self):
        target = datastructures.State(var_a=1, var_b=2)

        with pytest.raises(AttributeError):
            del target.var_c


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

        target.state.var_c = 3

        assert target.state == {"__trace": [], "var_a": 1, "var_b": 2, "var_c": 3}
        assert target.depth == 1

        # Enter nested scope
        target.push_state()
        target.state.var_a = 2
        del target.state["var_b"]
        target.state.var_d = 4

        assert target.state == {"__trace": [], "var_a": 2, "var_c": 3, "var_d": 4}
        assert target.depth == 2

        # Enter nested scope
        target.push_state()
        target.state.var_b = 2
        target.state.var_a = 1

        assert target.state == {
            "__trace": [],
            "var_a": 1,
            "var_c": 3,
            "var_d": 4,
            "var_b": 2,
        }
        assert target.depth == 3

        # Exit nested scope
        target.pop_state()

        assert target.state == {"__trace": [], "var_a": 2, "var_c": 3, "var_d": 4}
        assert target.depth == 2

        # Exit nested scope
        target.pop_state()

        assert target.state == {"__trace": [], "var_a": 1, "var_b": 2, "var_c": 3}
        assert target.depth == 1

    @pytest.mark.parametrize(
        "method, message, expected_level",
        (
            (
                datastructures.WorkflowContext.debug,
                "Log a debug message",
                logging.DEBUG,
            ),
            (datastructures.WorkflowContext.info, "Log an info message", logging.INFO),
            (
                datastructures.WorkflowContext.warning,
                "Log an warning message",
                logging.WARNING,
            ),
            (
                datastructures.WorkflowContext.error,
                "Log an error message",
                logging.ERROR,
            ),
            (
                datastructures.WorkflowContext.exception,
                "Log an exception message",
                logging.ERROR,
            ),
        ),
    )
    def test_logging__where_level_enabled(
        self, caplog, method, message, expected_level
    ):
        caplog.set_level(logging.DEBUG)
        target = datastructures.WorkflowContext(var_a=1, var_b=2)

        method(target, message)
        actual = caplog.record_tuples[0]

        assert actual == ("pyapp_flow", expected_level, f"  {message}")


class TestDescribeContext:
    def test_init(self):
        target = datastructures.DescribeContext("foo", bar=int)

        assert target.state == {"foo": (None, None), "bar": (int, None)}
