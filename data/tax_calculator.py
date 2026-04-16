"""Tax calculator module - state income tax effective rates."""

import csv
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "cache.db"
TAX_CSV_PATH = Path(__file__).parent / "tax_data.csv"


def _get_db() -> sqlite3.Connection:
    """Return a connection to the SQLite cache database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS taxes (
            state TEXT NOT NULL,
            bracket_min INTEGER NOT NULL,
            bracket_max INTEGER NOT NULL,
            effective_rate REAL NOT NULL,
            PRIMARY KEY (state, bracket_min)
        )"""
    )
    conn.commit()
    return conn


def populate_tax_cache(csv_path: Path | None = None) -> None:
    """Load tax data from CSV into SQLite cache."""
    path = csv_path or TAX_CSV_PATH
    conn = _get_db()

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute(
                "INSERT OR REPLACE INTO taxes (state, bracket_min, bracket_max, effective_rate) "
                "VALUES (?, ?, ?, ?)",
                (
                    row["state"].strip(),
                    int(row["bracket_min"]),
                    int(row["bracket_max"]),
                    float(row["effective_rate"]),
                ),
            )
    conn.commit()
    conn.close()


def get_effective_tax_rate(state: str, income: float) -> float:
    """Get the effective state income tax rate for a given state and income.

    Returns the rate as a percentage (e.g., 5.0 for 5%).
    Looks up the bracket that contains the given income.
    """
    from data.rpp_fetcher import normalize_state

    state = normalize_state(state)
    conn = _get_db()

    # Check if we have data cached
    row = conn.execute(
        "SELECT effective_rate FROM taxes WHERE state = ? AND bracket_min <= ? AND bracket_max >= ? "
        "ORDER BY bracket_min DESC LIMIT 1",
        (state, int(income), int(income)),
    ).fetchone()

    if row is None:
        # Try loading from CSV first
        conn.close()
        populate_tax_cache()
        conn = _get_db()
        row = conn.execute(
            "SELECT effective_rate FROM taxes WHERE state = ? AND bracket_min <= ? AND bracket_max >= ? "
            "ORDER BY bracket_min DESC LIMIT 1",
            (state, int(income), int(income)),
        ).fetchone()

    conn.close()

    if row is None:
        raise ValueError(f"No tax data for {state} at income ${income:,.0f}")

    return row[0]


def get_after_tax_income(state: str, income: float) -> float:
    """Calculate after-tax income given state and gross income.

    Returns the income after applying the effective state income tax rate.
    This is a simplified calculation using effective rates, not marginal brackets.
    """
    rate = get_effective_tax_rate(state, income)
    return income * (1 - rate / 100)


def get_tax_impact(state1: str, income1: float, state2: str, income2: float) -> dict:
    """Compare tax impact between two scenarios.

    Returns a dict with rates, after-tax incomes, and the difference.
    """
    rate1 = get_effective_tax_rate(state1, income1)
    rate2 = get_effective_tax_rate(state2, income2)
    after_tax1 = income1 * (1 - rate1 / 100)
    after_tax2 = income2 * (1 - rate2 / 100)

    return {
        "state1_rate": rate1,
        "state2_rate": rate2,
        "state1_after_tax": after_tax1,
        "state2_after_tax": after_tax2,
        "rate_difference": rate2 - rate1,
    }
