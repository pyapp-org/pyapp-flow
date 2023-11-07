"""Application Workflow"""
from typing import Any, Optional, Type

from typing_extensions import Self

from . import errors as exceptions, steps
from .datastructures import WorkflowContext, Navigable, Branches
from .functions import extract_inputs, skip_step, call_nodes
from .nodes import (
    Node,
    step,
    inline,
    Step,
    SetVar,
    ForEach,
    CaptureErrors,
    Conditional,
    If,
    FeatureEnabled,
    Switch,
    LogMessage,
    Append,
    TryExcept,
    TryUntil,
    Group,
)


class Nodes(Group):
    """A series of nodes to be executed on call."""

    __slots__ = ()

    def __call__(self, context: WorkflowContext):
        with context:
            self._execute(context)

    @property
    def name(self) -> str:
        return f"⏬ {type(self).__name__}"


class Workflow(Nodes):
    """A collection of Nodes that make up a workflow.

    :param name: The name of the workflow
    :param description: An optional description (similar to doc text) for the
        workflow.
    """

    __slots__ = ("_name", "description", "_required_vars")

    def __init__(self, name: str, description: str = None):
        super().__init__()
        self._name = name
        self.description = description
        self._required_vars = tuple()

    def __call__(self, context: WorkflowContext):
        context.info("⏩ Workflow: `%s`", context.format(self._name))
        with context:
            self._execute(context)

    def _execute(self, context: WorkflowContext):
        """Override execute to check for required variables."""
        for var_name, var_type in self._required_vars:
            try:
                var_value = context.state[var_name]
            except KeyError:
                raise exceptions.MissingVariableError(var_name) from None

            if var_type is not Any and not isinstance(var_value, var_type):
                raise exceptions.VariableTypeError(var_name, var_type)

        super()._execute(context)

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

    def require_vars(self, **kwargs: Optional[Type]) -> Self:
        """Require variables to be present in the context.

        If any type can be used, use ``typing.Any`` as the type.

        :param kwargs: Key/Type pairs to check in the context.
        :return: Returns self; fluent interface

        """
        self._required_vars = tuple(kwargs.items())
        return self
