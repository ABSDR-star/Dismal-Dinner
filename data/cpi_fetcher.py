"""CPI data module - fetches and caches BLS Consumer Price Index data."""

import os
import sqlite3
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(__file__).parent / "cache.db"

# BLS API v2 endpoint
BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
# CPI-U All Items (seasonally adjusted)
CPI_SERIES_ID = "CUUR0000SA0"

# Fallback CPI-U annual averages (source: BLS)
# Used when API is unavailable or no key is configured
_FALLBACK_CPI: dict[int, float] = {
    1990: 130.7, 1991: 136.2, 1992: 140.3, 1993: 144.5, 1994: 148.2,
    1995: 152.4, 1996: 156.9, 1997: 160.5, 1998: 163.0, 1999: 166.6,
    2000: 172.2, 2001: 177.1, 2002: 179.9, 2003: 184.0, 2004: 188.9,
    2005: 195.3, 2006: 201.6, 2007: 207.3, 2008: 215.3, 2009: 214.5,
    2010: 218.1, 2011: 224.9, 2012: 229.6, 2013: 233.0, 2014: 236.7,
    2015: 237.0, 2016: 240.0, 2017: 245.1, 2018: 251.1, 2019: 255.7,
    2020: 258.8, 2021: 271.0, 2022: 292.7, 2023: 304.7, 2024: 313.0,
    2025: 319.0,
}


def _get_db() -> sqlite3.Connection:
    """Return a connection to the SQLite cache database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS cpi (
            year INTEGER PRIMARY KEY,
            annual_avg REAL NOT NULL
        )"""
    )
    conn.commit()
    return conn


def _fetch_from_bls(start_year: int, end_year: int, api_key: str | None = None) -> dict:
    """Fetch CPI data from the BLS API. Returns parsed JSON response."""
    headers = {"Content-Type": "application/json"}
    payload = {
        "seriesid": [CPI_SERIES_ID],
        "startyear": str(start_year),
        "endyear": str(end_year),
    }
    if api_key:
        payload["registrationkey"] = api_key

    resp = requests.post(BLS_API_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "REQUEST_SUCCEEDED":
        msg = data.get("message", ["Unknown BLS API error"])
        raise RuntimeError(f"BLS API error: {msg}")

    return data


def _parse_annual_averages(bls_data: dict) -> dict[int, float]:
    """Extract annual average CPI values from BLS response."""
    results = {}
    for series in bls_data.get("Results", {}).get("series", []):
        for item in series.get("data", []):
            # BLS marks annual averages with period "M13"
            if item.get("period") == "M13":
                year = int(item["year"])
                value = float(item["value"])
                results[year] = value
    return results


def _cache_values(values: dict[int, float]) -> None:
    """Store CPI values in the SQLite cache."""
    conn = _get_db()
    for year, val in values.items():
        conn.execute(
            "INSERT OR REPLACE INTO cpi (year, annual_avg) VALUES (?, ?)",
            (year, val),
        )
    conn.commit()
    conn.close()


def _get_cached(year: int) -> float | None:
    """Retrieve a single year's CPI from cache."""
    conn = _get_db()
    row = conn.execute(
        "SELECT annual_avg FROM cpi WHERE year = ?", (year,)
    ).fetchone()
    conn.close()
    return row[0] if row else None


def _get_all_cached() -> dict[int, float]:
    """Return all cached CPI values."""
    conn = _get_db()
    rows = conn.execute("SELECT year, annual_avg FROM cpi").fetchall()
    conn.close()
    return {year: val for year, val in rows}


def populate_cpi_cache(
    start_year: int = 1990,
    end_year: int = 2025,
    api_key: str | None = None,
) -> None:
    """Fetch CPI data from BLS and store in local cache.

    Falls back to embedded data if the API is unavailable.
    BLS API limits requests to 20-year spans, so we chunk if needed.
    """
    if api_key is None:
        api_key = os.environ.get("BLS_API_KEY")

    try:
        chunk_size = 20
        for chunk_start in range(start_year, end_year + 1, chunk_size):
            chunk_end = min(chunk_start + chunk_size - 1, end_year)
            data = _fetch_from_bls(chunk_start, chunk_end, api_key)
            values = _parse_annual_averages(data)
            _cache_values(values)
    except Exception:
        # API failed — seed cache with fallback data
        _cache_values(_FALLBACK_CPI)


def get_cpi(year: int) -> float:
    """Get the CPI annual average for a given year. Uses cache, then fallback."""
    cached = _get_cached(year)
    if cached is not None:
        return cached

    # Check fallback data first (instant, no network)
    if year in _FALLBACK_CPI:
        _cache_values({year: _FALLBACK_CPI[year]})
        return _FALLBACK_CPI[year]

    # Try fetching from BLS API
    try:
        populate_cpi_cache(start_year=year, end_year=year)
    except Exception:
        pass

    cached = _get_cached(year)
    if cached is None:
        raise ValueError(f"No CPI data available for {year}")
    return cached


def get_inflation_factor(year1: int, year2: int) -> float:
    """Calculate the inflation factor from year1 to year2.

    Returns a multiplier: multiply year1 dollars by this to get year2 dollars.
    A value > 1 means prices increased (inflation).
    """
    cpi1 = get_cpi(year1)
    cpi2 = get_cpi(year2)
    return cpi2 / cpi1
