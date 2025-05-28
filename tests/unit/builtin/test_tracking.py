import pytest

import pyapp_flow as flow

from pyapp_flow.builtin import tracking
from pyapp_flow.testing import call_node


class TestCounter:
    @pytest.fixture
    def target(self):
        return flow.Workflow("Sample pipeline").nodes(
            flow.SetVar(items=list(range(0, 5))),
            tracking.increment("count"),
            flow.ForEach("item", "items").loop(
                tracking.increment("count"),
            ),
            tracking.decrement("count", amount=2),
        )

    def test_in_workflow(self, target):
        counter = tracking.Counter()

        call_node(target, count=counter)

        assert counter.value == 4

    def test_reverse_math(self):
        counter = tracking.Counter(10)

        assert 10 + counter == 20
        assert 15 - counter == 5
        assert 10 * counter == 100
        assert 12 / counter == 1

    def test_formatting(self):
        counter = tracking.Counter(42)

        assert str(counter) == "42"
        assert f"{counter:04}" == "0042"
