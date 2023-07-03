from pyapp_flow.cli import actions


def test_run_flow__where_flow_is_successful(fixture_path):
    flow_file = fixture_path / "flows" / "valid.py"

    result = actions.run_flow(flow_file, "my_flow", {"a": "x"}, False, False)

    assert result is None


def test_run_flow__where_flow_is_not_found_in_flowfile(fixture_path):
    flow_file = fixture_path / "flows" / "valid.py"

    result = actions.run_flow(flow_file, "eek", {}, False, False)

    assert result == 404


def test_run_flow__where_flowfile_is_invalid(fixture_path):
    flow_file = fixture_path / "flows" / "invalid.py"

    result = actions.run_flow(flow_file, "eek", {}, False, False)

    assert result == 500


def test_run_flow__where_flowfile_is_not_found(fixture_path):
    flow_file = fixture_path / "flows" / "eek.py"

    result = actions.run_flow(flow_file, "my_flow", {}, False, False)

    assert result == 404


def test_run_flow__where_flowfile_is_bad(fixture_path):
    flow_file = fixture_path / "flows" / "bad.py"

    result = actions.run_flow(flow_file, "my_flow", {}, False, False)

    assert result == 501
