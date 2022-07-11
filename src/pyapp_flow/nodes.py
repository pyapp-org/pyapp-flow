import logging
from typing import (
    Callable,
    Sequence,
    Union,
    Iterable,
    Type,
    Hashable,
    Mapping,
    List,
)

from .datastructures import WorkflowContext, DescribeContext
from .functions import extract_inputs, extract_outputs, call_nodes
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
    :param output: A sequence of ``str`` or ``Tuple[str, type]`` defining the
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

    def describe(self, context: DescribeContext):
        """
        Describe this node
        """
        context.requires(self, self.inputs)
        context.outputs(dict(self.outputs))
        yield self, None


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

    def describe(self, context: DescribeContext):
        """
        Describe this node
        """
        context.outputs(self.values)
        yield self, None


set_var = SetVar


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

    def __str__(self):
        return f"Append {self.message} to {self.target_var}"

    def describe(self, context: DescribeContext):
        """
        Describe this node
        """
        context.outputs({self.target_var: List[str]})
        yield self, None


append = Append


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

    def describe(self, context: DescribeContext):
        """
        Describe this node
        """
        context.outputs({self.target_var: List[Exception]})
        yield self, self._nodes
        for node in self._nodes:
            yield from node.describe(context)


capture = CaptureErrors


class Conditional:
    """
    Branch a workflow based on a condition.

    A condition can be either a context variable that can be evaluated as a
    boolean (using Python rules) or a callable that accepts a workflow context.
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
            call_nodes(context, nodes)

    def __str__(self):
        return f"Conditional branch"

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

    def describe(self, context: DescribeContext):
        """
        Describe this node
        """
        yield self, {True: self._true_nodes, False: self._false_nodes}
        for node in self._true_nodes:
            yield from node.describe(context)
        for node in self._false_nodes:
            yield from node.describe(context)


conditional = If = Conditional


class Switch:
    """
    Branch a workflow into one of multiple subprocesses

    A condition can be either a context variable that provides a hashable object
    or a callable that accepts a workflow context and returns a hashable object.
    """

    __slots__ = ("condition", "_options", "_default")

    def __init__(
        self,
        condition: Union[str, Callable[[WorkflowContext], Hashable]],
        options: Mapping[Hashable, Sequence[Callable]] = None,
        *,
        default: Sequence[Callable] = None,
    ):
        if isinstance(condition, str):
            self.condition = lambda context: context.state.get(condition)
        elif callable(condition):
            self.condition = condition
        else:
            raise TypeError("condition not context variable name or callable")

        self._options = options or {}
        self._default = default

    def __call__(self, context: WorkflowContext):
        value = self.condition(context)
        branch = self._options.get(value, None)
        if branch is None:
            if self._default:
                context.info("🔀 Switch %s -> default", value)
                branch = self._default
            else:
                context.info("🔀 Switch %s not matched", value)
                return
        else:
            context.info("🔀 Switch %s matched branch", value)

        call_nodes(context, branch)

    def __str__(self):
        return f"Switch into {', '.join(self._options)}"

    def case(self, key: Hashable, *nodes: Callable) -> "Switch":
        """
        Key to match in_var and execute this branch of nodes
        """
        self._options[key] = nodes
        return self

    def default(self, *nodes: Callable) -> "Switch":
        """
        Default to match if no option matches
        """
        self._default = nodes
        return self

    def describe(self, context: DescribeContext):
        """
        Describe this node
        """
        branches = dict(self._options)
        if self._default:
            branches[None] = self._default
        yield self, branches

        for nodes in self._options.values():
            for node in nodes:
                yield from node.describe(context)
        if self._default:
            for node in self._default:
                yield from node.describe(context)


switch = Switch


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
        context.log(self.level, message)

    def __str__(self):
        return f"Log Message {self.message}"

    def describe(self, context: DescribeContext):
        """
        Describe this node
        """
        yield self, None


log_message = LogMessage


class ForEach:
    """
    Nested for each loop
    """

    __slots__ = ("target_vars", "in_var", "_nodes", "_update_context")

    def __init__(
        self, target_vars: Union[str, Sequence[str]], in_var: str, *nodes: Callable
    ):
        if isinstance(target_vars, str):
            target_vars = [var.strip() for var in target_vars.split(",")]
        self.target_vars = target_vars
        self.in_var = in_var
        self._nodes = list(nodes)

        if len(target_vars) == 1:
            self._update_context = self._single_value(target_vars[0])
        else:
            self._update_context = self._multiple_value(target_vars)

    def __call__(self, context: WorkflowContext):
        context.info("🔁 %s", self)
        try:
            iterable = context.state[self.in_var]
        except KeyError:
            raise WorkflowRuntimeError(f"Variable {self.in_var} not found in context")

        if not isinstance(iterable, Iterable):
            raise WorkflowRuntimeError(f"Variable {self.in_var} is not iterable")

        for value in iterable:
            with context:
                self._update_context(value, context)
                call_nodes(context, self._nodes)

    def __str__(self):
        return f"For ({', '.join(self.target_vars)}) in `{self.in_var}`"

    def loop(self, *nodes: Callable) -> "ForEach":
        """
        Add nodes to call as part of the foreach block
        """
        self._nodes.extend(nodes)
        return self

    @staticmethod
    def _single_value(target_var: str):
        """
        Handle single value for target
        """

        def _values(value, context: WorkflowContext):
            context.state[target_var] = value

        return _values

    def _multiple_value(self, target_vars: Sequence[str]):
        """
        Handle multiple value for target
        """

        def _values(values, context: WorkflowContext):
            try:
                pairs = zip(target_vars, values)
            except (TypeError, ValueError):
                raise WorkflowRuntimeError(
                    f"Value {values} from {self.in_var} is not iterable"
                )

            context.state.update(pairs)

        return _values

    def describe(self, context: DescribeContext):
        """
        Describe this node
        """
        context.requires(self, (self.in_var,))
        context.outputs(self.target_vars)
        yield self, self._nodes
        for node in self._nodes:
            yield from node.describe(context)


for_each = ForEach
