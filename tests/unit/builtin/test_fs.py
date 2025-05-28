from pathlib import Path
from unittest.mock import Mock

import pytest

import pyapp_flow as flow
from pyapp_flow.builtin import fs
from pyapp_flow.testing import call_node


@pytest.fixture
def fs_path(fixture_path):
    return fixture_path / "builtin" / "fs"


@pytest.mark.parametrize(
    "path, expected",
    [
        ("{my_path}", True),
        ("{my_path}/my-dir", True),
        ("{my_path}/not-dir", False),
        ("{my_path}/my-dir/sub-dir", False),
        ("{my_path}/my-dir/sub-file.txt", False),
    ],
)
def test_dir_exists(fs_path, path, expected):
    target = fs.dir_exists(path)

    context = call_node(target, my_path=fs_path)
    actual = context.state.dir_exists

    assert actual == expected


@pytest.mark.parametrize(
    "path, expected",
    [
        ("{my_path}", False),
        ("{my_path}/my-dir", False),
        ("{my_path}/my-file.txt", True),
        ("{my_path}/my-dir/sub-dir", False),
        ("{my_path}/my-dir/sub-file.txt", True),
    ],
)
def test_file_exists(fs_path, path, expected):
    target = fs.file_exists(path)

    context = call_node(target, my_path=fs_path)
    actual = context.state.file_exists

    assert actual == expected


def test_ensure_dir(tmp_path: Path):
    target = fs.ensure_dir("{my_path}/my-dir/my-sub-dir")

    call_node(target, my_path=tmp_path)

    assert (tmp_path / "my-dir/my-sub-dir").is_dir()


def test_ensure_parent_dir(tmp_path: Path):
    target = fs.ensure_parent_dir("{my_path}/my-dir/my-sub-dir/my-file.txt")

    call_node(target, my_path=tmp_path)

    assert (tmp_path / "my-dir/my-sub-dir").is_dir()
    assert not (tmp_path / "my-dir/my-sub-dir/my-file.txt").exists()


class TestTemp:
    def test_name(self):
        target = fs.TempWorkspace()

        assert target.name == "📁 Temporary workspace"

    def test_ensure_removed(self, tmp_path: Path):
        target = fs.TempWorkspace(base_dir=tmp_path).nodes(
            fs.dir_exists("{workspace}"),
            flow.SetGlobalVar(actual_workspace=flow.alias("workspace")),
        )

        context = call_node(target)
        actual_workspace = context.state.actual_workspace
        actual_dir_exists = context.state.dir_exists

        assert actual_dir_exists
        assert not actual_workspace.exists()

    def test_not_removed(self, tmp_path: Path):
        target = fs.TempWorkspace(
            cleanup=False,
            base_dir=tmp_path,
        ).nodes(fs.dir_exists("{workspace}"))

        context = call_node(target)
        actual_workspace = context.state.workspace
        actual_dir_exists = context.state.dir_exists

        assert actual_dir_exists
        assert actual_workspace.exists()

    def test_remove_on_exception(self, tmp_path: Path):
        target = fs.TempWorkspace(base_dir=tmp_path).nodes(
            fs.dir_exists("{workspace}"),
            flow.SetGlobalVar(actual_workspace=flow.alias("workspace")),
            flow.steps.fatal("opps!"),
        )

        context = flow.WorkflowContext()
        with pytest.raises(flow.errors.FatalError):
            call_node(target, workflow_context=context)

        actual_workspace = context.state.actual_workspace
        actual_dir_exists = context.state.dir_exists

        assert actual_dir_exists
        assert not actual_workspace.exists()

    def test_raise_fatal_error_if_unable_to_remove_workspace(
        self, monkeypatch, tmp_path: Path
    ):
        monkeypatch.setattr("shutil.rmtree", Mock(side_effect=OSError))
        target = fs.TempWorkspace(base_dir=tmp_path)

        context = flow.WorkflowContext()
        with pytest.raises(flow.errors.StepFailedError):
            call_node(target, workflow_context=context)
        actual_workspace = context.state.workspace

        assert actual_workspace.is_dir()
