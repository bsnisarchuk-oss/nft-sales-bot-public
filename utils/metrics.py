"""Optional Prometheus metrics.

If prometheus_client is installed, exposes counters/gauges.
If not installed, all metric operations are no-ops.
"""

from __future__ import annotations

import logging

log = logging.getLogger("metrics")


class _Noop:
    """No-op stub used when prometheus_client is not installed."""

    def inc(self, *a, **kw):
        pass

    def dec(self, *a, **kw):
        pass

    def set(self, *a, **kw):
        pass

    def observe(self, *a, **kw):
        pass

    def labels(self, *a, **kw) -> _Noop:
        return self

    def time(self):
        import contextlib
        return contextlib.nullcontext()


try:
    from prometheus_client import Counter, Gauge, Histogram
    from prometheus_client import start_http_server as _start_http_server

    sales_total: Counter | _Noop = Counter("nft_sales_total", "Total NFT sales processed")
    sales_sent: Counter | _Noop = Counter("nft_sales_sent", "Total sale notifications sent", ["chat_id"])
    sales_skipped: Counter | _Noop = Counter("nft_sales_skipped", "Sales skipped (filters, quiet hours)", ["reason"])
    poll_duration: Histogram | _Noop = Histogram("nft_poll_duration_seconds", "Duration of each polling tick")
    tonapi_requests: Counter | _Noop = Counter("nft_tonapi_requests_total", "TonAPI requests", ["status"])
    circuit_breaker_state: Gauge | _Noop = Gauge("nft_circuit_breaker_state", "Circuit breaker state (0=closed, 1=open, 2=half-open)")
    active_chats: Gauge | _Noop = Gauge("nft_active_chats", "Number of active bound chats")
    tracked_collections: Gauge | _Noop = Gauge("nft_tracked_collections", "Number of tracked collections")

    PROMETHEUS_AVAILABLE = True

except ImportError:
    PROMETHEUS_AVAILABLE = False

    _noop = _Noop()
    sales_total = _noop
    sales_sent = _noop
    sales_skipped = _noop
    poll_duration = _noop
    tonapi_requests = _noop
    circuit_breaker_state = _noop
    active_chats = _noop
    tracked_collections = _noop

    def _start_http_server(*a, **kw):
        pass


def start_metrics_server(port: int = 9090) -> None:
    """Start the Prometheus metrics HTTP server if available."""
    if PROMETHEUS_AVAILABLE:
        try:
            _start_http_server(port)
            log.info("Prometheus metrics server started on port %d", port)
        except OSError as e:
            log.warning("Failed to start metrics server on port %d: %s", port, e)
    else:
        log.debug("prometheus_client not installed — metrics server disabled")
