import pytest

from pyapp_flow import steps, WorkflowContext


def valid_step_a(var_a: str, *, var_b: int):
    return f"{var_a}:{var_b}"


def valid_step_b(var_a: str, var_b: int = 42, *, ctx: WorkflowContext):
    return f"{var_a}:{var_b}"


def valid_multiple_returns(var_a: str):
    return var_a, var_a


class TestStep:
    def test_init__generates_correct_name(self):
        actual = steps.Step(valid_step_a)

        assert actual.name == "valid step a"

    def test_init__uses_assigned_name(self):
        actual = steps.Step(valid_step_a, name="Custom name")

        assert actual.name == "Custom name"

    def test_init__resolves_inputs(self):
        actual = steps.Step(valid_step_b)

        assert actual.inputs == {"var_a": str, "var_b": int}
        assert actual.context_var == "ctx"

    def test_init__accepts_lambda(self):
        actual = steps.Step(lambda var_a: f"{var_a}!", name="foo")

        assert actual.inputs == {"var_a": None}

    def test_call__all_vars_defined(self):
        context = WorkflowContext(var_a="foo", var_b=13)
        target = steps.Step(valid_step_a, outputs=(("var_c", str),))

        actual = target(context)

        assert actual == "foo:13"
        assert context.state["var_c"] == actual


class TestSetVar:
    def test_call(self):
        context = WorkflowContext(var_a="foo", var_b=13)
        target = steps.SetVar(var_b=42, var_c="bar")

        target(context)

        assert context.state == {"var_a": "foo", "var_b": 42, "var_c": "bar"}


class TestForEach:
    def test_call__each_item_is_called(self):
        context = WorkflowContext(var_a=["a", "b", "c"], var_b=[])
        target = steps.ForEach(
            "char", "var_a", steps.Step(lambda char, var_b: var_b.append(char))
        )

        target(context)

        assert context.state["var_a"] == context.state["var_b"]

    def test_call__in_var_is_missing(self):
        context = WorkflowContext(var_b=[])
        target = steps.ForEach(
            "char", "var_a", steps.Step(lambda char, var_b: var_b.append(char))
        )

        with pytest.raises(KeyError, match="not found in context"):
            target(context)

    def test_call__in_var_is_not_iterable(self):
        context = WorkflowContext(var_a=None, var_b=[])
        target = steps.ForEach(
            "char", "var_a", steps.Step(lambda char, var_b: var_b.append(char))
        )

        with pytest.raises(TypeError, match="is not iterable"):
            target(context)

    def test_str(self):
        target = steps.ForEach(
            "char", "var_a", steps.Step(lambda char, var_b: var_b.append(char))
        )

        assert str(target) == "For `char` in `var_a`"


class TestCaptureErrors:
    pass
