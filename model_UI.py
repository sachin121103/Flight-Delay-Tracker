import streamlit as st
import pandas as pd
import numpy as np
import hopsworks
import joblib
import json
from datetime import datetime
import os

# Get API key from Streamlit secrets or environment
try:
    hopsworks_api_key = st.secrets["HOPSWORKS_API_KEY"]
except (KeyError, FileNotFoundError):
    hopsworks_api_key = os.getenv("HOPSWORKS_API_KEY")
    if not hopsworks_api_key:
        st.error("⚠️ HOPSWORKS_API_KEY not found. Please add it to Streamlit secrets.")
        st.info("Go to: App Menu → Settings → Secrets")
        st.stop()

# --- Configuration ---

@st.cache_resource
def load_resources():
    """Connect to Hopsworks and download the model."""
    try:
        # Show connecting message
        with st.spinner("🔌 Connecting to Hopsworks..."):
            project = hopsworks.login(
                api_key_value=hopsworks_api_key, 
                host="eu-west.cloud.hopsworks.ai"
            )
        
        with st.spinner("📦 Loading feature store..."):
            fs = project.get_feature_store()
            mr = project.get_model_registry()
        
        # Download model from registry
        with st.spinner("🤖 Downloading model..."):
            model = mr.get_model(name='flight_delay_predictor', version=1)
            model_dir = model.download()
            model_pipeline = joblib.load(f"{model_dir}/model.pkl")
        
        with open(f"{model_dir}/metadata.json", 'r') as f:
            metadata = json.load(f)
        
        st.success("✅ Successfully connected to Hopsworks!")
        return fs, model_pipeline, metadata, project
        
    except Exception as e:
        st.error(f"❌ Failed to connect to Hopsworks: {str(e)}")
        st.info("Please check that your HOPSWORKS_API_KEY is correctly set in Streamlit secrets.")
        st.stop()
        return None, None, None, None

def engineer_features(batch_data):
    """Apply the same feature engineering as in the training pipeline."""
    # Create time-based features
    batch_data['hour'] = pd.to_datetime(batch_data['scheduled_time']).dt.hour
    batch_data['day_of_week'] = pd.to_datetime(batch_data['scheduled_time']).dt.dayofweek
    batch_data['month'] = pd.to_datetime(batch_data['scheduled_time']).dt.month
    
    # Create time_of_day bins
    batch_data['time_of_day'] = pd.cut(
        batch_data['hour'], 
        bins=[0, 6, 12, 18, 24], 
        labels=['night', 'morning', 'afternoon', 'evening'],
        include_lowest=True
    )
    
    # Create weather impact feature
    weather_weights = {'clear': 0, 'fog': 2, 'rain': 1, 'rain_windy': 3, 'snow': 4, 'windy': 2}
    batch_data['weather_impact'] = batch_data['weather_condition'].map(weather_weights).fillna(0)
    
    # Create weather-related binary features
    batch_data['high_wind'] = (batch_data['wind_speed'] > 15).astype(int)
    batch_data['low_visibility'] = (batch_data['visibility'] < 5).astype(int)
    batch_data['peak_international'] = (
        batch_data['is_peak_travel'] & (batch_data['route_type'] == 'international')
    ).astype(int)
    
    # Convert boolean columns to int
    for col in ['is_weekend', 'is_holiday', 'is_school_break', 'is_peak_travel', 
                'is_sportlov', 'is_summer_break', 'is_christmas_break']:
        if col in batch_data.columns:
            batch_data[col] = batch_data[col].fillna(False).astype(int)
    
    return batch_data

# --- UI Setup ---
st.set_page_config(page_title="Arlanda Flight Delay Predictor", page_icon="✈️")
st.title("✈️ Arlanda Flight Delay Predictor")
st.markdown("Enter your flight number to see the estimated risk of delay for today.")

# Initialize Hopsworks connection
if 'fs' not in st.session_state:
    with st.spinner("Connecting to Hopsworks Feature Store..."):
        st.session_state.fs, st.session_state.model, st.session_state.meta, st.session_state.project = load_resources()

# --- User Input ---
flight_input = st.text_input("Enter Flight Number (e.g., SK535):").strip().upper()

if st.button("Check Delay Risk"):
    if flight_input:
        fs = st.session_state.fs
        
        # 1. Fetch data from Feature Groups
        today = datetime.now().strftime("%Y-%m-%d")
        
        flights_fg = fs.get_feature_group('flight_schedules', version=1)
        temporal_fg = fs.get_feature_group('temporal_features', version=1)
        weather_fg = fs.get_feature_group('weather_features', version=1)
        
        # Query specific flight
        df_flight = flights_fg.filter(flights_fg.flight_number == flight_input).read()
        
        if df_flight.empty:
            st.error(f"No flight data found for {flight_input} today.")
        else:
            # 2. Merge with temporal features
            df_flight['date'] = pd.to_datetime(df_flight['scheduled_time']).dt.date.astype(str)
            df_temp = temporal_fg.filter(temporal_fg.date == today).read()
            
            batch = df_flight.merge(df_temp, on='date', how='left', suffixes=('', '_temporal'))
            
            # 3. Merge with weather features
            batch['scheduled_hour'] = pd.to_datetime(batch['scheduled_time']).dt.floor('H')
            df_weather = weather_fg.read()
            df_weather['weather_hour'] = pd.to_datetime(df_weather['timestamp']).dt.floor('H')
            
            batch = batch.merge(
                df_weather,
                left_on=['arn_airport_role', 'scheduled_hour'],
                right_on=['airport_code', 'weather_hour'],
                how='left',
                suffixes=('', '_weather')
            )
            
            # 4. Apply feature engineering
            batch = engineer_features(batch)
            
            # 5. Prepare features for prediction
            categorical_features = st.session_state.meta['categorical_features']
            numerical_features = st.session_state.meta['numerical_features']
            all_features = categorical_features + numerical_features
            
            # Extract features and handle missing values
            X = batch[all_features].copy()
            
            # Fill numerical features with median
            for col in numerical_features:
                if col in X.columns:
                    X[col] = X[col].fillna(X[col].median() if X[col].notna().any() else 0)
            
            # Fill categorical features with mode or 'UNKNOWN'
            for col in categorical_features:
                if col in X.columns:
                    X[col] = X[col].fillna(X[col].mode()[0] if len(X[col].mode()) > 0 else 'UNKNOWN')
            
            # 6. Make prediction
            prob = st.session_state.model.predict_proba(X)[0][1]
            is_delayed = st.session_state.model.predict(X)[0]

            # 7. Display Results
            st.divider()
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Delay Probability", f"{prob:.1%}")
            
            with col2:
                status = "🔴 DELAY LIKELY" if is_delayed == 1 else "🟢 LIKELY ON TIME"
                st.subheader(status)

            st.write(f"**Route:** {batch['route'].iloc[0]}")
            st.write(f"**Scheduled Time:** {batch['scheduled_time'].iloc[0]}")
            
            # Show weather conditions if available
            if 'weather_condition' in batch.columns and batch['weather_condition'].notna().any():
                st.write(f"**Weather Conditions:** {batch['weather_condition'].iloc[0]}")
            
            if prob > 0.7:
                st.warning("⚠️ High risk of delay detected. Consider checking with your airline.")
            elif prob > 0.4:
                st.info("ℹ️ Moderate delay risk. Monitor your flight status.")
            else:
                st.success("✅ Low delay risk. Flight should depart on time.")
                
    else:
        st.warning("Please enter a flight number.")