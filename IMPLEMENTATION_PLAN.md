# Dismal Dinner - MVP Implementation Plan

## Project Overview

A "Generational Truth Machine" that compares real purchasing power across time (CPI), space (RPP), and policy (Tax Gap). Answers questions like: "My parents got by on $17k in ABCity in 1997. Why am I struggling on $80k in XYZity today?"

## Design Principles

- **Simplicity First**: Single language (Python), minimal complexity
- **State-Level MVP**: Start with state comparisons, expand to cities later
- **Incremental Development**: Build in stages, each phase produces working deliverables
- **Data-Driven**: Cache government data locally for fast, reliable comparisons

---

## Technology Stack

### Core Technologies
- **Frontend/Backend**: Streamlit (Python-based, all-in-one solution)
- **Data Processing**: Pandas
- **Storage**: SQLite + CSV files
- **Visualization**: Plotly
- **Testing**: pytest + pytest-cov
- **Deployment**: Streamlit Cloud (free tier) or Render

### Why This Stack?
- **Single Language**: Everything in Python - no context switching
- **Zero DevOps**: Streamlit handles UI, state management, and deployment
- **Minimal Code**: ~300-400 lines for MVP vs 1000+ with separate frontend/backend
- **Free Hosting**: Streamlit Cloud requires zero configuration

---

## Data Sources Strategy

### 1. CPI Data (Bureau of Labor Statistics)
**Source**: BLS API v2
**Approach**: API with SQLite caching
**Rationale**:
- Official, structured JSON responses
- Historical data back to 1913
- Free tier (500 requests/day) sufficient for MVP
- More reliable than scraping HTML tables

**Implementation**:
- Register for BLS API key
- Fetch CPI-U (all items) annual data
- Cache in SQLite: `cpi(year, month, value)`
- Function: `get_inflation_factor(year1, year2)`

---

### 2. RPP Data (Bureau of Economic Analysis)
**Source**: BEA Regional Price Parities Excel files
**Approach**: Download + Parse with Pandas
**Rationale**:
- Annual Excel files readily available
- Complete datasets in one download
- No rate limits or API complexity
- Easy to inspect and validate

**Implementation**:
- Download latest BEA RPP Excel file
- Parse state-level data with Pandas
- Store in SQLite: `rpp(year, state, rpp_index)`
- Function: `get_location_factor(state1, state2, year)`

---

### 3. Tax Gap Data (State Income Tax)
**Source**: Tax Foundation data + manual curation
**Approach**: Curated CSV lookup table
**Rationale**:
- Census STC data too complex for MVP
- Tax Foundation provides clean effective rate data
- Simple lookup faster than real-time calculation
- Allows manual verification and adjustments

**Implementation**:
- Create `tax_data.csv` with state effective rates by income bracket
- Store in SQLite: `taxes(state, income_bracket, effective_rate)`
- Function: `get_effective_tax_rate(state, income)`
- MVP: State income tax only (no federal)

---

## Project Structure

```
dismal-dinner/
├── app.py                      # Main Streamlit application
├── calculator.py               # Core comparison logic
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
├── README.md                   # Project documentation
├── IMPLEMENTATION_PLAN.md      # This file
├── data/
│   ├── __init__.py
│   ├── cpi_fetcher.py         # BLS CPI data module
│   ├── rpp_fetcher.py         # BEA RPP data module
│   ├── tax_calculator.py      # Tax calculation module
│   ├── tax_data.csv           # State tax rates lookup
│   └── cache.db               # SQLite cache database
├── utils/
│   ├── __init__.py
│   └── helpers.py             # Utility functions
└── tests/
    ├── __init__.py
    ├── test_cpi_fetcher.py    # CPI module tests
    ├── test_rpp_fetcher.py    # RPP module tests
    ├── test_tax_calculator.py # Tax module tests
    ├── test_calculator.py     # Core logic tests
    └── test_integration.py    # End-to-end tests
```

---

## Development Phases

### Phase 1: Project Setup (1-2 hours)
**Goal**: Get a running Streamlit app

**Tasks**:
1. Initialize Python project structure
2. Create virtual environment
3. Install dependencies: `streamlit`, `pandas`, `requests`, `plotly`, `sqlite3`, `pytest`, `pytest-cov`
4. Create `.gitignore` for Python/data files
5. Set up basic Streamlit "Hello World" app

**Deliverable**: Running Streamlit app accessible via `streamlit run app.py`

**Tests**: N/A (setup phase)

---

### Phase 2: Data Collection & Storage (3-4 hours)
**Goal**: Three working data modules with SQLite cache

**2.1 CPI Data Module**
- Register for BLS API key (free)
- Create `data/cpi_fetcher.py`
- Fetch CPI-U (all items) data from 1990-present
- Implement SQLite caching
- Create function: `get_inflation_factor(year1, year2)`

**2.2 RPP Data Module**
- Download BEA RPP Excel file (latest year)
- Create `data/rpp_fetcher.py`
- Parse state-level RPP data with Pandas
- Implement SQLite caching
- Create function: `get_location_factor(state1, state2, year)`

**2.3 Tax Data Module**
- Research and compile state effective tax rates
- Create `data/tax_data.csv`
- Create `data/tax_calculator.py`
- Implement simple lookup logic
- Create function: `get_effective_tax_rate(state, income)`

**Deliverable**: Three importable modules with working cache

**Tests**:
- `test_cpi_fetcher.py`: API parsing, inflation calculations, cache logic
- `test_rpp_fetcher.py`: Excel parsing, location factors, state normalization
- `test_tax_calculator.py`: Rate lookups, bracket interpolation, edge cases

---

### Phase 3: Core Calculation Engine (2-3 hours)
**Goal**: Working lifestyle comparison calculator

**Tasks**:
1. Create `calculator.py`
2. Implement `compare_lifestyles(income1, state1, year1, income2, state2, year2)`
3. Calculate:
   - CPI adjustment factor
   - RPP adjustment factor
   - Tax adjustment factor
   - Overall "real purchasing power" percentage
   - Detailed breakdown

**Logic Flow**:
1. Adjust income1 to year2 dollars using CPI
2. Adjust for location difference using RPP
3. Calculate after-tax income for both scenarios
4. Return comprehensive comparison data

**Deliverable**: Tested calculation engine

**Tests**:
- `test_calculator.py`: Known scenario validation, factor isolation, identity comparisons, boundary conditions
- Target: 80%+ code coverage for this module

---

### Phase 4: Streamlit UI (3-4 hours)
**Goal**: Functional web interface

**Layout**:

**Header**:
- App title: "Dismal Dinner"
- Tagline from README
- Brief explanation

**Sidebar** (Inputs):
- **Scenario 1**:
  - Income (number input)
  - State (dropdown, all 50 states)
  - Year (slider, 1990-2024)
- **Scenario 2**:
  - Income (number input)
  - State (dropdown)
  - Year (slider)
- Compare button

**Main Area** (Results):
- Overall percentage difference (large, prominent)
- Breakdown visualization (Plotly chart)
- Detailed explanation text
- Factor-by-factor breakdown table
- Save/Export button

**Features**:
- Input validation
- Loading states
- Error handling
- Clear visual hierarchy

**Deliverable**: Usable web interface

**Tests**: Manual UI testing + integration tests

---

### Phase 5: Data Visualization (2 hours)
**Goal**: Professional, informative charts

**Visualizations**:

1. **Factor Breakdown Chart** (Primary):
   - Grouped/stacked bar chart
   - Shows CPI, RPP, and Tax impacts separately
   - Clear color coding
   - Interactive tooltips

2. **Effective Income Comparison** (Secondary):
   - Side-by-side bar comparison
   - Shows "real" purchasing power after all adjustments
   - Percentage difference annotation

3. **Optional Waterfall Chart**:
   - Shows step-by-step adjustment from income1 to income2 equivalent
   - Visual flow of how each factor contributes

**Deliverable**: Embedded Plotly charts in Streamlit app

**Tests**: Visual validation, chart data accuracy

---

### Phase 6: Save/Export Feature (1-2 hours)
**Goal**: Users can save and download comparisons

**Functionality**:

**Save to Database**:
- SQLite table: `saved_comparisons`
- Store all input parameters and results
- Timestamp each comparison
- Optional: User session management

**Export Options**:
- JSON download (structured data)
- CSV download (for spreadsheets)
- Optional: PNG export of visualization

**History View**:
- Sidebar section showing recent comparisons
- Click to reload previous comparison

**Deliverable**: Working persistence layer

**Tests**:
- `test_integration.py`: Save/load/export workflows

---

### Phase 7: Testing & Documentation (3-4 hours)
**Goal**: Reliable, well-documented codebase

**Testing Tasks**:
1. Achieve 80%+ test coverage on core modules
2. Write integration tests for full workflows
3. Test edge cases and error conditions
4. Validate against known real-world examples
5. Run full test suite with coverage report

**Documentation Tasks**:
1. Update README.md:
   - Installation instructions
   - Usage guide
   - Data source citations
   - Limitations and assumptions
   - Contributing guidelines
2. Add inline code comments
3. Create `requirements.txt` with pinned versions
4. Document API keys and environment variables

**Known Edge Cases to Test**:
- Same state/year comparisons (should be 100%)
- Years outside data range
- States with no income tax (TX, FL, etc.)
- Very high/low income values
- Missing or incomplete data

**Deliverable**:
- Test coverage report showing 80%+ coverage
- Comprehensive documentation

---

### Phase 8: Deployment (1-2 hours)
**Goal**: Live, publicly accessible app

**Streamlit Cloud Deployment**:
1. Ensure code is pushed to GitHub
2. Sign up for Streamlit Cloud (free)
3. Connect repository
4. Configure secrets (BLS API key)
5. Deploy application
6. Test live deployment
7. Configure custom domain (optional)

**Alternative: Render**:
- Deploy as web service
- Configure environment variables
- Set up health checks

**Deliverable**:
- Live URL
- Deployment documentation

---

## MVP Feature Checklist

### Must Have (MVP)
- [ ] Compare two scenarios (income/state/year)
- [ ] CPI adjustment calculation
- [ ] RPP adjustment calculation
- [ ] State tax impact calculation
- [ ] Overall "real purchasing power" percentage
- [ ] Visual breakdown chart
- [ ] Save/export comparison results
- [ ] State-level granularity
- [ ] Data caching for performance
- [ ] 80%+ test coverage on core logic

### Nice to Have (Post-MVP)
- [ ] Pre-configured "Specials" (Gaslight Special, Relocation Reality Check)
- [ ] City/MSA-level data (not just state)
- [ ] Federal tax calculations
- [ ] Historical tax code changes
- [ ] Compare multiple scenarios at once
- [ ] Share comparisons via URL
- [ ] User accounts/authentication
- [ ] Comparison history visualization
- [ ] Mobile-responsive design improvements

---

## Key Assumptions & Limitations

### MVP Scope
1. **Geographic**: State-level only, no city/MSA granularity
2. **Tax Calculation**: Effective rate lookup, not full tax code simulation
3. **Tax Scope**: State income tax only (no federal, FICA, sales, property taxes)
4. **Time Granularity**: Annual data, no monthly precision
5. **Historical Range**: Focus on 1990-present for data availability
6. **Tax Rates**: Using recent effective rates, not historical tax code changes
7. **Filing Status**: Single filer assumption
8. **No Deductions**: Standard effective rates without itemization

### Data Quality Notes
- CPI: National average, not region-specific inflation
- RPP: BEA updates annually, not real-time
- Tax: Simplified effective rates, not personalized calculations

### Performance Expectations
- Initial data load: ~5-10 seconds (one-time cache building)
- Subsequent comparisons: <1 second (cached data)
- Concurrent users: 10-50 (Streamlit Cloud free tier)

---

## Testing Strategy

### Test Coverage Goals
- **Core Calculator**: 90%+ coverage (most critical)
- **Data Modules**: 80%+ coverage
- **Overall Project**: 80%+ coverage

### Test Categories

**1. Unit Tests** (Isolated function testing)
- `test_cpi_fetcher.py`: API responses, calculations, caching
- `test_rpp_fetcher.py`: Excel parsing, state lookups
- `test_tax_calculator.py`: Rate lookups, interpolation
- `test_calculator.py`: Core comparison logic

**2. Integration Tests** (Multi-component workflows)
- `test_integration.py`: Full comparison workflows, data persistence

**3. Validation Tests** (Real-world accuracy)
- Known comparison scenarios
- Published inflation data validation
- Tax rate verification against official sources

### Testing Approach
- Write tests alongside development (not at end)
- Use pytest fixtures for sample data
- Mock external API calls in tests
- Use pytest-cov for coverage reporting
- Run tests before each commit

### Minimum Viable Test Suite (Time-Constrained)
Priority order if time is limited:
1. `test_calculator.py` - Core business logic (MUST HAVE)
2. `test_cpi_fetcher.py` - CPI calculations are critical
3. `test_tax_calculator.py` - Tax logic validation
4. One integration test for complete scenario

---

## Timeline Estimate

### Total MVP Development Time: 16-22 hours

| Phase | Task | Estimated Time |
|-------|------|----------------|
| 1 | Project Setup | 1-2 hours |
| 2 | Data Collection & Storage | 3-4 hours |
| 3 | Core Calculation Engine | 2-3 hours |
| 4 | Streamlit UI | 3-4 hours |
| 5 | Data Visualization | 2 hours |
| 6 | Save/Export Feature | 1-2 hours |
| 7 | Testing & Documentation | 3-4 hours |
| 8 | Deployment | 1-2 hours |

**Working Schedule**:
- 2-hour blocks: ~8-11 sessions
- Casual pace: 1-2 weeks
- Focused sprint: 3-4 days

---

## Dependencies

### Python Packages (requirements.txt)
```
streamlit>=1.28.0
pandas>=2.0.0
requests>=2.31.0
plotly>=5.17.0
openpyxl>=3.1.0          # For Excel parsing
pytest>=7.4.0
pytest-cov>=4.1.0
python-dotenv>=1.0.0     # For environment variables
```

### External Services
- **BLS API**: Free API key required (register at https://www.bls.gov/developers/)
- **BEA Data**: No API key needed for Excel downloads
- **Streamlit Cloud**: Free account for deployment

### Data Files (Not in Git)
- `data/cache.db` - SQLite database (generated)
- `data/rpp_data.xlsx` - Downloaded from BEA (gitignored)
- `.env` - API keys and secrets (gitignored)

---

## Success Metrics

### MVP Success Criteria
1. **Functionality**: All three factors (CPI, RPP, Tax) calculate correctly
2. **Accuracy**: Results match manual calculations within 1%
3. **Performance**: Comparisons complete in <1 second after cache warm
4. **Reliability**: 80%+ test coverage, all tests passing
5. **Usability**: Non-technical users can run comparisons without instructions
6. **Deployment**: Live URL accessible 99%+ uptime

### Post-Launch Validation
- Test with the example from README: "$17k in 1997 vs $80k in 2024"
- Validate against known inflation calculators
- Compare tax calculations to official state tax tables
- User feedback on accuracy and usability

---

## Risk Mitigation

### Potential Risks

**1. Data Source Changes**
- **Risk**: BLS/BEA change data formats or availability
- **Mitigation**: Cache data locally, version control data sources, document fallback options

**2. API Rate Limits**
- **Risk**: BLS API 500/day limit exceeded
- **Mitigation**: Aggressive caching, local data storage, batch requests efficiently

**3. Tax Calculation Complexity**
- **Risk**: Oversimplified tax model produces inaccurate results
- **Mitigation**: Clearly document assumptions, use published effective rates, add disclaimer

**4. Scope Creep**
- **Risk**: Feature requests delay MVP launch
- **Mitigation**: Strict MVP feature list, defer enhancements to post-MVP phases

**5. Deployment Issues**
- **Risk**: Streamlit Cloud limitations or downtime
- **Mitigation**: Test locally first, have Render as backup deployment option

---

## Next Steps

1. **Review and approve this plan**
2. **Set up development environment**
3. **Begin Phase 1: Project Setup**
4. **Iterate through phases sequentially**
5. **Test continuously**
6. **Deploy early, iterate based on usage**

---

## Questions & Clarifications

### Answered
- ✓ Tech stack prioritizing simplicity → Streamlit + Python
- ✓ API vs scraping → API for CPI, download for RPP, curated CSV for tax
- ✓ Tax data source → Tax Foundation + manual curation (not Census STC)
- ✓ Features → Percentages, data viz, state-level, save capability
- ✓ Scope → MVP first, general comparison tool
- ✓ Testing → Comprehensive unit tests with 80%+ coverage

### Open Questions
- None currently - ready to proceed with implementation

---

**Document Version**: 1.0
**Last Updated**: 2026-04-16
**Status**: Ready for Implementation
