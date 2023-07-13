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
)

from .datastructures import WorkflowContext, Navigable, Branches
from .functions import extract_inputs, extract_outputs, call_nodes, var_list, call_node
from .errors import FatalError, WorkflowRuntimeError, SkipStep, StepFailedError

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
        name: str = None,
        output: Union[str, Sequence[str]] = None,
        ignore_exceptions: Union[Type[Exception], Sequence[Type[Exception]]] = None,
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
    name: str = None,
    output: Union[str, Sequence[str]] = None,
    ignore_exceptions: Union[Type[Exception], Sequence[Type[Exception]]] = None,
) -> Union[Callable[[Callable], Step], Step]:
    """Decorate a method turning it into a step"""

    def decorator(func_) -> Step:
        return Step(func_, name, output, ignore_exceptions)

    return decorator(func) if func else decorator


def inline(
    func: Callable,
    name: str = None,
    ignore_exceptions: Union[Type[Exception], Sequence[Type[Exception]]] = None,
) -> Step:
    """Define an inline step.

    An inline step is a step that is executed immediately and not added to the
    workflow. This is useful for defining a step that is only used once.

    :param func: Callable function or lambda
    :param name: Optional name of the step (defaults to the name of the function)
    :param ignore_exceptions: Optional exception type or sequence of exception
    """

    return Step(func, name, ignore_exceptions=ignore_exceptions)


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

    def nodes(self, *nodes: Node):
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
        context.info("🔀 Condition is %s", condition)

        nodes = self._true_nodes if condition else self._false_nodes
        if nodes:
            context.set_trace_args({"condition": condition})
            call_nodes(context, nodes)

    @property
    def name(self):
        """Name of the node."""
        return f"Conditional branch"

    def branches(self) -> Optional[Branches]:
        return {"true": self._true_nodes, "false": self._false_nodes}

    def true(self, *nodes: Node) -> "Conditional":
        """Nodes to use for the true branch."""
        self._true_nodes = nodes
        return self

    def false(self, *nodes: Node) -> "Conditional":
        """Nodes to use for the false branch."""
        self._false_nodes = nodes
        return self


If = Conditional


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

    def case(self, key: Hashable, *nodes: Node) -> "Switch":
        """Key used to match branch and the nodes that make up the branch."""
        self._options[key] = nodes
        return self

    def default(self, *nodes: Node) -> "Switch":
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

    __slots__ = ("target_vars", "in_var", "_nodes", "_update_context")

    def __init__(self, target_vars: Union[str, Sequence[str]], in_var: str):
        self.target_vars = target_vars = var_list(target_vars)
        self.in_var = in_var
        self._nodes = []

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

        for value in iterable:
            pairs = self._context_update(value)
            context.set_trace_args(pairs)
            with context:
                context.state.update(pairs)
                call_nodes(context, self._nodes)

    @property
    def name(self):
        """Name of the node."""
        target_vars = ", ".join(f"`{var}`" for var in self.target_vars)
        return f"For ({target_vars}) in `{self.in_var}`"

    def branches(self) -> Optional[Branches]:
        return {"loop": self._nodes}

    def loop(self, *nodes: Node) -> "ForEach":
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
                return
        else:
            if self._default:
                call_node(context, self._default)

    @property
    def name(self) -> str:
        """Name of the node."""
        return f"Try until a node does not raise {self.except_types}"

    def branches(self) -> Optional[Branches]:
        return {"": self._nodes}

    def nodes(self, *nodes: Node) -> "TryUntil":
        """Nodes to try."""
        self._nodes = nodes
        return self

    def default(self, node: Node) -> "TryUntil":
        """Nodes to call if all nodes raise an exception."""
        self._default = node
        return self
