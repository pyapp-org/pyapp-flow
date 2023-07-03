from pathlib import Path

from unittest.mock import patch

import pytest

from pyapp_flow import cli


@pytest.mark.parametrize(
    "args, expected",
    (
        (
            ["foo"],
            (Path("./flowfile.py"), "foo", {}, False, False),
        ),
        (
            ["foo", "-f", "/path/to/flowfile.py"],
            (Path("/path/to/flowfile.py"), "foo", {}, False, False),
        ),
        (
            ["foo", "--dry-run"],
            (Path("./flowfile.py"), "foo", {}, True, False),
        ),
        (
            ["foo", "a=b"],
            (Path("./flowfile.py"), "foo", {"a": "b"}, False, False),
        ),
    ),
)
@patch("pyapp_flow.cli.actions.run_flow", return_value=0)
def test_run(mock_run_flow, args, expected):
    args = ["run"] + args
    cli.main(args)

    mock_run_flow.assert_called_once_with(*expected)
