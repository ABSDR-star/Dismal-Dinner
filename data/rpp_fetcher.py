"""RPP data module - Regional Price Parities from BEA."""

import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent / "cache.db"

# BEA publishes RPP data as Excel files. We expect the file at this path:
RPP_EXCEL_PATH = Path(__file__).parent / "rpp_data.xlsx"

# Fallback: embedded average RPP values (2022 data) for all 50 states + DC
# Source: Bureau of Economic Analysis, Regional Price Parities by State
# Index where 100 = national average
_FALLBACK_RPP: dict[str, float] = {
    "Alabama": 87.1, "Alaska": 104.2, "Arizona": 97.5, "Arkansas": 86.5,
    "California": 113.2, "Colorado": 104.1, "Connecticut": 108.5,
    "Delaware": 100.3, "Florida": 100.4, "Georgia": 93.2,
    "Hawaii": 119.2, "Idaho": 95.4, "Illinois": 98.0, "Indiana": 90.4,
    "Iowa": 89.4, "Kansas": 90.0, "Kentucky": 88.4, "Louisiana": 89.7,
    "Maine": 98.3, "Maryland": 109.0, "Massachusetts": 110.1,
    "Michigan": 92.4, "Minnesota": 97.0, "Mississippi": 84.8,
    "Missouri": 88.8, "Montana": 95.5, "Nebraska": 90.4, "Nevada": 98.0,
    "New Hampshire": 106.8, "New Jersey": 113.0, "New Mexico": 92.5,
    "New York": 115.5, "North Carolina": 93.5, "North Dakota": 91.3,
    "Ohio": 90.1, "Oklahoma": 88.1, "Oregon": 100.4, "Pennsylvania": 97.4,
    "Rhode Island": 100.2, "South Carolina": 91.0, "South Dakota": 90.2,
    "Tennessee": 90.5, "Texas": 96.2, "Utah": 97.8, "Vermont": 101.9,
    "Virginia": 103.7, "Washington": 106.7, "West Virginia": 86.7,
    "Wisconsin": 93.1, "Wyoming": 95.1,
    "District of Columbia": 117.2,
}

# State abbreviation to full name mapping
_STATE_ABBR: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut",
    "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana",
    "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts",
    "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota",
    "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}


def _get_db() -> sqlite3.Connection:
    """Return a connection to the SQLite cache database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rpp (
            year INTEGER NOT NULL,
            state TEXT NOT NULL,
            rpp_index REAL NOT NULL,
            PRIMARY KEY (year, state)
        )"""
    )
    conn.commit()
    return conn


def normalize_state(state: str) -> str:
    """Normalize a state name or abbreviation to its full name."""
    upper = state.strip().upper()
    if upper in _STATE_ABBR:
        return _STATE_ABBR[upper]
    # Try title-cased match
    title = state.strip().title()
    if title in _FALLBACK_RPP:
        return title
    # Special case
    if upper in ("DC", "DISTRICT OF COLUMBIA"):
        return "District of Columbia"
    raise ValueError(f"Unknown state: {state}")


def load_rpp_from_excel(excel_path: Path | None = None) -> dict[str, dict[int, float]]:
    """Parse BEA RPP Excel file into {state: {year: rpp_index}} dict."""
    path = excel_path or RPP_EXCEL_PATH
    if not path.exists():
        return {}

    df = pd.read_excel(path, sheet_name=0, header=None)
    # BEA files vary in format; we look for rows where first column is a state name
    results: dict[str, dict[int, float]] = {}

    # Try to find the header row with years
    header_row = None
    for idx, row in df.iterrows():
        vals = [str(v).strip() for v in row.values if pd.notna(v)]
        # Look for a row that contains year-like numbers
        year_count = sum(1 for v in vals if v.isdigit() and 1990 <= int(v) <= 2030)
        if year_count >= 3:
            header_row = idx
            break

    if header_row is None:
        return {}

    years = []
    for v in df.iloc[header_row]:
        if pd.notna(v):
            s = str(v).strip()
            if s.isdigit() and 1990 <= int(s) <= 2030:
                years.append(int(s))
            else:
                years.append(None)
        else:
            years.append(None)

    for idx in range(header_row + 1, len(df)):
        row = df.iloc[idx]
        state_name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        try:
            state_name = normalize_state(state_name)
        except ValueError:
            continue

        state_data = {}
        for col_idx, year in enumerate(years):
            if year is not None and col_idx < len(row):
                val = row.iloc[col_idx]
                if pd.notna(val):
                    try:
                        state_data[year] = float(val)
                    except (ValueError, TypeError):
                        pass
        if state_data:
            results[state_name] = state_data

    return results


def populate_rpp_cache(excel_path: Path | None = None) -> None:
    """Load RPP data from Excel or fallback and store in SQLite cache."""
    conn = _get_db()

    excel_data = load_rpp_from_excel(excel_path)
    if excel_data:
        for state, year_data in excel_data.items():
            for year, rpp_val in year_data.items():
                conn.execute(
                    "INSERT OR REPLACE INTO rpp (year, state, rpp_index) VALUES (?, ?, ?)",
                    (year, state, rpp_val),
                )
    else:
        # Use fallback data (keyed to year 2022)
        for state, rpp_val in _FALLBACK_RPP.items():
            conn.execute(
                "INSERT OR REPLACE INTO rpp (year, state, rpp_index) VALUES (?, ?, ?)",
                (2022, state, rpp_val),
            )

    conn.commit()
    conn.close()


def get_rpp(state: str, year: int | None = None) -> float:
    """Get the RPP index for a state. If no year-specific data, returns latest available."""
    state = normalize_state(state)
    conn = _get_db()

    if year is not None:
        row = conn.execute(
            "SELECT rpp_index FROM rpp WHERE state = ? AND year = ?",
            (state, year),
        ).fetchone()
        if row:
            conn.close()
            return row[0]

    # Fall back to latest available year for this state
    row = conn.execute(
        "SELECT rpp_index FROM rpp WHERE state = ? ORDER BY year DESC LIMIT 1",
        (state,),
    ).fetchone()
    conn.close()

    if row:
        return row[0]

    # Last resort: fallback dict
    if state in _FALLBACK_RPP:
        return _FALLBACK_RPP[state]

    raise ValueError(f"No RPP data available for {state}")


def get_location_factor(state1: str, state2: str, year: int | None = None) -> float:
    """Calculate location cost factor from state1 to state2.

    Returns a multiplier: values > 1 mean state2 is more expensive.
    Example: CA (113.2) vs MS (84.8) → 113.2/84.8 ≈ 1.335
    """
    rpp1 = get_rpp(state1, year)
    rpp2 = get_rpp(state2, year)
    return rpp2 / rpp1


def get_all_states() -> list[str]:
    """Return a sorted list of all state names."""
    return sorted(_FALLBACK_RPP.keys())
