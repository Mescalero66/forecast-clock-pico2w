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
        if self.loc_current_data.loc_geohash == geoHash and self.loc_current_data.loc_id != None:
            return self.loc_current_data
            # if the location hasn't changed, and there is existing location data, we don't need to check it again.
        else:
            self.loc_current_data = self.parse_location_json(geoHash)
            return self.loc_current_data
    
    def parse_location_json(self, geoHash):
        loc_url = f"https://api.weather.bom.gov.au/v1/locations/{geoHash}/"
        try:
            response = urequests.get(loc_url, timeout=5)
            if not hasattr(response, "status_code"):
                print(f"Error resolving Location Data from geoHash [{geoHash}]: invalid response")
                self.loc_valid_data = False
                return None
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
                return self.loc_current_data
            else:
                print(f"Error: HTTP Status Code when fetching Location JSON  {response.status_code}")
                self.loc_valid_data = False
                return None
        except Exception as e:
            print(f"Error resolving Location Data from geoHash [{geoHash}]: {e}")
            self.loc_valid_data = False
            return None

    # direct access properties
    @property
    def loc_name(self):
        return self.loc_current_data.loc_name
    
    @property
    def loc_state(self):
        return self.loc_current_data.loc_state

class ForecastMetadata:
    def __init__(self):
        # BoM Forecasts/Daily JSON Metadata
        self.fc_valid_data = False
        self.fc_response_timestamp = ""
        self.fc_issue_time = ""
        self.fc_next_issue_time = ""
        self.fc_geohash = ""
        self.fc_overnight_min = None

class ForecastData:
    def __init__(self):
        # BoM Forecasts/Daily JSON Data
        self.fc_rain_chance = None
        self.fc_uv_index = None
        self.fc_sunrise = ""
        self.fc_sunset = ""
        self.fc_date = ""
        self.fc_temp_max = None
        self.fc_temp_min = None
        self.fc_icon_descriptor = ""
        self.fc_short_text = ""
        self.fc_extended_text = ""


class BoMForecast:
    def __init__(self):
        self.fc_metadata = ForecastMetadata()
        self.fc_current_data = [ForecastData() for _ in range(7)]
        
    def update_forecast(self, geoHash):
        if self.fc_metadata.fc_geohash != geoHash or self.fc_current_data[0].fc_date != "":
            self.fc_metadata, self.fc_current_data = self.parse_forecast_json(geoHash)
            return self.fc_metadata, self.fc_current_data
        else:
            # if the location hasn't changed, and we have existing data, and we haven't passed the next issue time, don't get the JSON again.
            return self.fc_metadata, self.fc_current_data
    
    def parse_forecast_json(self, geoHash):
        fc_url = f"https://api.weather.bom.gov.au/v1/locations/{geoHash}/forecasts/daily"
        try:
            response = urequests.get(fc_url, timeout=5)
            if response.status_code != 200:
                print(f"Error: HTTP Status Code when Fetching Forecast JSON {response.status_code}")
                self.fc_valid_data = False
                return self.fc_metadata, self.fc_current_data
            else:
                json_response = response.json()
                # parse metadata
                json_meta = json_response["metadata"]
                self.fc_metadata.fc_response_timestamp = json_meta["response_timestamp"]
                self.fc_metadata.fc_issue_time = json_meta["issue_time"]
                self.fc_metadata.fc_next_issue_time = json_meta["next_issue_time"]
                self.fc_metadata.fc_geohash = geoHash

                json_days = json_response["data"]
                for i, day in enumerate(json_days):
                    if i >= len(self.fc_current_data):
                        break
                    dd = self.fc_current_data[i]
                    dd.fc_date = day["date"]
                    dd.fc_rain_chance = day["rain"]["chance"]
                    dd.fc_uv_index = day["uv"]["max_index"]
                    dd.fc_sunrise = day["astronomical"]["sunrise_time"]
                    dd.fc_sunset = day["astronomical"]["sunset_time"]
                    dd.fc_temp_max = day["temp_max"]
                    dd.fc_temp_min = day["temp_min"]
                    dd.fc_icon_descriptor = day["icon_descriptor"]
                    dd.fc_short_text = day["short_text"]
                    dd.fc_extended_text = day["extended_text"]
                    if i == 0:
                        if day["now"]["now_label"] == "Overnight min":
                            self.fc_metadata.fc_overnight_min = day["temp_now"]
                        elif day["now"]["later_label"] == "Overnight min":
                            self.fc_metadata.fc_overnight_min = day["temp_later"]
                    if i == 1 and self.fc_metadata.fc_overnight_min == None:
                        self.fc_metadata.fc_overnight_min = day["temp_min"]
                
                response.close()
                self.fc_valid_data = True
                return self.fc_metadata, self.fc_current_data
                
        except Exception as e:
            print(f"Error resolving Forecast Data from geoHash [{geoHash}]: {e}")
            self.fc_valid_data = False
            return self.fc_metadata, self.fc_current_data
