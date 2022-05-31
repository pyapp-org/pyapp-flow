from typing import Tuple

import pytest

from pyapp_flow import functions, WorkflowContext
from pyapp_flow.exceptions import WorkflowSetupError


def valid_a(context: WorkflowContext):
    pass


def valid_b(context: WorkflowContext, var_a: str):
    pass


def valid_c(context: WorkflowContext, *, var_a: str):
    pass


def valid_d(context: WorkflowContext, *, var_a: str, var_b: int = 42):
    pass


def valid_e() -> int:
    pass


def valid_f(var_a: str) -> str:
    pass


def valid_g(var_a: str, *, var_b: int = 42) -> Tuple[str, int]:
    pass


def valid_h(*, var_a: str, var_b: int = 42):
    pass


@pytest.mark.parametrize(
    "func, expected",
    (
        (valid_a, ({}, "context")),
        (valid_b, ({"var_a": str}, "context")),
        (valid_c, ({"var_a": str}, "context")),
        (valid_d, ({"var_a": str, "var_b": int}, "context")),
        (valid_e, ({}, None)),
        (valid_f, ({"var_a": str}, None)),
        (valid_g, ({"var_a": str, "var_b": int}, None)),
        (valid_h, ({"var_a": str, "var_b": int}, None)),
    ),
)
def test_extract_inputs__where_args_are_valid(func, expected):
    actual = functions.extract_inputs(func)

    assert actual == expected


@pytest.mark.parametrize(
    "func, names, expected",
    (
        (valid_e, "var_a", (("var_a", int),)),
        (valid_e, ("var_a",), (("var_a", int),)),
        (valid_f, "var_b", (("var_b", str),)),
        (valid_f, ("var_b",), (("var_b", str),)),
        (valid_g, ("var_a", "var_b"), (("var_a", str), ("var_b", int))),
    ),
)
def test_extract_outputs__where_args_are_valid(func, names, expected):
    actual = functions.extract_outputs(func, names)

    assert actual == expected


def invalid_a(context: WorkflowContext, /):
    pass


def invalid_b(context: WorkflowContext, /, var_a: str):
    pass


def invalid_c(context: WorkflowContext, other_context: WorkflowContext):
    pass


@pytest.mark.parametrize(
    "func, expected",
    (
        (invalid_a, "Positional only arguments"),
        (invalid_b, "Positional only arguments"),
        (invalid_c, "WorkflowContext supplied multiple times"),
    ),
)
def test_extract_inputs__where_args_are_invalid(func, expected):
    with pytest.raises(WorkflowSetupError, match=expected):
        functions.extract_inputs(func)


@pytest.mark.parametrize(
    "func, names",
    (
        (valid_f, None),
        (valid_f, ("a", "b")),
        (valid_g, None),
        (valid_g, "a"),
        (valid_g, ("a", "b", "c")),
    ),
)
def test_extract_outputs__where_args_are_invalid(func, names):
    with pytest.raises(
        WorkflowSetupError, match="Name count does not match type count."
    ):
        functions.extract_outputs(func, names)
