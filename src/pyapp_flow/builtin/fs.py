"""Filesystem steps."""

import shutil
import tempfile
from pathlib import Path

from .. import errors
from ..datastructures import WorkflowContext
from ..nodes import step, Step, WithContextBase


PathStr = Path | str


def format_path(path: PathStr, context: WorkflowContext) -> Path:
    """Format a path object using context variables."""
    path = Path(path)
    return Path(context.format(path.as_posix()))


def dir_exists(path: PathStr, output_var="dir_exists") -> Step:
    """Check if a directory exists.

    Often used with a condition block.

    :param path: Path to directory to check for.
    :param output_var: Name of output variable.
    :returns: Boolean of directory state.

    .. code-block:: python

        flow.If(
            dir_exists("/path/to/dir")
        ).true(...)

    """

    @step(name=f"📁 Does directory exist? {path}", output=output_var)
    def _step(context: WorkflowContext) -> bool:
        target = format_path(path, context)
        return target.is_dir()

    return _step


def file_exists(path: PathStr, output_var="file_exists") -> Step:
    """Check if a file exists.

    Often used with a condition block.

    :param path: Path to file to check for.
    :param output_var: Name of output variable.
    :returns: Boolean of file state.

    .. code-block:: python

        flow.If(
            file_exists("/path/to/dir/file.txt")
        ).true(...)

    """

    @step(name=f"📄 Does file exist? {path}", output=output_var)
    def _step(context: WorkflowContext) -> bool:
        target = format_path(path, context)
        return target.is_file()

    return _step


def ensure_dir(path: PathStr, *, parents: bool = True) -> Step:
    """Ensure a directory exists, creating if required.

    :param path: Path to file/dir that must exist.
    :param parents: If True, create parent directory's if necessary.

    .. code-block:: python

        ensure_dir("/path/to/dir")

    """

    @step(name=f"📁 Ensure directory exists {path}")
    def _step(context: WorkflowContext):
        target = format_path(path, context)
        target.mkdir(parents=parents, exist_ok=True)

    return _step


def ensure_parent_dir(path: PathStr, *, parents: bool = True) -> Step:
    """Ensure the parent directory exists, creating if required.

    :param path: Path to file/dir whose parent must exist.
    :param parents: If True, create parent directory's if necessary.

    .. code-block:: python

        ensure_parent_dir("/path/to/dir")

    """

    @step(name=f"📁 Ensure parent directory exists for {path}")
    def _step(context: WorkflowContext):
        target = format_path(path, context).parent
        target.mkdir(parents=parents, exist_ok=True)

    return _step


class TempWorkspace(WithContextBase):
    """Step that creates a temporary workspace that is cleaned up on exit.

    :param target_var: Variable the Path to the workspace is placed; default is
        ``workspace``.
    :param cleanup: Clean up the workspace on exit; default is True.
    :param prefix: A prefix to provide the workspace name; default is
        ``flow-``.
    :param base_dir: An optional location to create the temporary workspace.
        The default value of ``None`` will resolve the system ``TEMP`` variable
        as the base_dir.

    .. code-block:: python

        TempWorkspace()

    """

    """Temporary Workspace that is cleaned up on exit."""

    def __init__(
        self,
        target_var: str = "workspace",
        *,
        cleanup: bool = True,
        prefix: str = "flow-",
        base_dir: PathStr | None = None,
    ):
        """Initialise Temp Workspace.

        :param target_var: Target variable name; default is 'workspace'.
        :param cleanup: Clean-up the temporary workspace before exiting.
        :param prefix: Prefix for temporary workspace directory.
        :param base_dir: Location of the workspace directory; default is the current tmp path..
        """
        self.target_var = target_var
        self.cleanup = cleanup
        self.prefix = prefix
        self.base_dir = base_dir

        super().__init__()

    def enter(self, context: WorkflowContext):
        """Enter the context."""

        base_dir = None
        if self.base_dir:
            base_dir = format_path(self.base_dir, context)

        context.info("📁 Create temporary workspace")
        path = Path(tempfile.mkdtemp(prefix=self.prefix, dir=base_dir))
        context.debug("📁 Created temporary workspace: %s", path)

        context.state[self.target_var] = path

    def exit(self, context: WorkflowContext, exception: Exception | None):
        """Exit the context.

        The exception value is supplied if an exception was raised when calling child nodes.
        """
        if self.cleanup:
            path = context.state[self.target_var]
            context.info("🗑️ Clean up temporary workspace")
            try:
                shutil.rmtree(path)
                context.debug("🗑️ Cleaned up temporary workspace: %s", path)
            except Exception as ex:
                msg = f"Unable to remove temporary workspace: {ex}"
                raise errors.StepFailedError(msg) from ex

            del context.state[self.target_var]

    @property
    def name(self) -> str:
        """Name of the step."""
        return "📁 Temporary workspace"
