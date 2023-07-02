"""Parallel Nodes"""
import importlib
import enum
from functools import cached_property
from multiprocessing import Pool
from typing import Optional, Callable, Iterable, Any, Dict, Tuple, Sequence, Union

from pyapp_flow import Navigable, WorkflowContext, Branches
from pyapp_flow.errors import WorkflowRuntimeError, FatalError
from pyapp_flow.functions import merge_nested_entries


class MergeMethod(enum.Enum):
    """Method used to merge outputs of a parallel node."""

    Append = "append"
    Extend = "extend"


def import_node(node_id: str) -> Callable[[WorkflowContext], Any]:
    """Import a node."""
    module_name, _, func = node_id.rpartition(":")
    module = importlib.import_module(module_name)
    return getattr(module, func)


def _call_parallel_node(node_id, context_data, return_vars):
    """Wrapper to call parallel nodes."""
    try:
        node = import_node(node_id)
    except (AttributeError, ImportError) as ex:
        raise FatalError(f"Unable to import parallel node: {ex}")

    # Generate context and call node
    context = WorkflowContext(**context_data)
    node(context)

    # Generate return values from context
    state = context.state
    return tuple(state[var] for var in return_vars)


class _ParallelNode:
    """Wrapper around multiprocessing pool to do actual parallel processing."""

    __slots__ = ()

    pool_type = Pool

    def _map_to_pool(
        self,
        node_id: str,
        context_iter: Iterable[Dict[str, Any]],
        return_vars: Sequence[str],
    ) -> Sequence[Any]:
        """Map an iterable of context entries into a node.

        Uses a parallel worker pool."""
        return self._pool.starmap(
            _call_parallel_node,
            ((node_id, context_data, return_vars) for context_data in context_iter),
        )

    @cached_property
    def _pool(self):
        return self.pool_type()


class MapNode(Navigable, _ParallelNode):
    """Map an iterable into a specified node.

    Using the multiprocessing library to perform the operation in parallel.

    An independent context scope is created subprocess with an optional
    ``merge_var`` supplied to be collected from this context to be combined as
    the output of the parallel mapping operation.

    :param target_var: Singular or multiple variables to unpack value into.
        This value can be either a single string, a comma separated list of
        strings or a sequence of strings.
    :param in_var: Context variable containing a sequence of values to be
        iterated over.

    .. code-block:: python

        # Single direction mapping
        (
            MapNodes("message", in_var="messages")
            .loop("namespace:node_name")
        )

        # Mapping with merge variable
        (
            MapNodes("message", in_var="messages")
            .loop("namespace:node_name")
            .merge_var("results")
        )

    """

    __slots__ = ("target_var", "in_var", "_merge_vars", "_node_id")

    def __init__(self, target_var: str, in_var: str):
        self.target_var = target_var
        self.in_var = in_var
        self._merge_vars = []
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
            result_vars = [name for name, _ in self._merge_vars]
            results = self._map_to_pool(
                self._node_id,
                ({self.target_var: value} for value in iterable),
                result_vars,
            )
            context.state.update(
                zip(
                    result_vars,
                    merge_nested_entries(
                        results, [merge for _, merge in self._merge_vars]
                    ),
                )
            )

    @property
    def name(self):
        """Name of node."""
        return f"Map ({self.target_var}) in `{self.in_var}`"

    def branches(self) -> Optional[Branches]:
        """Branches to call on each iteration of the foreach block."""
        return {"loop": [self._node_id]}

    def loop(self, node: str) -> "MapNode":
        """Nodes to call on each iteration of the foreach block."""
        self._node_id = node
        return self

    def merge_vars(self, *merge_vars: Union[str, Tuple[str, MergeMethod]]) -> "MapNode":
        """Vars to merge back from parallel execution.

        These can optionally take a merge method to defined how the variables
        are merged; the default is ``append`` which will append each variable
        into a list. The other option is ``extend`` which allows for lists of
        results to be combined into a single list.
        """

        self._merge_vars = _merge_vars = []
        for merge_var in merge_vars:
            if isinstance(merge_var, str):
                var, method = merge_var, MergeMethod.Append
            else:
                var, method = merge_var
            _merge_vars.append((var, method.value))
        return self
