"""Tests for utils/circuit_breaker.py."""

import time

from utils.circuit_breaker import CBState, CircuitBreaker, CircuitOpenError


def test_initial_state_closed():
    cb = CircuitBreaker(failure_threshold=3)
    assert cb.state == CBState.CLOSED
    assert cb.allow_request()


def test_stays_closed_below_threshold():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CBState.CLOSED
    assert cb.allow_request()


def test_opens_after_threshold():
    cb = CircuitBreaker(failure_threshold=3)
    for _ in range(3):
        cb.record_failure()
    assert cb.state == CBState.OPEN
    assert not cb.allow_request()


def test_success_resets_failure_count():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    assert cb.state == CBState.CLOSED
    # Need 3 more failures to open
    cb.record_failure()
    assert cb.state == CBState.CLOSED


def test_open_to_half_open_after_recovery():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CBState.OPEN

    # Simulate time passing
    cb._last_failure_time = time.monotonic() - 2.0
    assert cb.state == CBState.HALF_OPEN
    assert cb.allow_request()  # one probe allowed


def test_half_open_success_closes():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=5.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CBState.OPEN

    # Simulate recovery timeout elapsed
    cb._last_failure_time = time.monotonic() - 10.0
    assert cb.state == CBState.HALF_OPEN
    cb.record_success()
    assert cb.state == CBState.CLOSED


def test_half_open_failure_reopens():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=5.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CBState.OPEN

    cb._last_failure_time = time.monotonic() - 10.0
    assert cb.state == CBState.HALF_OPEN
    cb.record_failure()
    assert cb.state == CBState.OPEN


def test_half_open_max_probes():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.0, half_open_max=1)
    cb.record_failure()
    cb.record_failure()
    cb._last_failure_time = time.monotonic() - 1.0

    assert cb.allow_request()  # first probe
    assert not cb.allow_request()  # second blocked


def test_circuit_open_error_is_client_error():
    err = CircuitOpenError("test")
    assert isinstance(err, Exception)
