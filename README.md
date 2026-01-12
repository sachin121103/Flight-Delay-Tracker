# Flight-Delay-Tracker
Project for ID2223 - Flight Delay Tracker
Group Duck: Axel Blennå and Sachin Prabhu Ram

This is a machine learning project built as the final assignment of the course ID2223 at KTH Royal Institute of Technology. The project is about predicting flight delays at Arlanda airport in Sweden. The predictions are binary classifications of whether or not the flight will be delayed, and a probability of how high the risk of delay is.

The project consists of a feature pipeline (in three parts), a training pipline, an inference pipeline, and a UI.

## Feature Pipeline
The feature pipeline consists of three files. They follow a similar pattern where they fetch data from an API, create dataframes for features, and then upload the dataframes to Hopsworks for feature storage.

### Flight Data
Data regarding flights from Arlanda airport is retrieved from the Swedavia API. This includes data such as the flight ID, destination, scheduled time and actual arrival or departure time if there is any delay. This pipeline is designed to run on a schedule in order to fetch updated flight schedules from previous days in order to make it possible to compare it to the original scheduled times. It also fetches data for the upcoming flights in order to use for predictions.

### Weather Data
The weather data was fetched from the SMHI API for the location of Arlanda airport. Then features were created for data such as temperature, wind direction, wind speed and humidity, to name a few. The weather conditions are evaluated by looking at the precipitation, visibility and wind speed in order to put labels such as “snow”, “rain” or “fog” on the data. The weather conditions are used to calculate the probability of delay.

### Temporal Data
The temporal feature pipeline is used to fetch public holidays in Sweden, which might affect the flight schedules. Features are created such as what day of the week it is, whether it is a public holiday or not and what season it is.


## Training Pipeline
The training pipeline fetches the flights, weather and temporal feature groups from the Hopsworks feature store. It then merges the flight data with the temporal data based on date. The weather data is then merged based on timestamp in order to make it more precise for the flight schedule. The probability of delay is calculated based on weather conditions and the temporal data.

The model used in an XGBoost Classifier for binary classification of whether a flight will be delayed or not. The model is saved in the Hopsworks model registry.

## Inference Pipeline
The inference pipeline loads the trained model and the feature groups from Hopsworks. It then merges the feature data in the same way as was done before training. Predictions are then made of whether a flight will be delayed or not, and by what probability. Finally, the inference pipeline also visualises the result using a dashboard.
