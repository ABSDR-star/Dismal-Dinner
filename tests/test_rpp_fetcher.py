"""Tests for the RPP fetcher module."""

import pytest
from data.rpp_fetcher import (
    normalize_state,
    get_rpp,
    get_location_factor,
    get_all_states,
    populate_rpp_cache,
    load_rpp_from_excel,
    _FALLBACK_RPP,
    _get_db,
    DB_PATH,
)


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    test_db = tmp_path / "test_cache.db"
    monkeypatch.setattr("data.rpp_fetcher.DB_PATH", test_db)
    yield test_db


class TestNormalizeState:
    def test_full_name(self):
        assert normalize_state("California") == "California"

    def test_abbreviation(self):
        assert normalize_state("CA") == "California"

    def test_lowercase(self):
        assert normalize_state("california") == "California"

    def test_abbreviation_lowercase(self):
        assert normalize_state("tx") == "Texas"

    def test_with_whitespace(self):
        assert normalize_state("  New York  ") == "New York"

    def test_dc(self):
        assert normalize_state("DC") == "District of Columbia"

    def test_dc_full(self):
        assert normalize_state("District of Columbia") == "District of Columbia"

    def test_unknown_state_raises(self):
        with pytest.raises(ValueError, match="Unknown state"):
            normalize_state("Narnia")


class TestGetRpp:
    def test_fallback_data(self):
        """Without cache, should fall back to embedded data."""
        rpp = get_rpp("California")
        assert rpp == pytest.approx(113.2)

    def test_abbreviation_input(self):
        rpp = get_rpp("CA")
        assert rpp == pytest.approx(113.2)

    def test_populated_cache(self):
        populate_rpp_cache()
        rpp = get_rpp("Mississippi")
        assert rpp == pytest.approx(84.8)

    def test_cheapest_state(self):
        rpp = get_rpp("MS")
        assert rpp < 90.0

    def test_expensive_state(self):
        rpp = get_rpp("HI")
        assert rpp > 115.0

    def test_with_specific_year_cached(self):
        populate_rpp_cache()
        rpp = get_rpp("California", year=2022)
        assert rpp == pytest.approx(113.2)

    def test_with_missing_year_falls_to_latest(self):
        populate_rpp_cache()
        rpp = get_rpp("California", year=1995)
        # No 1995 data, falls back to latest (2022)
        assert rpp == pytest.approx(113.2)

    def test_no_cache_uses_fallback(self):
        """Without populating cache, fallback dict is used."""
        rpp = get_rpp("Texas")
        assert rpp == pytest.approx(_FALLBACK_RPP["Texas"])


class TestLoadRppFromExcel:
    def test_missing_file_returns_empty(self):
        from pathlib import Path
        result = load_rpp_from_excel(Path("nonexistent.xlsx"))
        assert result == {}


class TestPopulateRppCache:
    def test_populates_all_states(self):
        populate_rpp_cache()
        conn = _get_db()
        count = conn.execute("SELECT COUNT(*) FROM rpp").fetchone()[0]
        conn.close()
        assert count == 51  # 50 states + DC


class TestGetLocationFactor:
    def test_same_state_returns_one(self):
        factor = get_location_factor("California", "California")
        assert factor == pytest.approx(1.0)

    def test_cheaper_to_expensive(self):
        factor = get_location_factor("Mississippi", "California")
        assert factor > 1.0  # CA is more expensive than MS

    def test_expensive_to_cheaper(self):
        factor = get_location_factor("California", "Mississippi")
        assert factor < 1.0

    def test_known_ratio(self):
        # CA=113.2, MS=84.8
        factor = get_location_factor("MS", "CA")
        assert factor == pytest.approx(113.2 / 84.8)

    def test_with_abbreviations(self):
        factor = get_location_factor("TX", "NY")
        expected = _FALLBACK_RPP["New York"] / _FALLBACK_RPP["Texas"]
        assert factor == pytest.approx(expected)


class TestGetAllStates:
    def test_returns_all_states(self):
        states = get_all_states()
        assert len(states) == 51  # 50 states + DC

    def test_sorted(self):
        states = get_all_states()
        assert states == sorted(states)

    def test_includes_dc(self):
        states = get_all_states()
        assert "District of Columbia" in states
