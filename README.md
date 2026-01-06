### GPS Weather Clock Project
(Australia Only)

# Pico 2W Pinout
![Raspberry Pi Pico 2W](https://www.raspberrypi.com/documentation/microcontrollers/images/pico2w-pinout.svg)

## Pins
| Component | Interface | I/O | Pin |
| --- | --- | --- | --- |
| **GPS** | `UART1` | UART0 RX | GP1 |
| **Multiplexer** | `I2C` | I2C1 SDA<br>I2C1 SCL | GP14<br>GP15 |
| **8 Digit LED** | `I2C` | I2C0 SDA<br>I2C0 SCL | GP4<br>GP5 |
| **4 Digit LED (A)** | `GPIO` | Data<br>Clock | GP18<br>GP19 |
| **4 Digit LED (B)** | `GPIO` | Data<br>Clock | GP20<br>GP21 |
| **OLED (A)** | `I2C` | Mux SDA<br>Mux SCL | SDA0<br>SCL0 |
| **OLED (B)** | `I2C` | Mux SDA<br>Mux SCL | SDA1<br>SCL1 |
| **OLED (C)** | `I2C` | Mux SDA<br>Mux SCL | SDA2<br>SCL2 |
| **OLED (D)** | `I2C` | Mux SDA<br>Mux SCL | SDA3<br>SCL3 |

### References
 - https://github.com/trickypr/bom-weather-docs/tree/main
 - https://github.com/peterhinch/micropython-async/blob/master/v3/docs/TUTORIAL.md

 - https://api.weather.bom.gov.au/v1/locations/r1r1mgn/
 - https://api.weather.bom.gov.au/v1/locations/r1r1mgn/forecasts/daily

 - https://reg.bom.gov.au/info/forecast_icons.shtml

 - https://docs.micropython.org/en/latest/library/json.html
 

## Functions
**THIS IS A DOGS BREAKFAST**
| Startup RO | Main RO | Function | Description |
| --- | --- | --- | --- |
| `1` | | async def get_GPS_fix(): | checks if GPS has a fix. if not, continually refreshes the GPS_obj until it has_fix |
| `2` | | async def get_GPS_data(): | checks if GPS has a fix. if yes, gets a fresh set of GPS_data, calculates the Geohash, gets the time and sets the Pico's internal clock, calculates local time from the timezone offset, sets the local date. |
| `3` | `1`| async def update_clock_display(): | updates the main clock display every second |
| `4` | | async def check_Wifi(): | checks if wifi is connected, attempts to connect if it isn't |
| `5` | | async def get_location(): | checks if GPS has a fix. if yes, uses the Geohash to resolve a Location Name and State. |
| `6` | | async def get_forecast(): | gets new forecast data from the BoM |
| `7` | | async def sync_forecast(): | attempts to read the forecast data on hand in terms of the current day, and current day plus one, and then updates all of the constants with the relevant data |
| `8` | `0` | async def main(): | starts the tasks in the correct order, then awaits them finishing (forever) |
| | `2` | async def update_time_sync(): | checks if the GPS_obj has new data, and that the data is not too old (30 sec). If it isn't, calculate the weekeday and set the pico's clock. calculate the local time and update the date  and time constants |
| | `3` | async def update_temperature_display(): | updates the 2 temperature LED displays, with alternate for overnight low |
| | `4` | async def update_new_forecast_data(): | checks the forecast data issue time to determine if an update is required / scheduled. If it is, get_forecast() is called |
| | `5` | async def oled_refresh_scheduler(): | attempts to schedule refreshing of OLEDs based on various criteria - doesn't work very well |
| | | async def date_check(y, m, d, wd): | checks if the date has ticked over to a new day. If yes, calls sync_forecast() |
| | | async def render_oleds(): | ONCE OFF VERSION - gets the correct data, and renders the 4 screens to be sent to the OLEDs |
| | | async def refresh_oleds(): | EVERY 2 MINUTES LOOP - gets the correct data, and renders the 4 screens to be sent to the OLEDs |
| | | async def update_GPS_data(): | checks if GPS has a fix. if yes, updates the GPS_DATA from the GPS_obj |
| | | def oled_event(event): | event handler - not useful |


## Data Requirements and Update Frequency
| No | Data | Dependencies | Refresh Interval |
| --- | --- | --- | --- |
| `1` |  |  |  |  |
| `1` |  |  |  |  |
| `1` |  |  |  |  |
| `1` |  |  |  |  |
| `1` |  |  |  |  |
| `1` |  |  |  |  |
| `1` |  |  |  |  |
| `1` |  |  |  |  |