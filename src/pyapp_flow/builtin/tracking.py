"""Useful objects for tracking."""

from typing_extensions import Self

from ..datastructures import WorkflowContext
from ..nodes import Step, step


class Counter:
    """Integer counter that will survive scope changes.

    Counter provides common integer methods.
    """

    __slots__ = ("_value",)

    def __init__(self, initial_value: int = 0):
        """Initialize counter."""
        self._value = initial_value

    def __add__(self, other: int) -> Self:
        """Add to the counter."""
        self._value += other
        return self

    def __sub__(self, other: int) -> Self:
        """Subtract from the counter."""
        self._value -= other
        return self

    def __radd__(self, other: int) -> int:
        """Reverse add."""
        return other + self._value

    def __rsub__(self, other: int) -> int:
        """Reverse subtract."""
        return other - self._value

    def __rmul__(self, other: int) -> int:
        """Reverse multiplication."""
        return other * self._value

    def __rtruediv__(self, other: int) -> int:
        """Reverse division.

        Note always integer division; use Counter.value to perform division to
        get a floating point result.
        """
        return other // self._value

    __rfloordiv__ = __rtruediv__

    def __str__(self):
        """Return string representation."""
        return str(self._value)

    def __format__(self, format_spec: str) -> str:
        """Format value to a string."""
        return format(self._value, format_spec)

    @property
    def value(self) -> int:
        """Return raw integer value."""
        return self._value


def increment(target_var: str, *, amount: int = 1) -> Step:
    """Increment a counter.

    :param target_var: Target variable containing counter instance.
    :param amount: Amount to increment; default is `1`

    .. code-block:: python

        increment("counter")

    """

    @step(name=f"Increment {target_var} by {amount}")
    def _step(context: WorkflowContext):
        context.state[target_var] += amount

    return _step


def decrement(target_var: str, *, amount: int = 1) -> Step:
    """Decrement a counter.

    :param target_var: Target variable containing counter instance.
    :param amount: Amount to decrement; default is `1`

    .. code-block:: python

        decrement("counter", amount=2)

    """

    @step(name=f"Decrement {target_var} by {amount}")
    def _step(context: WorkflowContext):
        context.state[target_var] -= amount

    return _step
