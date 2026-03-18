from decimal import Decimal

import pytest

from utils.digest import format_digest, has_data, record_sale, reset


@pytest.fixture(autouse=True)
def _cleanup():
    reset()
    yield
    reset()


def test_no_data_returns_none():
    assert format_digest(1) is None


def test_record_and_format():
    record_sale(1, "0:buyer1", Decimal("10.0"), "Col A")
    record_sale(1, "0:buyer2", Decimal("5.5"), "Col A")
    record_sale(1, "0:buyer1", Decimal("3.0"), "Col B")

    result = format_digest(1)
    assert result is not None
    assert "3" in result  # 3 sales
    assert "18.5" in result  # total volume
    assert "0:buyer1" in result  # top buyer
    assert "Col A" in result  # top collection


def test_format_resets_data():
    record_sale(1, "0:buyer", Decimal("1.0"), "Col")
    format_digest(1)
    assert has_data(1) is False


def test_has_data():
    assert has_data(1) is False
    record_sale(1, "0:buyer", Decimal("1.0"), "Col")
    assert has_data(1) is True


def test_independent_chats():
    record_sale(1, "0:b", Decimal("1.0"), "C")
    record_sale(2, "0:b", Decimal("2.0"), "C")
    assert has_data(1)
    assert has_data(2)
    reset(1)
    assert not has_data(1)
    assert has_data(2)
