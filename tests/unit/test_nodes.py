import logging
from typing import Tuple, List
from unittest.mock import ANY

import pytest

from pyapp_flow import nodes, WorkflowContext, skip_step
from pyapp_flow.errors import FatalError, WorkflowRuntimeError, StepFailedError
from pyapp_flow.testing import call_node


def valid_step_a(var_a: str, *, var_b: int) -> str:
    return f"{var_a}:{var_b}"


def valid_step_b(var_a: str, var_b: int = 42, *, ctx: WorkflowContext) -> str:
    return f"{var_a}:{var_b}"


def valid_multiple_returns(var_a: str) -> Tuple[str, str]:
    return var_a, var_a


def valid_raise_exception():
    raise KeyError("Boom!")


def valid_raise_fatal_exception():
    raise FatalError("Boom!")


def valid_skip_step():
    skip_step("Skip!")


class TestStep:
    def test_init__generates_correct_name(self):
        actual = nodes.Step(valid_step_a, output="arg_t")

        assert str(actual) == "Valid Step A"

    def test_init__uses_assigned_name(self):
        actual = nodes.Step(valid_step_a, name="Custom name", output="arg_t")

        assert str(actual) == "Custom name"

    def test_init__resolves_inputs(self):
        actual = nodes.Step(valid_step_b, output="arg_t")

        assert actual.inputs == {"var_a": str, "var_b": int}
        assert actual.context_var == "ctx"

    def test_init__accepts_lambda(self):
        actual = nodes.Step(lambda var_a: f"{var_a}!", name="foo")

        assert actual.inputs == {"var_a": None}

    def test_call__all_vars_defined(self):
        context = WorkflowContext(var_a="foo", var_b=13)
        target = nodes.Step(valid_step_a, output="var_c")

        actual = target(context)

        assert actual == "foo:13"
        assert context.state["var_c"] == actual

    def test_call__ignore_error(self):
        context = WorkflowContext()
        target = nodes.Step(valid_raise_exception, ignore_exceptions=KeyError)

        target(context)

    def test_call__unhandled_error(self):
        context = WorkflowContext()
        target = nodes.Step(valid_raise_exception, ignore_exceptions=TypeError)

        with pytest.raises(KeyError):
            target(context)

    def test_call__fatal_error(self):
        context = WorkflowContext()
        target = nodes.Step(valid_raise_fatal_exception, ignore_exceptions=TypeError)

        with pytest.raises(FatalError):
            target(context)

    def test_call__skipped(self):
        context = WorkflowContext()
        target = nodes.Step(valid_skip_step)

        target(context)


class TestAppend:
    def test_call__with_existing_variable(self):
        target = nodes.Append(target_var="messages", message="bar")

        context = call_node(target, messages=["foo"])

        assert context.state.messages == ["foo", "bar"]

    def test_call__with_no_variable(self):
        target = nodes.Append(target_var="messages", message="bar")

        context = call_node(target)

        assert context.state.messages == ["bar"]

    def test_call__with_formatting(self):
        target = nodes.Append(target_var="messages", message="{who}bar")

        context = call_node(target, who="foo")

        assert context.state.messages == ["foobar"]

    def test_str(self):
        target = nodes.Append(target_var="messages", message="bar")

        assert str(target) == "Append 'bar' to messages"


class TestSetVar:
    def test_call(self):
        target = nodes.SetVar(
            var_b=42, var_c="bar", var_d=lambda ctx: ctx.state["var_a"] + "bar"
        )

        context = call_node(target, var_a="foo", var_b=13)

        assert context.state == {
            "__trace": [ANY],
            "var_a": "foo",
            "var_b": 42,
            "var_c": "bar",
            "var_d": "foobar",
        }

    def test_str(self):
        target = nodes.SetVar(var_b=42, var_c="bar")

        assert str(target) == "Set value(s) for var_b, var_c"


class TestForEach:
    def test_call__each_item_is_called(self):
        target = nodes.ForEach("char", in_var="var_a").loop(
            nodes.Step(lambda char, var_b: var_b.append(char))
        )

        context = call_node(
            target,
            var_a=["ab", "cd", "ef"],
            var_b=[],
        )

        assert context.state.var_a == context.state.var_b

    def test_call__in_var_is_missing(self):
        target = nodes.ForEach("char", in_var="var_a").loop(
            nodes.Step(lambda char, var_b: var_b.append(char))
        )

        with pytest.raises(WorkflowRuntimeError, match="not found in context"):
            call_node(target, var_b=[])

    def test_call__in_var_is_not_iterable(self):
        target = nodes.ForEach("char", in_var="var_a").loop(
            nodes.Step(lambda char, var_b: var_b.append(char))
        )
        with pytest.raises(WorkflowRuntimeError, match="is not iterable"):
            call_node(target, var_a=None, var_b=[])

    def test_call__in_var_is_multiple_parts(self):
        target = nodes.ForEach(
            ("key_a", "key_b"),
            in_var="var_a",
        ).loop(
            nodes.Step(lambda key_a, key_b, var_b: var_b.append(key_b)),
        )

        context = call_node(target, var_a=[("a", 1), ("b", 2), ("c", 3)], var_b=[])

        assert context.state.var_b == [1, 2, 3]

    def test_call__in_var_is_multiple_string(self):
        target = nodes.ForEach(
            "key_a, key_b",
            in_var="var_a",
        ).loop(
            nodes.Step(lambda key_a, key_b, var_b: var_b.append(key_b)),
        )

        context = call_node(
            target,
            var_a=[("a", 1), ("b", 2), ("c", 3)],
            var_b=[],
        )

        assert context.state.var_b == [1, 2, 3]

    def test_call__in_var_is_multiple_parts_not_iterable(self):
        target = nodes.ForEach(
            ("key_a", "key_b"),
            in_var="var_a",
        ).loop(
            nodes.Step(lambda key_a, key_b, var_b: var_b.append(key_b)),
        )

        with pytest.raises(WorkflowRuntimeError, match="is not iterable"):
            call_node(target, var_a=[("a", 1), 2, ("c", 3)], var_b=[])

    def test_str__single_value(self):
        target = nodes.ForEach("char", in_var="var_a").loop(
            nodes.Step(lambda char, var_b: var_b.append(char))
        )

        assert str(target) == "For (`char`) in `var_a`"

    def test_str__multi_value(self):
        target = nodes.ForEach(("key_a", "key_b"), in_var="var_a").loop(
            nodes.Step(lambda char, var_b: var_b.append(char)),
        )

        assert str(target) == "For (`key_a`, `key_b`) in `var_a`"

    def test_branches(self):
        target = nodes.ForEach(("key_a", "key_b"), in_var="var_a").loop(
            nodes.Step(lambda char, var_b: var_b.append(char)),
        )

        actual = target.branches()

        assert actual == {
            "loop": (ANY,),
        }


class TestCaptureErrors:
    def test_call__with_no_errors(self):
        context = call_node(
            nodes.CaptureErrors("errors").nodes(nodes.LogMessage("foo")),
        )

        assert context.state["errors"] == []

    def test_call__fail_on_first_error(self):
        context = call_node(
            nodes.CaptureErrors("errors", try_all=False).nodes(
                nodes.LogMessage("foo"),
                nodes.Step(valid_raise_exception),
                nodes.Step(valid_raise_exception),
            )
        )

        assert [str(e) for e in context.state["errors"]] == ["'Boom!'"]

    def test_call__continue_after_error(self):
        context = call_node(
            nodes.CaptureErrors("errors").nodes(
                nodes.LogMessage("foo"),
                nodes.Step(valid_raise_exception),
                nodes.Step(valid_raise_exception),
            ),
        )

        assert [str(e) for e in context.state["errors"]] == ["'Boom!'", "'Boom!'"]

    def test_call__match_specified_exception(self):
        context = call_node(
            nodes.CaptureErrors("errors", except_types=KeyError).nodes(
                nodes.Step(valid_raise_exception),
            )
        )

        assert [str(e) for e in context.state.errors] == ["'Boom!'"]

    def test_call__not_match_specified_exception(self):
        with pytest.raises(KeyError):
            call_node(
                nodes.CaptureErrors("errors", except_types=(ValueError,)).nodes(
                    nodes.Step(valid_raise_exception),
                )
            )

    def test_str(self):
        target = nodes.CaptureErrors("errors").nodes(nodes.LogMessage("foo"))

        assert str(target) == "Capture errors into `errors`"

    def test_branches(self):
        target = nodes.CaptureErrors("errors", try_all=False).nodes(
            nodes.LogMessage("foo"),
            nodes.Step(valid_raise_exception),
            nodes.Step(valid_raise_exception),
        )

        actual = target.branches()

        assert actual == {"": (ANY, ANY, ANY)}


class TestConditional:
    def test_call__true_branch_with_named_variable(self):
        target = (
            nodes.Conditional("var")
            .true(nodes.Append("message", "True"))
            .false(nodes.Append("message", "False"))
        )
        context = call_node(target, var=True)

        assert context.state["message"] == ["True"]

    def test_call__false_branch_with_named_variable(self):
        target = (
            nodes.Conditional("var")
            .true(nodes.Append("message", "True"))
            .false(nodes.Append("message", "False"))
        )

        context = call_node(target, var=False)

        assert context.state["message"] == ["False"]

    def test_call__true_branch_with_callable(self):
        target = (
            nodes.Conditional(lambda ctx: True)
            .true(nodes.Append("message", "True"))
            .false(nodes.Append("message", "False"))
        )

        context = call_node(target)

        assert context.state["message"] == ["True"]

    def test_call__false_branch_with_callable(self):
        target = (
            nodes.Conditional(lambda ctx: False)
            .true(nodes.Append("message", "True"))
            .false(nodes.Append("message", "False"))
        )

        context = call_node(target)

        assert context.state["message"] == ["False"]

    def test_call__branch_no_nodes(self):
        target = nodes.Conditional(lambda ctx: False).true(
            nodes.Append("message", "True")
        )

        context = call_node(target)

        assert "message" not in context.state

    def test_call__invalid_conditional(self):
        with pytest.raises(TypeError):
            nodes.Conditional(None)

    def test_str(self):
        target = nodes.Conditional("foo")

        assert str(target) == "Conditional branch"

    def test_branches(self):
        target = (
            nodes.Conditional(lambda ctx: False)
            .true(nodes.Append("message", "True"))
            .false(nodes.Append("message", "False"))
        )

        actual = target.branches()

        assert actual == {
            "true": (ANY,),
            "false": (ANY,),
        }


class TestSwitch:
    @pytest.fixture
    def target(self):
        return (
            nodes.Switch("who")
            .case(
                "foo", nodes.Append("message", "foo1"), nodes.Append("message", "foo2")
            )
            .case(
                "bar", nodes.Append("message", "bar1"), nodes.Append("message", "bar2")
            )
        )

    def test_call__matching_branch(self, target):
        context = call_node(target, who="foo")

        assert context.state["message"] == ["foo1", "foo2"]

    def test_call__using_default(self, target):
        target.default(nodes.Append("message", "default"))

        context = call_node(target, who="eek")

        assert context.state["message"] == ["default"]

    def test_call__no_matching_branch(self, target):
        context = call_node(target, who="eek")

        assert "message" not in context.state

    def test_call__with_lambda_condition(self):
        target = nodes.Switch(lambda ctx: ctx.state["who"]).case(
            "foo", nodes.Append("message", "foo1")
        )

        context = call_node(target, who="foo")

        assert context.state["message"] == ["foo1"]

    def test_call__with_invalid_condition(self):
        with pytest.raises(TypeError, match="condition not context "):
            nodes.Switch(None)

    def test_str(self, target):
        assert str(target) == "Switch into foo, bar"

    def test_branches(self, target):
        actual = target.branches()

        assert actual == {
            "bar": (ANY, ANY),
            "foo": (ANY, ANY),
        }

    def test_branches__with_default(self, target):
        target.default(nodes.LogMessage("default called"))

        actual = target.branches()

        assert actual == {
            "bar": (ANY, ANY),
            "foo": (ANY, ANY),
            "*DEFAULT*": (ANY,),
        }


class TestLogMessage:
    def test_call__with_default_level(self, caplog):
        target = nodes.LogMessage("Foo{who}")

        with caplog.at_level(logging.INFO):
            call_node(target, who="bar")

        assert caplog.messages == ["  Foobar"]

    def test_call__with_error_level(self, caplog):
        target = nodes.LogMessage("Foo{who}", level=logging.ERROR)

        with caplog.at_level(logging.ERROR):
            call_node(target, who="bar")

        assert caplog.messages == ["  Foobar"]

    def test_call__at_greater_depth(self, caplog):
        context = WorkflowContext(who="oobar")
        target = nodes.LogMessage("Foo{who}")

        with caplog.at_level(logging.INFO):
            with context:
                target(context)

        assert caplog.messages == ["    Foooobar"]

    def test_str(self):
        target = nodes.LogMessage("Foo{who}")

        assert str(target) == "Log Message 'Foo{who}'"

    @pytest.mark.parametrize(
        "target, level",
        (
            (nodes.LogMessage("Foo{who}"), logging.INFO),
            (nodes.LogMessage.debug("Foo{who}"), logging.DEBUG),
            (nodes.LogMessage.info("Foo{who}"), logging.INFO),
            (nodes.LogMessage.warning("Foo{who}"), logging.WARNING),
            (nodes.LogMessage.error("Foo{who}"), logging.ERROR),
        ),
    )
    def test_log_level_methods(self, target, level):
        assert target.level == level
        assert target.message == "Foo{who}"


def track_step(match_value: str) -> nodes.Step:
    def _step(track: List[str], var_a: str):
        track.append(match_value)
        if var_a != match_value:
            raise StepFailedError()

    return nodes.Step(_step, name="tracking_step")


class TestTryUntil:
    @pytest.fixture
    def target(self):
        return (
            nodes.TryUntil()
            .nodes(track_step("a"), track_step("b"), track_step("c"))
            .default(nodes.Append("track", "default"))
        )

    def test_call__where_first_step_matches(self, target):
        context = call_node(target, track=[], var_a="a")

        assert context.state["track"] == ["a"]

    def test_call__where_last_step_matches(self, target):
        context = call_node(target, track=[], var_a="c")

        assert context.state["track"] == ["a", "b", "c"]

    def test_call__where_no_steps_match(self, target):
        context = call_node(target, track=[], var_a="z")

        assert context.state["track"] == ["a", "b", "c", "default"]

    def test_call__where_other_exception(self, target):
        target.except_types = (ValueError,)

        with pytest.raises(StepFailedError):
            call_node(target, track=[], var_a="z")
