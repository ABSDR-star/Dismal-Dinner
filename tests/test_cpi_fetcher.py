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

    @patch("data.cpi_fetcher._fetch_from_bls")
    def test_multi_year_chunking(self, mock_fetch):
        """Test that large year ranges are chunked properly."""
        mock_fetch.return_value = SAMPLE_BLS_RESPONSE
        populate_cpi_cache(start_year=1990, end_year=2023)
        # Should have been called multiple times for 33 year range
        assert mock_fetch.call_count >= 2

    @patch("data.cpi_fetcher._fetch_from_bls")
    def test_with_api_key(self, mock_fetch):
        """Test that API key is passed correctly."""
        mock_fetch.return_value = SAMPLE_BLS_RESPONSE
        populate_cpi_cache(start_year=2020, end_year=2023, api_key="test_key")
        # Verify API key was used - it's passed as the 3rd positional argument
        assert mock_fetch.called
        # Check the call arguments
        call_args = mock_fetch.call_args_list[0]
        # Args are (start_year, end_year, api_key)
        assert len(call_args[0]) == 3
        assert call_args[0][2] == "test_key"


class TestDatabaseOperations:
    """Tests for database connection and operations."""

    def test_db_creation_is_idempotent(self):
        """Test that creating DB multiple times is safe."""
        conn1 = _get_db()
        conn1.close()
        conn2 = _get_db()
        conn2.close()
        # Should not raise any errors

    def test_cache_values_empty_dict(self):
        """Test caching an empty dictionary."""
        _cache_values({})
        # Should not raise errors
        assert _get_all_cached() == {}

    def test_get_all_cached_after_multiple_inserts(self):
        """Test retrieving all values after multiple cache operations."""
        _cache_values({2020: 258.8})
        _cache_values({2021: 271.0})
        _cache_values({2022: 292.7})
        all_cached = _get_all_cached()
        assert len(all_cached) == 3
        assert 2020 in all_cached
        assert 2021 in all_cached
        assert 2022 in all_cached


class TestInflationFactorEdgeCases:
    """Tests for edge cases in inflation factor calculation."""

    def test_extreme_inflation(self):
        """Test with very high inflation scenario."""
        _cache_values({1990: 100.0, 2023: 500.0})
        factor = get_inflation_factor(1990, 2023)
        assert factor == pytest.approx(5.0)

    def test_deflation_scenario(self):
        """Test when prices go down (rare but possible)."""
        _cache_values({2020: 260.0, 2021: 255.0})
        factor = get_inflation_factor(2020, 2021)
        assert factor < 1.0
        assert factor == pytest.approx(255.0 / 260.0)

    def test_adjacent_years(self):
        """Test inflation between consecutive years."""
        _cache_values({2022: 292.7, 2023: 304.7})
        factor = get_inflation_factor(2022, 2023)
        assert factor > 1.0
        assert factor == pytest.approx(304.7 / 292.7)


class TestGetCpiEdgeCases:
    """Tests for edge cases in get_cpi function."""

    def test_get_cpi_uses_cached_before_fallback(self):
        """Test that cached value takes precedence over fallback."""
        # Cache a different value than fallback
        _cache_values({2020: 999.99})
        result = get_cpi(2020)
        assert result == pytest.approx(999.99)
        assert result != _FALLBACK_CPI[2020]

    @patch("data.cpi_fetcher.populate_cpi_cache")
    def test_get_cpi_handles_populate_failure(self, mock_populate):
        """Test that get_cpi handles populate failures gracefully."""
        mock_populate.side_effect = Exception("Network error")
        # Should fall back to _FALLBACK_CPI
        result = get_cpi(2020)
        assert result == pytest.approx(_FALLBACK_CPI[2020])

    def test_get_cpi_missing_year_no_fallback(self):
        """Test error when year is not in cache or fallback."""
        with pytest.raises(ValueError, match="No CPI data"):
            get_cpi(1800)


class TestFetchFromBlsEdgeCases:
    """Tests for edge cases in BLS API fetching."""

    @patch("data.cpi_fetcher.requests.post")
    def test_timeout_handling(self, mock_post):
        """Test that timeouts are handled properly."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
        with pytest.raises(requests.exceptions.Timeout):
            _fetch_from_bls(2020, 2023)

    @patch("data.cpi_fetcher.requests.post")
    def test_malformed_json_response(self, mock_post):
        """Test handling of malformed JSON response."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_resp

        with pytest.raises(ValueError):
            _fetch_from_bls(2020, 2023)

    @patch("data.cpi_fetcher.requests.post")
    def test_empty_message_in_error(self, mock_post):
        """Test error handling when BLS returns error without message."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "REQUEST_FAILED"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        with pytest.raises(RuntimeError, match="BLS API error"):
            _fetch_from_bls(2020, 2023)
