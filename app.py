import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import numpy as np

# --- Page Configuration ---
st.set_page_config(page_title="Pro Trading Terminal", page_icon="📈", layout="wide")

# --- Session State Initialization ---
if 'stock_data' not in st.session_state:
    st.session_state.stock_data = {}
if 'results_data' not in st.session_state:
    st.session_state.results_data = []
if 'last_updated' not in st.session_state:
    st.session_state.last_updated = "Never"
if 'last_timer_count' not in st.session_state:
    st.session_state.last_timer_count = 0

# ==========================================
# SIDEBAR: CONTROLS
# ==========================================
with st.sidebar:
    st.title("⚙️ Dashboard Controls")
    st.divider()
    
    tickers_input = st.text_input("Enter Tickers (NSE: .NS, BSE: .BO):", "AAPL, RELIANCE.NS, TSLA, NVDA")
    tickers = [ticker.strip().upper() for ticker in tickers_input.split(",") if ticker.strip()]

    selected_period = st.selectbox("Historical Period:", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3)
    selected_interval = st.selectbox("Chart Interval:", ["30m", "1h", "1d", "1wk", "1mo"], index=2)

    st.divider()
    st.subheader("⏱️ Automation")
    auto_refresh = st.toggle("Enable Auto-Refresh")
    
    is_timer_tick = False
    if auto_refresh:
        freq = st.selectbox("Frequency:", ["1 Minute", "5 Minutes", "15 Minutes"], index=1)
        mapping = {"1 Minute": 60000, "5 Minutes": 300000, "15 Minutes": 900000}
        timer_count = st_autorefresh(interval=mapping[freq], key="data_refresh")
        if timer_count != st.session_state.last_timer_count:
            st.session_state.last_timer_count = timer_count
            is_timer_tick = True

    st.divider()
    run_button = st.button("🚀 Update Analysis", type="primary", use_container_width=True)

# ==========================================
# DATA FETCHING & LOGIC
# ==========================================
if run_button or is_timer_tick:
    if not tickers:
        st.sidebar.warning("Enter a ticker.")
    else:
        with st.spinner("Processing Market Data..."):
            results, stock_data_dict = [], {}
            for ticker in tickers:
                try:
                    df = yf.download(ticker, period=selected_period, interval=selected_interval, progress=False)
                    if df.empty or len(df) < 50: continue
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

                    # Technical Indicators
                    df.ta.sma(length=18, append=True)
                    df.ta.sma(length=50, append=True)
                    df.ta.macd(append=True) 
                    df.ta.rsi(length=14, append=True)
                    df.ta.adx(length=14, append=True)
                    df.ta.bbands(length=20, std=2, append=True)

                    df['Floor'] = df['Low'].rolling(window=20).min()
                    df['Ceil'] = df['High'].rolling(window=20).max()

                    # Signal Logic
                    df['M_Buy'] = (df['MACD_12_26_9'] > df['MACDs_12_26_9']) & (df['MACD_12_26_9'].shift(1) <= df['MACDs_12_26_9'].shift(1))
                    df['M_Sell'] = (df['MACD_12_26_9'] < df['MACDs_12_26_9']) & (df['MACD_12_26_9'].shift(1) >= df['MACDs_12_26_9'].shift(1))

                    stock_data_dict[ticker] = df
                    latest = df.iloc[-1]
                    
                    results.append({
                        "Ticker": ticker, "Price": f"{latest['Close']:.2f}",
                        "SMA Rec": "Buy" if latest['SMA_18'] > latest['SMA_50'] else "Sell",
                        "MACD Rec": "Buy" if latest['MACD_12_26_9'] > latest['MACDs_12_26_9'] else "Sell",
                        "RSI": round(latest['RSI_14'], 2),
                        "ADX": f"{round(latest['ADX_14'], 1)}",
                        "Support": f"{latest['Floor']:.2f}", "Resistance": f"{latest['Ceil']:.2f}"
                    })
                except Exception as e: st.error(f"{ticker} Error: {e}")

            st.session_state.stock_data = stock_data_dict
            st.session_state.results_data = results
            st.session_state.last_updated = datetime.now().strftime("%I:%M:%S %p")

# ==========================================
# MAIN DASHBOARD DISPLAY
# ==========================================
st.title("📈 Pro Technical Terminal")

if st.session_state.results_data:
    df_res = pd.DataFrame(st.session_state.results_data)
    
    def highlight(val):
        color = 'rgba(0, 255, 0, 0.2)' if val == 'Buy' else 'rgba(255, 0, 0, 0.2)'
        text = '#00FF00' if val == 'Buy' else '#FF0000'
        return f'background-color: {color}; color: {text}; font-weight: bold'

    st.subheader(f"Market Overview (Refreshed: {st.session_state.last_updated})", divider="gray")
    event = st.dataframe(df_res.style.map(highlight, subset=['SMA Rec', 'MACD Rec']), use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")

    if event.selection.rows:
        sel_idx = event.selection.rows[0]
        ticker = df_res.iloc[sel_idx]['Ticker']
        df = st.session_state.stock_data[ticker]

        st.subheader(f"📊 {ticker} Deep Dive Analysis", divider="blue")
        
        # --- Volume Profile Logic ---
        bins = 40
        price_min, price_max = df['Low'].min(), df['High'].max()
        bin_edges = np.linspace(price_min, price_max, bins + 1)
        v_profile, _ = np.histogram(df['Close'], bins=bin_edges, weights=df['Volume'])
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        # Create Subplots
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
            row_heights=[0.35, 0.35, 0.3],
            specs=[[{"secondary_y": False}], [{"secondary_y": True}], [{"secondary_y": False}]]
        )

        # TIER 1: TREND (Line Chart + Signals)
        upper_col = [c for c in df.columns if c.startswith('BBU')][0]
        lower_col = [c for c in df.columns if c.startswith('BBL')][0]
        
        fig.add_trace(go.Scatter(x=df.index, y=df[upper_col], line=dict(color='rgba(255,255,255,0.2)', width=1, dash='dash'), name='BB Upper', showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df[lower_col], line=dict(color='rgba(255,255,255,0.2)', width=1, dash='dash'), fill='tonexty', fillcolor='rgba(128,128,128,0.1)', name='BBands'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], line=dict(color='white', width=2), name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_18'], line=dict(color='#00BFFF', width=1.5), name='SMA 18'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='#FFA500', width=1.5), name='SMA 50'), row=1, col=1)
        
        # Signals
        buys, sells = df[df['M_Buy']], df[df['M_Sell']]
        fig.add_trace(go.Scatter(x=buys.index, y=buys['Low']*0.98, mode='markers', marker=dict(symbol='triangle-up', size=12, color='#00FF00'), name='Buy'), row=1, col=1)
        fig.add_trace(go.Scatter(x=sells.index, y=sells['High']*1.02, mode='markers', marker=dict(symbol='triangle-down', size=12, color='#FF0000'), name='Sell'), row=1, col=1)

        # TIER 2: STRUCTURE (Candlesticks + Volume Profile)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Candles'), row=2, col=1)
        # Volume Profile as a horizontal bar chart on secondary x-axis
        fig.add_trace(go.Bar(
            y=bin_centers, x=v_profile, orientation='h', name='Volume Profile',
            marker_color='rgba(0, 191, 255, 0.2)', showlegend=True, xaxis='x2'
        ), row=2, col=1)

        # TIER 3: MOMENTUM (MACD)
        hist_colors = ['#00FF00' if v >= 0 else '#FF0000' for v in df['MACDh_12_26_9']]
        fig.add_trace(go.Bar(x=df.index, y=df['MACDh_12_26_9'], marker_color=hist_colors, name='Momentum'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_12_26_9'], line=dict(color='#00BFFF'), name='MACD'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACDs_12_26_9'], line=dict(color='#FFA500'), name='Signal'), row=3, col=1)

        # Layout Tuning
        fig.update_layout(
            height=1000, template='plotly_dark', showlegend=True,
            xaxis3_title="Time", yaxis_title="Trend ($)", yaxis2_title="Structure", yaxis3_title="Momentum",
            xaxis2=dict(overlaying='x', side='top', showgrid=False, zeroline=False, showticklabels=False, range=[0, max(v_profile)*5]),
            hovermode='x unified', margin=dict(l=10, r=10, t=30, b=10),
            xaxis_rangeslider_visible=False
        )
        st.plotly_chart(fig, use_container_width=True)
