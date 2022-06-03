"""
Exceptions
"""


class WorkflowException(Exception):
    pass


class WorkflowSetupError(WorkflowException):
    """
    Error setting up workflow
    """


class WorkflowRuntimeError(WorkflowException, RuntimeError):
    """
    Error within the workflow runtime
    """


class StepFailedError(WorkflowException):
    """
    Error occurred within a step
    """


class FatalError(WorkflowException):
    """
    Fatal error occurred terminate the workflow.
    """
