"""CLI entry point."""
from importlib import metadata
from pathlib import Path
from typing import Optional

from pyapp.app import CliApplication, Arg, argument, CommandOptions, KeyValueAction

app = CliApplication(
    description="PyApp Flow",
    version=metadata.version("pyapp-flow"),
    env_loglevel_key="FLOW_LOGLEVEL",
    env_settings_key="FLOW_SETTINGS",
)
main = app.dispatch


@app.command(name="list", aliases=("ls",))
def list_flows(
    *,
    flow_file: Path = Arg(
        "-f",
        "--flow-file",
        default=Path("./flowfile.py"),
        help="Location of flow file; default is ./flowfile.py",
    ),
) -> Optional[int]:
    """List available workflows."""
    from .actions import list_flows

    return list_flows(flow_file)


@app.command
@argument("NAME", help_text="Name of workflow")
@argument(
    "ARGS",
    action=KeyValueAction,
    nargs="*",
    help_text="Key/Value arguments added to flow context",
)
@argument(
    "-f",
    "--flow-file",
    type=Path,
    default=Path("./flowfile.py"),
    help_text="Location of flow file; default is ./flowfile.py",
)
@argument(
    "--dry-run",
    action="store_true",
    help_text="Dry run; do not execute actions",
)
@argument(
    "--full-trace",
    action="store_true",
    help_text="Show full trace on error.",
)
def run(opts: CommandOptions) -> Optional[int]:
    """Run a workflow."""
    from .actions import run_flow

    return run_flow(opts.flow_file, opts.NAME, opts.ARGS, opts.dry_run, opts.full_trace)


# @app.command
# def graph(
#     name: str = Arg(help="Name of workflow"),
#     *,
#     flow_file: Path = Arg(
#         "-f",
#         "--flow-file",
#         default=Path("./flowfile.py"),
#         help="Location of flow file; default is ./flowfile.py",
#     ),
# ) -> Optional[int]:
#     """Graph a workflow."""
#     from .actions import graph_flow
#
#     return graph_flow(flow_file, name)
