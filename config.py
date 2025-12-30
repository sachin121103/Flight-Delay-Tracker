import os
from dotenv import load_dotenv

load_dotenv()

hopsworks_api_key = os.getenv("HOPSWORKS_API_KEY")
hopsworks_project_name = os.getenv("HOPSWORKS_PROJECT_NAME")
swedavia_api_key = os.getenv("SWEDAVIA_API_PRIMARY_KEY")

Arlanda = "ARN"
SMHI_Weather_URL = "https://opendata-download-metfcst.smhi.se/api"
Airport_Coordinates = {
    "ARN": {"lat": 59.6519, "long": 17.9186},
}

