import logging
from pathlib import Path
from typing import Sequence, Tuple

import pyapp_flow as flow
from pyapp_flow.parallel_nodes import MapNode

HERE = Path(__file__).parent


@flow.step(output="files")
def iterate_files() -> Sequence[Path]:
    folder = HERE.parent / "src/pyapp_flow"
    return [entry for entry in folder.iterdir() if entry.is_file()]


@flow.step(name="Count lines in {file.name}", output="file_sizes")
def count_lines(file: Path) -> Tuple[Path, int]:
    return (file, len(file.read_text().splitlines()))


@flow.step
def print_results(file_sizes: Sequence[Tuple[Path, int]]):
    print("\n".join(f"{f.name}: {lc}" for f, lc in file_sizes))


parallel_print = flow.Workflow(
    name="parallel flow",
).nodes(
    iterate_files,
    (
        MapNode("file", in_var="files")
        .loop("parallel_sample:count_lines")
        .merge_vars("file_sizes")
    ),
    print_results,
)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    parallel_print.execute()
