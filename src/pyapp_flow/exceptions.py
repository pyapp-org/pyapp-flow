"""
Exceptions
"""


class WorkflowException(Exception):
    pass


class WorkflowSetupError(WorkflowException):
    """ """


class StepFailedError(WorkflowException):
    """
    Error occurred within a step
    """


class FatalError(WorkflowException):
    """
    Fatal error occurred terminate the workflow.
    """
