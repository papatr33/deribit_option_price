import streamlit as st
import requests
import datetime
import pandas as pd
from streamlit_lightweight_charts import renderLightweightCharts

# Set the page to full width
st.set_page_config(layout="wide")

# Constants
API_URL = 'https://history.deribit.com/api/v2/public/'

# Helper Functions
def generate_contract_name(coin, expiry_date, strike_price, option_type):
    """
    Generate the contract name based on the inputs.
    """
    # Format expiry date without leading zero
    day_str = str(expiry_date.day)
    monthyear_str = expiry_date.strftime('%b%y').upper()
    expiry_str = f"{day_str}{monthyear_str}"
    contract_name = f"{coin}-{expiry_str}-{int(strike_price)}-{option_type[0]}"
    return contract_name

def get_historical_prices_tradingview(instrument_name, start_timestamp, end_timestamp, resolution):
    """
    Retrieve historical prices and volumes using the get_tradingview_chart_data endpoint.
    """
    params = {
        'instrument_name': instrument_name,
        'start_timestamp': int(start_timestamp * 1000),  # Convert to milliseconds
        'end_timestamp': int(end_timestamp * 1000),      # Convert to milliseconds
        'resolution': resolution
    }
    try:
        response = requests.get(API_URL + 'get_tradingview_chart_data', params=params)
        data = response.json()
        if 'result' in data:
            result = data['result']
            df = pd.DataFrame({
                'time': [int(t / 1000) for t in result['ticks']],  # Convert timestamps to seconds
                'value': result['close'],                          # For area chart (closing prices)
                'volume': result['volume']                         # Corrected from 'volumes' to 'volume'
            })
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

def format_data_for_chart(df):
    """
    Format the DataFrame into the structure expected by renderLightweightCharts.
    """
    price_data = df[['time', 'value']].to_dict('records')
    volume_data = df[['time', 'volume']].to_dict('records')
    return price_data, volume_data

# Streamlit App
st.title('Deribit Option Price Viewer')

st.sidebar.header('Option Contract Selection')

# Option Contract Inputs
coin = st.sidebar.selectbox('Coin', ['BTC', 'ETH', 'SOL'], key='coin')
expiry_date = st.sidebar.date_input('Expiry Date',  key='expiry_date')
strike_price = st.sidebar.number_input('Strike Price', min_value=0, step=500, key='strike_price')
option_type = st.sidebar.selectbox('Option Type', ['Call', 'Put'], key='option_type')

# Generate Contract Name
if st.sidebar.button('Generate Contract Name'):
    expiry_datetime = datetime.datetime.combine(expiry_date, datetime.time())
    contract_name = generate_contract_name(coin, expiry_datetime, strike_price, option_type)
    st.session_state['contract_name'] = contract_name
    st.sidebar.write(f'**Contract Name:** {contract_name}')
else:
    contract_name = st.session_state.get('contract_name', None)
    if contract_name:
        st.sidebar.write(f'**Contract Name:** {contract_name}')

if contract_name:
    # Main Page Inputs

    # Create three columns for Start Date, End Date, and Price Interval
    
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            start_date = st.date_input('Start Date', value=expiry_date - datetime.timedelta(days=30), max_value=datetime.date.today(), key='start_date')
        with col2:
            end_date = st.date_input('End Date', value=datetime.date.today(), max_value=datetime.date.today(), key='end_date')
        with col3:
            interval = st.selectbox('Price Interval', ['Daily', 'Hourly', '15-Minute'], key='interval')

    # Map interval to resolution
    resolution_map = {
        'Daily': 'D',
        'Hourly': '60',
        '15-Minute': '15'
    }
    resolution = resolution_map[interval]

    # Add a button to retrieve historical prices
    if st.button('Get Historical Prices'):
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
        with st.spinner('Fetching historical prices...'):
            df = get_historical_prices_tradingview(contract_name, start_datetime.timestamp(), end_datetime.timestamp(), resolution)
        
        if not df.empty:
            st.success('Historical prices retrieved successfully!')

            # Format data for the chart
            price_data, volume_data = format_data_for_chart(df)

            # Define the chart options
            chart_options = {
                "layout": {
                    "textColor": 'black',
                    "background": {
                        "type": 'solid',
                        "color": 'white'
                    }
                },
                "priceScale": {
                    "position": 'right',
                    # Set y-axis to display 4 decimal places
                    "priceFormat": {
                        "type": 'price',
                        "precision": 4,
                        "minMove": 0.0001
                    }
                },
                "timeScale": {
                    "timeVisible": True,
                    "secondsVisible": False,
                },
                "grid": {
                    "vertLines": {
                        "color": '#eee'
                    },
                    "horzLines": {
                        "color": '#eee'
                    }
                }
            }

            # Define the price series as an area chart
            price_series = {
                "type": 'Area',
                "data": price_data,
                "options": {
                    "topColor": 'rgba(38,198,218, 0.56)',
                    "bottomColor": 'rgba(38,198,218, 0.04)',
                    "lineColor": 'rgba(38,198,218, 1)',
                    "lineWidth": 2,
                    # Ensure the series uses 4 decimal places
                    "priceFormat": {
                        "type": 'price',
                        "precision": 4,
                        "minMove": 0.0001
                    },
                },
            }

            # Define the volume series as a histogram
            volume_series = {
                "type": 'Histogram',
                "data": volume_data,
                "options": {
                    "color": '#26a69a',
                    "priceFormat": {
                        "type": 'volume',
                    },
                    "priceScaleId": '',  # Overlay volume on the main chart
                },
                "priceScale": {
                    "scaleMargins": {
                        "top": 0.8,
                        "bottom": 0,
                    }
                },
            }

            # Combine the series
            series = [price_series, volume_series]

            # Render the chart
            st.write(f"### Historical Prices for {contract_name}")
            renderLightweightCharts([{
                "chart": chart_options,
                "series": series
            }], key='chart')

        else:
            st.error('No data available for the selected contract and date range.')