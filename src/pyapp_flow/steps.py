from typing import Callable, Sequence, Union, Tuple, Iterable, Type

from pyapp_flow import extract_inputs, WorkflowContext

Variable = Union[str, Tuple[str, type]]


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
        outputs: Sequence[Variable] = None,
        ignore_exceptions: Union[Type[Exception], Sequence[Type[Exception]]] = None,
    ):
        self.func = func
        self.outputs = outputs or ()
        self.name = name or func.__name__.replace("_", " ")
        self.ignore_exceptions = ignore_exceptions

        self.inputs, self.context_var = extract_inputs(func)

    def __str__(self):
        return self.name

    def __call__(self, context: WorkflowContext):
        state = context.state
        kwargs = {name: state.get(name) for name in self.inputs}
        if self.context_var:
            kwargs[self.context_var] = context

        context.info("⚫ Step `%s`", self)
        try:
            results = self.func(**kwargs)

        except Exception as ex:
            if self.ignore_exceptions and isinstance(ex, self.ignore_exceptions):
                context.warning("  ❌ Ignoring exception: %s", ex)
            else:
                context.error("  ⛔ Exception raised: %s", ex)
                raise

        else:
            if self.outputs:
                # Helper so a simple return can be used for a single result
                if len(self.outputs) == 1:
                    results = (results,)

                for name, value in zip([name for name, _ in self.outputs], results):
                    context.state[name] = value


def step(
    func=None,
    *,
    name: str = None,
    outputs: Sequence[Variable] = None,
    ignore_exceptions: Union[Type[Exception], Sequence[Type[Exception]]] = None,
) -> Step:
    """
    Decorate a method turning it into a step
    """

    def decorator(func_):
        return Step(func_, name, outputs, ignore_exceptions)

    return decorator(func) if func else decorator


def set_var(**kwargs):
    """
    Set context variable to specified values
    """

    @step(name="set var")
    def _set_var(context: WorkflowContext):
        context.state.update(**kwargs)

    return _set_var


class ForEach:
    """
    Nested for each loop
    """

    __slots__ = ("target_var", "in_var", "_nodes")

    def __init__(self, target_var: str, in_var: str, *nodes: Callable):
        self.target_var = target_var
        self.in_var = in_var
        self._nodes = nodes

    def __call__(self, context: WorkflowContext):
        context.info("➰ For `%s` in `%s`", self.target_var, self.in_var)
        try:
            iterable = context.state[self.in_var]
        except KeyError:
            raise KeyError(f"Variable {self.in_var} not found in context")

        if not isinstance(iterable, Iterable):
            raise TypeError(f"Variable {self.in_var} is not iterable")

        for value in iterable:
            with context:
                context.state[self.target_var] = value
                for node in self._nodes:
                    node(context)

    def __str__(self):
        return f"foreach {self.target_var} in {self.in_var}"


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
        context.info("🥅 Capture errors into `%s`", self.target_var)

        context.state.setdefault(self.target_var, list())
        with context:
            for node in self._nodes:
                try:
                    node(context)
                except Exception as ex:
                    context.state[self.target_var] = ex
                    if not self.try_all:
                        break

    def __str__(self):
        return f"Capture errors into `{self.target_var}`"


class Conditional:
    """
    Branch a workflow based on a condition.

    A condition can be either a boolean based context variable or a callable that accepts a workflow context.
    """

    __slots__ = ("condition", "_true_nodes", "_false_nodes")

    def __init__(
        self, condition: Union[str, Callable[[WorkflowContext], bool]], *nodes: Callable
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
        context.info("Condition is %s errors into `%s`", condition)

        nodes = self._true_nodes if condition else self._false_nodes
        if nodes:
            with context:
                for node in nodes:
                    node(context)

    def if_false(self, *nodes: Callable):
        """
        If the condition is false execute these nodes
        """
        self._false_nodes = nodes
