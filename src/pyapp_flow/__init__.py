"""
Application Workflow
"""
from typing import Callable, Union, Sequence, Mapping, Hashable

from . import exceptions
from .datastructures import WorkflowContext
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


class Nodes:
    """
    A series of nodes to be executed on call.
    """

    __slots__ = ("_nodes",)

    def __init__(self, *nodes_: Callable):
        self._nodes = list(nodes_)

    def __call__(self, context: WorkflowContext):
        with context:
            self._execute(context)

    def _execute(self, context: WorkflowContext):
        for node in self._nodes:
            node(context)


class Workflow(Nodes):
    """
    A workflow definition.
    """

    __slots__ = ("name", "description")

    def __init__(self, *nodes_: Callable, name: str, description: str = None):
        super().__init__(*nodes_)
        self.name = name
        self.description = description

    def __call__(self, context: WorkflowContext):
        context.info("⏩ Workflow: `%s`", self.name)
        with context:
            self._execute(context)

    def __str__(self):
        return self.name

    def execute(self, context: WorkflowContext = None) -> WorkflowContext:
        """
        Execute workflow
        """
        context = context or WorkflowContext()
        context.logger.info("⏩ Workflow: `%s`", self.name)
        self._execute(context)
        return context

    def nodes(self, *nodes_: Callable) -> "Workflow":
        """
        Add additional node(s)
        """
        self._nodes.extend(nodes_)
        return self

    def nested(self, *nodes_: Callable) -> "Workflow":
        """
        Add nested node(s), nested nodes have their own scope
        """
        self._nodes.append(Nodes(*nodes_))
        return self

    def set_vars(self, **kwargs) -> "Workflow":
        """
        Set variables to a particular value
        """
        self._nodes.append(SetVar(**kwargs))
        return self
