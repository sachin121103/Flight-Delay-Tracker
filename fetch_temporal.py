"""This is the file that contains getting information regarding holidays, school breaks etc. to determine load"""

import pandas as pd
import requests
from datetime import datetime, timedelta
import sys
from hopsworks_utils import get_feature_store, get_or_create_feature_group

sys.path.append('.')

def fetch_swedish_holidays(year):
    url = f"https://api.dagsmart.se/holidays?year={year}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        holidays = []

        for h in data:
            holidays.append(h["date"])

        return holidays
    
    except Exception as e:
        print(f"Error: {e}")
        return []
    
# If need be: Below is an array of Swedish holidays (2026 only):
# ['2026-01-01', '2026-01-06', '2026-04-03', '2026-04-04', '2026-04-05', '2026-04-06', '2026-05-01', '2026-05-14', '2026-05-23', '2026-05-24', '2026-06-06', '2026-06-19', '2026-06-20', '2026-10-31', '2026-12-24', '2026-12-25', '2026-12-26', '2026-12-31']

def create_temporal_features(start_date, end_date):
    dates = pd.date_range(start=start_date, end=end_date, freq='D')

    years = list(set([d.year for d in dates]))
    holidays = []
    for year in years:
        holidays.extend(fetch_swedish_holidays(year))
    
    holiday_set = set(holidays)
    temporal_data = []

    for date in dates:
        date_str = date.strftime("%Y-%m-%d")

        is_sports_break = (date.month == 2 and 10 <= date.day <= 24)
        is_summer_break = (date.month == 6 and date.day > 14) or (date.month==7) or (date.month==8 and date.day < 16)
        is_winter_break = (date.month == 12 and date.day > 19) or (date.month == 1 and date.day < 8)
        is_peak_travel = is_summer_break or is_winter_break

        features = {
            "date": date_str,
            "year": date.year,
            "month": date.month,
            "day": date.day,
            "day_of_week": date.dayofweek,
            "is_weekend": date.dayofweek >= 5,
            "is_holiday": date_str in holiday_set,
            "is_sports_break": is_sports_break,
            "is_summer_break": is_summer_break,
            "is_winter_break": is_winter_break,
            "is_school_break": is_winter_break or is_summer_break or is_sports_break,
            "is_peak_travel": is_peak_travel,
            "season": "winter" if date.month in [1,2,12] else "spring" if date.month in [3,4,5] else "summer" if date.month in [6,7,8] else "fall",
            "created_at": datetime.now()
        }

        temporal_data.append(features)
        temporal_df = pd.DataFrame(temporal_data)

        return temporal_df
    
def update_temporal_features():
    start_date = datetime.now() - timedelta(days=60)
    end_date = datetime.now() - timedelta(days=90)

    df = create_temporal_features(start_date, end_date)
    fs = get_feature_store()

    temporal_fg = get_or_create_feature_group(fs=fs, name="Temporal_Features", version=1, primary_key=["date"], 
                                              description="Temporal feature information regarding holidays, school breaks etc. to determine load",
                                              online_enabled=True)
    
    temporal_fg.insert(df, overwrite=True)
    return df


update_temporal_features()