from __future__ import annotations

import pytest

from app.adapters.api.validate import parse_date, parse_date_range, parse_search_query, parse_slug
from app.domain.exceptions import AppError


def test_parse_date_rejects_invalid():
    with pytest.raises(AppError) as exc:
        parse_date("2026-13-01")
    assert exc.value.status == 422
    assert exc.value.message == "Invalid date. Use YYYY-MM-DD."


def test_parse_slug_rejects_traversal():
    with pytest.raises(AppError) as exc:
        parse_slug("../etc/passwd")
    assert exc.value.message == "Invalid slug."


def test_parse_search_query_rules():
    assert parse_search_query("  Claude  ", present=True) == "Claude"
    assert parse_search_query(" \x00  ", present=True) is None
    with pytest.raises(AppError):
        parse_search_query(None, present=False)
    with pytest.raises(AppError):
        parse_search_query("x" * 101, present=True)


def test_parse_date_range_span():
    with pytest.raises(AppError) as exc:
        parse_date_range("2026-01-01", "2026-04-01")
    assert exc.value.message == "Invalid date range."