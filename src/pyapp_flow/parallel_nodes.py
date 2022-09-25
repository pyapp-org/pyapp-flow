"""
Parallel Nodes
"""
import importlib
from multiprocessing import Pool
from typing import Optional, Callable, Iterable, Any, Dict, Tuple

from pyapp_flow import Navigable, WorkflowContext, Branches
from pyapp_flow.exceptions import WorkflowRuntimeError


def import_node(node_id: str) -> Callable[[WorkflowContext], Any]:
    """
    Import a node
    """
    module_name, func = node_id.split(":")
    module = importlib.import_module(module_name)
    return getattr(module, func)


def _call_parallel_node(args: Tuple[Dict[str, Any], Optional[str], str]):
    """
    Wrapper to call parallel nodes
    """
    context_vars, merge_var, node_id = args
    context = WorkflowContext(**context_vars)
    node = import_node(node_id)
    node(context)
    if merge_var:
        return context.state[merge_var]


class MapNodes(Navigable):
    """
    Map an iterable set of values into a specified node using the multiprocessing
    library to perform the operation in parallel.

    A independent context scope is created for each loop with an optional
    ``merge_var`` supplied to be collected from this context to be combined as
    the output of the parallel mapping operation.

    :param target_var: Singular or multiple variables to unpack value into. This
        value can be either a single string, a comma separated list of strings or
        a sequence of strings.
    :param in_var: Context variable containing a sequence of values to be iterated
        over.
    :param merge_var: Context variable containing resulting value to be combined
        into a result list (the order of this list is not guaranteed is determined
        by the completion order of each sub-process).

    .. code-block:: python

        # With a single target variable
        (
            ParallelForEach("message", in_var="messages")
            .loop(log_message("- {message}"))
        )

        # With multiple target variables
        (
            ParallelForEach("name, age", in_var="students")
            .loop(log_message("- {name} is {age} years old."))
        )

    """

    __slots__ = ("target_var", "in_var", "merge_var", "_node_id", "_process_pool")

    def __init__(self, target_var: str, in_var: str, *, merge_var: str = None):
        self.target_var = target_var
        self.in_var = in_var
        self.merge_var = merge_var
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
            result = process_pool.map(
                _call_parallel_node,
                (
                    ({self.target_var: value}, self.merge_var, self._node_id)
                    for value in iterable
                ),
            )
            if self.merge_var:
                context.state[self.merge_var] = result

    def _get_pool(self):
        if not self._process_pool:
            self._process_pool = Pool()
        return self._process_pool

    @property
    def name(self):
        return f"Map ({self.target_var}) in `{self.in_var}`"

    def branches(self) -> Optional[Branches]:
        return {"loop": [self._node_id]}

    def loop(self, node_id: str) -> "MapNodes":
        """
        Nodes to call on each iteration of the foreach block
        """
        self._node_id = node_id
        return self
