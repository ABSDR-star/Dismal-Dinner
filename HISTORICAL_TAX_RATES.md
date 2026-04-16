# Historical Tax Rates Feature

## Current Status: Future Enhancement

This document summarizes the analysis of adding historical tax rate support to the Dismal-Dinner application.

## Current Implementation

The application currently uses **static tax rates** that do not adjust based on the year being analyzed:

- Tax rates are stored in `data/tax_data.csv` with no year dimension
- The `get_effective_tax_rate(state, income)` function only considers state and income
- Same tax rates are applied regardless of whether comparing 1990 or 2025

### What's Already Time-Adjusted

✅ **CPI (Inflation)**: Adjusts for purchasing power changes over time
✅ **RPP (Regional Price Parity)**: Adjusts for cost-of-living differences between states
❌ **Tax Rates**: Uses current rates for all time periods

## Why This Matters

When comparing incomes from different historical periods, the application may be inaccurate because:

- State tax rates have changed significantly over the past 35 years (1990-2025)
- Some states have reformed their tax structures (changed brackets, rates)
- A few states have added or removed income taxes entirely

**Example**: Comparing $50,000 in California (1995) vs $100,000 in Texas (2025) would use today's California tax rates, not the actual 1995 rates.

## Implementation Difficulty Assessment

### Data Collection: **MODERATE TO HIGH DIFFICULTY**

**Main Challenge**: Obtaining accurate historical tax data

- **Scope**: 50 states × 35 years × multiple brackets = ~5,000+ data points
- **Sources needed**:
  - State revenue department archives
  - Tax Foundation historical reports
  - Academic databases (NBER TAXSIM)
  - IRS historical state tax records

**Complexity**:
- Tax bracket structures changed frequently
- Need to calculate effective rates (not just marginal rates)
- Must handle special cases (temporary taxes, filing status variations)
- Data quality and consistency validation required

### Code Changes: **LOW TO MODERATE DIFFICULTY**

Required modifications are straightforward:

1. **Database Schema**: Add `year` column to tax table
   ```
   Current: (state, bracket_min, bracket_max, effective_rate)
   New:     (state, year, bracket_min, bracket_max, effective_rate)
   ```

2. **Function Signatures**: Update to accept year parameter
   - `get_effective_tax_rate(state, income, year)`
   - Pass `year1` and `year2` from `compare_lifestyles()`

3. **Files to Modify**:
   - `data/tax_calculator.py`
   - `calculator.py`
   - Database initialization code
   - Test files

**Estimated code changes**: 5-10 files, ~50-100 lines modified

## Recommended Implementation Approaches

### Option A: Full Historical Data (Most Accurate)
- **Effort**: 60-100 hours
- **Approach**: Research and compile comprehensive historical tax data
- **Pros**: Most accurate, handles all edge cases
- **Cons**: Significant time investment, ongoing maintenance

### Option B: Simplified Estimates (Quick Solution)
- **Effort**: 8-16 hours
- **Approach**: Use aggregate scaling factors based on decade
- **Pros**: Fast to implement
- **Cons**: Less accurate, directional only

### Option C: External API Integration
- **Effort**: 16-24 hours
- **Approach**: Integrate with TAXSIM or Tax Policy Center APIs
- **Pros**: Maintainable, data updates handled externally
- **Cons**: Dependency risk, may require subscription

### Option D: Phased Approach (Recommended if implementing)
- **Phase 1**: Add year parameter to code structure (4-8 hours)
- **Phase 2**: Add key year snapshots: 1990, 2000, 2010, 2020, 2025 (16-24 hours)
- **Phase 3**: Fill gaps incrementally based on user needs (ongoing)

**Total for MVP**: ~20-32 hours

## Decision

**Status**: Deferred to future release

The technical implementation is manageable, but **data collection is the primary bottleneck**. The effort required to obtain and validate accurate historical tax rate data across 50 states and 35 years significantly outweighs the immediate benefit.

## Future Considerations

If this feature is revisited:

1. Start with a phased approach (add infrastructure first)
2. Consider using existing tax research databases/APIs
3. Focus on key milestone years rather than complete coverage
4. Accept community contributions for historical data
5. Clearly document limitations and accuracy of historical data

## Related Files

- `data/tax_calculator.py` - Current tax rate lookup logic
- `data/tax_data.csv` - Current static tax rate data
- `calculator.py:46-49` - Where tax rates are used in comparisons

---

*Last Updated: 2026-04-16*
