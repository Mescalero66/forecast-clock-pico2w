import urequests
import json

class LocationData:
    def __init__(self):
        self.valid_data = False
        self.response_timestamp = ""
        self.geohash = ""
        self.timezone = ""
        self.latitude = 0.0
        self.longitude = 0.0
        self.marine_area_id = ""
        self.tidal_point = ""
        self.has_wave = False
        self.id = ""
        self.name = ""
        self.state = ""

class BoMLocationReader:
    def __init__(self):
        self.current_data = LocationData()
    
    def update(self, geoHash):
        if self.current_data.geohash == geoHash and self.current_data.id != "":
            return self.current_data
        else:
            self.current_data = self.parse_json(geoHash)
            return self.current_data
    
    def parse_json(self, geoHash):
        url = f"https://api.weather.bom.gov.au/v1/locations/{geoHash}/"
        try:
            response = urequests.get(url)
            if response.status_code == 200:
                json_data = response.json()
                self.response_timestamp = json_data["metadata"]["response_timestamp"]
                self.current_data.geohash  = json_data["data"]["geohash"]
                self.current_data.timezone = json_data["data"]["timezone"]
                self.current_data.latitude = json_data["data"]["latitude"]
                self.current_data.longitude = json_data["data"]["longitude"]
                self.current_data.marine_area_id = json_data["data"]["marine_area_id"]
                self.current_data.tidal_point = json_data["data"]["tidal_point"]
                self.current_data.has_wave = json_data["data"]["has_wave"]
                self.current_data.id = json_data["data"]["id"]
                self.current_data.name = json_data["data"]["name"]
                self.current_data.state = json_data["data"]["state"]
                response.close()
                self.valid_data = True
                return json_data
            else:
                print(f"Error: HTTP Status Code {response.status_code}")
        except Exception as e:
            print(f"Error resolving location name from geoHash [{geoHash}]: {e}")
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
