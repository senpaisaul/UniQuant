import streamlit as st
import yfinance as yf
from utils.market_data import MarketDataService
# Import sub-modules
import modules.stock_prediction.historical as historical
import modules.stock_prediction.prediction as prediction
import modules.stock_prediction.session_log as session_log

def render():
    st.title("📈 Stock Price Analysis & Prediction")

    # Sidebar for stock selection
    st.sidebar.markdown("---")
    st.sidebar.header("Stock Selection")
    ticker = st.sidebar.text_input("Enter Stock Ticker", value="AAPL", key="stock_ticker_input").upper()
    
    # Navigation within the module
    page = st.sidebar.radio("Navigate", ["📊 Historical Analysis", "🔮 Price Prediction", "📋 Session Log"], key="stock_nav")

    # Show activity count in sidebar
    if 'stock_activity_log' in st.session_state and st.session_state.stock_activity_log:
        st.sidebar.markdown("---")
        st.sidebar.info(f"📋 **Session Activities:** {len(st.session_state.stock_activity_log)}")
        
        # Show last activity
        last_activity = st.session_state.stock_activity_log[-1]
        st.sidebar.caption(f"Last: {last_activity['activity_type']} - {last_activity['ticker']}")

    st.sidebar.markdown("---")

    # Load data if we are not in Session Log
    data = None
    if page != "📋 Session Log":
        data = MarketDataService.fetch_history(ticker)
        
        if data is None or data.empty:
            st.error(f"Could not load data for {ticker}. Please check the ticker symbol.")
            return

        # Display stock info in sidebar
        info = MarketDataService.get_info(ticker)
        company_name = info.get('longName', ticker)
        st.sidebar.success(f"**{company_name}**")
        st.sidebar.metric("Current Price", f"${data['Close'].iloc[-1]:.2f}")

    # Route to appropriate page
    if page == "📊 Historical Analysis":
        historical.show(data, ticker)
    elif page == "🔮 Price Prediction":
        prediction.show(data, ticker)
    else:
        session_log.show()
