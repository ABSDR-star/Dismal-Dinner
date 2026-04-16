"""Integration tests - full comparison workflows and data persistence."""

import json
import pytest
from calculator import compare_lifestyles
from utils.history import save_comparison, load_recent_comparisons, DB_PATH
from datetime import datetime


@pytest.fixture(autouse=True)
def mock_all_dbs(tmp_path, monkeypatch):
    """Point all modules to temp databases."""
    test_db = tmp_path / "test_cache.db"
    monkeypatch.setattr("data.cpi_fetcher.DB_PATH", test_db)
    monkeypatch.setattr("data.rpp_fetcher.DB_PATH", test_db)
    monkeypatch.setattr("data.tax_calculator.DB_PATH", test_db)
    monkeypatch.setattr("utils.history.DB_PATH", test_db)

    from data.cpi_fetcher import _cache_values
    _cache_values({
        1997: 160.5, 2000: 172.2, 2020: 258.8, 2023: 304.7, 2024: 313.0,
    })
    from data.rpp_fetcher import populate_rpp_cache
    populate_rpp_cache()
    from data.tax_calculator import populate_tax_cache
    populate_tax_cache()


class TestFullComparisonWorkflow:
    def test_readme_example(self):
        """The classic question: $17k Ohio 1997 vs $80k California 2024."""
        result = compare_lifestyles(17000, "Ohio", 1997, 80000, "California", 2024)
        assert result["purchasing_power_pct"] > 0
        assert result["cpi_factor"] > 1.0
        assert result["location_factor"] > 1.0
        assert "summary" in result

    def test_same_everything_is_100(self):
        result = compare_lifestyles(50000, "Texas", 2020, 50000, "Texas", 2020)
        assert result["purchasing_power_pct"] == pytest.approx(100.0)

    def test_comparison_result_is_json_serializable(self):
        result = compare_lifestyles(50000, "Ohio", 2000, 75000, "Oregon", 2023)
        # All values should be JSON-safe (no numpy, no custom objects)
        serialized = json.dumps(result)
        assert isinstance(serialized, str)
        roundtrip = json.loads(serialized)
        assert roundtrip["purchasing_power_pct"] == result["purchasing_power_pct"]


class TestSaveAndLoadHistory:
    def _make_export_data(self, income1=50000, state1="Texas", year1=2020,
                          income2=60000, state2="Ohio", year2=2023):
        result = compare_lifestyles(income1, state1, year1, income2, state2, year2)
        return {
            "scenario1_income": income1,
            "scenario1_state": result["state1"],
            "scenario1_year": year1,
            "scenario1_tax_rate": result["tax_rate1"],
            "scenario1_after_tax": result["after_tax1"],
            "scenario2_income": income2,
            "scenario2_state": result["state2"],
            "scenario2_year": year2,
            "scenario2_tax_rate": result["tax_rate2"],
            "scenario2_after_tax": result["after_tax2"],
            "cpi_factor": round(result["cpi_factor"], 4),
            "location_factor": round(result["location_factor"], 4),
            "purchasing_power_pct": round(result["purchasing_power_pct"], 2),
            "scenario1_equivalent_after_tax": round(result["after_tax1_equivalent"], 2),
            "gap": round(result["after_tax2"] - result["after_tax1_equivalent"], 2),
            "generated_at": datetime.now().isoformat(),
        }

    def test_save_and_load(self):
        data = self._make_export_data()
        save_comparison(data)
        history = load_recent_comparisons(limit=10)
        assert len(history) == 1
        assert history[0]["scenario1_state"] == "Texas"
        assert history[0]["scenario2_state"] == "Ohio"

    def test_load_empty(self):
        history = load_recent_comparisons()
        assert history == []

    def test_multiple_saves_ordered(self):
        save_comparison(self._make_export_data(income1=30000))
        save_comparison(self._make_export_data(income1=50000))
        save_comparison(self._make_export_data(income1=90000))
        history = load_recent_comparisons(limit=10)
        assert len(history) == 3
        # Most recent first
        assert history[0]["scenario1_income"] == 90000
        assert history[2]["scenario1_income"] == 30000

    def test_limit_respected(self):
        for i in range(10):
            save_comparison(self._make_export_data(income1=10000 * (i + 1)))
        history = load_recent_comparisons(limit=3)
        assert len(history) == 3

    def test_export_data_csv_compatible(self):
        """Export data should be flat (no nested dicts) for CSV."""
        data = self._make_export_data()
        for key, val in data.items():
            assert not isinstance(val, (dict, list)), f"{key} is not CSV-compatible"


class TestEdgeCases:
    def test_invalid_year_raises(self):
        with pytest.raises(ValueError, match="outside supported range"):
            compare_lifestyles(50000, "Texas", 1800, 50000, "Texas", 2020)

    def test_zero_income_raises(self):
        with pytest.raises(ValueError, match="positive"):
            compare_lifestyles(0, "Texas", 2020, 50000, "Texas", 2020)

    def test_negative_income_raises(self):
        with pytest.raises(ValueError, match="positive"):
            compare_lifestyles(-10000, "Texas", 2020, 50000, "Texas", 2020)

    def test_invalid_state_raises(self):
        with pytest.raises(ValueError, match="Unknown state"):
            compare_lifestyles(50000, "Atlantis", 2020, 50000, "Texas", 2020)
