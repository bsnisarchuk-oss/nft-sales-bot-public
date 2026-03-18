"""Circuit breaker pattern for TonAPI resilience."""

from __future__ import annotations

import time
from enum import Enum

import aiohttp


class CBState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(aiohttp.ClientError):
    """Raised when circuit breaker is open — requests are not allowed."""


class CircuitBreaker:
    """Simple three-state circuit breaker.

    CLOSED  → normal operation; failures increment counter
    OPEN    → all requests rejected immediately (CircuitOpenError)
    HALF_OPEN → one probe request allowed; success → CLOSED, failure → OPEN
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max: int = 1,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max
        self._state = CBState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0

    @property
    def state(self) -> CBState:
        if self._state == CBState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = CBState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    def allow_request(self) -> bool:
        s = self.state
        if s == CBState.CLOSED:
            return True
        if s == CBState.HALF_OPEN:
            if self._half_open_calls < self.half_open_max:
                self._half_open_calls += 1
                return True
            return False
        return False  # OPEN

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = CBState.CLOSED

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._state == CBState.HALF_OPEN:
            self._state = CBState.OPEN
        elif self._failure_count >= self.failure_threshold:
            self._state = CBState.OPEN
