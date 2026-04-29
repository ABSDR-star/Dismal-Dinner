"""Tests for the comparison history module."""

import pytest
import sqlite3
from datetime import datetime
from utils.history import save_comparison, load_recent_comparisons, _get_db, DB_PATH


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    test_db = tmp_path / "test_history.db"
    monkeypatch.setattr("utils.history.DB_PATH", test_db)
    yield test_db


class TestSaveComparison:
    """Tests for saving comparisons."""

    def test_save_single_comparison(self):
        """Test saving a single comparison."""
        data = {
            "scenario1_income": 50000,
            "scenario1_state": "Texas",
            "scenario1_year": 2020,
            "scenario1_tax_rate": 0.0,
            "scenario1_after_tax": 50000,
            "scenario2_income": 60000,
            "scenario2_state": "California",
            "scenario2_year": 2023,
            "scenario2_tax_rate": 6.0,
            "scenario2_after_tax": 56400,
            "cpi_factor": 1.15,
            "location_factor": 1.25,
            "purchasing_power_pct": 85.5,
            "scenario1_equivalent_after_tax": 65000,
            "gap": -8600,
            "generated_at": datetime.now().isoformat(),
        }
        save_comparison(data)

        history = load_recent_comparisons(limit=1)
        assert len(history) == 1
        assert history[0]["scenario1_income"] == 50000
        assert history[0]["scenario2_state"] == "California"

    def test_save_multiple_comparisons(self):
        """Test saving multiple comparisons."""
        for i in range(5):
            data = {
                "scenario1_income": 50000 + i * 1000,
                "scenario1_state": "Texas",
                "scenario1_year": 2020,
                "scenario1_tax_rate": 0.0,
                "scenario1_after_tax": 50000 + i * 1000,
                "scenario2_income": 60000,
                "scenario2_state": "California",
                "scenario2_year": 2023,
                "scenario2_tax_rate": 6.0,
                "scenario2_after_tax": 56400,
                "cpi_factor": 1.15,
                "location_factor": 1.25,
                "purchasing_power_pct": 85.5,
                "scenario1_equivalent_after_tax": 65000,
                "gap": -8600,
                "generated_at": datetime.now().isoformat(),
            }
            save_comparison(data)

        history = load_recent_comparisons(limit=10)
        assert len(history) == 5

    def test_save_with_null_values(self):
        """Test that saving with missing optional fields works."""
        data = {
            "scenario1_income": 50000,
            "scenario1_state": "Texas",
            "scenario1_year": 2020,
            "scenario1_tax_rate": 0.0,
            "scenario1_after_tax": 50000,
            "scenario2_income": 60000,
            "scenario2_state": "California",
            "scenario2_year": 2023,
            "scenario2_tax_rate": 6.0,
            "scenario2_after_tax": 56400,
            "cpi_factor": 1.15,
            "location_factor": 1.25,
            "purchasing_power_pct": 85.5,
            "scenario1_equivalent_after_tax": 65000,
            "gap": -8600,
            "generated_at": datetime.now().isoformat(),
        }
        save_comparison(data)
        history = load_recent_comparisons(limit=1)
        assert len(history) == 1


class TestLoadRecentComparisons:
    """Tests for loading comparisons."""

    def test_load_empty_database(self):
        """Test loading from empty database."""
        history = load_recent_comparisons()
        assert history == []

    def test_load_with_limit(self):
        """Test that limit parameter works correctly."""
        # Save 10 comparisons
        for i in range(10):
            data = {
                "scenario1_income": 50000 + i,
                "scenario1_state": "Texas",
                "scenario1_year": 2020,
                "scenario1_tax_rate": 0.0,
                "scenario1_after_tax": 50000,
                "scenario2_income": 60000,
                "scenario2_state": "California",
                "scenario2_year": 2023,
                "scenario2_tax_rate": 6.0,
                "scenario2_after_tax": 56400,
                "cpi_factor": 1.15,
                "location_factor": 1.25,
                "purchasing_power_pct": 85.5,
                "scenario1_equivalent_after_tax": 65000,
                "gap": -8600,
                "generated_at": datetime.now().isoformat(),
            }
            save_comparison(data)

        # Load only 3
        history = load_recent_comparisons(limit=3)
        assert len(history) == 3

    def test_load_returns_most_recent_first(self):
        """Test that most recent comparisons are returned first."""
        # Save comparisons with different incomes
        for i in range(5):
            data = {
                "scenario1_income": 10000 * (i + 1),
                "scenario1_state": "Texas",
                "scenario1_year": 2020,
                "scenario1_tax_rate": 0.0,
                "scenario1_after_tax": 50000,
                "scenario2_income": 60000,
                "scenario2_state": "California",
                "scenario2_year": 2023,
                "scenario2_tax_rate": 6.0,
                "scenario2_after_tax": 56400,
                "cpi_factor": 1.15,
                "location_factor": 1.25,
                "purchasing_power_pct": 85.5,
                "scenario1_equivalent_after_tax": 65000,
                "gap": -8600,
                "generated_at": datetime.now().isoformat(),
            }
            save_comparison(data)

        history = load_recent_comparisons(limit=10)
        # Most recent (last saved) should be first
        assert history[0]["scenario1_income"] == 50000
        assert history[-1]["scenario1_income"] == 10000

    def test_load_with_zero_limit(self):
        """Test loading with limit=0."""
        save_comparison({
            "scenario1_income": 50000,
            "scenario1_state": "Texas",
            "scenario1_year": 2020,
            "scenario1_tax_rate": 0.0,
            "scenario1_after_tax": 50000,
            "scenario2_income": 60000,
            "scenario2_state": "California",
            "scenario2_year": 2023,
            "scenario2_tax_rate": 6.0,
            "scenario2_after_tax": 56400,
            "cpi_factor": 1.15,
            "location_factor": 1.25,
            "purchasing_power_pct": 85.5,
            "scenario1_equivalent_after_tax": 65000,
            "gap": -8600,
            "generated_at": datetime.now().isoformat(),
        })

        history = load_recent_comparisons(limit=0)
        assert history == []

    def test_load_returns_all_fields(self):
        """Test that all fields are properly returned."""
        data = {
            "scenario1_income": 50000,
            "scenario1_state": "Texas",
            "scenario1_year": 2020,
            "scenario1_tax_rate": 0.0,
            "scenario1_after_tax": 50000,
            "scenario2_income": 60000,
            "scenario2_state": "California",
            "scenario2_year": 2023,
            "scenario2_tax_rate": 6.0,
            "scenario2_after_tax": 56400,
            "cpi_factor": 1.15,
            "location_factor": 1.25,
            "purchasing_power_pct": 85.5,
            "scenario1_equivalent_after_tax": 65000,
            "gap": -8600,
            "generated_at": datetime.now().isoformat(),
        }
        save_comparison(data)

        history = load_recent_comparisons(limit=1)
        result = history[0]

        # Check all expected fields are present
        expected_fields = [
            "id", "scenario1_income", "scenario1_state", "scenario1_year",
            "scenario1_tax_rate", "scenario1_after_tax",
            "scenario2_income", "scenario2_state", "scenario2_year",
            "scenario2_tax_rate", "scenario2_after_tax",
            "cpi_factor", "location_factor", "purchasing_power_pct",
            "scenario1_equivalent_after_tax", "gap", "generated_at",
        ]
        for field in expected_fields:
            assert field in result, f"Missing field: {field}"


class TestDatabaseOperations:
    """Tests for database operations."""

    def test_get_db_creates_table(self):
        """Test that _get_db creates the table if it doesn't exist."""
        conn = _get_db()
        # Check that table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='saved_comparisons'"
        )
        result = cursor.fetchone()
        conn.close()
        assert result is not None

    def test_get_db_is_idempotent(self):
        """Test that calling _get_db multiple times is safe."""
        conn1 = _get_db()
        conn1.close()
        conn2 = _get_db()
        conn2.close()
        # Should not raise any errors

    def test_database_persists_data(self):
        """Test that data persists across connections."""
        data = {
            "scenario1_income": 50000,
            "scenario1_state": "Texas",
            "scenario1_year": 2020,
            "scenario1_tax_rate": 0.0,
            "scenario1_after_tax": 50000,
            "scenario2_income": 60000,
            "scenario2_state": "California",
            "scenario2_year": 2023,
            "scenario2_tax_rate": 6.0,
            "scenario2_after_tax": 56400,
            "cpi_factor": 1.15,
            "location_factor": 1.25,
            "purchasing_power_pct": 85.5,
            "scenario1_equivalent_after_tax": 65000,
            "gap": -8600,
            "generated_at": datetime.now().isoformat(),
        }
        save_comparison(data)

        # Close and reopen connection
        conn = _get_db()
        conn.close()

        # Data should still be there
        history = load_recent_comparisons(limit=10)
        assert len(history) == 1


class TestEdgeCases:
    """Tests for edge cases."""

    def test_extreme_values(self):
        """Test with extreme comparison values."""
        data = {
            "scenario1_income": 999_999_999,
            "scenario1_state": "Texas",
            "scenario1_year": 1990,
            "scenario1_tax_rate": 0.0,
            "scenario1_after_tax": 999_999_999,
            "scenario2_income": 1,
            "scenario2_state": "California",
            "scenario2_year": 2025,
            "scenario2_tax_rate": 13.3,
            "scenario2_after_tax": 0.87,
            "cpi_factor": 10.5,
            "location_factor": 2.5,
            "purchasing_power_pct": 0.00001,
            "scenario1_equivalent_after_tax": 26_249_999_973.75,
            "gap": -26_249_999_972.88,
            "generated_at": datetime.now().isoformat(),
        }
        save_comparison(data)

        history = load_recent_comparisons(limit=1)
        assert len(history) == 1
        assert history[0]["scenario1_income"] == 999_999_999

    def test_negative_gap(self):
        """Test with negative gap values."""
        data = {
            "scenario1_income": 100000,
            "scenario1_state": "Texas",
            "scenario1_year": 2020,
            "scenario1_tax_rate": 0.0,
            "scenario1_after_tax": 100000,
            "scenario2_income": 60000,
            "scenario2_state": "California",
            "scenario2_year": 2023,
            "scenario2_tax_rate": 6.0,
            "scenario2_after_tax": 56400,
            "cpi_factor": 1.15,
            "location_factor": 1.25,
            "purchasing_power_pct": 50.0,
            "scenario1_equivalent_after_tax": 143750,
            "gap": -87350,
            "generated_at": datetime.now().isoformat(),
        }
        save_comparison(data)

        history = load_recent_comparisons(limit=1)
        assert history[0]["gap"] == -87350

    def test_special_characters_in_state_names(self):
        """Test with state names containing special characters."""
        data = {
            "scenario1_income": 50000,
            "scenario1_state": "District of Columbia",
            "scenario1_year": 2020,
            "scenario1_tax_rate": 8.5,
            "scenario1_after_tax": 45750,
            "scenario2_income": 60000,
            "scenario2_state": "New York",
            "scenario2_year": 2023,
            "scenario2_tax_rate": 6.85,
            "scenario2_after_tax": 55890,
            "cpi_factor": 1.15,
            "location_factor": 1.05,
            "purchasing_power_pct": 95.0,
            "scenario1_equivalent_after_tax": 55368.75,
            "gap": 521.25,
            "generated_at": datetime.now().isoformat(),
        }
        save_comparison(data)

        history = load_recent_comparisons(limit=1)
        assert history[0]["scenario1_state"] == "District of Columbia"
        assert history[0]["scenario2_state"] == "New York"
