"""Tests for the CPI fetcher module."""

import json
import sqlite3
from unittest.mock import patch, MagicMock
import pytest
import requests
from data.cpi_fetcher import (
    _parse_annual_averages,
    _fetch_from_bls,
    get_inflation_factor,
    get_cpi,
    _get_db,
    _get_all_cached,
    _cache_values,
    _get_cached,
    _FALLBACK_CPI,
    populate_cpi_cache,
    DB_PATH,
)


# Sample BLS API response
SAMPLE_BLS_RESPONSE = {
    "status": "REQUEST_SUCCEEDED",
    "Results": {
        "series": [
            {
                "seriesID": "CUUR0000SA0",
                "data": [
                    {"year": "2023", "period": "M13", "value": "304.702"},
                    {"year": "2023", "period": "M12", "value": "306.746"},
                    {"year": "2022", "period": "M13", "value": "292.655"},
                    {"year": "2022", "period": "M12", "value": "296.797"},
                    {"year": "2000", "period": "M13", "value": "172.200"},
                    {"year": "1997", "period": "M13", "value": "160.525"},
                ],
            }
        ]
    },
}


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    test_db = tmp_path / "test_cache.db"
    monkeypatch.setattr("data.cpi_fetcher.DB_PATH", test_db)
    yield test_db


class TestParseAnnualAverages:
    def test_extracts_m13_entries(self):
        result = _parse_annual_averages(SAMPLE_BLS_RESPONSE)
        assert result[2023] == pytest.approx(304.702)
        assert result[2022] == pytest.approx(292.655)
        assert result[2000] == pytest.approx(172.200)

    def test_ignores_monthly_entries(self):
        result = _parse_annual_averages(SAMPLE_BLS_RESPONSE)
        # M12 entries should not create duplicate year entries
        # The M13 value should win
        assert result[2023] == pytest.approx(304.702)

    def test_empty_response(self):
        result = _parse_annual_averages({"Results": {"series": []}})
        assert result == {}

    def test_missing_results(self):
        result = _parse_annual_averages({})
        assert result == {}


class TestCacheOperations:
    def test_cache_and_retrieve(self):
        _cache_values({2020: 258.811, 2021: 270.970})
        assert _get_cached(2020) == pytest.approx(258.811)
        assert _get_cached(2021) == pytest.approx(270.970)

    def test_cache_miss_returns_none(self):
        assert _get_cached(1900) is None

    def test_cache_overwrite(self):
        _cache_values({2020: 100.0})
        _cache_values({2020: 200.0})
        assert _get_cached(2020) == pytest.approx(200.0)


class TestGetInflationFactor:
    def test_same_year_returns_one(self):
        _cache_values({2020: 258.811})
        factor = get_inflation_factor(2020, 2020)
        assert factor == pytest.approx(1.0)

    def test_inflation_increases(self):
        _cache_values({2000: 172.200, 2023: 304.702})
        factor = get_inflation_factor(2000, 2023)
        assert factor > 1.0
        assert factor == pytest.approx(304.702 / 172.200)

    def test_deflation_direction(self):
        _cache_values({2000: 172.200, 2023: 304.702})
        factor = get_inflation_factor(2023, 2000)
        assert factor < 1.0

    def test_known_calculation(self):
        # $1 in 1997 ≈ $1.90 in 2023
        _cache_values({1997: 160.525, 2023: 304.702})
        factor = get_inflation_factor(1997, 2023)
        assert factor == pytest.approx(304.702 / 160.525)


class TestGetCpi:
    def test_returns_cached_value(self):
        _cache_values({2020: 258.811})
        assert get_cpi(2020) == pytest.approx(258.811)

    @patch("data.cpi_fetcher.populate_cpi_cache")
    def test_fetches_when_not_cached(self, mock_populate):
        """When not cached and not in fallback, it calls populate and then reads cache."""
        def side_effect(*args, **kwargs):
            _cache_values({1991: 136.200})
        mock_populate.side_effect = side_effect

        # Use a year where fallback is NOT checked (clear it temporarily)
        from data.cpi_fetcher import _FALLBACK_CPI
        original = _FALLBACK_CPI.pop(1991, None)
        try:
            result = get_cpi(1991)
            assert result == pytest.approx(136.200)
            mock_populate.assert_called_once()
        finally:
            if original is not None:
                _FALLBACK_CPI[1991] = original

    @patch("data.cpi_fetcher.populate_cpi_cache")
    def test_raises_when_unavailable(self, mock_populate):
        mock_populate.return_value = None  # doesn't cache anything
        with pytest.raises(ValueError, match="No CPI data"):
            get_cpi(1800)

    def test_uses_fallback_when_not_cached(self):
        """get_cpi should use _FALLBACK_CPI for known years without API call."""
        result = get_cpi(2020)
        assert result == pytest.approx(_FALLBACK_CPI[2020])


class TestGetAllCached:
    def test_empty_initially(self):
        assert _get_all_cached() == {}

    def test_returns_all(self):
        _cache_values({2020: 258.8, 2021: 271.0})
        result = _get_all_cached()
        assert len(result) == 2
        assert result[2020] == pytest.approx(258.8)


class TestFetchFromBls:
    @patch("data.cpi_fetcher.requests.post")
    def test_successful_fetch(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_BLS_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = _fetch_from_bls(2020, 2023)
        assert result["status"] == "REQUEST_SUCCEEDED"
        mock_post.assert_called_once()

    @patch("data.cpi_fetcher.requests.post")
    def test_api_key_included(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_BLS_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        _fetch_from_bls(2020, 2023, api_key="test_key")
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["registrationkey"] == "test_key"

    @patch("data.cpi_fetcher.requests.post")
    def test_failed_status_raises(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "REQUEST_FAILED", "message": ["bad"]}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        with pytest.raises(RuntimeError, match="BLS API error"):
            _fetch_from_bls(2020, 2023)

    @patch("data.cpi_fetcher.requests.post")
    def test_http_error_raises(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("no network")
        with pytest.raises(requests.exceptions.ConnectionError):
            _fetch_from_bls(2020, 2023)


class TestPopulateCpiCache:
    @patch("data.cpi_fetcher._fetch_from_bls")
    def test_successful_populate(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_BLS_RESPONSE
        populate_cpi_cache(start_year=2022, end_year=2023)
        assert _get_cached(2023) == pytest.approx(304.702)
        assert _get_cached(2022) == pytest.approx(292.655)

    @patch("data.cpi_fetcher._fetch_from_bls")
    def test_api_failure_uses_fallback(self, mock_fetch):
        mock_fetch.side_effect = RuntimeError("API down")
        populate_cpi_cache(start_year=2020, end_year=2023)
        # Should have loaded fallback data
        assert _get_cached(2020) is not None
