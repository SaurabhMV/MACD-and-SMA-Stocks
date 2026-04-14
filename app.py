import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

# --- Page Configuration ---
st.set_page_config(page_title="Stock Technical Analysis", page_icon="📈", layout="wide")
st.title("📈 Stock Technical Analysis Dashboard")
st.write("Analyze multiple stocks and **click on any row in the table** to view its SMA and MACD charts with Buy/Sell signals.")

# --- Session State Initialization ---
if 'stock_data' not in st.session_state:
    st.session_state.stock_data = {}
if 'results_data' not in st.session_state:
    st.session_state.results_data = []

# --- User Inputs ---
tickers_input = st.text_input("Enter Stock Tickers (comma-separated):", "AAPL, MSFT, TSLA, NVDA")
tickers = [ticker.strip().upper() for ticker in tickers_input.split(",") if ticker.strip()]

# --- Analysis Logic ---
if st.button("Run Analysis", type="primary"):
    if not tickers:
        st.warning("Please enter at least one ticker.")
    else:
        with st.spinner("Fetching market data and calculating indicators..."):
            results = []
            stock_data_dict = {}

            for ticker in tickers:
                try:
                    df = yf.download(ticker, period="1y", progress=False)

                    if df.empty or len(df) < 50:
                        st.error(f"Not enough historical data for {ticker}. Skipping.")
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

                    # --- Calculate Historical Crossovers for Chart Signals ---
                    # SMA Crossovers
                    df['SMA_Buy'] = (df['SMA_18'] > df['SMA_50']) & (df['SMA_18'].shift(1) <= df['SMA_50'].shift(1))
                    df['SMA_Sell'] = (df['SMA_18'] < df['SMA_50']) & (df['SMA_18'].shift(1) >= df['SMA_50'].shift(1))

                    # MACD Crossovers
                    df['MACD_Buy'] = (df['MACD_12_26_9'] > df['MACDs_12_26_9']) & (df['MACD_12_26_9'].shift(1) <= df['MACDs_12_26_9'].shift(1))
                    df['MACD_Sell'] = (df['MACD_12_26_9'] < df['MACDs_12_26_9']) & (df['MACD_12_26_9'].shift(1) >= df['MACDs_12_26_9'].shift(1))

                    # Save dataframe for charting later
                    stock_data_dict[ticker] = df

                    # Extract latest values for the table
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

                    # Current Day Recommendations
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

            # Save to session state
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
    
    styled_df = df_results.style.map(
        style_recommendations, 
        subset=['SMA Rec', 'MACD Rec']
    )

    st.subheader("Technical Analysis Results")
    st.info("💡 **Click on any row** below to view the interactive SMA and MACD charts.")
    
    event = st.dataframe(
        styled_df, 
        use_container_width=True, 
        hide_index=True,
        on_select="rerun",          
        selection_mode="single-row" 
    )

    # --- Chart Generation Logic (Plotly with Signals) ---
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_ticker = df_results.iloc[selected_idx]['Ticker']
        
        st.divider()
        st.subheader(f"📊 Detailed Charts for {selected_ticker}")
        
        hist_df = st.session_state.stock_data[selected_ticker]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**Price vs SMA (18/50) - {selected_ticker}**")
            
            fig_sma = go.Figure()
            # Plot Close Price & SMAs
            fig_sma.add_trace(go.Scatter(x=hist_df.index, y=hist_df['Close'], name='Close Price', line=dict(color='gray', width=1.5)))
            fig_sma.add_trace(go.Scatter(x=hist_df.index, y=hist_df['SMA_18'], name='SMA(18) Fast', line=dict(color='blue', width=2)))
            fig_sma.add_trace(go.Scatter(x=hist_df.index, y=hist_df['SMA_50'], name='SMA(50) Slow', line=dict(color='orange', width=2)))
            
            # Extract Buy/Sell Dates for SMA
            sma_buys = hist_df[hist_df['SMA_Buy']]
            sma_sells = hist_df[hist_df['SMA_Sell']]
            
            # Plot SMA Signals
            fig_sma.add_trace(go.Scatter(x=sma_buys.index, y=sma_buys['SMA_18'], mode='markers', name='Buy Signal', marker=dict(symbol='triangle-up', size=14, color='#00FF00', line=dict(width=1, color='darkgreen'))))
            fig_sma.add_trace(go.Scatter(x=sma_sells.index, y=sma_sells['SMA_18'], mode='markers', name='Sell Signal', marker=dict(symbol='triangle-down', size=14, color='#FF0000', line=dict(width=1, color='darkred'))))

            fig_sma.update_layout(
                xaxis_title="Date", yaxis_title="Price ($)", hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=0, r=0, t=30, b=0)
            )
            st.plotly_chart(fig_sma, use_container_width=True)

        with col2:
            st.markdown(f"**MACD & Momentum - {selected_ticker}**")
            
            fig_macd = go.Figure()
            
            # Histogram Colors
            colors = ['#2ca02c' if val >= 0 else '#d62728' for val in hist_df['MACDh_12_26_9']]
            
            # Plot Histogram & Lines
            fig_macd.add_trace(go.Bar(x=hist_df.index, y=hist_df['MACDh_12_26_9'], name='Histogram', marker_color=colors))
            fig_macd.add_trace(go.Scatter(x=hist_df.index, y=hist_df['MACD_12_26_9'], name='MACD Line', line=dict(color='blue', width=2)))
            fig_macd.add_trace(go.Scatter(x=hist_df.index, y=hist_df['MACDs_12_26_9'], name='Signal Line', line=dict(color='orange', width=2)))
            
            # Extract Buy/Sell Dates for MACD
            macd_buys = hist_df[hist_df['MACD_Buy']]
            macd_sells = hist_df[hist_df['MACD_Sell']]
            
            # Plot MACD Signals
            fig_macd.add_trace(go.Scatter(x=macd_buys.index, y=macd_buys['MACD_12_26_9'], mode='markers', name='Buy Signal', marker=dict(symbol='triangle-up', size=14, color='#00FF00', line=dict(width=1, color='darkgreen'))))
            fig_macd.add_trace(go.Scatter(x=macd_sells.index, y=macd_sells['MACD_12_26_9'], mode='markers', name='Sell Signal', marker=dict(symbol='triangle-down', size=14, color='#FF0000', line=dict(width=1, color='darkred'))))

            fig_macd.update_layout(
                xaxis_title="Date", yaxis_title="MACD Value", hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=0, r=0, t=30, b=0)
            )
            st.plotly_chart(fig_macd, use_container_width=True)
