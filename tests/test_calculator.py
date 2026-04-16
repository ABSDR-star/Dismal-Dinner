"""Tests for the core comparison calculator."""

import pytest
from unittest.mock import patch
from calculator import compare_lifestyles, _compute_breakdown, _build_summary


# We mock the data fetchers so tests don't need real API/DB access.

@pytest.fixture(autouse=True)
def mock_data_modules(tmp_path, monkeypatch):
    """Mock all data modules with predictable values."""
    # Use temp DB for any module that touches SQLite
    test_db = tmp_path / "test_cache.db"
    monkeypatch.setattr("data.cpi_fetcher.DB_PATH", test_db)
    monkeypatch.setattr("data.rpp_fetcher.DB_PATH", test_db)
    monkeypatch.setattr("data.tax_calculator.DB_PATH", test_db)

    # Populate CPI cache with known values
    from data.cpi_fetcher import _cache_values
    _cache_values({
        1997: 160.525,
        2000: 172.200,
        2010: 218.056,
        2020: 258.811,
        2023: 304.702,
        2024: 313.000,
    })

    # Populate RPP cache
    from data.rpp_fetcher import populate_rpp_cache
    populate_rpp_cache()

    # Populate tax cache
    from data.tax_calculator import populate_tax_cache
    populate_tax_cache()


class TestCompareLifestyles:
    def test_identity_comparison(self):
        """Same income, same state, same year → 100%."""
        result = compare_lifestyles(50000, "Texas", 2020, 50000, "Texas", 2020)
        assert result["purchasing_power_pct"] == pytest.approx(100.0)

    def test_same_state_same_year_higher_income(self):
        """Higher income2 with everything else equal → >100%."""
        result = compare_lifestyles(50000, "Texas", 2020, 80000, "Texas", 2020)
        assert result["purchasing_power_pct"] > 100.0

    def test_same_state_same_year_lower_income(self):
        """Lower income2 with everything else equal → <100%."""
        result = compare_lifestyles(80000, "Texas", 2020, 50000, "Texas", 2020)
        assert result["purchasing_power_pct"] < 100.0

    def test_inflation_erodes_purchasing_power(self):
        """Same nominal income but later year → less purchasing power."""
        result = compare_lifestyles(50000, "Texas", 2000, 50000, "Texas", 2023)
        assert result["purchasing_power_pct"] < 100.0
        assert result["cpi_factor"] > 1.0

    def test_higher_cost_state_reduces_power(self):
        """Moving to expensive state with same income → less purchasing power."""
        result = compare_lifestyles(
            80000, "Mississippi", 2020, 80000, "California", 2020
        )
        assert result["purchasing_power_pct"] < 100.0
        assert result["location_factor"] > 1.0

    def test_lower_cost_state_increases_power(self):
        """Moving to cheaper state with same income → more purchasing power."""
        result = compare_lifestyles(
            80000, "California", 2020, 80000, "Mississippi", 2020
        )
        assert result["purchasing_power_pct"] > 100.0
        assert result["location_factor"] < 1.0

    def test_no_tax_vs_tax_state(self):
        """No-tax state has advantage over taxed state, all else equal."""
        result_tx = compare_lifestyles(80000, "Texas", 2020, 80000, "Texas", 2020)
        result_ca = compare_lifestyles(80000, "Texas", 2020, 80000, "California", 2020)
        # CA result should show less purchasing power than TX (taxes + cost)
        assert result_ca["purchasing_power_pct"] < result_tx["purchasing_power_pct"]

    def test_result_contains_all_keys(self):
        result = compare_lifestyles(50000, "Ohio", 2020, 60000, "Oregon", 2023)
        expected_keys = [
            "purchasing_power_pct", "summary",
            "income1", "state1", "year1",
            "income2", "state2", "year2",
            "cpi_factor", "income1_inflation_adjusted",
            "location_factor", "rpp_state1", "rpp_state2", "income1_equivalent",
            "tax_rate1", "tax_rate2", "after_tax1", "after_tax2",
            "after_tax1_equivalent", "breakdown",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_state_abbreviations_work(self):
        result = compare_lifestyles(50000, "TX", 2020, 50000, "TX", 2020)
        assert result["purchasing_power_pct"] == pytest.approx(100.0)
        assert result["state1"] == "Texas"
        assert result["state2"] == "Texas"

    def test_summary_better_off(self):
        result = compare_lifestyles(30000, "Texas", 2020, 100000, "Texas", 2020)
        assert "better off" in result["summary"]

    def test_summary_worse_off(self):
        result = compare_lifestyles(100000, "Texas", 2020, 30000, "Texas", 2020)
        assert "worse off" in result["summary"]

    def test_cpi_factor_stored(self):
        result = compare_lifestyles(50000, "Texas", 2000, 50000, "Texas", 2023)
        expected_cpi = 304.702 / 172.200
        assert result["cpi_factor"] == pytest.approx(expected_cpi)

    def test_tax_rates_stored(self):
        result = compare_lifestyles(50000, "Texas", 2020, 80000, "California", 2020)
        assert result["tax_rate1"] == pytest.approx(0.0)  # TX
        assert result["tax_rate2"] == pytest.approx(6.0)   # CA 50k-150k bracket


class TestComputeBreakdown:
    def test_no_change_scenario(self):
        bd = _compute_breakdown(
            income1=50000, income2=50000,
            cpi_factor=1.0, location_factor=1.0,
            tax_rate1=0.0, tax_rate2=0.0,
        )
        assert bd["inflation_impact"] == pytest.approx(0.0)
        assert bd["location_impact"] == pytest.approx(0.0)
        assert bd["tax_impact"] == pytest.approx(0.0)
        assert bd["gap"] == pytest.approx(0.0)

    def test_inflation_only(self):
        bd = _compute_breakdown(
            income1=50000, income2=50000,
            cpi_factor=2.0, location_factor=1.0,
            tax_rate1=0.0, tax_rate2=0.0,
        )
        assert bd["inflation_impact"] == pytest.approx(50000)
        assert bd["after_inflation"] == pytest.approx(100000)
        assert bd["gap"] == pytest.approx(-50000)  # income2 can't keep up

    def test_location_only(self):
        bd = _compute_breakdown(
            income1=50000, income2=50000,
            cpi_factor=1.0, location_factor=1.5,
            tax_rate1=0.0, tax_rate2=0.0,
        )
        assert bd["location_impact"] == pytest.approx(25000)
        assert bd["after_location"] == pytest.approx(75000)

    def test_tax_impact(self):
        bd = _compute_breakdown(
            income1=100000, income2=100000,
            cpi_factor=1.0, location_factor=1.0,
            tax_rate1=0.0, tax_rate2=5.0,
        )
        # Moving from 0% to 5% tax: negative impact
        assert bd["tax_impact"] == pytest.approx(-5000)

    def test_breakdown_keys(self):
        bd = _compute_breakdown(50000, 60000, 1.5, 1.1, 3.0, 5.0)
        expected = [
            "nominal_income1", "after_inflation", "after_location",
            "inflation_impact", "location_impact", "tax_impact",
            "equivalent_pretax", "equivalent_after_tax",
            "income2_after_tax", "gap",
        ]
        for key in expected:
            assert key in bd


class TestBuildSummary:
    def test_better_off(self):
        s = _build_summary(17000, "Ohio", 1997, 80000, "Ohio", 2024, 120.0)
        assert "better off" in s

    def test_worse_off(self):
        s = _build_summary(17000, "Ohio", 1997, 80000, "California", 2024, 60.0)
        assert "worse off" in s

    def test_about_the_same(self):
        s = _build_summary(50000, "Texas", 2020, 52000, "Texas", 2020, 100.0)
        assert "about the same" in s

    def test_contains_amounts(self):
        s = _build_summary(17000, "Ohio", 1997, 80000, "California", 2024, 75.5)
        assert "$17,000" in s
        assert "$80,000" in s
        assert "Ohio" in s
        assert "California" in s
        assert "1997" in s
        assert "2024" in s
