import logging
import random
import time

import pyapp_flow as flow
from pyapp_flow.parallel_nodes import MapNodes


@flow.step(output="foo")
def report_value(value: str) -> str:
    delay = random.randint(1, 4)
    time.sleep(delay)
    if delay == 5:
        raise ValueError("EEK!")
    print(value)
    return value


parallel_print = flow.Workflow(name="parallel flow",).nodes(
    flow.SetVar(
        values=["abc", "def", "ghi", "jkl", "mno", "pqr"],
    ),
    MapNodes("value", in_var="values", merge_var="foo").loop(
        "parallel_sample:report_value"
    ),
    flow.LogMessage("Result: {foo}"),
)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    parallel_print.execute()
