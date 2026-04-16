import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Dismal Dinner",
    page_icon="🍽️",
    layout="wide"
)

# Header
st.title("🍽️ Dismal Dinner")
st.subheader("The Generational Truth Machine")

# Welcome message
st.markdown("""
Welcome to **Dismal Dinner** - a tool that compares real purchasing power across:
- **Time** (CPI inflation adjustment)
- **Space** (Regional Price Parities)
- **Policy** (Tax differences)

### Example Question
*"My parents got by on $17k in 1997. Why am I struggling on $80k today?"*

This application will help you answer questions like this by providing data-driven comparisons
of lifestyle affordability across different times, locations, and tax policies.
""")

# Status message
st.info("✅ Phase 1 Complete: Basic Streamlit app is running!")

# Sidebar placeholder
with st.sidebar:
    st.header("Coming Soon")
    st.markdown("""
    - Scenario comparison inputs
    - CPI adjustment calculator
    - Regional price parity analysis
    - Tax impact calculations
    - Visual breakdowns
    """)

# Footer
st.divider()
st.caption("Phase 1: Project Setup | Next: Data Collection & Storage")
