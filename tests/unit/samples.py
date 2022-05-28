from typing import Sequence

import pyapp_flow as wf


@wf.step(outputs=[("options", Sequence[str])])
def load_options() -> Sequence["str"]:
    """
    Load options from file
    """
    return ["a", "b", "f"]


@wf.step
def process_option(current_option: str):
    """
    Process an option
    """
    print(current_option)


process_workflow = (
    wf.Workflow()
    .nodes(load_options)
    .foreach("current_option", "options", process_option)
)


if __name__ == "__main__":
    process_workflow.execute()
