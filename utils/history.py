"""Comparison history - save and load past comparisons from SQLite."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "cache.db"


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS saved_comparisons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario1_income REAL,
            scenario1_state TEXT,
            scenario1_year INTEGER,
            scenario1_tax_rate REAL,
            scenario1_after_tax REAL,
            scenario2_income REAL,
            scenario2_state TEXT,
            scenario2_year INTEGER,
            scenario2_tax_rate REAL,
            scenario2_after_tax REAL,
            cpi_factor REAL,
            location_factor REAL,
            purchasing_power_pct REAL,
            scenario1_equivalent_after_tax REAL,
            gap REAL,
            generated_at TEXT
        )"""
    )
    conn.commit()
    return conn


def save_comparison(data: dict) -> None:
    """Save a comparison result to the database."""
    conn = _get_db()
    conn.execute(
        """INSERT INTO saved_comparisons (
            scenario1_income, scenario1_state, scenario1_year,
            scenario1_tax_rate, scenario1_after_tax,
            scenario2_income, scenario2_state, scenario2_year,
            scenario2_tax_rate, scenario2_after_tax,
            cpi_factor, location_factor, purchasing_power_pct,
            scenario1_equivalent_after_tax, gap, generated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["scenario1_income"],
            data["scenario1_state"],
            data["scenario1_year"],
            data["scenario1_tax_rate"],
            data["scenario1_after_tax"],
            data["scenario2_income"],
            data["scenario2_state"],
            data["scenario2_year"],
            data["scenario2_tax_rate"],
            data["scenario2_after_tax"],
            data["cpi_factor"],
            data["location_factor"],
            data["purchasing_power_pct"],
            data["scenario1_equivalent_after_tax"],
            data["gap"],
            data["generated_at"],
        ),
    )
    conn.commit()
    conn.close()


def load_recent_comparisons(limit: int = 10) -> list[dict]:
    """Load the most recent comparisons from the database."""
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM saved_comparisons ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()

    columns = [
        "id", "scenario1_income", "scenario1_state", "scenario1_year",
        "scenario1_tax_rate", "scenario1_after_tax",
        "scenario2_income", "scenario2_state", "scenario2_year",
        "scenario2_tax_rate", "scenario2_after_tax",
        "cpi_factor", "location_factor", "purchasing_power_pct",
        "scenario1_equivalent_after_tax", "gap", "generated_at",
    ]
    return [dict(zip(columns, row)) for row in rows]
