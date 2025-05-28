"""Application Workflow"""

import sys
from typing_extensions import Self

from . import errors as exceptions
from . import steps, builtin
from .datastructures import Branches, Navigable, WorkflowContext
from .functions import (
    call_nodes,
    extract_inputs,
    required_variables_in_context,
    skip_step,
)
from .nodes import (
    Append,
    CaptureErrors,
    Conditional,
    DefaultVar,
    FeatureEnabled,
    ForEach,
    Group,
    Nodes,
    If,
    LogMessage,
    Node,
    SetVar,
    SetGlobalVar,
    Step,
    Switch,
    TryExcept,
    TryUntil,
    inline,
    step,
)
from .steps import (
    alias,
)


class Workflow(Nodes):
    """A collection of Nodes that make up a workflow.

    :param name: The name of the workflow
    :param description: An optional description (similar to doc text) for the
        workflow.
    """

    __slots__ = ("_name", "description", "_required_vars")

    def __init__(self, name: str, description: str | None = None):
        super().__init__()
        self._name = name
        self.description = description
        self._required_vars = tuple()

    def __call__(self, context: WorkflowContext):
        context.info("⏩ Workflow: `%s`", context.format(self._name))
        with context:
            required_variables_in_context(self.name, self._required_vars, context)
            self._execute(context)

    @property
    def name(self):
        return self._name

    def execute(
        self, context: WorkflowContext = None, *, dry_run: bool = False, **context_vars
    ) -> WorkflowContext:
        """Execute workflow.

        This is the main way to trigger a work flow.

        :param context: Optional context; a new one will be created if not supplied.
        :param dry_run: Flag used to skip steps that have side effects.
        :param context_vars: Key/Value pairs to initialise the context with.
        :return: The context used to execute the workflow

        """
        context = context or WorkflowContext(dry_run=dry_run)
        context.state.update(context_vars)
        context.info("⏩ Workflow: `%s`", self._name)
        required_variables_in_context(self.name, self._required_vars, context)
        self._execute(context)
        return context

    def nodes(self, *nodes_: Node) -> Self:
        """Append additional node(s) into the node list.

        :param nodes_: Nodes to append to the current block
        :return: Returns self; fluent interface
        """
        self._nodes.extend(nodes_)
        return self

    def nested(self, *nodes_: Node) -> Self:
        """Add nested node(s), nested nodes have their own scope.

        :param nodes_: Collection of nodes call from nested block.
        :return: Returns self; fluent interface

        """
        self._nodes.append(Nodes(*nodes_))
        return self

    def set_vars(self, **kwargs) -> Self:
        """Set variables to a particular value.

        :param kwargs: Key/Value pairs to update in the context
        :return: Returns self; fluent interface

        """
        self._nodes.append(SetVar(**kwargs))
        return self

    def default_vars(self, **kwargs) -> Self:
        """Default variables to a particular value.

        :param kwargs: Key/Value pairs to update in the context
        :return: Returns self; fluent interface

        """
        self._nodes.append(DefaultVar(**kwargs))
        return self

    def require_vars(self, **kwargs: type | None) -> Self:
        """Require variables to be present in the context.

        If any type can be used, use ``typing.Any`` as the type.

        :param kwargs: Key/Type pairs to check in the context.
        :return: Returns self; fluent interface

        """
        self._required_vars = tuple(kwargs.items())
        return self


_debugger_active = getattr(sys, "gettrace", lambda: None)() is not None


def break_point(*, debugger_only: bool = False) -> Step:
    """Place a breakpoint in a flow to allow for debugging or inspection of context.

    :param debugger_only: Only trigger if the debugger is active.
    """

    @step(name="Breakpoint")
    def _step(ctx: WorkflowContext):
        if not _debugger_active:
            if debugger_only:
                skip_step("Debugger not active")
            ctx.info("WorkflowContext is available in `ctx` variable")

        breakpoint()

    return _step

