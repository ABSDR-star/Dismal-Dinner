"""Core comparison engine - combines CPI, RPP, and Tax factors."""

from data.cpi_fetcher import get_inflation_factor, get_cpi
from data.rpp_fetcher import get_location_factor, get_rpp, normalize_state
from data.tax_calculator import get_effective_tax_rate, get_after_tax_income


def compare_lifestyles(
    income1: float,
    state1: str,
    year1: int,
    income2: float,
    state2: str,
    year2: int,
) -> dict:
    """Compare real purchasing power between two scenarios.

    Scenario 1: earning income1 in state1 during year1
    Scenario 2: earning income2 in state2 during year2

    Returns a dict with the overall comparison and factor-by-factor breakdown.
    """
    if income1 <= 0 or income2 <= 0:
        raise ValueError("Income must be positive")
    if not (1990 <= year1 <= 2025):
        raise ValueError(f"Year {year1} outside supported range (1990–2025)")
    if not (1990 <= year2 <= 2025):
        raise ValueError(f"Year {year2} outside supported range (1990–2025)")

    state1 = normalize_state(state1)
    state2 = normalize_state(state2)

    # --- Factor 1: CPI (inflation adjustment) ---
    # What would income1 be worth in year2 dollars?
    cpi_factor = get_inflation_factor(year1, year2)
    income1_adjusted_for_inflation = income1 * cpi_factor

    # --- Factor 2: RPP (location cost adjustment) ---
    # How much more/less expensive is state2 vs state1?
    location_factor = get_location_factor(state1, state2)

    # To maintain the same lifestyle in state2, you'd need income1 * cpi * location
    income1_equivalent = income1_adjusted_for_inflation * location_factor

    # --- Factor 3: Tax (state income tax impact) ---
    tax_rate1 = get_effective_tax_rate(state1, income1)
    tax_rate2 = get_effective_tax_rate(state2, income2)
    after_tax1 = income1 * (1 - tax_rate1 / 100)
    after_tax2 = income2 * (1 - tax_rate2 / 100)

    # After-tax income1 equivalent in year2/state2 terms
    after_tax1_equivalent = after_tax1 * cpi_factor * location_factor

    # --- Overall comparison ---
    # How does income2's purchasing power compare to income1's?
    if after_tax1_equivalent > 0:
        purchasing_power_ratio = after_tax2 / after_tax1_equivalent
    else:
        purchasing_power_ratio = 0.0

    purchasing_power_pct = purchasing_power_ratio * 100

    return {
        # Summary
        "purchasing_power_pct": purchasing_power_pct,
        "summary": _build_summary(
            income1, state1, year1, income2, state2, year2, purchasing_power_pct
        ),
        # Input echo
        "income1": income1,
        "state1": state1,
        "year1": year1,
        "income2": income2,
        "state2": state2,
        "year2": year2,
        # CPI factor
        "cpi_factor": cpi_factor,
        "income1_inflation_adjusted": income1_adjusted_for_inflation,
        # RPP factor
        "location_factor": location_factor,
        "rpp_state1": get_rpp(state1),
        "rpp_state2": get_rpp(state2),
        "income1_equivalent": income1_equivalent,
        # Tax factor
        "tax_rate1": tax_rate1,
        "tax_rate2": tax_rate2,
        "after_tax1": after_tax1,
        "after_tax2": after_tax2,
        "after_tax1_equivalent": after_tax1_equivalent,
        # Breakdown contributions (how much each factor shifts things)
        "breakdown": _compute_breakdown(
            income1, income2, cpi_factor, location_factor,
            tax_rate1, tax_rate2,
        ),
    }


def _compute_breakdown(
    income1: float,
    income2: float,
    cpi_factor: float,
    location_factor: float,
    tax_rate1: float,
    tax_rate2: float,
) -> dict:
    """Compute how each factor contributes to the gap between the two incomes.

    Returns each factor's dollar impact and the net result.
    """
    # Start with nominal income1
    step0 = income1

    # After inflation adjustment
    step1 = income1 * cpi_factor
    inflation_impact = step1 - step0

    # After location adjustment
    step2 = step1 * location_factor
    location_impact = step2 - step1

    # income1 equivalent (pre-tax, in year2/state2 terms)
    equivalent_pretax = step2

    # Tax on scenario 1 equivalent vs scenario 2
    after_tax_equivalent = equivalent_pretax * (1 - tax_rate1 / 100)
    after_tax2 = income2 * (1 - tax_rate2 / 100)

    # Tax impact: difference caused by tax rate change
    # (what you'd keep at rate1 vs rate2 on the equivalent income)
    tax_impact_on_equivalent = equivalent_pretax * (tax_rate1 - tax_rate2) / 100

    return {
        "nominal_income1": step0,
        "after_inflation": step1,
        "after_location": step2,
        "inflation_impact": inflation_impact,
        "location_impact": location_impact,
        "tax_impact": tax_impact_on_equivalent,
        "equivalent_pretax": equivalent_pretax,
        "equivalent_after_tax": after_tax_equivalent,
        "income2_after_tax": after_tax2,
        "gap": after_tax2 - after_tax_equivalent,
    }


def _build_summary(
    income1: float,
    state1: str,
    year1: int,
    income2: float,
    state2: str,
    year2: int,
    pct: float,
) -> str:
    """Build a human-readable summary of the comparison."""
    if pct > 105:
        verdict = "better off"
    elif pct < 95:
        verdict = "worse off"
    else:
        verdict = "about the same"

    return (
        f"${income2:,.0f} in {state2} ({year2}) has "
        f"{pct:.1f}% of the real purchasing power of "
        f"${income1:,.0f} in {state1} ({year1}). "
        f"You are {verdict}."
    )
