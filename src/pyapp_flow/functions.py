from typing import Callable, Mapping, Tuple

from .datastructures import WorkflowContext


def extract_inputs(func: Callable) -> Tuple[Mapping[str, type], str]:
    """
    Extract input variables from function
    """
    func_code = func.__code__
    annotations = func.__annotations__

    # Ensure there are no positional only items
    if func_code.co_posonlyargcount:
        raise TypeError(
            "Positional only arguments are not supported.\n\n"
            f"\tdef {func_code.co_name}(...)"
        )

    inputs = {}
    context_var = None
    for name in func_code.co_varnames:
        type_ = annotations.get(name)
        # Extract a context instance
        if type_ is WorkflowContext:
            if context_var is not None:
                raise TypeError(
                    "WorkflowContext supplied multiple times.\n\n"
                    f"\tdef {func_code.co_name}({context_var}: WorkflowContext, {name}: WorkflowContext)"
                )
            context_var = name

        else:
            inputs[name] = type_

    return inputs, context_var
