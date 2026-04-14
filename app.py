import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Page Configuration ---
st.set_page_config(page_title="Stock Technical Analysis", page_icon="📈", layout="wide")
st.title("📈 Stock Technical Analysis Dashboard")
st.write("Analyze multiple stocks, adjust timeframes, and **click on any row in the table** to view detailed price action and MACD signals.")

# --- Session State Initialization ---
if 'stock_data' not in st.session_state:
    st.session_state.stock_data = {}
if 'results_data' not in st.session_state:
    st.session_state.results_data = []

# --- User Inputs (Tickers, Period, Interval) ---
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    tickers_input = st.text_input("Enter Stock Tickers (comma-separated):", "AAPL, MSFT, TSLA, NVDA")
    tickers = [ticker.strip().upper() for ticker in tickers_input.split(",") if ticker.strip()]

with col2:
    selected_period = st.selectbox(
        "Historical Period:", 
        ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"], 
        index=3 # Defaults to '1y'
    )

with col3:
    selected_interval = st.selectbox(
        "Chart Interval:", 
        ["30m", "1h", "1d", "1wk", "1mo"], 
        index=2 # Defaults to '1d'
    )

if selected_interval in ["30m", "1h"]:
    st.caption("⚠️ *Note: Yahoo Finance limits 30m data to the last 60 days, and 1h data to the last 2 years.*")

# --- Analysis Logic ---
if st.button("Run Analysis", type="primary"):
    if not tickers:
        st.warning("Please enter at least one ticker.")
    else:
        with st.spinner(f"Fetching {selected_period} of {selected_interval} data and calculating indicators..."):
            results = []
            stock_data_dict = {}

            for ticker in tickers:
                try:
                    df = yf.download(ticker, period=selected_period, interval=selected_interval, progress=False)

                    if df.empty or len(df) < 50:
                        st.error(f"Not enough data for {ticker}. Try a shorter period for intraday intervals.")
                        continue
                    
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)

                    # Calculate Indicators
                    df.ta.sma(length=18, append=True)
                    df.ta.sma(length=50, append=True)
                    df.ta.macd(append=True) 
                    df.ta.rsi(length=14, append=True)
                    df.ta.adx(length=14, append=True)

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
                        trend_strength = "Weak/Sideways"

                    results.append({
                        "Ticker": ticker,
                        "Price": f"${current_price:.2f}",
                        "SMA(18)": round(sma_18, 2),
                        "SMA(50)": round(sma_50, 2),
                        "SMA Rec": sma_rec,
                        "MACD": round(macd_line, 2),
                        "MACD Signal": round(macd_signal, 2),
                        "MACD Rec": macd_rec,
                        "Wilder's RSI": round(rsi, 2),
                        "ADX (Strength)": f"{round(adx, 2)} ({trend_strength})",
                        "Support (Floor)": f"${support:.2f}",
                        "Resistance (Ceil)": f"${resistance:.2f}"
                    })

                except Exception as e:
                    st.error(f"Error calculating data for {ticker}: {e}")

            st.session_state.stock_data = stock_data_dict
            st.session_state.results_data = results

# --- Display Results and Charts ---
if st.session_state.results_data:
    df_results = pd.DataFrame(st.session_state.results_data)

    def style_recommendations(val):
        if val == 'Buy':
            return 'color: #00FF00; font-weight: bold;'
        elif val == 'Sell':
            return 'color: #FF0000; font-weight: bold;'
        return ''
    
    styled_df = df_results.style.map(style_recommendations, subset=['SMA Rec', 'MACD Rec'])

    st.subheader("Technical Analysis Results")
    st.info("💡 **Click on any row** below to view the interactive Price Action and MACD charts.")
    
    event = st.dataframe(
        styled_df, 
        use_container_width=True, 
        hide_index=True,
        on_select="rerun",          
        selection_mode="single-row" 
    )

    # --- Unified Professional Chart Logic ---
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_ticker = df_results.iloc[selected_idx]['Ticker']
        
        st.divider()
        st.subheader(f"📊 {selected_ticker} - Price Action & MACD Signals")
        
        hist_df = st.session_state.stock_data[selected_ticker]

        # Extract Buy/Sell Dates
        sma_buys = hist_df[hist_df['SMA_Buy']]
        sma_sells = hist_df[hist_df['SMA_Sell']]
        macd_buys = hist_df[hist_df['MACD_Buy']]
        macd_sells = hist_df[hist_df['MACD_Sell']]

        # Create Subplots: Row 1 = Price (70%), Row 2 = MACD (30%)
        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.05, 
            row_heights=[0.7, 0.3],
            subplot_titles=("Price Action (Close) & SMAs", "MACD & Momentum")
        )

        # --- Top Chart: Price Action (Line Chart) ---
        # 1. Close Price Line
        fig.add_trace(go.Scatter(
            x=hist_df.index, y=hist_df['Close'], 
            mode='lines', name='Close Price', 
            line=dict(color='white', width=2) # Using white/light gray to stand out against standard dark/light themes
        ), row=1, col=1)

        # 2. SMAs
        fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['SMA_18'], line=dict(color='#00BFFF', width=1.5), name='SMA(18)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['SMA_50'], line=dict(color='#FFA500', width=1.5), name='SMA(50)'), row=1, col=1)

        # 3. MACD Signals plotted on the Price Chart
        # We still use the 'Low' and 'High' columns just to offset the arrows slightly so they don't cover the price line
        fig.add_trace(go.Scatter(
            x=macd_buys.index, y=macd_buys['Low'] * 0.98, mode='markers', 
            name='MACD Buy Signal', marker=dict(symbol='triangle-up', size=14, color='#00FF00', line=dict(width=1, color='darkgreen'))
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=macd_sells.index, y=macd_sells['High'] * 1.02, mode='markers', 
            name='MACD Sell Signal', marker=dict(symbol='triangle-down', size=14, color='#FF0000', line=dict(width=1, color='darkred'))
        ), row=1, col=1)

        # --- Bottom Chart: MACD ---
        colors = ['#2ca02c' if val >= 0 else '#d62728' for val in hist_df['MACDh_12_26_9']]
        
        fig.add_trace(go.Bar(x=hist_df.index, y=hist_df['MACDh_12_26_9'], marker_color=colors, name='MACD Histogram'), row=2, col=1)
        fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['MACD_12_26_9'], line=dict(color='#00BFFF', width=1.5), name='MACD Line'), row=2, col=1)
        fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['MACDs_12_26_9'], line=dict(color='#FFA500', width=1.5), name='Signal Line'), row=2, col=1)

        # Clean up layout
        fig.update_layout(
            height=700,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=50, b=20)
        )
        
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Value", row=2, col=1)

        st.plotly_chart(fig, use_container_width=True)
