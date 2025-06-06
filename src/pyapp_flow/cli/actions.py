"""Actions for the CLI."""

import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType

from rich import print
from rich.traceback import Traceback

import pyapp_flow
from pyapp_flow import Workflow, WorkflowContext, errors

log = logging.getLogger(__package__)


def _import_flow_file(flow_file: Path) -> ModuleType:
    """Import flow file and return the module.

    Based off the import code in nox.
    """
    if not flow_file.is_file():
        msg = f"Flow file not found at: {flow_file}"
        raise FileNotFoundError(msg)

    spec = importlib.util.spec_from_file_location("user_flow_module", flow_file)
    if spec is None:
        msg = f"Unable to import flow file: {flow_file}"
        raise ImportError(msg)

    module = importlib.util.module_from_spec(spec)
    sys.modules["user_flow_module"] = module

    # See https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    loader = spec.loader
    loader.exec_module(module)

    return module


def _resolve_flow(module: ModuleType, name: str) -> Workflow:
    """Resolve a workflow from a module."""
    flows = {
        key: value
        for key, value in module.__dict__.items()
        if isinstance(value, Workflow)
    }

    try:
        return flows[name]
    except KeyError:
        msg = f"Workflow not found: {name}; try one of: {', '.join(flows)}"
        raise RuntimeError(msg) from None


def list_flows(flow_file: Path):
    """List workflows in the flow file."""
    try:
        flow_module = _import_flow_file(flow_file)
    except FileNotFoundError:
        log.error("Flow file not found")
        return 404

    flows = [
        f"\n⏩ {key}"
        for key, value in flow_module.__dict__.items()
        if isinstance(value, Workflow)
    ]

    print(f"Available workflows:{''.join(flows)}")


def run_flow(
    flow_file: Path, name: str, args: dict[str, str], dry_run: bool, full_trace: bool
) -> int:
    """Run a workflow."""
    try:
        flow_module = _import_flow_file(flow_file)
    except FileNotFoundError:
        log.error("Flow file not found")
        return 13
    except Exception:
        traceback = Traceback(
            suppress=() if full_trace else [pyapp_flow],
            show_locals=True,
        )
        print(traceback)
        return 1

    try:
        flow = _resolve_flow(flow_module, name)
    except RuntimeError as ex:
        log.error(ex)
        return 13

    context = WorkflowContext(
        dry_run=dry_run,
        flow_path=flow_file.parent.resolve(),
    )

    try:
        flow.execute(context, **args)
    except errors.VariableError as ex:
        if context.flow_trace:
            print(context.flow_trace)
        print(f"{flow.name} {ex}")
        return 1
    except Exception:
        print(context.flow_trace)
        traceback = Traceback(
            suppress=() if full_trace else [pyapp_flow],
            show_locals=True,
        )
        print(traceback)
        return 1


def graph_flow(flow_file: Path, name: str):
    """Graph a workflow."""
    try:
        flow_module = _import_flow_file(flow_file)
    except FileNotFoundError:
        log.error("Flow file not found")
        return 404

    try:
        flow = _resolve_flow(flow_module, name)
    except RuntimeError as ex:
        log.error(ex)
        return 404
