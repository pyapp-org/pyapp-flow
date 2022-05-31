"""
Application Workflow
"""
from typing import Callable, Union

from .datastructures import WorkflowContext
from .functions import extract_inputs
from .steps import (
    Variable,
    step,
    Step,
    set_var,
    SetVar,
    for_each,
    ForEach,
    capture,
    CaptureErrors,
    conditional,
    Conditional,
    log_message,
    LogMessage,
)


class Workflow:
    """
    A workflow definition.
    """

    __slots__ = ("_nodes", "name", "description")

    def __init__(self, *nodes: Callable, name: str, description: str = None):
        self._nodes = list(nodes)
        self.name = name
        self.description = description

    def __call__(self, context: WorkflowContext):
        context.info("⏩ Workflow: `%s`", self.name)
        with context:
            self._execute(context)

    def execute(self, context: WorkflowContext = None) -> WorkflowContext:
        """
        Execute workflow
        """
        context = context or WorkflowContext()
        context.logger.info("⏩ Workflow: `%s`", self.name)
        self._execute(context)
        return context

    def _execute(self, context: WorkflowContext):
        for node in self._nodes:
            node(context)

    def nodes(self, *nodes: Callable) -> "Workflow":
        """
        Add additional node(s)
        """
        self._nodes.extend(nodes)
        return self

    steps = nodes
    node = nodes

    def set_vars(self, **kwargs) -> "Workflow":
        """
        Set variables to a particular value
        """
        self._nodes.append(set_var(**kwargs))
        return self

    set_var = set_vars

    def foreach(self, target_var: str, in_var: str, *nodes: Callable) -> "Workflow":
        """
        Iterate through a sequence variable assigning each value to the target variable
        before executing the specified steps.
        """
        self._nodes.append(ForEach(target_var, in_var, *nodes))
        return self

    def condition(
        self, condition: Union[str, Callable[[WorkflowContext], bool]], *nodes: Callable
    ):
        """
        Conditional pipeline, only supports true branch
        """
        self._nodes.append(Conditional(condition, *nodes))
        return self

    def capture_errors(
        self, target_var: str, *nodes: Callable, try_all: bool = False
    ) -> "Workflow":
        """
        Capture an errors generated by a step and append to specified variable (this is
        created if not found as a list).

        :param target_var: Name of a list variable to append error to (this is created if not found)
        :param nodes: Nodes to execute
        :param try_all: Every step is tried even if an error is raised in an earlier step
        """
        self._nodes.append(CaptureErrors(target_var, *nodes, try_all=try_all))
        return self
