import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- Page Configuration ---
st.set_page_config(page_title="Stock Technical Analysis", page_icon="📈", layout="wide")
st.title("📈 Stock Technical Analysis Dashboard")
st.write("Analyze multiple stocks and **click on any row in the table** to view its SMA and MACD charts.")

# --- Session State Initialization ---
# We use session state to store data so the app doesn't re-download data when we click a row
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

                    # Save dataframe for charting later
                    stock_data_dict[ticker] = df

                    # Extract latest values
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

                    # Recommendations
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

            # Save to session state to persist after button click
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
    st.info("💡 **Click on any row** below to view the SMA and MACD charts for that stock.")
    
    # Render the interactive dataframe
    event = st.dataframe(
        styled_df, 
        use_container_width=True, 
        hide_index=True,
        on_select="rerun",          # Triggers a rerun when a row is clicked
        selection_mode="single_row" # Restricts selection to one row at a time
    )

    # --- Chart Generation Logic ---
    # Check if the user has selected a row
    if event.selection.rows:
        # Get the index of the selected row
        selected_idx = event.selection.rows[0]
        
        # Look up the ticker symbol from that row
        selected_ticker = df_results.iloc[selected_idx]['Ticker']
        
        st.divider()
        st.subheader(f"📊 Detailed Charts for {selected_ticker}")
        
        # Retrieve the historical data for the selected ticker from session state
        hist_df = st.session_state.stock_data[selected_ticker]

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Price vs SMA (18/50)**")
            # Filter the dataframe to only the columns we want to plot
            sma_chart_data = hist_df[['Close', 'SMA_18', 'SMA_50']]
            st.line_chart(sma_chart_data)

        with col2:
            st.write("**MACD Trend**")
            # MACD Line and Signal Line
            macd_chart_data = hist_df[['MACD_12_26_9', 'MACDs_12_26_9']]
            st.line_chart(macd_chart_data)
