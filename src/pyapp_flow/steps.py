import logging
from typing import Callable, Sequence, Union, Iterable, Type

from .datastructures import WorkflowContext
from .functions import extract_inputs, extract_outputs
from .exceptions import FatalError, WorkflowRuntimeError


class Step:
    """
    Wrapper around a function that defines a workflow step

    Typically, this would be applied using the ``step`` decorator eg:

    >>> @step(outputs=(("var_b", str),))
    >>> def my_step(*, var_a: str):
    >>>     return var_a.replace("a", "b")

    The behaviour of the decorator is to define ``var_a`` as an input of type
    string and expect a single output of type ``str`` that will be assigned to
    the ``var_b`` variable. All variables are read/written into the
    ``WorkflowContext.state``.

    To get access to the workflow context object include a variable of type
    ``WorkflowContext`` eg:

    >>> @step
    >>> def my_step(context: WorkflowContext):
    >>>     pass

    :param func: Callable function or lambda
    :param name: Optional name of the step (defaults to the name of the function)
    :param outputs:: A sequence of ``str`` or ``Tuple[str, type]`` defining the
        output(s) of the step function.
    """

    __slots__ = (
        "func",
        "inputs",
        "outputs",
        "name",
        "ignore_exceptions",
        "context_var",
    )

    def __init__(
        self,
        func: Callable,
        name: str = None,
        output: Union[str, Sequence[str]] = None,
        ignore_exceptions: Union[Type[Exception], Sequence[Type[Exception]]] = None,
    ):
        self.func = func
        self.name = name or func.__name__.replace("_", " ")
        self.ignore_exceptions = ignore_exceptions

        self.inputs, self.context_var = extract_inputs(func)
        self.outputs = extract_outputs(func, output)

    def __call__(self, context: WorkflowContext):
        state = context.state

        # Prepare args from context
        kwargs = {name: state[name] for name in self.inputs if name in state}
        if self.context_var:
            kwargs[self.context_var] = context

        context.info("🔹Step `%s`", context.format(self.name))
        try:
            results = self.func(**kwargs)

        except FatalError as ex:
            context.error("  ⛔ Fatal error raised: %s", ex)
            raise

        except Exception as ex:
            if self.ignore_exceptions and isinstance(ex, self.ignore_exceptions):
                context.warning("  ❌ Ignoring exception: %s", ex)
            else:
                context.error("  ⛔ Exception raised: %s", ex)
                raise

        else:
            if self.outputs:
                # Helper so a simple return can be used for a single result
                values = (results,) if len(self.outputs) == 1 else results
                for name, value in zip([name for name, _ in self.outputs], values):
                    context.state[name] = value

            return results

    def __str__(self):
        return self.name


def step(
    func=None,
    *,
    name: str = None,
    output: Sequence[str] = None,
    ignore_exceptions: Union[Type[Exception], Sequence[Type[Exception]]] = None,
) -> Step:
    """
    Decorate a method turning it into a step
    """

    def decorator(func_):
        return Step(func_, name, output, ignore_exceptions)

    return decorator(func) if func else decorator


class SetVar:
    """
    Set context variable to specified values
    """

    __slots__ = ("values",)

    def __init__(self, **values):
        self.values = values

    def __call__(self, context: WorkflowContext):
        context.info("📝 %s", self)
        context.state.update(self.values)

    def __str__(self):
        return f"Set value(s) for {', '.join(self.values)}"


set_var = SetVar


class ForEach:
    """
    Nested for each loop
    """

    __slots__ = ("target_vars", "in_var", "_nodes", "_parse_values")

    def __init__(
        self, target_vars: Union[str, Sequence[str]], in_var: str, *nodes: Callable
    ):
        if isinstance(target_vars, str):
            self.target_vars = (target_vars,)
            self._parse_values = self._single_value(target_vars)
        else:
            self.target_vars = target_vars
            self._parse_values = self._multiple_value(target_vars)
        self.in_var = in_var
        self._nodes = nodes

    def __call__(self, context: WorkflowContext):
        context.info("🔁 %s", self)
        try:
            iterable = context.state[self.in_var]
        except KeyError:
            raise WorkflowRuntimeError(f"Variable {self.in_var} not found in context")

        if not isinstance(iterable, Iterable):
            raise WorkflowRuntimeError(f"Variable {self.in_var} is not iterable")

        for value in iterable:
            values = self._parse_values(value)
            with context:
                context.state.update(values)
                for node in self._nodes:
                    node(context)

    def __str__(self):
        return f"For ({', '.join(self.target_vars)}) in `{self.in_var}`"

    def _single_value(self, target_var: str):
        """
        Handle single value for target
        """

        def _values(values):
            return ((target_var, values),)

        return _values

    def _multiple_value(self, target_vars: Sequence[str]):
        """
        Handle multiple value for target
        """

        def _values(values):
            try:
                return zip(target_vars, values)
            except (TypeError, ValueError):
                raise WorkflowRuntimeError(
                    f"Value {values} from {self.in_var} is not iterable"
                )

        return _values


for_each = ForEach


class CaptureErrors:
    """
    Capture any errors generated by steps
    """

    __slots__ = ("target_var", "_nodes", "try_all")

    def __init__(self, target_var: str, *nodes: Callable, try_all: bool = True):
        self.target_var = target_var
        self._nodes = nodes
        self.try_all = try_all

    def __call__(self, context: WorkflowContext):
        context.info("🥅 %s", self)

        try:
            var = context.state[self.target_var]
        except KeyError:
            var = context.state[self.target_var] = []

        with context:
            for node in self._nodes:
                try:
                    node(context)
                except Exception as ex:
                    var.append(ex)
                    if not self.try_all:
                        break

    def __str__(self):
        return f"Capture errors into `{self.target_var}`"


capture = CaptureErrors


class Conditional:
    """
    Branch a workflow based on a condition.

    A condition can be either a boolean based context variable or a callable that accepts a workflow context.
    """

    __slots__ = ("condition", "_true_nodes", "_false_nodes")

    def __init__(
        self,
        condition: Union[str, Callable[[WorkflowContext], bool]],
        *nodes: Callable,
    ):
        if isinstance(condition, str):
            self.condition = lambda context: bool(context.state.get(condition))
        elif callable(condition):
            self.condition = condition
        else:
            raise TypeError("condition not context variable name or callable")

        self._true_nodes = nodes
        self._false_nodes = None

    def __call__(self, context: WorkflowContext):
        condition = self.condition(context)
        context.info("🔀 Condition is %s", condition)

        if nodes := self._true_nodes if condition else self._false_nodes:
            for node in nodes:
                node(context)

    def true(self, *nodes: Callable) -> "Conditional":
        """
        If the condition is true execute these nodes
        """
        self._true_nodes = nodes
        return self

    def false(self, *nodes: Callable) -> "Conditional":
        """
        If the condition is false execute these nodes
        """
        self._false_nodes = nodes
        return self


conditional = Conditional


class LogMessage:
    """
    Print a message to log
    """

    __slots__ = ("message", "level")

    def __init__(self, message: str, *, level: int = logging.INFO):
        self.message = message
        self.level = level

    def __call__(self, context: WorkflowContext):
        message = context.format(self.message)
        context._log(self.level, message)


log_message = LogMessage


class Append:
    """
    Append a value to a list
    """

    __slots__ = ("target_var", "message")

    def __init__(self, target_var: str, message: str):
        self.target_var = target_var
        self.message = message

    def __call__(self, context: WorkflowContext):
        message = context.format(self.message)
        try:
            context.state[self.target_var].append(message)
        except KeyError:
            context.state[self.target_var] = [message]


append = Append
