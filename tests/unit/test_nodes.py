from typing import Tuple

import pytest

from pyapp_flow import nodes, WorkflowContext
from pyapp_flow.exceptions import FatalError, WorkflowRuntimeError


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


class TestStep:
    def test_init__generates_correct_name(self):
        actual = nodes.Step(valid_step_a, output="arg_t")

        assert str(actual) == "valid step a"

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


class TestSetVar:
    def test_call(self):
        context = WorkflowContext(var_a="foo", var_b=13)
        target = nodes.SetVar(var_b=42, var_c="bar")

        target(context)

        assert context.state == {"var_a": "foo", "var_b": 42, "var_c": "bar"}

    def test_str(self):
        target = nodes.SetVar(var_b=42, var_c="bar")

        assert str(target) == "Set value(s) for var_b, var_c"


class TestForEach:
    def test_call__each_item_is_called(self):
        context = WorkflowContext(var_a=["ab", "cd", "ef"], var_b=[])
        target = nodes.ForEach("char", in_var="var_a").loop(
            nodes.Step(lambda char, var_b: var_b.append(char))
        )

        target(context)

        assert context.state["var_a"] == context.state["var_b"]

    def test_call__in_var_is_missing(self):
        context = WorkflowContext(var_b=[])
        target = nodes.ForEach("char", in_var="var_a").loop(
            nodes.Step(lambda char, var_b: var_b.append(char))
        )

        with pytest.raises(WorkflowRuntimeError, match="not found in context"):
            target(context)

    def test_call__in_var_is_not_iterable(self):
        context = WorkflowContext(var_a=None, var_b=[])
        target = nodes.ForEach("char", in_var="var_a").loop(
            nodes.Step(lambda char, var_b: var_b.append(char))
        )

        with pytest.raises(WorkflowRuntimeError, match="is not iterable"):
            target(context)

    def test_call__in_var_is_multiple_parts(self):
        context = WorkflowContext(var_a=[("a", 1), ("b", 2), ("c", 3)], var_b=[])
        target = nodes.ForEach(("key_a", "key_b"), in_var="var_a",).loop(
            nodes.Step(lambda key_a, key_b, var_b: var_b.append(key_b)),
        )

        target(context)
        actual = context.state["var_b"]

        assert actual == [1, 2, 3]

    def test_call__in_var_is_multiple_string(self):
        context = WorkflowContext(var_a=[("a", 1), ("b", 2), ("c", 3)], var_b=[])
        target = nodes.ForEach("key_a, key_b", in_var="var_a",).loop(
            nodes.Step(lambda key_a, key_b, var_b: var_b.append(key_b)),
        )

        target(context)
        actual = context.state["var_b"]

        assert actual == [1, 2, 3]

    def test_call__in_var_is_multiple_parts_not_iterable(self):
        context = WorkflowContext(var_a=[("a", 1), 2, ("c", 3)], var_b=[])
        target = nodes.ForEach(("key_a", "key_b"), in_var="var_a",).loop(
            nodes.Step(lambda key_a, key_b, var_b: var_b.append(key_b)),
        )

        with pytest.raises(WorkflowRuntimeError, match="is not iterable"):
            target(context)

    def test_str__single_value(self):
        target = nodes.ForEach("char", in_var="var_a").loop(
            nodes.Step(lambda char, var_b: var_b.append(char))
        )

        assert str(target) == "For (char) in `var_a`"

    def test_str__multi_value(self):
        target = nodes.ForEach(("key_a", "key_b"), in_var="var_a").loop(
            nodes.Step(lambda char, var_b: var_b.append(char)),
        )

        assert str(target) == "For (key_a, key_b) in `var_a`"


class TestCaptureErrors:
    def test_call__with_no_errors(self):
        context = WorkflowContext()
        target = nodes.CaptureErrors("errors", nodes.LogMessage("foo"))

        target(context)

        assert context.state["errors"] == []

    def test_call__fail_on_first_error(self):
        context = WorkflowContext()
        target = nodes.CaptureErrors(
            "errors",
            nodes.LogMessage("foo"),
            nodes.Step(valid_raise_exception),
            nodes.Step(valid_raise_exception),
            try_all=False,
        )

        target(context)

        assert [str(e) for e in context.state["errors"]] == ["'Boom!'"]

    def test_call__continue_after_error(self):
        context = WorkflowContext()
        target = nodes.CaptureErrors(
            "errors",
            nodes.LogMessage("foo"),
            nodes.Step(valid_raise_exception),
            nodes.Step(valid_raise_exception),
        )

        target(context)

        assert [str(e) for e in context.state["errors"]] == ["'Boom!'", "'Boom!'"]

    def test_str(self):
        target = nodes.CaptureErrors("errors", nodes.LogMessage("foo"))

        assert str(target) == "Capture errors into `errors`"


class TestConditional:
    def test_call__true_branch_with_named_variable(self):
        context = WorkflowContext(var=True)
        target = (
            nodes.Conditional("var")
            .true(nodes.append("message", "True"))
            .false(nodes.append("message", "False"))
        )

        target(context)

        assert context.state["message"] == ["True"]

    def test_call__false_branch_with_named_variable(self):
        context = WorkflowContext(var=False)
        target = (
            nodes.Conditional("var")
            .true(nodes.append("message", "True"))
            .false(nodes.append("message", "False"))
        )

        target(context)

        assert context.state["message"] == ["False"]

    def test_call__true_branch_with_callable(self):
        context = WorkflowContext()
        target = (
            nodes.Conditional(lambda ctx: True)
            .true(nodes.append("message", "True"))
            .false(nodes.append("message", "False"))
        )

        target(context)

        assert context.state["message"] == ["True"]

    def test_call__false_branch_with_callable(self):
        context = WorkflowContext()
        target = (
            nodes.Conditional(lambda ctx: False)
            .true(nodes.append("message", "True"))
            .false(nodes.append("message", "False"))
        )

        target(context)

        assert context.state["message"] == ["False"]

    def test_call__invalid_conditional(self):
        with pytest.raises(TypeError):
            nodes.Conditional(None)


class TestSwitch:
    @pytest.fixture
    def target(self):
        return (
            nodes.Switch("who")
            .case(
                "foo", nodes.append("message", "foo1"), nodes.append("message", "foo2")
            )
            .case(
                "bar", nodes.append("message", "bar1"), nodes.append("message", "bar2")
            )
        )

    def test_call__matching_branch(self, target):
        context = WorkflowContext(who="foo")

        target(context)

        assert context.state["message"] == ["foo1", "foo2"]

    def test_call__using_default(self, target):
        context = WorkflowContext(who="eek")
        target.default(nodes.append("message", "default"))

        target(context)

        assert context.state["message"] == ["default"]

    def test_call__no_matching_branch(self, target):
        context = WorkflowContext(who="eek")

        target(context)

        assert "message" not in context.state

    def test_call__with_lambda_condition(self):
        context = WorkflowContext(who="foo")
        target = nodes.Switch(lambda ctx: ctx.state["who"]).case(
            "foo", nodes.append("message", "foo1")
        )

        target(context)

        assert context.state["message"] == ["foo1"]

    def test_call__with_invalid_condition(self):

        with pytest.raises(TypeError, match="condition not context "):
            nodes.Switch(None)
