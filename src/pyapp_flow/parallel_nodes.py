"""
Parallel Nodes
"""
import importlib
import itertools
from functools import cached_property
from multiprocessing import Pool
from typing import Optional, Callable, Iterable, Any, Dict, Tuple, Sequence

from pyapp_flow import Navigable, WorkflowContext, Branches
from pyapp_flow.exceptions import WorkflowRuntimeError


def import_node(node_id: str) -> Callable[[WorkflowContext], Any]:
    """
    Import a node
    """
    module_name, func = node_id.split(":")
    module = importlib.import_module(module_name)
    return getattr(module, func)


def _call_parallel_node(args: Tuple[str, Sequence[str], Dict[str, Any]]):
    """
    Wrapper to call parallel nodes
    """
    # Decode args and import node
    node_id, return_vars, context_data = args
    node = import_node(node_id)

    # Generate context and call node
    context = WorkflowContext(**context_data)
    node(context)

    # Generate return values from context
    state = context.state
    return [state[var] for var in return_vars]


class _ParallelNode:
    """
    Wrapper around multiprocessing pool to do actual parallel processing
    """

    __slots__ = ()

    pool_type = Pool

    def _map_to_pool(
        self,
        node_id: str,
        return_vars: Sequence[str],
        context_iter: Iterable[Dict[str, Any]],
    ) -> Sequence[Any]:
        return self._pool.map(
            _call_parallel_node,
            ((node_id, return_vars, context_data) for context_data in context_iter),
        )

    @cached_property
    def _pool(self):
        return Pool()


class MapNode(Navigable, _ParallelNode):
    """
    Map an iterable into a specified node using the multiprocessing library to
    perform the operation in parallel.

    An independent context scope is created subprocess with an optional
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

        # Single direction mapping
        (
            MapNodes("message", in_var="messages")
            .loop("namespace:node_name")
        )

        # Mapping with merge variable
        (
            MapNodes("message", in_var="messages", merge_var="results")
            .loop("namespace:node_name")
        )

    """

    __slots__ = ("target_var", "in_var", "merge_var", "_node_id")

    def __init__(self, target_var: str, in_var: str, *, merge_var: str = None):
        self.target_var = target_var
        self.in_var = in_var
        self.merge_var = merge_var
        self._node_id = None

    def __call__(self, context: WorkflowContext):
        context.info("🔁 %s", self)
        try:
            iterable = context.state[self.in_var]
        except KeyError:
            raise WorkflowRuntimeError(f"Variable {self.in_var} not found in context")

        if not isinstance(iterable, Iterable):
            raise WorkflowRuntimeError(f"Variable {self.in_var} is not iterable")

        if self._node_id:
            result_vars = [self.merge_var] if self.merge_var else []

            results = self._map_to_pool(
                self._node_id,
                result_vars,
                ({self.target_var: value} for value in iterable),
            )

    def _get_pool(self):
        if not self._process_pool:
            self._process_pool = Pool()
        return self._process_pool

    @property
    def name(self):
        return f"Map ({self.target_var}) in `{self.in_var}`"

    def branches(self) -> Optional[Branches]:
        return {"loop": [self._node_id]}

    def loop(self, node_id: str) -> "MapNode":
        """
        Nodes to call on each iteration of the foreach block
        """
        self._node_id = node_id
        return self
