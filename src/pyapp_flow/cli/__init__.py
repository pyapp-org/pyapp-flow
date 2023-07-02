from pathlib import Path
from typing import Optional, Dict, Mapping

from pyapp.app import CliApplication, Arg

app = CliApplication(
    description="PyApp Flow",
    env_loglevel_key="FLOW_LOGLEVEL",
    env_settings_key="FLOW_SETTINGS",
)
main = app.dispatch


@app.command
def run(
    name: str = Arg(help="Name of workflow"),
    args: Mapping[str, str] = Arg(help="Key/Value arguments added to flow context"),
    *,
    flow_file: Path = Arg(
        "-f",
        default=Path("./flowfile.py"),
        help="Location of flow file; default is ./flowfile.py",
    ),
    dry_run: bool = Arg(default=False, help="Dry run; do not execute actions"),
) -> Optional[int]:
    """
    Run a workflow
    """
    from .actions import run_flow

    return run_flow(flow_file, name, args or {}, dry_run)


@app.command
def graph(
    name: str = Arg(help="Name of workflow"),
    *,
    flow_file: Path = Arg(
        "-f",
        default=Path("./flowfile.py"),
        help="Location of flow file; default is ./flowfile.py",
    ),
) -> Optional[int]:
    """
    Graph a workflow.
    """
    from .actions import graph_flow

    return graph_flow(flow_file, name)
