import pytest

from utils.whale_detector import SWEEP_MIN_COUNT, record_purchase, reset


@pytest.fixture(autouse=True)
def _cleanup():
    reset()
    yield
    reset()


def test_no_sweep_below_threshold():
    """Below SWEEP_MIN_COUNT purchases, no sweep event."""
    for i in range(SWEEP_MIN_COUNT - 1):
        result = record_purchase("buyer_a", f"trace_{i}")
    assert result is None


def test_sweep_at_threshold():
    """Exactly SWEEP_MIN_COUNT purchases triggers sweep."""
    result = None
    for i in range(SWEEP_MIN_COUNT):
        result = record_purchase("buyer_a", f"trace_{i}")
    assert result is not None
    assert result.buyer == "buyer_a"
    assert result.count == SWEEP_MIN_COUNT


def test_sweep_only_fires_once():
    """Sweep fires only at threshold, not on subsequent purchases."""
    results = []
    for i in range(SWEEP_MIN_COUNT + 3):
        results.append(record_purchase("buyer_a", f"trace_{i}"))
    non_none = [r for r in results if r is not None]
    assert len(non_none) == 1
    assert non_none[0].count == SWEEP_MIN_COUNT


def test_different_buyers_independent():
    """Different buyers have independent histories."""
    for i in range(SWEEP_MIN_COUNT - 1):
        record_purchase("buyer_a", f"trace_a_{i}")
    for i in range(SWEEP_MIN_COUNT - 1):
        record_purchase("buyer_b", f"trace_b_{i}")

    result_a = record_purchase("buyer_a", "trace_a_final")
    result_b = record_purchase("buyer_b", "trace_b_final")

    assert result_a is not None
    assert result_a.buyer == "buyer_a"
    assert result_b is not None
    assert result_b.buyer == "buyer_b"


def test_reset_clears_history():
    """reset() clears all buyer history."""
    for i in range(SWEEP_MIN_COUNT - 1):
        record_purchase("buyer_a", f"trace_{i}")
    reset()
    result = record_purchase("buyer_a", "trace_after_reset")
    assert result is None
