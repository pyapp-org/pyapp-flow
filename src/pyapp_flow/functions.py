from typing import Callable, Mapping, Tuple, Sequence, Union, Iterable

from .datastructures import WorkflowContext
from .errors import WorkflowSetupError, SkipStep


def skip_step(message: str):
    """Skip the current step.

    Uses a SkipStep exception to skip the current step.
    """
    raise SkipStep(message)


def var_list(var_names: Union[str, Sequence[str]]) -> Sequence[str]:
    """Split a comma separated list of var names into individual names."""
    if isinstance(var_names, str):
        var_names = var_names.split(",")
    return [name.strip() for name in var_names]


def extract_inputs(func: Callable) -> Tuple[Mapping[str, type], str]:
    """Extract input variables from function."""
    func_code = func.__code__
    annotations = func.__annotations__

    # Ensure there are no positional only items
    if func_code.co_posonlyargcount:
        raise WorkflowSetupError(
            "Positional only arguments are not supported.\n\n"
            f"\tdef {func_code.co_name}(...)"
        )

    inputs = {}
    context_var = None
    total_args = sum(
        getattr(func_code, name, 0)
        for name in ("co_argcount", "co_posonlyargcount", "co_kwonlyargcount")
    )
    for name in func_code.co_varnames[:total_args]:
        type_ = annotations.get(name)
        # Extract a context instance
        if type_ is WorkflowContext:
            if context_var is not None:
                raise WorkflowSetupError(
                    "WorkflowContext supplied multiple times.\n\n"
                    f"\tdef {func_code.co_name}({context_var}: WorkflowContext, {name}: WorkflowContext)"
                )
            context_var = name

        else:
            inputs[name] = type_

    return inputs, context_var


def extract_outputs(
    func: Callable, names: Union[str, Sequence[str]]
) -> Sequence[Tuple[str, type]]:
    """Extract outputs from function."""
    types = func.__annotations__.get("return")

    # Ensure names is a list
    is_singular = False
    if names is None:
        names = ()
    elif isinstance(names, str):
        names = var_list(names)
        is_singular = len(names) == 1

    # Ensure types is a list
    if types is None:
        types = ()
    elif getattr(types, "_name", None) == "Tuple":
        types = (types,) if is_singular else types.__args__
    else:
        types = (types,)

    if len(names) != len(types):
        raise WorkflowSetupError("Name count does not match type count.")

    return tuple(zip(names, types))


def call_node(context: WorkflowContext, node: Callable):
    """Call a single node."""
    context.trace(node)
    try:
        node(context)
    except SkipStep:
        raise
    except Exception:
        context.capture_trace()
        raise


def call_nodes(context: WorkflowContext, nodes: Sequence[Callable]):
    """Call each node in a sequence."""
    for node in nodes:
        call_node(context, node)


def merge_nested_entries(
    iterable: Iterable[list], merge_methods: Sequence[str]
) -> Sequence[list]:
    """Rotate and combine rows of data.

    >>> merge_nested_entries([[1, 2, [3]], [4, 5, [6, 7]]], ("append", "append", "extend"))
    ... [[1, 4], [2, 5], [3, 6, 7]]

    """
    results = tuple([] for _ in merge_methods)
    merge_methods = tuple(
        getattr(result, method) for result, method in zip(results, merge_methods)
    )

    for entry in iterable:
        for value, merge_method in zip(entry, merge_methods):
            merge_method(value)

    return results
