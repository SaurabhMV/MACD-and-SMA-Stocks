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
st.set_page_config(page_title="Pro Technical Analysis", page_icon="📈", layout="wide")

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
# SIDEBAR: CONTROLS & INPUTS
# ==========================================
with st.sidebar:
    st.title("⚙️ Dashboard Controls")
    st.write("Configure your analysis parameters below.")
    st.divider()
    
    tickers_input = st.text_input("Enter Stock Tickers (comma-separated):", "AAPL, MSFT, TSLA, NVDA")
    tickers = [ticker.strip().upper() for ticker in tickers_input.split(",") if ticker.strip()]

    selected_period = st.selectbox(
        "Historical Period:", 
        ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"], 
        index=3
    )

    selected_interval = st.selectbox(
        "Chart Interval:", 
        ["30m", "1h", "1d", "1wk", "1mo"], 
        index=2
    )

    if selected_interval in ["30m", "1h"]:
        st.caption("⚠️ *Yahoo limits 30m data to 60 days, and 1h data to 2 years.*")
        
    st.divider()
    
    # --- Auto-Refresh Controls ---
    st.subheader("⏱️ Automation")
    auto_refresh = st.toggle("Enable Auto-Refresh")
    
    is_timer_tick = False
    if auto_refresh:
        refresh_interval = st.selectbox(
            "Refresh Frequency:", 
            ["1 Minute", "5 Minutes", "15 Minutes", "30 Minutes"], 
            index=1
        )
        
        interval_mapping = {
            "1 Minute": 60 * 1000,
            "5 Minutes": 5 * 60 * 1000,
            "15 Minutes": 15 * 60 * 1000,
            "30 Minutes": 30 * 60 * 1000
        }
        
        timer_count = st_autorefresh(interval=interval_mapping[refresh_interval], key="data_refresh")
        
        if timer_count != st.session_state.last_timer_count:
            st.session_state.last_timer_count = timer_count
            is_timer_tick = True

    st.divider()
    run_button = st.button("🚀 Run Analysis / Update Now", type="primary", use_container_width=True)

# ==========================================
# MAIN CANVAS: TITLE & DATA LOGIC
# ==========================================
st.title("📈 Pro Technical Analysis Dashboard")
st.markdown("Analyze market trends, identify momentum shifts, and visualize actionable **Buy/Sell signals**.")

if run_button or is_timer_tick:
    if not tickers:
        st.sidebar.warning("Please enter at least one ticker.")
    else:
        with st.spinner(f"Fetching {selected_period} of {selected_interval} data..."):
            results = []
            stock_data_dict = {}

            for ticker in tickers:
                try:
                    df = yf.download(ticker, period=selected_period, interval=selected_interval, progress=False)

                    if df.empty or len(df) < 50:
                        st.toast(f"Not enough data for {ticker}. Skipped.", icon="⚠️")
                        continue
                    
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)

                    # Indicators
                    df.ta.sma(length=18, append=True)
                    df.ta.sma(length=50, append=True)
                    df.ta.macd(append=True) 
                    df.ta.rsi(length=14, append=True)
                    df.ta.adx(length=14, append=True)
                    
                    # Bollinger Bands (20-period, 2 standard deviations)
                    df.ta.bbands(length=20, std=2, append=True)

                    df['Support_20d'] = df['Low'].rolling(window=20).min()
                    df['Resistance_20d'] = df['High'].rolling(window=20).max()

                    # Crossovers
                    df['SMA_Buy'] = (df['SMA_18'] > df['SMA_50']) & (df['SMA_18'].shift(1) <= df['SMA_50'].shift(1))
                    df['SMA_Sell'] = (df['SMA_18'] < df['SMA_50']) & (df['SMA_18'].shift(1) >= df['SMA_50'].shift(1))
                    df['MACD_Buy'] = (df['MACD_12_26_9'] > df['MACDs_12_26_9']) & (df['MACD_12_26_9'].shift(1) <= df['MACDs_12_26_9'].shift(1))
                    df['MACD_Sell'] = (df['MACD_12_26_9'] < df['MACDs_12_26_9']) & (df['MACD_12_26_9'].shift(1) >= df['MACDs_12_26_9'].shift(1))

                    stock_data_dict[ticker] = df

                    latest = df.iloc[-1]
                    current_price = latest['Close']
                    sma_18 = latest['SMA_18']
                    sma_50 = latest['SMA_50']
                    macd_line = latest['MACD_12_26_9']
                    macd_signal = latest['MACDs_12_26_9']
                    rsi = latest['RSI_14']
                    adx = latest['ADX_14']
                    support = latest['Support_20d']
                    resistance = latest['Resistance_20d']

                    sma_rec = "Buy" if sma_18 > sma_50 else "Sell"
                    macd_rec = "Buy" if macd_line > macd_signal else "Sell"

                    if pd.isna(adx):
                        trend_strength = "N/A"
                    elif adx > 25:
                        trend_strength = "Strong"
                    elif adx > 20:
                        trend_strength = "Moderate"
                    else:
                        trend_strength = "Weak"

                    results.append({
                        "Ticker": ticker,
                        "Price": f"${current_price:.2f}",
                        "SMA(18)": round(sma_18, 2),
                        "SMA(50)": round(sma_50, 2),
                        "SMA Rec": sma_rec,
                        "MACD": round(macd_line, 2),
                        "MACD Signal": round(macd_signal, 2),
                        "MACD Rec": macd_rec,
                        "RSI (14)": round(rsi, 2),
                        "ADX Trend": f"{round(adx, 2)} ({trend_strength})",
                        "Floor": f"${support:.2f}",
                        "Ceiling": f"${resistance:.2f}"
                    })

                except Exception as e:
                    st.error(f"Error for {ticker}: {e}")

            st.session_state.stock_data = stock_data_dict
            st.session_state.results_data = results
            st.session_state.last_updated = datetime.now().strftime("%I:%M:%S %p")

# ==========================================
# MAIN CANVAS: DASHBOARD DISPLAY
# ==========================================
if st.session_state.results_data:
    df_results = pd.DataFrame(st.session_state.results_data)

    def style_recommendations(val):
        if val == 'Buy':
            return 'color: #00FF00; font-weight: bold; background-color: rgba(0, 255, 0, 0.1);'
        elif val == 'Sell':
            return 'color: #FF0000; font-weight: bold; background-color: rgba(255, 0, 0, 0.1);'
        return ''
    
    styled_df = df_results.style.map(style_recommendations, subset=['SMA Rec', 'MACD Rec'])

    col_title, col_time = st.columns([3, 1])
    with col_title:
        st.subheader("Market Overview", divider="gray")
    with col_time:
        st.write("") 
        st.caption(f"🔄 **Last Updated:** {st.session_state.last_updated}")
        
    st.info("💡 **Click on any row** below to load its interactive charts and detailed metrics.")
    
    event = st.dataframe(
        styled_df, 
        use_container_width=True, 
        hide_index=True,
        on_select="rerun",          
        selection_mode="single-row" 
    )

    # --- Interactive Selected Details ---
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_row = df_results.iloc[selected_idx]
        selected_ticker = selected_row['Ticker']
        hist_df = st.session_state.stock_data[selected_ticker]
        
        st.subheader(f"📊 {selected_ticker} Deep Dive", divider="blue")
        
        # --- KPI Metric Cards ---
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            prev_close = hist_df['Close'].iloc[-2]
            curr_close = hist_df['Close'].iloc[-1]
            pct_change = ((curr_close - prev_close) / prev_close) * 100
            st.metric("Latest Price", f"${curr_close:.2f}", f"{pct_change:.2f}%")
        with col2:
            st.metric("RSI (Momentum)", selected_row['RSI (14)'], "Overbought > 70" if float(selected_row['RSI (14)']) > 70 else "Oversold < 30" if float(selected_row['RSI (14)']) < 30 else "Neutral", delta_color="off")
        with col3:
            st.metric("ADX (Trend Strength)", selected_row['ADX Trend'].split(" ")[0], selected_row['ADX Trend'].split(" ")[1].replace("(","").replace(")",""), delta_color="normal" if "Strong" in selected_row['ADX Trend'] else "off")
        with col4:
            st.metric("Support / Resistance", f"{selected_row['Floor']} / {selected_row['Ceiling']}")

        st.write("")

        # --- Volume Profile Logic ---
        bins = 40
        price_min, price_max = hist_df['Low'].min(), hist_df['High'].max()
        bin_edges = np.linspace(price_min, price_max, bins + 1)
        v_profile, _ = np.histogram(hist_df['Close'], bins=bin_edges, weights=hist_df['Volume'])
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        # --- Professional Stacked 3-Tier Chart ---
        sma_buys = hist_df[hist_df['SMA_Buy']]
        sma_sells = hist_df[hist_df['SMA_Sell']]
        macd_buys = hist_df[hist_df['MACD_Buy']]
        macd_sells = hist_df[hist_df['MACD_Sell']]

        fig = make_subplots(
            rows=3, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03, 
            row_heights=[0.35, 0.35, 0.30] 
        )

        # --- DYNAMIC BOLLINGER BANDS LOOKUP ---
        bb_upper_col = [col for col in hist_df.columns if col.startswith('BBU')][0]
        bb_lower_col = [col for col in hist_df.columns if col.startswith('BBL')][0]

        # TIER 1: Trend (Row 1) 
        fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['SMA_18'], line=dict(color='#00BFFF', width=1.5), name='SMA(18) Fast'), row=1, col=1)
        fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['SMA_50'], line=dict(color='#FFA500', width=1.5), name='SMA(50) Slow'), row=1, col=1)

        # MACD Signals (Tier 1)
        fig.add_trace(go.Scatter(x=macd_buys.index, y=macd_buys['Low'] * 0.98, mode='markers', name='MACD Buy', marker=dict(symbol='triangle-up', size=14, color='#00FF00', line=dict(width=1, color='darkgreen'))), row=1, col=1)
        fig.add_trace(go.Scatter(x=macd_sells.index, y=macd_sells['High'] * 1.02, mode='markers', name='MACD Sell', marker=dict(symbol='triangle-down', size=14, color='#FF0000', line=dict(width=1, color='darkred'))), row=1, col=1)

        # TIER 2: Market Structure - Bollinger Bands, Candlesticks, CLOSE PRICE LINE, & Volume Profile (Row 2)
        # Bollinger Bands added to Row 2 (behind candles)
        fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df[bb_upper_col], mode='lines', line=dict(color='rgba(255, 255, 255, 0.3)', width=1, dash='dash'), name='BB Upper', showlegend=False), row=2, col=1)
        fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df[bb_lower_col], mode='lines', line=dict(color='rgba(255, 255, 255, 0.3)', width=1, dash='dash'), fill='tonexty', fillcolor='rgba(128, 128, 128, 0.1)', name='Bollinger Bands', showlegend=True), row=2, col=1)

        # HIGH CONTRAST Candlesticks
        fig.add_trace(go.Candlestick(
            x=hist_df.index, 
            open=hist_df['Open'], 
            high=hist_df['High'], 
            low=hist_df['Low'], 
            close=hist_df['Close'], 
            name='Candlesticks',
            increasing=dict(line=dict(color='#00FF00', width=1.5), fillcolor='rgba(0, 255, 0, 0.8)'), # Pure Neon Green
            decreasing=dict(line=dict(color='#FF0000', width=1.5), fillcolor='rgba(255, 0, 0, 0.8)')  # Pure Bright Red
        ), row=2, col=1)
        
        # Close Price Line (Increased opacity for better contrast)
        fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['Close'], mode='lines', name='Close Price', line=dict(color='rgba(255, 255, 255, 0.8)', width=1.5)), row=2, col=1)
        
        # Volume Profile plotted on an independent X-axis (x4) mapped to y-axis 2
        fig.add_trace(go.Bar(
            y=bin_centers, x=v_profile, orientation='h', name='Volume Profile',
            marker_color='rgba(0, 191, 255, 0.2)', showlegend=True,
            xaxis='x4', yaxis='y2' 
        ))

        # TIER 3: Momentum - MACD (Row 3)
        colors = ['#2ca02c' if val >= 0 else '#d62728' for val in hist_df['MACDh_12_26_9']]
        fig.add_trace(go.Bar(x=hist_df.index, y=hist_df['MACDh_12_26_9'], marker_color=colors, name='MACD Histogram'), row=3, col=1)
        fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['MACD_12_26_9'], line=dict(color='#00BFFF', width=1.5), name='MACD Line'), row=3, col=1)
        fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['MACDs_12_26_9'], line=dict(color='#FFA500', width=1.5), name='Signal Line'), row=3, col=1)

        # Styling the Layout
        fig.update_layout(
            height=1200, 
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_rangeslider_visible=False,
            xaxis2_rangeslider_visible=False, 
            
            # Independent X-axis (x4) for the Volume Profile
            xaxis4=dict(
                overlaying='x2', 
                side='top', 
                showgrid=False, 
                zeroline=False, 
                showticklabels=False, 
                range=[0, max(v_profile) * 5] 
            )
        )
        
        # Gridlines
        fig.update_yaxes(title_text="Trend ($)", row=1, col=1, showgrid=True, gridcolor='rgba(128, 128, 128, 0.2)')
        fig.update_yaxes(title_text="Structure", row=2, col=1, showgrid=True, gridcolor='rgba(128, 128, 128, 0.2)')
        fig.update_yaxes(title_text="Momentum", row=3, col=1, showgrid=True, gridcolor='rgba(128, 128, 128, 0.2)')
        fig.update_xaxes(showgrid=True, gridcolor='rgba(128, 128, 128, 0.2)')

        st.plotly_chart(fig, use_container_width=True)
