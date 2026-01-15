import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# --- Page Config ---
st.set_page_config(page_title="TradingView Style Interface", layout="wide", initial_sidebar_state="collapsed")

# --- Custom CSS for Dark Theme and Styling ---
st.markdown("""
<style>
    /* Dark Mode Global */
    [data-testid="stAppViewContainer"] {
        background-color: #000000; /* Black background */
        color: #ffffff;
    }
    [data-testid="stHeader"] {
        background-color: #000000;
    }
    [data-testid="stToolbar"] {
        right: 2rem;
    }

    /* Header and Price Styles */
    .stock-header {
        font-size: 18px;
        font-weight: 600;
        color: #ffffff;
        margin-bottom: 5px;
    }
    .stock-symbol {
        font-size: 16px;
        color: #888888;
    }
    .stock-price {
        font-size: 48px;
        font-weight: 700;
        color: #ffffff;
    }
    .price-change {
        font-size: 20px;
        font-weight: 600;
    }
    .price-up {
        color: #00C853; /* Green for positive change */
    }
    .price-down {
        color: #FF3D00; /* Red for negative change */
    }

    /* Button Styling for Timeframes and Bottom Bar */
    .stButton>button {
        background-color: #1A1A1A;
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-size: 14px;
        font-weight: 500;
        margin-right: 5px;
    }
    .stButton>button:hover {
        background-color: #333333;
    }
    .stButton>button:focus {
        background-color: #1A1A1A;
        color: #ffffff;
        box-shadow: none;
    }
    /* Selected Timeframe Button Style (simulated with custom class, not directly stButton) */
    .selected-timeframe {
        background-color: #333333;
        color: #00C853;
    }

    /* Plotly Graph Container */
    [data-testid="stPlotlyChart"] {
        background-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Dummy Data for Chart ---
dates = pd.date_range(start="2023-01-01", periods=100)
prices = np.linspace(150, 250, 100) + np.random.randn(100) * 5
df = pd.DataFrame({'Date': dates, 'Price': prices})

# --- Header Section ---
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown('<div class="stock-header">Tesla</div>', unsafe_allow_html=True)
    st.markdown('<div class="stock-symbol">TSLA - NASDAQ</div>', unsafe_allow_html=True)

# --- Price Section ---
current_price = df['Price'].iloc[-1]
price_change = current_price - df['Price'].iloc[0]
percent_change = (price_change / df['Price'].iloc[0]) * 100
change_class = "price-up" if price_change >= 0 else "price-down"
change_arrow = "↑" if price_change >= 0 else "↓"

st.markdown(
    f'<div class="stock-price">${current_price:.2f} <span class="price-change {change_class}">{change_arrow} {abs(percent_change):.2f}%</span></div>',
    unsafe_allow_html=True
)

# --- Chart Section ---
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df['Date'],
    y=df['Price'],
    mode='lines',
    line=dict(color='#00C853', width=2),
    fill='tozeroy',
    fillcolor='rgba(0, 200, 83, 0.1)'
))

fig.update_layout(
    margin=dict(l=0, r=0, t=0, b=0),
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    xaxis=dict(visible=False, showgrid=False),
    yaxis=dict(visible=False, showgrid=False),
    hovermode='x',
    height=350
)
st.plotly_chart(fig, use_container_width=True)

# --- Timeframe Selection & Bottom Bar ---
# Using columns to layout the buttons horizontally
col_tf1, col_tf2, col_tf3, col_tf4, col_tf5, col_tf6, col_spacer, col_bot1, col_bot2, col_bot3 = st.columns([1, 1, 1, 1, 1, 1, 4, 1, 1, 1])

with col_tf1: st.button("1G")
with col_tf2: st.button("1H")
with col_tf3: st.button("1A", key="selected_1a") # Simulate selection
with col_tf4: st.button("3A")
with col_tf5: st.button("1Y")
with col_tf6: st.button("5Y")

with col_bot1: st.button("⚡", help="Sinyaller")
with col_bot2: st.button("🔔", help="Alarmlar")
with col_bot3: st.button("⛶", help="Tam Ekran")

# --- Inject custom script to style the 'selected' button ---
st.markdown("""
<script>
    // Find the button with key "selected_1a" and add the selected-timeframe class
    const buttons = window.parent.document.querySelectorAll('button');
    buttons.forEach(button => {
        if (button.innerText === "1A") {
            button.classList.add('selected-timeframe');
            button.style.backgroundColor = '#333333';
            button.style.color = '#00C853';
        }
    });
</script>
""", unsafe_allow_html=True)