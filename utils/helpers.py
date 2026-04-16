"""Utility helper functions."""

from datetime import datetime


def format_currency(amount: float) -> str:
    """Format a number as USD currency."""
    return f"${amount:,.2f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a number as a percentage string."""
    return f"{value:.{decimals}f}%"


def current_year() -> int:
    """Return the current calendar year."""
    return datetime.now().year


def clamp_year(year: int, min_year: int = 1990, max_year: int | None = None) -> int:
    """Clamp a year to valid range."""
    if max_year is None:
        max_year = current_year()
    return max(min_year, min(year, max_year))
