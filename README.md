# 🍽️ Dismal Dinner

A "Generational Truth Machine" that uses BLS and BEA data to calculate Real Purchasing Power. Stop comparing salaries and start comparing lifestyles across time (CPI), space (RPP), and policy (Tax Gap).

> "My parents got by on $17k in Ohio in 1997. Why am I struggling on $80k in California today?"

Dismal Dinner was built to answer that exact question. Standard inflation calculators are a lie of omission—they tell you how the dollar changed, but they don't tell you how the location or the tax man changed.

## The Equation

For each scenario, we compute what a salary actually buys:

$$
\text{Purchasing Power} = \text{Income} \times (1 - \text{Tax Rate}) \times \text{CPI Factor} \times \text{RPP Factor}
$$

Then we compare them:

$$
\text{Result \%} = \frac{\text{Purchasing Power}_B}{\text{Purchasing Power}_A} \times 100
$$

A result of 100% means the two lifestyles are equivalent. Below 100% means Scenario B buys less; above means it buys more.

| Step | Factor | What It Does | Example | Source |
|------|--------|-------------|---------|--------|
| 1 | **CPI (When)** | Converts both incomes to the same year's dollars | $17k in 1997 → ~$33k in 2024 dollars | Bureau of Labor Statistics |
| 2 | **RPP (Where)** | Adjusts for regional cost of living | A dollar in Ohio buys ~18% more than in California | Bureau of Economic Analysis |
| 3 | **Tax Gap (Gouge)** | Subtracts each state's effective income tax rate | 0% in TX vs ~9% in CA on the same salary | Tax Foundation data |

The final output is a **purchasing power percentage** plus a dollar-level breakdown showing exactly how much each factor shifts the comparison.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/your-username/dismal-dinner.git
cd dismal-dinner

# Create virtual environment and install dependencies
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# (Optional) Set up BLS API key for higher rate limits
cp .env.example .env
# Edit .env and add your key from https://www.bls.gov/developers/

# Run the app
streamlit run app.py
```

The app runs at `http://localhost:8501`. No API key is required — embedded fallback data covers 1990–2025.

## Features

- Compare purchasing power across any two income/state/year scenarios
- CPI inflation adjustment (1990–2025)
- Regional Price Parity cost-of-living adjustment (all 50 states + DC)
- State income tax impact (with progressive bracket support)
- Interactive waterfall and bar chart visualizations
- Export results as JSON or CSV
- Comparison history saved locally

## Data Sources

| Factor | Source | Method |
|--------|--------|--------|
| CPI | [Bureau of Labor Statistics](https://www.bls.gov/cpi/) | API with embedded fallback |
| RPP | [Bureau of Economic Analysis](https://www.bea.gov/data/prices-expenditures/regional-price-parities-state-and-metro-area) | Embedded state-level data |
| Tax | [Tax Foundation](https://taxfoundation.org/) | Curated effective rates CSV |

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ --cov=data --cov=utils --cov=calculator --cov-report=term-missing
```

Current coverage: **84%** across 114 tests.

## Project Structure

```
├── app.py                  # Streamlit web interface
├── calculator.py           # Core comparison engine
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── data/
│   ├── cpi_fetcher.py      # BLS CPI data module
│   ├── rpp_fetcher.py      # BEA RPP data module
│   ├── tax_calculator.py   # State tax calculations
│   └── tax_data.csv        # State tax rates lookup
├── utils/
│   ├── helpers.py          # Formatting utilities
│   └── history.py          # Comparison history persistence
└── tests/                  # 114 tests (pytest)
```

## Limitations

- **State-level only** — no city/MSA granularity yet
- **State income tax only** — no federal, FICA, sales, or property taxes
- **Simplified tax rates** — effective rate lookup, not full tax code simulation
- **Single filer assumption** — no filing status or deductions
- **Annual data** — no monthly precision
- **CPI is national** — not region-specific inflation

## Specials 

- **The Gaslight Special**: Compare any 1990s midwest salary to a modern HCOL coastal salary
- **The Relocation Reality Check**: Is that 20% raise in a new city actually a 15% pay cut?

## License

Open source. See LICENSE file for details.

