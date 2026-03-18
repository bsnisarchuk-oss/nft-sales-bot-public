from unittest.mock import patch

from utils.metrics import (
    PROMETHEUS_AVAILABLE,
    _Noop,
    active_chats,
    sales_sent,
    sales_total,
    tonapi_requests,
)


def test_prometheus_available():
    assert PROMETHEUS_AVAILABLE is True


def test_counter_inc():
    before = sales_total._value.get()
    sales_total.inc()
    assert sales_total._value.get() == before + 1


def test_labeled_counter():
    sales_sent.labels(chat_id="123").inc()


def test_gauge_set():
    active_chats.set(5)
    assert active_chats._value.get() == 5


def test_tonapi_requests_labels():
    tonapi_requests.labels(status="200").inc()


# ── _Noop methods ──

def test_noop_inc():
    n = _Noop()
    n.inc()  # should not raise


def test_noop_dec():
    n = _Noop()
    n.dec()


def test_noop_set():
    n = _Noop()
    n.set(42)


def test_noop_observe():
    n = _Noop()
    n.observe(1.5)


def test_noop_labels_returns_self():
    n = _Noop()
    result = n.labels(chat_id="1")
    assert result is n


def test_noop_time_returns_context_manager():
    n = _Noop()
    cm = n.time()
    # contextlib.nullcontext — must be usable as context manager
    with cm:
        pass


# ── start_metrics_server ──

def test_start_metrics_server_not_available(caplog):
    import logging

    from utils.metrics import start_metrics_server
    with patch("utils.metrics.PROMETHEUS_AVAILABLE", False):
        with caplog.at_level(logging.DEBUG, logger="metrics"):
            start_metrics_server(9999)
    assert any("not installed" in r.message for r in caplog.records)


def test_start_metrics_server_available():
    from utils.metrics import start_metrics_server
    with patch("utils.metrics.PROMETHEUS_AVAILABLE", True), \
         patch("utils.metrics._start_http_server") as mock_srv:
        start_metrics_server(9999)
    mock_srv.assert_called_once_with(9999)


def test_start_metrics_server_oserror(caplog):
    import logging

    from utils.metrics import start_metrics_server
    with patch("utils.metrics.PROMETHEUS_AVAILABLE", True), \
         patch("utils.metrics._start_http_server", side_effect=OSError("port in use")):
        with caplog.at_level(logging.WARNING, logger="metrics"):
            start_metrics_server(9999)
    assert any("Failed" in r.message for r in caplog.records)
