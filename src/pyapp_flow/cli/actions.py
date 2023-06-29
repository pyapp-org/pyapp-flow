import importlib.util
import logging
import sys
from pathlib import Path
from typing import Dict
from types import ModuleType

from pyapp_flow import Workflow

log = logging.getLogger(__package__)


def _import_flow_file(flow_file: Path) -> ModuleType:
    """Import flow file and return the module.

    Based off the import code in nox.
    """
    if not flow_file.is_file():
        raise RuntimeError(f"Flow file not found at: {flow_file}")

    spec = importlib.util.spec_from_file_location("user_flow_module", flow_file)
    if spec is None:
        raise RuntimeError(f"Unable to import flow file: {flow_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["user_flow_module"] = module

    # See https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    loader = spec.loader
    loader.exec_module(module)

    return module


def _resolve_flow(module: ModuleType, name: str) -> Workflow:
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
        ) from None


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
