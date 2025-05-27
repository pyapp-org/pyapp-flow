from collections.abc import Iterable
from typing import Callable, Any

from .datastructures import WorkflowContext
from .errors import (
    WorkflowSetupError,
    SkipStep,
    MissingVariableError,
    VariableTypeError,
)
from .helpers import human_join_strings


def skip_step(message: str):
    """Skip the current step.

    Uses a SkipStep exception to skip the current step.
    """
    raise SkipStep(message)


def var_list(var_names: str | list[str]) -> list[str]:
    """Split a comma separated list of var names into individual names."""
    if isinstance(var_names, str):
        var_names = var_names.split(",")
    return [name.strip() for name in var_names]


def extract_inputs(func: Callable) -> tuple[dict[str, type], str]:
    """Extract input variables from function."""
    func_code = func.__code__
    annotations = func.__annotations__

    # Ensure there are no positional only items
    if func_code.co_posonlyargcount:
        msg = (
            "Positional only arguments are not supported.\n\n"
            f"\tdef {func_code.co_name}(...)"
        )
        raise WorkflowSetupError(msg)

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
                msg = (
                    "WorkflowContext supplied multiple times.\n\n"
                    f"\tdef {func_code.co_name}({context_var}: WorkflowContext, {name}: WorkflowContext)"
                )
                raise WorkflowSetupError(msg)
            context_var = name

        else:
            inputs[name] = type_

    return inputs, context_var


def extract_outputs(
    func: Callable, names: str | list[str]
) -> tuple[tuple[str, type], ...]:
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
        msg = "Name count does not match type count."
        raise WorkflowSetupError(msg)

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


def call_nodes(context: WorkflowContext, nodes: tuple[Callable, ...]):
    """Call each node in a sequence."""
    for node in nodes:
        call_node(context, node)


def merge_nested_entries(
    iterable: Iterable[list], merge_methods: tuple[str, ...]
) -> tuple[list, ...]:
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


def required_variables_in_context(
    node_name: str,
    required_vars: list[tuple[str, type]],
    context: WorkflowContext,
):
    """Check all variables are in the context."""
    missing = []
    invalid_types = []

    for var_name, var_type in required_vars:
        try:
            value = context.state[var_name]
        except KeyError:
            missing.append(var_name)
        else:
            if var_type is not Any and not isinstance(value, var_type):
                invalid_types.append(var_name)

    if missing:
        msg = (
            f"{node_name} missing {len(missing)} required context variable: "
            f"{human_join_strings(missing)}"
        )
        raise MissingVariableError(msg)

    if invalid_types:
        msg = (
            f"{node_name} has {len(invalid_types)} context variable(s) with invalid types: "
            f"{human_join_strings(invalid_types)}"
        )
        raise VariableTypeError(msg)
