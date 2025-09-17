import urequests
import json
import time

class LocationData:
    def __init__(self):
        # BoM Location JSON Data
        self.loc_valid_data = False
        self.loc_response_timestamp = ""
        self.loc_geohash = ""
        self.loc_timezone = ""
        self.loc_latitude = 0.0
        self.loc_longitude = 0.0
        self.loc_id = ""
        self.loc_name = ""
        self.loc_state = ""

class BoMLocation:
    def __init__(self):
        self.loc_current_data = LocationData()
    
    def update_location(self, geoHash):
        if self.loc_current_data.loc_geohash == geoHash and self.loc_current_data.loc_id != "":
            return self.loc_current_data
            # if the location hasn't changed, and there is existing location data, we don't need to check it again.
        else:
            self.loc_current_data = self.parse_location_json(geoHash)
            return self.loc_current_data
    
    def parse_location_json(self, geoHash):
        loc_url = f"https://api.weather.bom.gov.au/v1/locations/{geoHash}/"
        try:
            response = urequests.get(loc_url)
            if response.status_code == 200:
                json_data = response.json()
                self.loc_response_timestamp = json_data["metadata"]["response_timestamp"]
                self.loc_current_data.loc_geohash  = json_data["data"]["geohash"]
                self.loc_current_data.loc_timezone = json_data["data"]["timezone"]
                self.loc_current_data.loc_latitude = json_data["data"]["latitude"]
                self.loc_current_data.loc_longitude = json_data["data"]["longitude"]
                self.loc_current_data.loc_id = json_data["data"]["id"]
                self.loc_current_data.loc_name = json_data["data"]["name"]
                self.loc_current_data.loc_state = json_data["data"]["state"]
                response.close()
                self.loc_valid_data = True
                return
            else:
                print(f"Error: HTTP Status Code when fetching Location JSON  {response.status_code}")
                self.loc_valid_data = False
        except Exception as e:
            print(f"Error resolving Location Data from geoHash [{geoHash}]: {e}")
            self.loc_valid_data = False
            return

    # direct access properties
    @property
    def loc_name(self):
        self.update()
        return self.current_data.name
    
    @property
    def loc_state(self):
        self.update()
        return self.current_data.state

class ForecastMetadata:
    def __init__(self):
        # BoM Forecasts/Daily JSON Metadata
        self.fc_valid_data = False
        self.fc_response_timestamp = ""
        self.fc_issue_time = ""
        self.fc_next_issue_time = ""
        self.fc_geohash = ""

class ForecastData:
    def __init__(self):
        # BoM Forecasts/Daily JSON Data
        self.fc_rain_chance = 0
        self.fc_uv_index = 0
        self.fc_sunrise = ""
        self.fc_sunset = ""
        self.fc_date = ""
        self.fc_temp_max = 0
        self.fc_temp_min = 0
        self.fc_icon_descriptor = ""
        self.fc_short_text = ""
        self.fc_extended_text = ""

class BoMForecast:
    def __init__(self):
        self.fc_metadata = ForecastMetadata()
        self.fc_current_data = [ForecastData() for _ in range(8)]
        
    def update_forecast(self, geoHash):
        now = time.time()
        if self.fc_metadata.fc_next_issue_time:
            # if we've already got the next issue time, set the time to re-check
            next = time.mktime(time.strptime(self.fc_metadata.fc_next_issue_time, "%Y-%m-%dT%H:%M:%SZ")) + 120
        else:
            # otherwise, force a refresh
            next = 0

        if self.fc_metadata.fc_geohash == geoHash or self.fc_current_data[0].fc_date != "" or (now > next):
            self.fc_current_data = self.parse_forecast_json(geoHash)
            return self.fc_current_data
        else:
            # if the location hasn't changed, and we have existing data, and we haven't passed the next issue time, don't get the JSON again.
            return self.fc_current_data
    
    def parse_forecast_json(self, geoHash):
        fc_url = f"https://api.weather.bom.gov.au/v1/locations/{geoHash}/forecasts/daily"
        try:
            response = urequests.get(fc_url)
            if response.status_code != 200:
                print(f"Error: HTTP Status Code when Fetching Forecast JSON {response.status_code}")
                self.fc_valid_data = False
                return
            else:
                json_response = response.json()
                # parse metadata
                json_meta = json_response["metadata"]
                self.fc_response_timestamp = json_meta["response_timestamp"]
                self.fc_issue_time = json_meta["issue_time"]
                self.fc_next_issue_time = json_meta["next_issue_time"]
                self.fc_geohash = geoHash

                json_days = json_response["data"]
                for i, day in enumerate(json_days):
                    if i >= len(self.fc_current_data):
                        break
                    dd = self.fc_current_data[i]
                    dd.fc_date = time.mktime(time.strptime((json_days["date"]), "%Y-%m-%dT%H:%M:%SZ"))
                    dd.fc_rain_chance = json_days["rain"]["chance"]
                    dd.fc_uv_index = json_days["uv"]["max_index"]
                    dd.fc_sunrise = json_days["astronomical"]["sunrise_time"]
                    dd.fc_sunset = json_days["astronomical"]["sunset_time"]
                    dd.fc_date = json_days["date"]
                    dd.fc_temp_max = json_days["temp_max"]
                    dd.fc_temp_min = json_days["temp_min"]
                    dd.fc_icon_descriptor = json_days["icon_descriptor"]
                    dd.fc_short_text = json_days["short_text"]
                    dd.fc_extended_text = json_days["extended_text"]
                    response.close()
                    self.fc_valid_data = True
                    return json_days
                
        except Exception as e:
            print(f"Error resolving Forecast Data from geoHash [{geoHash}]: {e}")
            self.fc_valid_data = False
            return
