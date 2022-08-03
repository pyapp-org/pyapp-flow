from __future__ import annotations

import abc
import logging
from collections import deque
from typing import Dict, Any, Type, Union, Sequence, Optional

Branches = Dict[str, Sequence["Navigable"]]


class Navigable(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """
        Name of object
        """

    def branches(self) -> Optional[Branches]:
        """
        Branches from an object in the workflow node tree.
        """

    def __str__(self):
        return self.name


class State(Dict[str, Any]):
    """
    Wrapper around dict to support attribute accessors
    """

    def __getattr__(self, var: str) -> Any:
        try:
            return self[var]
        except KeyError:
            raise AttributeError(f"State has no attribute {var!r}") from None

    def __setattr__(self, var: str, value: Any):
        self[var] = value

    def __delattr__(self, var: str):
        try:
            del self[var]
        except KeyError:
            raise AttributeError(f"State has no attribute {var!r}") from None


class StateContext:
    """
    Base object that tracks nested state
    """

    __slots__ = ("state", "_state_vector")

    def __init__(self, state: Union[State, Dict[str, Any]]):
        self.state = State(state)
        self._state_vector = deque([self.state])

    def __enter__(self):
        self.push_state()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pop_state()

    def push_state(self):
        """
        Clone the current state so any modification doesn't affect the outer
        scope and append it to the state vector.
        """
        self.state = State(self.state)
        self._state_vector.append(self.state)

    def pop_state(self):
        """
        Pop the top state from the state vector.
        """
        self._state_vector.pop()
        self.state = self._state_vector[-1]

    @property
    def depth(self) -> int:
        """
        Current scope depth; or size of the current state vector
        """
        return len(self._state_vector)


class WorkflowContext(StateContext):
    """
    Current context of the workflow.

    This object can be used as a context object to apply state scoping.

    The current state can be modified via the ``state`` property, this is a
    ``dict`` of Key/Value pairs.

    :param logger: And optional logger; one will be created named `pyapp_flow`
        if not provided.
    :param variables: Initial state of variables.

    .. code-block:: python

        context = WorkflowContext(foo="123")

        with context:
            assert context.state["foo"] == "123"
            context.state["bar"] == "456"

        assert "bar" not in context.state

    """

    __slots__ = ("logger",)

    def __init__(self, logger: logging.Logger = None, **variables):
        super().__init__(variables)
        self.logger = logger or logging.getLogger("pyapp_flow")

    @property
    def indent(self) -> str:
        """
        Helper that returns an indent based on the scope depth for formatting
        log messages.
        """
        return "  " * self.depth

    def log(self, level: int, msg: str, *args, **kwargs):
        """
        Log a message to logger indented by the current scope depth.
        """
        self.logger.log(level, f"{self.indent}{msg}", *args, **kwargs)

    def debug(self, msg, *args):
        """
        Write a debug message to log
        """
        self.log(logging.DEBUG, msg, *args)

    def info(self, msg, *args):
        """
        Write a info message to log
        """
        self.log(logging.INFO, msg, *args)

    def warning(self, msg, *args):
        """
        Write a warning message to log
        """
        self.log(logging.WARNING, msg, *args)

    def error(self, msg, *args):
        """
        Write a error message to log
        """
        self.log(logging.ERROR, msg, *args)

    def exception(self, msg, *args):
        """
        Write a exception message to log
        """
        self.log(logging.ERROR, msg, *args, exc_info=True)

    def format(self, message: str) -> str:
        """
        Format a message using context variables.

        Return a formatted version of message, using substitutions context
        variables. The substitutions are identified by braces ('{' and '}').

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
        state = {var: (None, None) for var in variables}
        state.update(
            {var: (var_type, None) for var, var_type in typed_variables.items()}
        )
        super().__init__(state)
