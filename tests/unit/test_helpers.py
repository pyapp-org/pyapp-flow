import pytest

from pyapp_flow import helpers


@pytest.mark.parametrize(
    "items, expected",
    (
        ([], ""),
        (["a"], "a"),
        (["a", "b"], "a and b"),
        (["a", "b", "c"], "a, b and c"),
    ),
)
def test_human_join_strings(items, expected):
    actual = helpers.human_join_strings(items)

    assert actual == expected
