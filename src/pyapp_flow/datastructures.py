from __future__ import annotations

import logging
from typing import Dict, Any


class WorkflowContext:
    """
    Current context of the workflow
    """

    __slots__ = ("_state", "log")

    def __init__(self, logger: logging.Logger = None, **variables):
        self._state = [variables]
        self.log = logger or logging.getLogger("pyapp_flow")

    def __enter__(self):
        self.push_state()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pop_state()

    def push_state(self):
        """
        Clone the current state so any modification doesn't affect the outer scope
        """
        self._state.append(dict(self.state))

    def pop_state(self):
        """
        Discard current state scope
        """
        self._state.pop(-1)

    @property
    def state(self) -> Dict[str, Any]:
        """
        Current state
        """
        return self._state[-1]

    @property
    def depth(self) -> int:
        """
        Current nesting level
        """
        return len(self._state)

    @property
    def indent(self) -> str:
        """
        Helper that returns an indent for printing
        """
        return "  " * self.depth

    def _log(self, level: int, msg, *args):
        self.log.log(level, f"{self.indent}{msg}", *args)

    def debug(self, msg, *args):
        """
        Write indented debug message to log
        """
        self._log(logging.DEBUG, msg, *args)

    def info(self, msg, *args):
        """
        Write indented info message to log
        """
        self._log(logging.INFO, msg, *args)

    def warning(self, msg, *args):
        """
        Write indented warning message to log
        """
        self._log(logging.WARNING, msg, *args)

    def error(self, msg, *args):
        """
        Write indented error message to log
        """
        self._log(logging.ERROR, msg, *args)

    def format_name(self, name: str) -> str:
        """
        Format a name using context variables
        """
        return name.format(**self.state)
