from typing import List

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


sub_flow = flow.Workflow(name="Sub Flow").nodes(
    add_message("sub_flow"),
)


sample_flow = (
    flow.Workflow(name="Sample Flow")
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
        flow.CaptureErrors("errors", try_all=True,).nodes(
            raise_error(ValueError("Error A")),
            raise_error(ValueError("Error B")),
        ),
        flow.If(lambda ctx: ctx.state["arg_1"] < ctx.state["arg_2"]).true(
            add_message("arg_1 is smaller")
        ),
        flow.ForEach("error", in_var="errors").loop(
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


def test_workflow():
    actual = sample_flow.execute()

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


def test_workflow_str():
    assert str(sub_flow) == "Sub Flow"
