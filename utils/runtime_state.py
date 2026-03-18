import time
from dataclasses import dataclass, field


@dataclass
class RuntimeState:
    started_at: float = field(default_factory=time.time)
    last_tick_at: float = 0.0
    last_tick_addr: str = ""
    last_tick_trace: str = ""
    total_traces: int = 0
    total_sales: int = 0
    last_sale_at: float = 0.0
    last_sale_trace: str = ""
    last_error: str = ""
    error_timestamps: list[float] = field(default_factory=list)


STATE = RuntimeState()


def mark_tick(addr: str = "", trace_id: str = "") -> None:
    STATE.last_tick_at = time.time()
    STATE.last_tick_addr = addr
    STATE.last_tick_trace = trace_id


def inc_traces(n: int = 1) -> None:
    STATE.total_traces += n


def mark_sale(trace_id: str) -> None:
    STATE.total_sales += 1
    STATE.last_sale_at = time.time()
    STATE.last_sale_trace = trace_id


def mark_error(msg: str) -> None:
    STATE.last_error = msg
    STATE.error_timestamps.append(time.time())
    # оставляем только ошибки за последний час
    now = time.time()
    STATE.error_timestamps = [ts for ts in STATE.error_timestamps if now - ts < 3600]


def snapshot() -> dict:
    return {
        "started_at": STATE.started_at,
        "last_tick_at": STATE.last_tick_at,
        "last_tick_addr": STATE.last_tick_addr,
        "last_tick_trace": STATE.last_tick_trace,
        "total_traces": STATE.total_traces,
        "total_sales": STATE.total_sales,
        "last_sale_at": STATE.last_sale_at,
        "last_sale_trace": STATE.last_sale_trace,
        "last_error": STATE.last_error,
        "errors_last_hour": len(STATE.error_timestamps),
    }
