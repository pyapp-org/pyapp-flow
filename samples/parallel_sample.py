import logging
import random
import time

import pyapp_flow as flow
from pyapp_flow.parallel_nodes import ParallelForEach


@flow.step
def report_value(value: str):
    time.sleep(random.randint(1, 4))
    print(value)


parallel_print = flow.Workflow(name="parallel flow",).nodes(
    flow.SetVar(
        values=["abc", "def", "ghi", "jkl", "mno", "pqr"],
    ),
    ParallelForEach("value", in_var="values").loop("parallel_sample:report_value"),
)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    parallel_print.execute()
