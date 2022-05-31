import logging
from typing import Sequence

import pyapp_flow as flow


@flow.step(output="options")
def load_options() -> Sequence["str"]:
    """
    Load options from file
    """
    return ["abc", "def", "ghi"]


@flow.step
def process_option(current_option: str, foo: str):
    """
    Process an option
    """
    print(foo, current_option)


@flow.step(output="rcurrent_object")
def flip_option(current_option: str) -> str:
    """
    Process an option
    """
    return "".join(reversed(current_option))


@flow.step
def print_flip_option(rcurrent_object: str):
    """
    Process an option
    """
    print(rcurrent_object)


@flow.step(ignore_exceptions=ValueError)
def fail_nicely():
    raise ValueError("Eek!")


flip_workflow = flow.Workflow(name="Flip Workflow").nodes(
    flip_option,
    print_flip_option,
)

process_workflow = (
    flow.Workflow(name="Do Process")
    .set_vars(foo="bar")
    .nodes(
        fail_nicely,
        load_options,
        flow.Conditional("good").false(flow.log_message("{foo} is False")),
    )
    .foreach("current_option", "options", process_option, flip_workflow)
)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print(process_workflow.execute().state)
