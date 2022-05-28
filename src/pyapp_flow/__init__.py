"""
Application Workflow
"""
import logging
from typing import Callable, Sequence, Union, Tuple, Mapping, Any, Dict, Iterable

LOG = logging.getLogger(__name__)
Variable = Union[str, Tuple[str, type]]


class WorkflowContext:
    __slots__ = ("_state",)

    def __init__(self, **variables):
        self._state = [variables]

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


class Step:
    __slots__ = ("func", "inputs", "outputs", "name", "include_context")

    def __init__(
        self,
        func: Callable,
        inputs: Sequence[Variable] = None,
        outputs: Sequence[Variable] = None,
        name: str = None,
    ):
        self.func = func
        self.inputs = inputs or ()
        self.outputs = outputs or ()
        self.name = name or func.__name__
        self.include_context = False

    def __str__(self):
        return self.name

    def __call__(self, context: WorkflowContext):
        state = context.state
        args = (context,) if self.include_context else ()
        kwargs = {name: state.get(name) for name, _ in self.inputs}

        LOG.info("Calling step %s", self)
        try:
            results = self.func(*args, **kwargs)
        except Exception as ex:
            LOG.error("Exception raised in step %s: %s", self, ex)
            raise

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
    inputs: Sequence[Variable] = None,
    outputs: Sequence[Variable] = None,
) -> Step:
    """
    Step decorator
    """

    def decorator(func_):
        return Step(func_, inputs, outputs, name)

    return decorator(func) if func else decorator


class Workflow:
    def __init__(self, *nodes: Callable, name: str = None, description: str = None):
        self._nodes = list(nodes)
        self.name = name
        self.description = description

    def __call__(self, context: WorkflowContext):
        with context:
            self.execute(context)

    def execute(self, context: WorkflowContext = None):
        """
        Execute workflow
        """
        context = context or WorkflowContext()
        for node in self._nodes:
            node(context)

    def nodes(self, *nodes: Callable) -> "Workflow":
        """
        Add additional node(s)
        """
        self._nodes.extend(nodes)
        return self

    node = nodes

    def nested(self, *nodes: Callable) -> "Workflow":
        """
        Execute nodes in a nested scope
        """
        self._nodes.append(Workflow(*nodes))
        return self

    def foreach(self, target_var: str, in_var: str, *nodes: Callable) -> "Workflow":
        """
        Iterate through a sequence variable assigning each value to the target variable
        before executing the specified steps.
        """
        self._nodes.append(ForEach(target_var, in_var, *nodes))
        return self

    def capture_errors(
        self, target_var: str, *nodes: Callable, try_all: bool = False
    ) -> "Workflow":
        """
        Capture an errors generated by a step and append to specified variable (this is
        created if not found as a list).

        :param target_var: Name of a list variable to append error to (this is created if not found)
        :param nodes: Nodes to execute
        :param try_all: Every step is tried even if an error is raised in an earlier step
        """
        return self


class ForEach:
    def __init__(self, target_var: str, in_var: str, *nodes: Callable):
        self.target_var = target_var
        self.in_var = in_var
        self._nodes = nodes

    def __call__(self, context: WorkflowContext):
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
