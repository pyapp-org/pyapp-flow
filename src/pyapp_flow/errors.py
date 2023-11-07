"""Exceptions raised by pyApp-Flow."""


class WorkflowException(Exception):
    pass


class MissingVariableError(WorkflowException, TypeError):
    """Variable not found in context."""


class VariableTypeError(WorkflowException, TypeError):
    """Variable type is invalid."""


class WorkflowSetupError(WorkflowException):
    """Error setting up workflow"""


class WorkflowRuntimeError(WorkflowException, RuntimeError):
    """Error within the workflow runtime"""


class StepFailedError(WorkflowException):
    """Error occurred within a step"""


class FatalError(WorkflowException):
    """Fatal error occurred terminate the workflow."""


class SkipStep(WorkflowException):
    """Skip the current step."""
