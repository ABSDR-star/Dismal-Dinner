import json
from datetime import datetime
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from calculator import compare_lifestyles
from data.rpp_fetcher import get_all_states
from utils.helpers import format_currency, format_percentage
from utils.history import save_comparison, load_recent_comparisons

# Page configuration
st.set_page_config(
    page_title="Dismal Dinner",
    page_icon="🍽️",
    layout="wide",
)

# Header
st.title("🍽️ Dismal Dinner")
st.subheader("The Generational Truth Machine")
st.markdown(
    "Compare real purchasing power across **time** (CPI), "
    "**location** (RPP), and **tax policy** (state income tax)."
)
st.caption("📱 On mobile? Tap the **>** arrow in the top-left corner to open the sidebar and set your scenarios.")
st.markdown(
    "<style>@media (min-width: 769px) { .stCaption:first-of-type { display: none; } }</style>",
    unsafe_allow_html=True,
)

# --- Sidebar: Inputs ---
ALL_STATES = get_all_states()

with st.sidebar:
    st.header("Scenario 1 — Then")
    income1 = st.number_input(
        "Income ($)", min_value=0, max_value=10_000_000,
        value=27_000, step=1_000, key="income1",
    )
    state1 = st.selectbox("State", ALL_STATES, index=ALL_STATES.index("Ohio"), key="state1")
    year1 = st.slider("Year", 1990, 2025, 1997, key="year1")

    st.divider()

    st.header("Scenario 2 — Now")
    income2 = st.number_input(
        "Income ($)", min_value=0, max_value=10_000_000,
        value=60_000, step=1_000, key="income2",
    )
    state2 = st.selectbox("State", ALL_STATES, index=ALL_STATES.index("California"), key="state2")
    year2 = st.slider("Year", 1990, 2025, 2024, key="year2")

    st.divider()
    compare_btn = st.button("🔍 Compare", use_container_width=True, type="primary")

    # --- History ---
    history = load_recent_comparisons(limit=5)
    if history:
        st.divider()
        st.header("Recent Comparisons")
        for h in history:
            label = (
                f"${h['scenario1_income']:,.0f} {h['scenario1_state']} ({h['scenario1_year']}) vs "
                f"${h['scenario2_income']:,.0f} {h['scenario2_state']} ({h['scenario2_year']}) "
                f"→ {h['purchasing_power_pct']:.1f}%"
            )
            st.caption(label)

# --- Main: Results ---
if compare_btn:
    if income1 <= 0 or income2 <= 0:
        st.error("Income must be greater than zero.")
    else:
        with st.spinner("Crunching the numbers..."):
            try:
                result = compare_lifestyles(income1, state1, year1, income2, state2, year2)
            except ValueError as e:
                st.error(f"Invalid input: {e}")
                st.stop()
            except Exception:
                st.error("An unexpected error occurred. Please check your inputs and try again.")
                st.stop()

        # --- Big number ---
        pct = result["purchasing_power_pct"]
        if pct > 105:
            delta_color = "normal"
        elif pct < 95:
            delta_color = "inverse"
        else:
            delta_color = "off"

        col_metric, col_summary = st.columns([1, 2])
        with col_metric:
            st.metric(
                label="Real Purchasing Power",
                value=f"{pct:.1f}%",
                delta=f"{pct - 100:.1f}%" if pct != 100 else "Even",
                delta_color=delta_color,
            )
        with col_summary:
            st.info(result["summary"])

        st.divider()

        # --- Factor breakdown table ---
        st.subheader("Factor-by-Factor Breakdown")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Inflation (CPI)", f"{result['cpi_factor']:.3f}x",
                       help="Multiplier to convert Scenario 1 dollars to Scenario 2 dollars")
            st.caption(
                f"${income1:,.0f} in {year1} → "
                f"{format_currency(result['income1_inflation_adjusted'])} in {year2}"
            )

        with col2:
            lf = result["location_factor"]
            st.metric("Location (RPP)", f"{lf:.3f}x",
                       help="Cost-of-living ratio between the two states")
            st.caption(
                f"{state1} ({result['rpp_state1']:.1f}) → "
                f"{state2} ({result['rpp_state2']:.1f})"
            )

        with col3:
            st.metric("Tax Gap",
                       f"{result['tax_rate2']:.1f}% vs {result['tax_rate1']:.1f}%",
                       delta=f"{result['tax_rate2'] - result['tax_rate1']:+.1f}pp",
                       delta_color="inverse",
                       help="Effective state income tax rates")
            st.caption(
                f"After tax: {format_currency(result['after_tax2'])} vs "
                f"{format_currency(result['after_tax1'])}"
            )

        st.divider()

        # --- Visualizations ---
        bd = result["breakdown"]

        # 1. Waterfall chart: how income1 transforms to its equivalent
        st.subheader("How Your Dollar Transforms")
        st.caption(
            f"Starting from {format_currency(income1)} in {state1} ({year1}), "
            f"each bar shows what adds to the cost of matching that lifestyle in {state2} ({year2})."
        )
        waterfall = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "relative", "relative", "total"],
            x=[
                f"Original<br>({state1} {year1})",
                f"Inflation<br>({year1}→{year2})",
                f"Location<br>({state1}→{state2})",
                "Tax<br>Adjustment",
                f"Equivalent<br>({state2} {year2})",
            ],
            y=[
                bd["nominal_income1"],
                bd["inflation_impact"],
                bd["location_impact"],
                bd["tax_impact"],
                bd["equivalent_after_tax"],
            ],
            text=[
                format_currency(bd["nominal_income1"]),
                f"+{format_currency(bd['inflation_impact'])}" if bd["inflation_impact"] >= 0
                    else format_currency(bd["inflation_impact"]),
                f"+{format_currency(bd['location_impact'])}" if bd["location_impact"] >= 0
                    else format_currency(bd["location_impact"]),
                f"+{format_currency(bd['tax_impact'])}" if bd["tax_impact"] >= 0
                    else format_currency(bd["tax_impact"]),
                format_currency(bd["equivalent_after_tax"]),
            ],
            textposition="outside",
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": "#ef4444"}},
            decreasing={"marker": {"color": "#22c55e"}},
            totals={"marker": {"color": "#3b82f6"}},
            showlegend=False,
        ))
        # Add invisible traces for the legend
        waterfall.add_trace(go.Bar(
            x=[None], y=[None], marker_color="#ef4444",
            name="Costs more", showlegend=True,
        ))
        waterfall.add_trace(go.Bar(
            x=[None], y=[None], marker_color="#22c55e",
            name="Costs less", showlegend=True,
        ))
        waterfall.add_trace(go.Bar(
            x=[None], y=[None], marker_color="#3b82f6",
            name="Start / End total", showlegend=True,
        ))
        waterfall.update_layout(
            title=f"What {format_currency(income1)} in {state1} ({year1}) equals today",
            yaxis_title="Dollars",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            height=450,
            xaxis=dict(fixedrange=True),
            yaxis=dict(fixedrange=True),
        )
        st.plotly_chart(waterfall, use_container_width=True, config={"displayModeBar": False})

        # 2. Side-by-side bar: after-tax purchasing power
        st.subheader("After-Tax Purchasing Power Comparison")
        bars = go.Figure(data=[
            go.Bar(
                name="Scenario 1 (equivalent)",
                x=["After-Tax Income"],
                y=[result["after_tax1_equivalent"]],
                text=[format_currency(result["after_tax1_equivalent"])],
                textposition="auto",
                marker_color="#3b82f6",
            ),
            go.Bar(
                name="Scenario 2 (actual)",
                x=["After-Tax Income"],
                y=[result["after_tax2"]],
                text=[format_currency(result["after_tax2"])],
                textposition="auto",
                marker_color="#f59e0b",
            ),
        ])
        bars.update_layout(
            barmode="group",
            yaxis_title="Dollars",
            height=380,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            xaxis=dict(fixedrange=True),
            yaxis=dict(fixedrange=True),
        )
        gap = result["after_tax2"] - result["after_tax1_equivalent"]
        bars.add_annotation(
            x="After-Tax Income", y=max(result["after_tax2"], result["after_tax1_equivalent"]),
            text=f"Gap: {format_currency(abs(gap))} {'ahead' if gap >= 0 else 'behind'}",
            showarrow=False, yshift=25, font=dict(size=14),
        )
        st.plotly_chart(bars, use_container_width=True, config={"displayModeBar": False})

        # --- Detailed data ---
        with st.expander("📊 Raw Comparison Data"):
            detail_col1, detail_col2 = st.columns(2)
            with detail_col1:
                st.markdown("**Scenario 1**")
                st.write(f"Income: {format_currency(income1)}")
                st.write(f"State: {state1}")
                st.write(f"Year: {year1}")
                st.write(f"Tax rate: {format_percentage(result['tax_rate1'])}")
                st.write(f"After tax: {format_currency(result['after_tax1'])}")
            with detail_col2:
                st.markdown("**Scenario 2**")
                st.write(f"Income: {format_currency(income2)}")
                st.write(f"State: {state2}")
                st.write(f"Year: {year2}")
                st.write(f"Tax rate: {format_percentage(result['tax_rate2'])}")
                st.write(f"After tax: {format_currency(result['after_tax2'])}")

            st.divider()
            st.write(f"CPI factor: {result['cpi_factor']:.4f}")
            st.write(f"Location factor: {result['location_factor']:.4f}")
            st.write(f"Scenario 1 equivalent (inflation+location adjusted, after tax): "
                      f"{format_currency(result['after_tax1_equivalent'])}")

        # --- Export buttons ---
        st.subheader("Export Results")
        export_col1, export_col2 = st.columns(2)

        # Build export data (flat dict, no nested breakdown)
        export_data = {
            "scenario1_income": income1,
            "scenario1_state": result["state1"],
            "scenario1_year": year1,
            "scenario1_tax_rate": result["tax_rate1"],
            "scenario1_after_tax": result["after_tax1"],
            "scenario2_income": income2,
            "scenario2_state": result["state2"],
            "scenario2_year": year2,
            "scenario2_tax_rate": result["tax_rate2"],
            "scenario2_after_tax": result["after_tax2"],
            "cpi_factor": round(result["cpi_factor"], 4),
            "location_factor": round(result["location_factor"], 4),
            "purchasing_power_pct": round(pct, 2),
            "scenario1_equivalent_after_tax": round(result["after_tax1_equivalent"], 2),
            "gap": round(gap, 2),
            "generated_at": datetime.now().isoformat(),
        }

        with export_col1:
            st.download_button(
                "\u2b07 Download JSON",
                data=json.dumps(export_data, indent=2),
                file_name="dismal_dinner_comparison.json",
                mime="application/json",
                use_container_width=True,
            )
        with export_col2:
            csv_df = pd.DataFrame([export_data])
            st.download_button(
                "\u2b07 Download CSV",
                data=csv_df.to_csv(index=False),
                file_name="dismal_dinner_comparison.csv",
                mime="text/csv",
                use_container_width=True,
            )

        # Save to history
        save_comparison(export_data)

# --- Welcome state (no comparison yet) ---
else:
    st.markdown("""
    **We've all asked ourselves the question:**

    > *"My parents got by on 27K in Ohio in 1997. Why am I struggling on 60K in California today?"*

    **This tool gives you a real answer** — adjusting for inflation, cost of living, and taxes so you can compare apples to apples.

    ### How it works
    1. **Open the sidebar** — tap the **>** arrow in the top-left corner (on mobile) or use the sidebar on the left (on desktop)
    2. **Set Scenario 1** — your parents' income, state, and year
    3. **Set Scenario 2** — your current income, state, and year
    4. **Click Compare** to see the real purchasing power breakdown

    The defaults are pre-loaded with this example. Hit **Compare** to find out!

    ### Other things you can answer
    - **"How much is my parents' income really worth today?"** — Keep the same state and just change the years
    - **"Should I take this job in a new city?"** — Pit a job offer in one state against your current gig in another
    - **"Is moving to a no-income-tax state worth it?"** — Compare the same salary in Texas vs. California (or any pair)
    - **"Have wages in my state kept up with the cost of living?"** — Set both scenarios to the same state, different years and incomes
    - **"How far did a dollar go when my parents were young?"** — Pick any two eras and see the real difference
    """)

# Footer
st.divider()
st.caption(
    "Data: BLS CPI-U · BEA Regional Price Parities · Tax Foundation effective rates. "
    "Disclaimer: Simplified estimates for illustration. Not financial advice."
)
