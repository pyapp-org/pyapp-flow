import importlib
import logging
from pathlib import Path
from typing import Dict

from pyapp_flow import Workflow

log = logging.getLogger(__package__)


def _import_flow_file(flow_file: Path) -> object:
    """Import flow file and return the module."""
    if not flow_file.is_file():
        raise RuntimeError(f"Flow file not found at: {flow_file}")

    flow_module = importlib.import_module(flow_file.stem, flow_file.parent)
    return flow_module


def _resolve_flow(module: object, name: str) -> Workflow:
    """Resolve a workflow from a module."""
    flows = {
        value.name: value
        for key, value in module.__dict__.items()
        if isinstance(value, Workflow)
    }

    try:
        return flows[name]
    except KeyError:
        raise RuntimeError(
            f"Workflow not found: {name}; try one of: {', '.join(flows)}"
        )


def _resolve_required_args(flow: Workflow) -> Dict[str, type]:
    """Resolve required arguments from a workflow."""


def run_flow(flow_file: Path, name: str, args: Dict[str, str], dry_run: bool):
    """
    Run a workflow
    """
    flow_module = _import_flow_file(flow_file)
    flow = _resolve_flow(flow_module, name)

    try:
        flow.execute(**args, dry_run=dry_run)
    except Exception:
        log.exception("Error running workflow")
