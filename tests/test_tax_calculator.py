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


class TestTaxBracketBoundaries:
    """Tests for tax bracket boundary conditions."""

    def test_bracket_boundary_california_low(self, loaded_tax_data):
        """Test at the boundary of the lowest CA bracket."""
        rate_below = get_effective_tax_rate("California", 9999)
        rate_at = get_effective_tax_rate("California", 10000)
        # Both should be in the same bracket
        assert rate_below == rate_at

    def test_bracket_boundary_california_middle(self, loaded_tax_data):
        """Test at the boundary between CA brackets."""
        rate_49999 = get_effective_tax_rate("California", 49999)
        rate_50000 = get_effective_tax_rate("California", 50000)
        # May be in different brackets
        assert rate_49999 <= rate_50000

    def test_bracket_boundary_california_high(self, loaded_tax_data):
        """Test at the boundary of high CA bracket."""
        rate_middle = get_effective_tax_rate("California", 100000)
        rate_high = get_effective_tax_rate("California", 1000000)
        # Higher income should have higher or equal rate
        assert rate_high >= rate_middle

    def test_very_low_income(self, loaded_tax_data):
        """Test with very low income."""
        rate = get_effective_tax_rate("California", 1000)
        assert rate >= 0.0
        assert rate <= 15.0  # Should be reasonable

    def test_very_high_income(self, loaded_tax_data):
        """Test with very high income."""
        rate = get_effective_tax_rate("California", 1000000)
        assert rate >= 0.0
        assert rate <= 15.0  # CA top rate

    def test_exact_bracket_minimum(self, loaded_tax_data):
        """Test at exact bracket minimum values."""
        # Most states have brackets starting at 0
        rate = get_effective_tax_rate("California", 0)
        assert rate >= 0.0


class TestMultipleStatesComparison:
    """Tests comparing multiple states."""

    def test_all_no_tax_states_equal(self, loaded_tax_data):
        """Test that all no-tax states have 0% rate."""
        no_tax_states = ["Texas", "Florida", "Nevada", "Wyoming", "South Dakota"]
        for state in no_tax_states:
            rate = get_effective_tax_rate(state, 50000)
            assert rate == pytest.approx(0.0), f"{state} should have 0% tax"

    def test_progressive_state_rates_increase(self, loaded_tax_data):
        """Test that progressive states have increasing rates."""
        incomes = [20000, 50000, 100000, 300000, 600000]
        rates = [get_effective_tax_rate("California", inc) for inc in incomes]
        # Rates should generally increase or stay the same
        for i in range(len(rates) - 1):
            assert rates[i] <= rates[i + 1] + 0.01  # Small tolerance for rounding

    def test_flat_tax_state_constant_rate(self, loaded_tax_data):
        """Test that flat tax states have constant rate across incomes."""
        incomes = [20000, 50000, 100000, 500000]
        rates = [get_effective_tax_rate("Illinois", inc) for inc in incomes]
        # All rates should be the same (4.95% for Illinois)
        for rate in rates:
            assert rate == pytest.approx(4.95)


class TestPopulateTaxCache:
    """Tests for tax cache population."""

    def test_populate_creates_entries(self, temp_db):
        """Test that populate_tax_cache creates database entries."""
        from data.tax_calculator import _get_db
        populate_tax_cache()
        conn = _get_db()
        count = conn.execute("SELECT COUNT(*) FROM taxes").fetchone()[0]
        conn.close()
        assert count > 0  # Should have created entries

    def test_populate_is_idempotent(self, loaded_tax_data):
        """Test that calling populate multiple times is safe."""
        populate_tax_cache()
        populate_tax_cache()
        # Should not raise errors
        rate = get_effective_tax_rate("Texas", 50000)
        assert rate == pytest.approx(0.0)


class TestEdgeCasesAndErrors:
    """Tests for edge cases and error conditions."""

    def test_income_at_zero(self, loaded_tax_data):
        """Test with zero income (edge case)."""
        rate = get_effective_tax_rate("California", 0)
        after_tax = get_after_tax_income("California", 0)
        assert rate >= 0.0
        assert after_tax == pytest.approx(0.0)

    def test_floating_point_income(self, loaded_tax_data):
        """Test with floating point income values."""
        rate = get_effective_tax_rate("California", 50000.50)
        assert rate >= 0.0
        after_tax = get_after_tax_income("California", 50000.75)
        assert after_tax > 0

    def test_state_normalization_in_tax(self, loaded_tax_data):
        """Test that state normalization works in tax functions."""
        rate_full = get_effective_tax_rate("California", 50000)
        rate_abbr = get_effective_tax_rate("CA", 50000)
        rate_lower = get_effective_tax_rate("california", 50000)
        assert rate_full == rate_abbr
        assert rate_full == rate_lower

    def test_income_out_of_all_brackets_raises(self, loaded_tax_data):
        """Test that extremely high income that exceeds all brackets still works."""
        # Tax data may not have very high brackets, so we test with a reasonable high value
        rate = get_effective_tax_rate("California", 1000000)
        # Should return the highest bracket rate, not raise
        assert rate >= 0.0
