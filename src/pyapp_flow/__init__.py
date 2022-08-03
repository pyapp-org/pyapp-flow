"""
Application Workflow
"""
from typing import Callable, Optional

from . import exceptions
from .datastructures import WorkflowContext, Navigable, Branches
from .functions import extract_inputs
from .nodes import (
    step,
    Step,
    SetVar,
    ForEach,
    CaptureErrors,
    Conditional,
    If,
    Switch,
    LogMessage,
    Append,
)


class Nodes(Navigable):
    """
    A series of nodes to be executed on call.
    """

    __slots__ = ("_nodes",)

    def __init__(self, *nodes_):
        self._nodes = list(nodes_)

    def __call__(self, context: WorkflowContext):
        with context:
            self._execute(context)

    @property
    def name(self):
        return "Nodes"

    def branches(self) -> Optional[Branches]:
        return {"": self._nodes}

    def _execute(self, context: WorkflowContext):
        for node in self._nodes:
            node(context)


class Workflow(Nodes):
    """
    A collection of Nodes that make up a workflow.

    :param name: The name of the workflow
    :param description: An optional description (similar to doc text) for the
        workflow.
    """

    __slots__ = ("_name", "description")

    def __init__(self, name: str, description: str = None):
        super().__init__()
        self._name = name
        self.description = description

    def __call__(self, context: WorkflowContext):
        context.info("⏩ Workflow: `%s`", self._name)
        with context:
            self._execute(context)

    @property
    def name(self):
        return self._name

    def execute(
        self, context: WorkflowContext = None, **context_vars
    ) -> WorkflowContext:
        """
        Execute workflow. This is the main way to trigger a work flow

        :param context: Optional context; a new one will be created if not supplied.
        :param context_vars: Key/Value pairs to initialise the context with.
        :return: The context used to execute the workflow

        """
        context = context or WorkflowContext()
        context.state.update(context_vars)
        context.logger.info("⏩ Workflow: `%s`", self._name)
        self._execute(context)
        return context

    def nodes(self, *nodes_: Callable) -> "Workflow":
        """
        Append additional node(s) into the node list

        :param nodes_: Nodes to append to the current block
        :return: Returns self; fluent interface

        """
        self._nodes.extend(nodes_)
        return self

    def nested(self, *nodes_: Callable) -> "Workflow":
        """
        Add nested node(s), nested nodes have their own scope

        :param nodes_: Collection of nodes call from nested block.
        :return: Returns self; fluent interface

        """
        self._nodes.append(Nodes(*nodes_))
        return self

    def set_vars(self, **kwargs) -> "Workflow":
        """
        Set variables to a particular value

        :param kwargs: Key/Value pairs to update in the context
        :return: Returns self; fluent interface

        """
        self._nodes.append(SetVar(**kwargs))
        return self
