import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from .session_log import log_activity

def calculate_indicators(data):
    """Calculate technical indicators"""
    df = data.copy()
    
    # Moving Averages
    df['SMA_20'] = SMAIndicator(close=df['Close'], window=20).sma_indicator()
    df['SMA_50'] = SMAIndicator(close=df['Close'], window=50).sma_indicator()
    df['EMA_20'] = EMAIndicator(close=df['Close'], window=20).ema_indicator()
    
    # RSI
    df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
    
    # MACD
    macd = MACD(close=df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Hist'] = macd.macd_diff()
    
    # Bollinger Bands
    bb = BollingerBands(close=df['Close'], window=20, window_dev=2)
    df['BB_High'] = bb.bollinger_hband()
    df['BB_Low'] = bb.bollinger_lband()
    df['BB_Mid'] = bb.bollinger_mavg()
    
    return df

def show(data, ticker):
    st.header(f"📊 Historical Analysis - {ticker}")
    
    # Calculate indicators
    df = calculate_indicators(data)
    
    # Log this analysis activity
    # Use namespaced session state key
    if 'stock_last_analysis_ticker' not in st.session_state or st.session_state.stock_last_analysis_ticker != ticker:
        log_activity(
            activity_type='Analysis',
            ticker=ticker,
            period='All Time',
            current_price=data['Close'].iloc[-1],
            price_high=data['High'].max(),
            price_low=data['Low'].min()
        )
        st.session_state.stock_last_analysis_ticker = ticker
        st.toast(f"✅ Analysis logged for {ticker}", icon="📊")
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        period = st.selectbox("Select Time Period", 
                             ["1 Month", "3 Months", "6 Months", "1 Year", "2 Years", "All"],
                             index=3,
                             key="stock_analysis_period")
    
    # Filter data based on period
    if period != "All":
        days_map = {"1 Month": 30, "3 Months": 90, "6 Months": 180, "1 Year": 365, "2 Years": 730}
        days = days_map[period]
        df = df.tail(days)
    
    # Summary Statistics
    st.subheader("📈 Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Current Price", f"${df['Close'].iloc[-1]:.2f}")
    with col2:
        change = df['Close'].iloc[-1] - df['Close'].iloc[0]
        pct_change = (change / df['Close'].iloc[0]) * 100
        st.metric("Period Change", f"${change:.2f}", f"{pct_change:.2f}%")
    with col3:
        st.metric("Highest", f"${df['High'].max():.2f}")
    with col4:
        st.metric("Lowest", f"${df['Low'].min():.2f}")
    
    st.markdown("---")
    
    # Price Chart with Moving Averages
    st.subheader("💹 Price Chart with Moving Averages")
    fig1 = go.Figure()
    
    fig1.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Price'
    ))
    
    fig1.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], 
                              name='SMA 20', line=dict(color='orange', width=1)))
    fig1.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], 
                              name='SMA 50', line=dict(color='blue', width=1)))
    fig1.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], 
                              name='EMA 20', line=dict(color='purple', width=1, dash='dash')))
    
    fig1.update_layout(
        title=f"{ticker} Price with Moving Averages",
        yaxis_title="Price ($)",
        xaxis_title="Date",
        height=500,
        hovermode='x unified',
        template='plotly_dark'
    )
    
    st.plotly_chart(fig1, use_container_width=True)
    
    # Bollinger Bands
    st.subheader("📊 Bollinger Bands")
    fig2 = go.Figure()
    
    fig2.add_trace(go.Scatter(x=df.index, y=df['BB_High'], 
                              name='Upper Band', line=dict(color='red', width=1)))
    fig2.add_trace(go.Scatter(x=df.index, y=df['BB_Mid'], 
                              name='Middle Band', line=dict(color='gray', width=1)))
    fig2.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], 
                              name='Lower Band', line=dict(color='green', width=1)))
    fig2.add_trace(go.Scatter(x=df.index, y=df['Close'], 
                              name='Close Price', line=dict(color='white', width=2)))
    
    fig2.update_layout(
        title=f"{ticker} Bollinger Bands",
        yaxis_title="Price ($)",
        xaxis_title="Date",
        height=400,
        hovermode='x unified',
        template='plotly_dark'
    )
    
    st.plotly_chart(fig2, use_container_width=True)
    
    # Volume Chart
    st.subheader("📊 Trading Volume")
    fig3 = go.Figure()
    
    colors = ['red' if row['Close'] < row['Open'] else 'green' for _, row in df.iterrows()]
    
    fig3.add_trace(go.Bar(
        x=df.index,
        y=df['Volume'],
        name='Volume',
        marker_color=colors
    ))
    
    fig3.update_layout(
        title=f"{ticker} Trading Volume",
        yaxis_title="Volume",
        xaxis_title="Date",
        height=300,
        template='plotly_dark'
    )
    
    st.plotly_chart(fig3, use_container_width=True)
    
    # Technical Indicators
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📉 RSI (Relative Strength Index)")
        fig4 = go.Figure()
        
        fig4.add_trace(go.Scatter(x=df.index, y=df['RSI'], 
                                  name='RSI', line=dict(color='cyan', width=2)))
        fig4.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
        fig4.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")
        
        fig4.update_layout(
            yaxis_title="RSI",
            xaxis_title="Date",
            height=300,
            template='plotly_dark'
        )
        
        st.plotly_chart(fig4, use_container_width=True)
    
    with col2:
        st.subheader("📈 MACD")
        fig5 = go.Figure()
        
        fig5.add_trace(go.Scatter(x=df.index, y=df['MACD'], 
                                  name='MACD', line=dict(color='blue', width=2)))
        fig5.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], 
                                  name='Signal', line=dict(color='orange', width=2)))
        fig5.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], 
                              name='Histogram', marker_color='gray'))
        
        fig5.update_layout(
            yaxis_title="MACD",
            xaxis_title="Date",
            height=300,
            template='plotly_dark'
        )
        
        st.plotly_chart(fig5, use_container_width=True)
    
    # Price Distribution
    st.subheader("📊 Price Distribution")
    fig6 = go.Figure()
    
    fig6.add_trace(go.Histogram(x=df['Close'], nbinsx=50, 
                                name='Price Distribution',
                                marker_color='lightblue'))
    
    fig6.update_layout(
        title=f"{ticker} Price Distribution",
        xaxis_title="Price ($)",
        yaxis_title="Frequency",
        height=300,
        template='plotly_dark'
    )
    
    st.plotly_chart(fig6, use_container_width=True)
