"""Tests for the tax calculator module."""

import pytest
from data.tax_calculator import (
    get_effective_tax_rate,
    get_after_tax_income,
    get_tax_impact,
    populate_tax_cache,
    DB_PATH,
)


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    test_db = tmp_path / "test_cache.db"
    monkeypatch.setattr("data.tax_calculator.DB_PATH", test_db)
    # Also patch rpp_fetcher DB so normalize_state doesn't fail
    monkeypatch.setattr("data.rpp_fetcher.DB_PATH", test_db)
    yield test_db


@pytest.fixture
def loaded_tax_data(temp_db):
    """Populate tax cache from the real CSV."""
    populate_tax_cache()


class TestGetEffectiveTaxRate:
    def test_no_income_tax_state(self, loaded_tax_data):
        rate = get_effective_tax_rate("Texas", 100000)
        assert rate == pytest.approx(0.0)

    def test_no_income_tax_florida(self, loaded_tax_data):
        rate = get_effective_tax_rate("Florida", 50000)
        assert rate == pytest.approx(0.0)

    def test_flat_tax_state(self, loaded_tax_data):
        rate = get_effective_tax_rate("Illinois", 75000)
        assert rate == pytest.approx(4.95)

    def test_progressive_low_bracket(self, loaded_tax_data):
        rate = get_effective_tax_rate("California", 30000)
        assert rate == pytest.approx(2.20)

    def test_progressive_high_bracket(self, loaded_tax_data):
        rate = get_effective_tax_rate("California", 600000)
        assert rate == pytest.approx(12.30)

    def test_abbreviation_input(self, loaded_tax_data):
        rate = get_effective_tax_rate("CA", 30000)
        assert rate == pytest.approx(2.20)

    def test_unknown_state_raises(self, loaded_tax_data):
        with pytest.raises(ValueError):
            get_effective_tax_rate("Atlantis", 50000)

    def test_auto_loads_csv(self, temp_db):
        """Should auto-populate from CSV if cache is empty."""
        rate = get_effective_tax_rate("Texas", 50000)
        assert rate == pytest.approx(0.0)


class TestGetAfterTaxIncome:
    def test_no_tax_state(self, loaded_tax_data):
        result = get_after_tax_income("Texas", 100000)
        assert result == pytest.approx(100000)

    def test_with_tax(self, loaded_tax_data):
        # Illinois flat 4.95%
        result = get_after_tax_income("Illinois", 100000)
        assert result == pytest.approx(95050)

    def test_high_tax_state(self, loaded_tax_data):
        # CA at 600k → 12.3% effective
        result = get_after_tax_income("California", 600000)
        expected = 600000 * (1 - 12.30 / 100)
        assert result == pytest.approx(expected)


class TestGetTaxImpact:
    def test_same_state(self, loaded_tax_data):
        result = get_tax_impact("Texas", 50000, "Texas", 50000)
        assert result["rate_difference"] == pytest.approx(0.0)

    def test_different_states(self, loaded_tax_data):
        result = get_tax_impact("Texas", 80000, "California", 80000)
        assert result["state1_rate"] == pytest.approx(0.0)
        assert result["state2_rate"] == pytest.approx(6.0)
        assert result["rate_difference"] == pytest.approx(6.0)

    def test_after_tax_values(self, loaded_tax_data):
        result = get_tax_impact("Texas", 100000, "Illinois", 100000)
        assert result["state1_after_tax"] == pytest.approx(100000)
        assert result["state2_after_tax"] == pytest.approx(95050)

    def test_result_keys(self, loaded_tax_data):
        result = get_tax_impact("TX", 50000, "CA", 50000)
        assert "state1_rate" in result
        assert "state2_rate" in result
        assert "state1_after_tax" in result
        assert "state2_after_tax" in result
        assert "rate_difference" in result
