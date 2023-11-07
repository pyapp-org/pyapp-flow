from typing import List, Any
from unittest.mock import ANY

import pytest

import pyapp_flow as flow


@flow.step(output="arg_t")
def add_args(arg_1: int, arg_2: int) -> int:
    return arg_1 + arg_2


def add_message(msg: str):
    @flow.step
    def message(context: flow.WorkflowContext, messages: List[str]):
        messages.append(context.format(msg))

    return message


def raise_error(exception):
    @flow.step
    def error():
        raise exception

    return error


basic_flow = flow.Nodes(add_args, add_message)


class TestNodes:
    def test_str(self):
        assert str(basic_flow) == "⏬ Nodes"

    def test_branches(self):
        actual = basic_flow.branches()

        assert actual == {"": [ANY, ANY]}


sub_flow = flow.Workflow(name="Sub Flow").nodes(
    add_message("sub_flow"),
)


sample_flow = (
    flow.Workflow(name="Sample Flow")
    .require_vars(arg_3=int, arg_4=Any)
    .set_vars(
        messages=[],
        arg_1=13,
        arg_2=42,
    )
    .nodes(
        add_args,
        add_message("single"),
        add_message("{arg_t:03d}"),
        sub_flow,
    )
    .nested(add_message("nested"))
    .nodes(
        flow.CaptureErrors(
            "errors",
            try_all=True,
        ).nodes(
            raise_error(ValueError("Error A")),
            raise_error(ValueError("Error B")),
        ),
        flow.If(lambda ctx: ctx.state["arg_1"] < ctx.state["arg_2"]).true(
            add_message("arg_1 is smaller")
        ),
        flow.ForEach("error", in_var="errors", loop_label="error={error}").loop(
            flow.LogMessage("{error}"), add_message("{error}")
        ),
        flow.Switch("arg_1")
        .case(
            13,
            add_message("it's 13"),
        )
        .case(
            42,
            add_message("it's 42"),
        ),
    )
)


class TestWorkflow:
    def test_workflow(self):
        actual = sample_flow.execute(arg_3=69, arg_4="hello")

        assert actual.state["messages"] == [
            "single",
            "055",
            "sub_flow",
            "nested",
            "arg_1 is smaller",
            "Error A",
            "Error B",
            "it's 13",
        ]

    def test_workflow__where_required_var_is_not_defined(self):
        with pytest.raises(flow.errors.MissingVariableError):
            sample_flow.execute(arg_4="hello")

    def test_workflow__where_required_var_is_incorrect_type(self):
        with pytest.raises(flow.errors.VariableTypeError):
            sample_flow.execute(arg_3="not an int", arg_4="hello")

    def test_str(self):
        assert str(sub_flow) == "Sub Flow"
