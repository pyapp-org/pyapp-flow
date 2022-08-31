"""
Parallel Nodes
"""
import importlib
from multiprocessing import Pool
from typing import Optional, Callable, Iterable

from pyapp_flow import Navigable, WorkflowContext, Branches
from pyapp_flow.exceptions import WorkflowRuntimeError


def import_node(node_id: str) -> Callable[[WorkflowContext], None]:
    """
    Import a node
    """
    module_name, func = node_id.split(":")
    module = importlib.import_module(module_name)
    return getattr(module, func)


def call_parallel_node(args):
    context_vars, node_id = args
    context = WorkflowContext(**context_vars)
    node = import_node(node_id)
    node(context)


class ParallelForEach(Navigable):
    """
    For each loop to iterate through a set of values and call a set of nodes
    on each value; analogous with a for loop this node will iterate through a
    sequence and call each of the child nodes.

    All nodes within a for-each loop are in a nested context scope.

    Values can be un-packed into multiple context variables using Python iterable
    unpacking rules.

    :param target_vars: Singular or multiple variables to unpack value into. This
        value can be either a single string, a comma separated list of strings or
        a sequence of strings.
    :param in_var: Context variable containing a sequence of values to be iterated
        over.

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

    __slots__ = ("target_var", "in_var", "_node_id", "_process_pool")

    def __init__(self, target_var: str, in_var: str):
        self.target_var = target_var
        self.in_var = in_var
        self._node_id = None

        self._process_pool = None

    def __call__(self, context: WorkflowContext):
        context.info("🔁 %s", self)
        try:
            iterable = context.state[self.in_var]
        except KeyError:
            raise WorkflowRuntimeError(f"Variable {self.in_var} not found in context")

        if not isinstance(iterable, Iterable):
            raise WorkflowRuntimeError(f"Variable {self.in_var} is not iterable")

        if self._node_id:
            process_pool = self._get_pool()
            process_pool.map(
                call_parallel_node,
                [({self.target_var: value}, self._node_id) for value in iterable],
            )

    def _get_pool(self):
        if not self._process_pool:
            self._process_pool = Pool()
        return self._process_pool

    @property
    def name(self):
        return f"For ({self.target_var}) in `{self.in_var}`"

    def branches(self) -> Optional[Branches]:
        return {"loop": self._nodes_id}

    def loop(self, node_id: str) -> "ParallelForEach":
        """
        Nodes to call on each iteration of the foreach block
        """
        self._node_id = node_id
        return self
