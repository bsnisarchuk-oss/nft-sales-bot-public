from datetime import datetime, time

from utils.quiet_hours import is_quiet_now, parse_time


class TestParseTime:
    def test_valid(self):
        assert parse_time("23:00") == time(23, 0)

    def test_valid_single_digit(self):
        assert parse_time("7:30") == time(7, 30)

    def test_invalid_hour(self):
        assert parse_time("25:00") is None

    def test_invalid_minute(self):
        assert parse_time("12:60") is None

    def test_garbage(self):
        assert parse_time("abc") is None

    def test_empty(self):
        assert parse_time("") is None


class TestIsQuietNow:
    def test_not_configured(self):
        assert is_quiet_now("", "") is False

    def test_invalid_start(self):
        assert is_quiet_now("abc", "07:00") is False

    def test_same_day_in_range(self):
        now = datetime(2026, 1, 1, 10, 0)
        assert is_quiet_now("09:00", "17:00", now=now) is True

    def test_same_day_out_range(self):
        now = datetime(2026, 1, 1, 18, 0)
        assert is_quiet_now("09:00", "17:00", now=now) is False

    def test_cross_midnight_in_range_before_midnight(self):
        now = datetime(2026, 1, 1, 23, 30)
        assert is_quiet_now("23:00", "07:00", now=now) is True

    def test_cross_midnight_in_range_after_midnight(self):
        now = datetime(2026, 1, 2, 3, 0)
        assert is_quiet_now("23:00", "07:00", now=now) is True

    def test_cross_midnight_out_range(self):
        now = datetime(2026, 1, 1, 12, 0)
        assert is_quiet_now("23:00", "07:00", now=now) is False

    def test_boundary_start_inclusive(self):
        now = datetime(2026, 1, 1, 23, 0)
        assert is_quiet_now("23:00", "07:00", now=now) is True

    def test_boundary_end_exclusive(self):
        now = datetime(2026, 1, 1, 7, 0)
        assert is_quiet_now("23:00", "07:00", now=now) is False
