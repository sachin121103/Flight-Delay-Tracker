import os
from dotenv import load_dotenv

load_dotenv()

hopsworks_api_key = os.getenv("HOPSWORKS_API_KEY")
hopsworks_project_name = os.getenv("HOPSWORKS_PROJECT_NAME")

Arlanda = "ARN"
SMHI_Weather_URL = "https://opendata-download-metfcst.smhi.se/api"
Airport_Coordinates = {
    "ARN": {"lat": 59.6519, "long": 17.9186},
}



print(hopsworks_api_key)