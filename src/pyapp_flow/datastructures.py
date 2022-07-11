from __future__ import annotations

import logging
from collections import deque
from typing import Dict, Any, Type


class StateContext:
    """
    Base object that tracks nested state
    """

    __slots__ = ("state", "_state_vector")

    def __init__(self, state: Dict[str, Any]):
        self.state = state
        self._state_vector = deque([state])

    def __enter__(self):
        self.push_state()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pop_state()

    def push_state(self):
        """
        Clone the current state so any modification doesn't affect the outer scope
        """
        self.state = dict(self.state)
        self._state_vector.append(self.state)

    def pop_state(self):
        """
        Discard current state scope
        """
        self._state_vector.pop()
        self.state = self._state_vector[-1]

    @property
    def depth(self) -> int:
        """
        Current nesting level
        """
        return len(self._state_vector)


class WorkflowContext(StateContext):
    """
    Current context of the workflow
    """

    __slots__ = ("logger",)

    def __init__(self, logger: logging.Logger = None, **variables):
        super().__init__(variables)
        self.logger = logger or logging.getLogger("pyapp_flow")

    @property
    def indent(self) -> str:
        """
        Helper that returns an indent for printing
        """
        return "  " * self.depth

    def log(self, level: int, msg: str, *args, **kwargs):
        """
        Log a message
        """
        self.logger.log(level, f"{self.indent}{msg}", *args, **kwargs)

    def debug(self, msg, *args):
        """
        Write indented debug message to log
        """
        self.log(logging.DEBUG, msg, *args)

    def info(self, msg, *args):
        """
        Write indented info message to log
        """
        self.log(logging.INFO, msg, *args)

    def warning(self, msg, *args):
        """
        Write indented warning message to log
        """
        self.log(logging.WARNING, msg, *args)

    def error(self, msg, *args):
        """
        Write indented error message to log
        """
        self.log(logging.ERROR, msg, *args)

    def exception(self, msg, *args):
        """
        Write indented error message to log
        """
        self.log(logging.ERROR, msg, *args, exc_info=True)

    def format(self, message: str) -> str:
        """
        Format a message using context variables
        """
        try:
            return message.format(**self.state)
        except Exception as ex:
            self.exception("Exception formatting message %r: %s", message, ex)
            return message


class DescribeContext(StateContext):
    """
    Context used to describe/verify a workflow.
    """

    __slots__ = ()

    def __init__(self, *variables: str, **typed_variables: Type):
        state = {var: None for var in variables}
        state.update(typed_variables)
        super().__init__(state)
