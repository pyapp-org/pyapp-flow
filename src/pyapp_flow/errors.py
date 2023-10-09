"""Exceptions raised by pyApp-Flow."""


class WorkflowException(Exception):
    pass


class WorkflowSetupError(WorkflowException):
    """Error setting up workflow"""


class WorkflowRuntimeError(WorkflowException, RuntimeError):
    """Error within the workflow runtime"""


class StepFailedError(WorkflowRuntimeError):
    """Error occurred within a step"""


class FatalError(WorkflowRuntimeError):
    """Fatal error occurred terminate the workflow."""


class SkipStep(WorkflowRuntimeError):
    """Skip the current step."""
