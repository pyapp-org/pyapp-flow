from pathlib import Path
from typing import Optional, Dict

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
    args: Optional[Dict[str, str]] = Arg(),
    *,
    flow_file: Path = Arg(
        "-f",
        default=Path("./flowfile.py"),
        help="Location of flow file; default is ./flowfile.py",
    ),
    dry_run: bool = False
):
    """
    Run a workflow
    """
    from .actions import run_flow

    run_flow(flow_file, name, args or {}, dry_run)
