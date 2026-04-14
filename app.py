import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- Page Configuration ---
st.set_page_config(page_title="Stock Technical Analysis", page_icon="📈", layout="wide")
st.title("📈 Stock Technical Analysis Dashboard")
st.write("Analyze multiple stocks using SMA, MACD, RSI, ADX, and identify recent Support/Resistance levels.")

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

            for ticker in tickers:
                try:
                    # Fetch 1 year of daily data to ensure enough history for the 50-day SMA and ADX
                    df = yf.download(ticker, period="1y", progress=False)

                    if df.empty or len(df) < 50:
                        st.error(f"Not enough historical data for {ticker}. Skipping.")
                        continue
                    
                    # Handle yfinance multi-index columns (happens in newer yfinance versions)
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)

                    # --- 1. Simple Moving Averages (18 & 50) ---
                    df.ta.sma(length=18, append=True)
                    df.ta.sma(length=50, append=True)

                    # --- 2. MACD (Fast 12, Slow 26, Signal 9) ---
                    df.ta.macd(append=True)

                    # --- 3. Wilder's RSI (14) ---
                    df.ta.rsi(length=14, append=True)

                    # --- 4. ADX Strength (14) ---
                    df.ta.adx(length=14, append=True)

                    # --- 5. Support & Resistance (20-day rolling High/Low) ---
                    df['Support_20d'] = df['Low'].rolling(window=20).min()
                    df['Resistance_20d'] = df['High'].rolling(window=20).max()

                    # Extract the most recent day's values
                    latest = df.iloc[-1]

                    # Map pandas_ta default column names
                    current_price = latest['Close']
                    sma_18 = latest['SMA_18']
                    sma_50 = latest['SMA_50']
                    macd_line = latest['MACD_12_26_9']
                    macd_signal = latest['MACDs_12_26_9']
                    rsi = latest['RSI_14']
                    adx = latest['ADX_14']
                    support = latest['Support_20d']
                    resistance = latest['Resistance_20d']

                    # --- Recommendations Logic ---
                    # SMA Rec: Bullish if faster SMA is above slower SMA
                    sma_rec = "Buy" if sma_18 > sma_50 else "Sell"
                    
                    # MACD Rec: Bullish if MACD line is above the Signal line
                    macd_rec = "Buy" if macd_line > macd_signal else "Sell"

                    # Contextualize ADX Strength (Trend strength, regardless of direction)
                    if pd.isna(adx):
                        trend_strength = "N/A"
                    elif adx > 25:
                        trend_strength = "Strong"
                    elif adx > 20:
                        trend_strength = "Moderate"
                    else:
                        trend_strength = "Weak/Sideways"

                    # Append to results
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

            # --- Display Results ---
            if results:
                df_results = pd.DataFrame(results)

                # Apply styling to highlight Buy/Sell recommendations
                def style_recommendations(val):
                    if val == 'Buy':
                        return 'color: #00FF00; font-weight: bold;' # Green
                    elif val == 'Sell':
                        return 'color: #FF0000; font-weight: bold;' # Red
                    return ''
                
                # Apply styling to the dataframe (compatible with modern pandas)
                styled_df = df_results.style.map(
                    style_recommendations, 
                    subset=['SMA Rec', 'MACD Rec']
                )

                st.subheader("Technical Analysis Results")
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
