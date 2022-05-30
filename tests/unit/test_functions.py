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


def valid_e():
    pass


def valid_f(var_a: str):
    pass


def valid_g(var_a: str, *, var_b: int = 42):
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
