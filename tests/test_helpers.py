"""Tests for utility helper functions."""

import pytest
from utils.helpers import format_currency, format_percentage, current_year, clamp_year


class TestFormatCurrency:
    def test_basic(self):
        assert format_currency(1234.56) == "$1,234.56"

    def test_large_number(self):
        assert format_currency(1000000) == "$1,000,000.00"

    def test_zero(self):
        assert format_currency(0) == "$0.00"

    def test_negative(self):
        assert format_currency(-500.5) == "$-500.50"

    def test_small_decimal(self):
        assert format_currency(0.99) == "$0.99"


class TestFormatPercentage:
    def test_basic(self):
        assert format_percentage(5.0) == "5.0%"

    def test_custom_decimals(self):
        assert format_percentage(3.456, decimals=2) == "3.46%"

    def test_zero(self):
        assert format_percentage(0) == "0.0%"

    def test_large(self):
        assert format_percentage(99.9) == "99.9%"


class TestCurrentYear:
    def test_returns_int(self):
        assert isinstance(current_year(), int)

    def test_reasonable_range(self):
        assert 2020 <= current_year() <= 2030


class TestClampYear:
    def test_within_range(self):
        assert clamp_year(2000) == 2000

    def test_below_min(self):
        assert clamp_year(1900) == 1990

    def test_above_max(self):
        assert clamp_year(2050, max_year=2025) == 2025

    def test_custom_min(self):
        assert clamp_year(1950, min_year=1970) == 1970

    def test_default_max_is_current_year(self):
        result = clamp_year(9999)
        assert result == current_year()
