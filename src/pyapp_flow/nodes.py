import logging
from typing import (
    Callable,
    Sequence,
    Union,
    Iterable,
    Type,
    Hashable,
    Optional,
    Any,
    Dict,
)
from typing_extensions import Self

from pyapp import feature_flags

from .datastructures import WorkflowContext, Navigable, Branches
from .errors import FatalError, WorkflowRuntimeError, SkipStep, StepFailedError
from .functions import extract_inputs, extract_outputs, call_nodes, var_list, call_node
from .helpers import change_log_level

Node = Callable[[WorkflowContext], Any]


class Step(Navigable):
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
        "_name",
        "ignore_exceptions",
        "context_var",
    )

    def __init__(
        self,
        func: Callable,
        name: str | None = None,
        output: str | Sequence[str] | None = None,
        ignore_exceptions: type[Exception] | Sequence[type[Exception]] | None = None,
    ):
        self.func = func
        self._name = name or func.__name__.replace("_", " ").title()
        self.ignore_exceptions = ignore_exceptions

        self.inputs, self.context_var = extract_inputs(func)
        self.outputs = extract_outputs(func, output)

    def __call__(self, context: WorkflowContext) -> Any:
        """Call the step function."""
        state = context.state

        # Prepare args from context
        kwargs = {name: state[name] for name in self.inputs if name in state}
        if self.context_var:
            kwargs[self.context_var] = context

        context.info("🔹Step `%s`", context.format(self.name))
        try:
            results = self.func(**kwargs)

        except SkipStep as ex:
            context.warning(" 🔃 Skipping step: %s", ex)

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
                for name, value in zip((output[0] for output in self.outputs), values):
                    context.state[name] = value

            return results

    @property
    def name(self) -> str:
        """Name of the node."""
        return self._name


def step(
    func=None,
    *,
    name: str | None = None,
    output: str | Sequence[str] | None = None,
    ignore_exceptions: type[Exception] | Sequence[type[Exception]] | None = None,
) -> Callable[[Callable], Step] | Step:
    """Decorate a method turning it into a step"""

    def decorator(func_) -> Step:
        return Step(func_, name, output, ignore_exceptions)

    return decorator(func) if func else decorator


def inline(
    func: Callable,
    name: str | None = None,
    ignore_exceptions: type[Exception] | Sequence[type[Exception]] | None = None,
) -> Step:
    """Define an inline step.

    An inline step is a step that is executed immediately and not added to the
    workflow. This is useful for defining a step that is only used once.

    :param func: Callable function or lambda
    :param name: Optional name of the step (defaults to the name of the function)
    :param ignore_exceptions: Optional exception type or sequence of exception
    """

    return Step(func, name, ignore_exceptions=ignore_exceptions)


class Group(Navigable):
    """Group of nodes.

    Useful for creating composable blocks, that don't require variable scope."""

    __slots__ = ("_nodes", "_finally_nodes", "_log_level")

    def __init__(self, *nodes_: Node, log_level: Union[str, int, None] = None):
        """Initialise nodes."""
        self._nodes = list(nodes_)
        self._finally_nodes = None
        self._log_level = log_level

    def __call__(self, context: WorkflowContext):
        self._execute(context)

    @property
    def name(self) -> str:
        return f"🔽 {type(self).__name__}"

    def and_finally(self, *nodes) -> Self:
        """Nodes that are always called even if an exception is raised.

        This is analogous to a ``finally`` block."""
        self._finally_nodes = nodes
        return self

    def branches(self) -> Branches | None:
        """Return branches for this node."""
        if self._finally_nodes:
            return {"": self._nodes + self._finally_nodes}
        else:
            return {"": self._nodes}

    def _execute(self, context: WorkflowContext):
        with change_log_level(self._log_level):
            try:
                call_nodes(context, self._nodes)
            finally:
                if self._finally_nodes:
                    call_nodes(context, self._finally_nodes)


class SetVar(Navigable):
    """Set context variable to specified values

    :param values: Key/Value pairs or Key/Callable pairs to be applied to the
                   context.

    .. code-block:: python

        SetVar(
            title="Hyperion",
            published=datetime.date(1996, 11, 1),
            updated=lambda context: datetime.datetime.now()
        )

    """

    __slots__ = ("values",)

    def __init__(
        self,
        **values: Union[Any, Callable[[WorkflowContext], Any]],
    ):
        self.values = values

    def __call__(self, context: WorkflowContext):
        """Call object implementation."""
        context.info("📝 %s", self)
        values = (
            (key, value(context) if callable(value) else value)
            for key, value in self.values.items()
        )
        context.state.update(values)

    @property
    def name(self):
        """Name of the node."""
        return f"Set value(s) for {', '.join(self.values)}"


class SetGlobalVar(Navigable):
    """Set global context variable to specified values

    :param values: Key/Value pairs or Key/Callable pairs to be applied to the
                   context.

    .. code-block:: python

        SetGlobalVar(
            title="Hyperion",
            published=datetime.date(1996, 11, 1),
            updated=lambda context: datetime.datetime.now()
        )

    """

    __slots__ = ("values",)

    def __init__(
        self,
        **values: Any | Node,
    ):
        self.values = values

    def __call__(self, context: WorkflowContext):
        """Call object implementation."""
        context.info("📝 %s", self)
        values = [
            (key, value(context) if callable(value) else value)
            for key, value in self.values.items()
        ]

        # Set at all levels in the state vector
        for state in context._state_vector:
            state.update(values)

    @property
    def name(self):
        """Name of the node."""
        return f"Set global value(s) for {', '.join(self.values)}"


class DefaultVar(Navigable):
    """Set context variable to specified values if not already set.

    :param values: Key/Value pairs or Key/Vallable pairs to be applied to the context
                   if key is not already defined.

    .. code-block:: python

        DefaultVar(
            title="Hyperion",
            published=datetime.date(1996, 11, 1),
            updated=inline(lambda: datetime.datetime.now())
        )
    """

    __slots__ = ("values",)

    def __init__(
        self,
        **values: Any | Callable[[WorkflowContext], Any],
    ):
        self.values = values

    def __call__(self, context: WorkflowContext):
        """Call object implementation."""
        context.info("📝 %s", self)
        values = [
            (key, value(context) if callable(value) else value)
            for key, value in self.values.items()
            if key not in context.state
        ]
        context.state.update(values)

    @property
    def name(self):
        """Name of the node"""
        return f"Default value(s) for {', '.join(self.values)}"


class Append(Navigable):
    """Append a message to a list.

    The message is formatted using :func:`pyapp_flow.WorkflowContext.format`
    before being appended the ``target_var``.

    If the target_var does not exist a new list will be created.

    :param target_var: Name of the context variable with the list
    :param message: The message to be formatted and added to the list.

    .. code-block:: python

        Append("messages", "Unable to complete book")

    """

    __slots__ = ("target_var", "message")

    def __init__(self, target_var: str, message: str):
        self.target_var = target_var
        self.message = message

    def __call__(self, context: WorkflowContext):
        """Call object implementation."""
        message = context.format(self.message)
        try:
            context.state[self.target_var].append(message)
        except KeyError:
            context.state[self.target_var] = [message]

    @property
    def name(self):
        """Name of the node."""
        return f"Append {self.message!r} to {self.target_var}"


class CaptureErrors(Navigable):
    """Capture and store any exceptions raised by node(s).

    Errors are captured into the specified variable.

    If the target_var does not exist a new list will be created.

    :param target_var: Name of the context variable with the list
    :param try_all: Call every node even if a previous node raised an exception.

    .. code-block:: python

        (
            CaptureErrors("errors", try_all=True)
            .nodes(
                ...  # Node(s) to try
            )
        )

    """

    __slots__ = ("target_var", "_nodes", "try_all")

    def __init__(
        self,
        target_var: str,
        try_all: bool = True,
        *,
        except_types: Union[type, Sequence[type]] = None,
    ):
        self.target_var = target_var
        self.except_types = except_types
        self._nodes = []
        self.try_all = try_all

    def __call__(self, context: WorkflowContext):
        """Call object implementation."""
        context.info("🥅 %s", self)
        except_types = self.except_types

        try:
            var = context.state[self.target_var]
        except KeyError:
            var = context.state[self.target_var] = []

        with context:
            for node in self._nodes:
                try:
                    call_node(context, node)
                except Exception as ex:
                    if except_types and not isinstance(ex, except_types):
                        raise
                    var.append(ex)
                    if not self.try_all:
                        break

    @property
    def name(self):
        """Name of the node."""
        return f"Capture errors into `{self.target_var}`"

    def branches(self) -> Optional[Branches]:
        return {"": tuple(self._nodes)}

    def nodes(self, *nodes: Node) -> Self:
        """Add additional nodes."""
        self._nodes.extend(nodes)
        return self


class Conditional(Navigable):
    """Branch a workflow based on a condition, analogous with an if statement.

    :param condition: A condition can be either a context variable that can be
        interpreted as a ``bool`` (using Python rules) or a callable that
        accepts a :class:`pyapp_flow.WorkflowContext` and returns a ``bool``.

    .. code-block:: python

        # With context variable
        (
            If("is_successful")
            .true(LogMessage("Process successful :)"))
            .false(LogMessage("Process failed :("))
        )

        # With Lambda
        (
            If(lambda context: len(context.state.errors) == 0)
            .true(LogMessage("Process successful :)"))
            .false(LogMessage("Process failed :("))
        )

    """

    __slots__ = ("condition", "_true_nodes", "_false_nodes")

    def __init__(self, condition: Union[str, Callable[[WorkflowContext], bool]]):
        if isinstance(condition, str):
            self.condition = lambda context: bool(context.state.get(condition))
        elif callable(condition):
            self.condition = condition
        else:
            raise TypeError("condition not context variable name or callable")

        self._true_nodes = None
        self._false_nodes = None

    def __call__(self, context: WorkflowContext):
        """Call object implementation."""
        condition = self.condition(context)
        context.info("🔀 Condition is %s", bool(condition))

        nodes = self._true_nodes if condition else self._false_nodes
        if nodes:
            context.set_trace_args({"condition": condition})
            with context.block_indent():
                call_nodes(context, nodes)

    @property
    def name(self):
        """Name of the node."""
        return "Conditional branch"

    def branches(self) -> Optional[Branches]:
        return {"true": self._true_nodes, "false": self._false_nodes}

    def true(self, *nodes: Node) -> Self:
        """Nodes to use for the true branch."""
        self._true_nodes = nodes
        return self

    def false(self, *nodes: Node) -> Self:
        """Nodes to use for the false branch."""
        self._false_nodes = nodes
        return self


If = Conditional


class FeatureEnabled(Navigable):
    """Conditional that checks if a feature-flag is enabled, analogous with an
    if statement.

    This feature utilises PyApp feature-flags see:
    https://docs.pyapp.info/en/latest/reference/feature-flags.html

    :param flag: Name of flag
    :param default: Default flag state

    .. code-block:: python

        (
            FeatureEnabled("MY-FEATURE")
            .true(LogMessage("Feature enabled :)"))
            .false(LogMessage("Feature disabled :("))
        )

    """

    __slots__ = ("_flag", "_default", "_true_nodes", "_false_nodes")

    def __init__(self, flag: str, *, default: bool = False):
        self._flag = flag
        self._default = default
        self._true_nodes = None
        self._false_nodes = None

    def __call__(self, context: WorkflowContext):
        """Call object implementation."""
        condition = feature_flags.get(self._flag, default=self._default)
        context.info("🚩 %s is %s", self._flag, "enabled" if condition else "disabled")

        nodes = self._true_nodes if condition else self._false_nodes
        if nodes:
            context.set_trace_args({"condition": condition})
            call_nodes(context, nodes)

    @property
    def name(self) -> str:
        """Name of the node."""
        return f"Feature flag: {self._flag}"

    def branches(self) -> Optional[Branches]:
        return {"true": self._true_nodes, "false": self._false_nodes}

    def true(self, *nodes: Node) -> Self:
        """Nodes to use for the true branch."""
        self._true_nodes = nodes
        return self

    def false(self, *nodes: Node) -> Self:
        """Nodes to use for the false branch."""
        self._false_nodes = nodes
        return self


class Switch(Navigable):
    """Branch a workflow into one of multiple subprocesses, analogous with a
    switch statement found in many languages or with Python a dict lookup with
    a default fallback.

    :param condition: A condition can be either a context variable that that
        provides a hashable object or a callable that accepts a
        :class:`pyapp_flow.WorkflowContext` and returns a hashable object.

    .. code-block:: python

        (
            Switch("status")
            .case("Active", ...)  # Active branch node(s)
            .case("Starting", ...)  # Starting branch node(s)
            .default(...)  # Optional default fallback branch node(s)
        )

    """

    __slots__ = ("condition", "_options", "_default")

    def __init__(self, condition: Union[str, Callable[[WorkflowContext], Hashable]]):
        if isinstance(condition, str):
            self.condition = lambda context: context.state.get(condition)
        elif callable(condition):
            self.condition = condition
        else:
            raise TypeError("condition not context variable name or callable")

        self._options = {}
        self._default = None

    def __call__(self, context: WorkflowContext):
        """Call object implementation."""
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

        context.set_trace_args({"switch": value})
        call_nodes(context, branch)

    @property
    def name(self):
        """Name of the node."""
        return f"Switch into {', '.join(self._options)}"

    def branches(self) -> Optional[Branches]:
        branches = {str(case): nodes for case, nodes in self._options.items()}
        if self._default:
            branches["*DEFAULT*"] = self._default
        return branches

    def case(self, key: Hashable, *nodes: Node) -> Self:
        """Key used to match branch and the nodes that make up the branch."""
        self._options[key] = nodes
        return self

    def default(self, *nodes: Node) -> Self:
        """If a case key is not matched use these nodes as the default branch."""
        self._default = nodes
        return self


class LogMessage(Navigable):
    """Print a message to log with optional level.

    The message is formatted using :func:`pyapp_flow.WorkflowContext.format`
    before being appended to the log.

    :param message: The message to be formatted and added to the list.
    :param level: Log level to use for log message; a constant from the logging
        module.

    .. code-block:: python

        LogMessage("Failed to complete task", level=logging.ERROR)

    """

    __slots__ = ("message", "level")

    @classmethod
    def debug(cls, message: str) -> "LogMessage":
        """Create a log message with level DEBUG."""
        return cls(message, level=logging.DEBUG)

    @classmethod
    def info(cls, message: str) -> "LogMessage":
        """Create a log message with level INFO."""
        return cls(message, level=logging.INFO)

    @classmethod
    def warning(cls, message: str) -> "LogMessage":
        """Create a log message with level WARNING."""
        return cls(message, level=logging.WARNING)

    @classmethod
    def error(cls, message: str) -> "LogMessage":
        """Create a log message with level ERROR."""
        return cls(message, level=logging.ERROR)

    def __init__(self, message: str, *, level: int = logging.INFO):
        self.message = message
        self.level = level

    def __call__(self, context: WorkflowContext):
        """Call object implementation."""
        message = context.format(self.message)
        context.log(self.level, message)

    @property
    def name(self):
        """Name of the node."""
        return f"Log Message {self.message!r}"


class ForEach(Navigable):
    """For each loop to iterate through a set of values.

    Call a set of nodes on each value; analogous with a for loop this node
    will iterate through a sequence and call each of the child nodes.

    All nodes within a for-each loop are in a nested context scope.

    Values can be un-packed into multiple context variables using Python
    iterable unpacking rules.

    :param target_vars: Singular or multiple variables to unpack value into.
        This value can be either a single string, a comma separated list of
        strings or a sequence of strings.
    :param in_var: Context variable containing a sequence of values to be
        iterated over.

    .. code-block:: python

        # With a single target variable
        (
            ForEach("message", in_var="messages")
            .loop(log_message("- {message}"))
        )

        # With multiple target variables
        (
            ForEach("name, age", in_var="students")
            .loop(log_message("- {name} is {age} years old."))
        )

    """

    __slots__ = ("target_vars", "in_var", "_nodes", "_loop_label", "_update_context")

    def __init__(
        self,
        target_vars: Union[str, Sequence[str]],
        in_var: str,
        *,
        loop_label: str = None,
    ):
        self.target_vars = target_vars = var_list(target_vars)
        self.in_var = in_var
        self._nodes = []
        self._loop_label = loop_label or f"Next {self.target_vars_name}"

        if len(target_vars) == 1:
            self._context_update = self._single_value(target_vars[0])
        else:
            self._context_update = self._multiple_value(target_vars)

    def __call__(self, context: WorkflowContext):
        """Call object implementation."""
        context.info("🔁 %s", self)
        try:
            iterable = context.state[self.in_var]
        except KeyError:
            raise WorkflowRuntimeError(f"Variable {self.in_var} not found in context")

        if not isinstance(iterable, Iterable):
            raise WorkflowRuntimeError(f"Variable {self.in_var} is not iterable")

        with context.block_indent():
            for value in iterable:
                pairs = self._context_update(value)
                context.set_trace_args(pairs)
                context.info("🔂 %s", self._loop_label)
                with context:
                    context.state.update(pairs)
                    call_nodes(context, self._nodes)

    @property
    def target_vars_name(self):
        """Display value for target vars."""
        target_vars = ", ".join(f"`{var}`" for var in self.target_vars)
        return target_vars if len(self.target_vars) == 1 else f"({target_vars})"

    @property
    def name(self):
        """Name of the node."""
        return f"For {self.target_vars_name} in `{self.in_var}`"

    def branches(self) -> Optional[Branches]:
        return {"loop": self._nodes}

    def loop(self, *nodes: Node) -> Self:
        """Nodes to call on each iteration of the foreach block."""
        self._nodes = nodes
        return self

    @staticmethod
    def _single_value(target_var: str):
        """Handle single value for target."""

        def _values(value):
            return {target_var: value}

        return _values

    def _multiple_value(self, target_vars: Sequence[str]):
        """Handle multiple value for target."""

        def _values(values):
            try:
                return dict(zip(target_vars, values))
            except (TypeError, ValueError):
                raise WorkflowRuntimeError(
                    f"Value {values} from {self.in_var} is not iterable"
                )

        return _values


class TryExcept(Navigable):
    """Try a set of nodes and catch any exceptions.

    .. code-block:: python

        (
            TryExcept(
                resolve_state_a,
                resolve_state_b,
            )
            .except_on(RuntimeError, fallback_state)
        )
    """

    __slots__ = ("_nodes", "_exceptions")

    def __init__(self, *nodes: Node):
        self._nodes = nodes
        self._exceptions: Dict[Type[Exception], Sequence[Node]] = {}
        self._finally = None

    def __call__(self, context: WorkflowContext):
        """Call object implementation."""
        context.info("🎌 %s", self)
        with context.block_indent():
            try:
                call_nodes(context, self._nodes)

            except tuple(self._exceptions.keys()) as exception:
                context.info("🚨 Caught %s", type(exception).__name__)
                context.state.exception = exception

                # Call first matching set of nodes
                for exception_type, nodes in self._exceptions.items():
                    if isinstance(exception, exception_type):
                        call_nodes(context, self._exceptions[exception_type])
                        break

    @property
    def name(self) -> str:
        """Name of the node."""
        return "Try/Except"

    def branches(self) -> Optional[Branches]:
        return {"": self._nodes}

    def except_on(self, exception: Type[Exception], *nodes: Node) -> Self:
        """Nodes to call if the exception is raised."""
        self._exceptions[exception] = nodes
        return self


class TryUntil(Navigable):
    """Try a set of nodes until one of them does not raise an exception.

    The default behaviour is to catch a :class:`StepFailedError` exception.

    :param except_types: Exception type(s) to catch; defaults to :class:`StepFailedError`.

    .. code-block:: python

        (
            TryUntil()
            .nodes(
                resolve_state_a,
                resolve_state_b,
            )
            .default(
                fallback_state,
            )
        )
    """

    __slots__ = ("except_types", "_nodes", "_default")

    def __init__(
        self,
        except_types: Union[
            Type[Exception], Sequence[Type[Exception]]
        ] = StepFailedError,
    ):
        self.except_types = except_types
        self._nodes = []
        self._default = None

    def __call__(self, context: WorkflowContext):
        """Call object implementation."""
        context.info("🔁 %s", self)

        for node in self._nodes:
            try:
                call_node(context, node)
            except self.except_types:
                continue
            else:
                break
        else:
            if self._default:
                call_node(context, self._default)

    @property
    def name(self) -> str:
        """Name of the node."""
        return f"Try until a node does not raise {self.except_types}"

    def branches(self) -> Optional[Branches]:
        return {"": self._nodes}

    def nodes(self, *nodes: Node) -> Self:
        """Nodes to try."""
        self._nodes = nodes
        return self

    def default(self, node: Node) -> Self:
        """Nodes to call if all nodes raise an exception."""
        self._default = node
        return self
