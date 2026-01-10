import sys, time, os, machine, builtins, gc
import asyncio
from machine import I2C, Pin, UART, RTC

from hardware.LED8_HT16K33 import HT16K33LED
from hardware.GPS_PARSER import GPSReader, GPSData
from hardware.LED4_TM1650 import LED4digdisp
from hardware.MUX_TCA9548A import I2CMultiplex
from hardware.OLED_SSD1306 import SSD1306_I2C
from hardware.WLAN import WLAN

import functions.timezones as AusTimeZones
import functions.geohash as Geohash
import functions.forecast as BoMData
import functions.time_cruncher as TimeCruncher
import functions.weather_icons as IconGrabber

from functions.string_writer import ezFBfont as ezFBfont
from fonts import spleen8, spleen12, spleen16, spleen23, helvetica15bold

## CONSTANTS
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS_OF_YEAR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
## PINS
PIN_UART_TX = 0
PIN_UART_RX = 1
PIN_MUX_SDA = 14
PIN_MUX_SCL = 15
PIN_LED8_SDA = 4
PIN_LED8_SCL = 5
PIN_LED4H_SDA = 20
PIN_LED4H_SCL = 21
PIN_LED4L_SDA = 18
PIN_LED4L_SCL = 19
## MUX
ADDR_MUX = 0x70
## OLEDS
OLED_RES_X = 128
OLED_RES_Y = 64
OLED_ID_TL = 2
OLED_ID_TR = 3
OLED_ID_BL = 0
OLED_ID_BR = 1
## LOGGING
ENABLE_LOGGING = 1
_current_log_filename = None
_original_print = builtins.print
## PARAMETERS
BOM_MINIMUM_POLL_INTERVAL = 120 * 60
EVENING_CUTOFF = 18
MORNING_CUTOFF = 2
INTERVAL_FORECAST_DATA = 23 * 60 * 60
INTERVAL_BULLETIN_AGE = 14 * 60 * 60
INTERVAL_FORECAST_SYNC = 30 * 60
INTERVAL_OLED_REFRESH = 30 * 60
INTERVAL_SYNC_WATCHES = 1 * 60 ## TESTING ONLY - RETURN TO 24 MINUTES
INTERVAL_LED_REFRESH = 15 * 60

## HARDWARE
wlan = WLAN()                                                                               # create WLAN object
utcRTC = RTC()                                                                              # create UTC Real Time Clock
localRTC = RTC()                                                                            # create Local Real Time Clock
uart = UART(0, baudrate=9600, tx=Pin(PIN_UART_TX), rx=Pin(PIN_UART_RX))                     # Set up UART connection to GPS module
i2c = I2C(0, scl=Pin(PIN_LED8_SCL), sda=Pin(PIN_LED8_SDA))                                  # Set up I2C connection
mux = I2CMultiplex(ADDR_MUX, I2Cbus=1, scl_pin=PIN_MUX_SCL, sda_pin=PIN_MUX_SDA)            # Set up I2C multiplexer
GPS_obj = GPSReader(uart)                                                                   # Create a GPS reader object 
disp8 = HT16K33LED(i2c)                                                                     # Create 8digit LED object
disp4H = LED4digdisp(1, PIN_LED4H_SCL, PIN_LED4H_SDA)                                       # Create 4digit LED object (HIGH)         
disp4L = LED4digdisp(2, PIN_LED4L_SCL, PIN_LED4L_SDA)                                       # Create 4digit LED object (LOW)
BoMLocInfo = BoMData.BoMLocation()                                                          # Create the BoM Location data structure
BoMForecastInfo = BoMData.BoMForecast()                                                     # Create the BoM Forecast data structure
TimezoneInfo = AusTimeZones.LocalTimezone()                                                 # Create the Timezone data structure

mux.select_port(OLED_ID_TL)                                                                 # select the correct mux port
oledTL = SSD1306_I2C(OLED_RES_X, OLED_RES_Y, mux.i2c)                                       # and create the OLED object
oledTL8 = ezFBfont(oledTL, spleen8)
oledTL12 = ezFBfont(oledTL, spleen12)
oledTL16 = ezFBfont(oledTL, spleen16)
oledTL23 = ezFBfont(oledTL, spleen23)
oledTLhead = ezFBfont(oledTL, helvetica15bold, hgap=2)
mux.select_port(OLED_ID_TR)
oledTR = SSD1306_I2C(OLED_RES_X, OLED_RES_Y, mux.i2c)
oledTR8 = ezFBfont(oledTR, spleen8)
oledTR12 = ezFBfont(oledTR, spleen12)
oledTR16 = ezFBfont(oledTR, spleen16)
oledTR23 = ezFBfont(oledTR, spleen23)
oledTRhead = ezFBfont(oledTR, helvetica15bold, hgap=2)
mux.select_port(OLED_ID_BL)
oledBL = SSD1306_I2C(OLED_RES_X, OLED_RES_Y, mux.i2c)
oledBL8 = ezFBfont(oledBL, spleen8)
oledBL12 = ezFBfont(oledBL, spleen12)
oledBL16 = ezFBfont(oledBL, spleen16)
oledBL23 = ezFBfont(oledBL, spleen23)
oledBLhead = ezFBfont(oledBL, helvetica15bold, hgap=2)
mux.select_port(OLED_ID_BR)
oledBR = SSD1306_I2C(OLED_RES_X, OLED_RES_Y, mux.i2c)
oledBR8 = ezFBfont(oledBR, spleen8)
oledBR12 = ezFBfont(oledBR, spleen12)
oledBR16 = ezFBfont(oledBR, spleen16)
oledBR23 = ezFBfont(oledBR, spleen23)
oledBRhead = ezFBfont(oledBR, helvetica15bold, hgap=2)

disp8.set_brightness(15)                                        # TURN ON THE 8 DIGIT CLOCK DISPLAY WITH MAX BRIGHTNESS
disp4H.display_on(0)                                            # TURN ON THE UPPER 4 DIGIT DISPLAY WITH MAX BRIGHTNESS
disp4H.show_string("__*C")                                    
disp4L.display_on(0)                                            # TURN ON THE LOWER 4 DIGIT DISPLAY WITH MAX BRIGHTNESS
disp4L.show_string("__*C") 

class PrintLogger:
    def __init__(self, logfile, flush_interval=60):
        self.logfile = logfile
        self.flush_interval = flush_interval
        self._buffer = []
        self._last_flush = time.ticks_ms()

    def log_line(self, line):
        ts = self.timestamp()
        entry = ts + line + "\n"
        self._buffer.append(entry)
        if "ERROR" in line or "EXCEPTION" in line or "failed" in line or "cancelled" in line:
            self.flush()
        if time.ticks_diff(time.ticks_ms(), self._last_flush) >= self.flush_interval * 1000:
            self.flush()

    def flush(self):
        if self._buffer:
            self.logfile.write("".join(self._buffer))
            self.logfile.flush()
            self._buffer.clear()
            self._last_flush = time.ticks_ms()

    def timestamp(self):
        lt = localRTC.datetime()
        return "[{:04d}-{:02d}-{:02d} {:02d}.{:02d}.{:02d}] ".format(lt[0], lt[1], lt[2], lt[4], lt[5], lt[6])

def create_daily_log_file():
    global _current_log_filename
    y, m, d = GPS_obj.current_data.year, GPS_obj.current_data.month, GPS_obj.current_data.day
    filename = "logs/forecastclock_{:04d}{:02d}{:02d}.txt".format(y, m, d)
    if "logs" not in os.listdir():
        os.mkdir("logs")
    if _current_log_filename != filename:
        cleanup_old_logs()
        _current_log_filename = filename
    return _current_log_filename

def cleanup_old_logs():
    if "logs" not in os.listdir():
        return
    files = [f for f in os.listdir("logs") if f.startswith("forecastclock_") and f.endswith(".txt")]
    files.sort()
    while len(files) > 2:
        oldest = files.pop(0)
        os.remove(f"logs/{oldest}")
        print(f"Deleted old log: {oldest}")

async def radar_GPS_animation(t):
    disp4H.show_string(" _# ")
    disp4L.show_string(" ~~ ")
    await asyncio.sleep(t)
    disp4H.show_string(" _=>")
    await asyncio.sleep(t)
    disp4H.show_string(" __=")
    await asyncio.sleep(t)
    disp4H.show_string(" ___")
    disp4L.show_string(" ~~>")
    await asyncio.sleep(t)
    disp4H.show_string(" __ ")
    disp4L.show_string(" ~>=")
    await asyncio.sleep(t)
    disp4L.show_string(" ~# ")
    await asyncio.sleep(t)
    disp4L.show_string(" #~ ")
    await asyncio.sleep(t)
    disp4L.show_string("=>~ ")
    await asyncio.sleep(t)
    disp4L.show_string(">~~ ")
    await asyncio.sleep(t)
    disp4H.show_string("___ ")
    disp4L.show_string("~~~ ")
    await asyncio.sleep(t)
    disp4L.show_string(" ~~ ")
    disp4H.show_string("=__ ")
    await asyncio.sleep(t)
    disp4H.show_string(">=_ ")
    await asyncio.sleep(t)
    disp4H.show_string(" #_ ")
    await asyncio.sleep(t)
    return
    
async def get_GPS_fix():
    t = 0.1
    while not GPS_obj.has_fix:
        print(f"get_GPS_fix()  Listens for satellites: {GPS_obj.has_new_data:02}/{GPS_obj.current_data.has_fix:02}/{GPS_obj.current_data.satellites:02} + [{GPS_obj.message_buffer}]")
        asyncio.run(radar_GPS_animation(t))
        NoS = f"GPS = {GPS_obj.current_data.satellites:02}"
        disp8.set_string(NoS, "r")
        GPS_obj.get_data()
        asyncio.run(radar_GPS_animation(t))
        NoS = f"GPS = {GPS_obj.current_data.satellites:02}"
        disp8.set_string(NoS, "r")
    return GPS_obj.has_fix

async def enable_Wifi():
    if wlan.checkWiFi() == True:
        pass
    else:
        wlan.connectWiFi(retries=3, wait_per_try=5)
    return wlan.checkWiFi()

async def system_setup():
    # initial set up of the GPS dataset, internal clock, timezone offset and local time.
    while GPS_obj.latitude == None or GPS_obj.longitude == None or GPS_obj.latitude == 0.0 or GPS_obj.longitude == 0.0:
        # ensuring that we have the coordinates before anything else happens
        GPS_obj.get_data()
        await asyncio.sleep(1)
    print(f"system_setup()  Lat: [{GPS_obj.current_data.latitude:03.4f}] Long: [{GPS_obj.current_data.longitude:03.4f}] Alt: [{GPS_obj.current_data.altitude:.1f}]")
    temp_string = f"{GPS_obj.current_data.latitude:08}"
    disp8.set_string(temp_string, "r")
    await asyncio.sleep(0.5)
    temp_string = f"{GPS_obj.current_data.longitude:08}"
    disp8.set_string(temp_string, "r")
    await asyncio.sleep(0.5)
    # get geohash code from GPS coordinates
    _geohash = Geohash.encode(float(GPS_obj.current_data.latitude), float(GPS_obj.current_data.longitude), precision=7)
    print(f"system_setup()  geohash: [{_geohash}]")
    temp_string = f"{_geohash:08}"
    disp8.set_string(temp_string, "r")
    await asyncio.sleep(0.5)
    # calculate day_of_week, required to set the Pico internal clock (UTC)
    y, m, d = GPS_obj.current_data.year, GPS_obj.current_data.month, GPS_obj.current_data.day
    day_of_week = TimeCruncher.get_weekday(y, m, d)
    await asyncio.sleep(0.5)
    # set the UTC clock time from GPS data
    hh, mm, ss = GPS_obj.current_data.hour, GPS_obj.current_data.minute, GPS_obj.current_data.second
    utcRTC.datetime((y, m, d, day_of_week, hh, mm, ss, 0))
    await asyncio.sleep(0.5)
    # get the (UTC) datetime we just set and display it
    utcY, utcM, utcD, _, utcHr, utcMn, utcSc, _ = utcRTC.datetime()
    print(f"system_setup()  UTC: {utcY:04}-{utcM:02}-{utcD:02} {utcHr:02}.{utcMn:02}.{utcSc:02}")
    await asyncio.sleep(0.5)
    # calculate the local time from the GPS coordinates and UTC time
    tziData = TimezoneInfo.update_localtime(float(GPS_obj.current_data.latitude), float(GPS_obj.current_data.longitude), (utcY, utcM, utcD, utcHr, utcMn, utcSc))
    temp_string = f"{tziData.local_year:04}{tziData.local_month:02}{tziData.local_day:02}"
    disp8.set_string(temp_string, "r")
    await asyncio.sleep(1)
    # set timezone offset (in seconds)
    _timezoneOffset = TimezoneInfo.tz_offset_minutes * 60
    print(f"system_setup()  TZO: {TimezoneInfo.tz_data.zone_id} DST: {TimezoneInfo.tz_data.is_DST} Offset: {TimezoneInfo.tz_offset_minutes} mins")
    # set the local clock time from the converted local time from TimezoneInfo
    day_of_week = TimeCruncher.get_weekday(tziData.local_year, tziData.local_month, tziData.local_day)
    localRTC.datetime((tziData.local_year, tziData.local_month, tziData.local_day, day_of_week, tziData.local_hour, tziData.local_minute, tziData.local_second, 0))
    await asyncio.sleep(0.5)
    # get the (Local) datetime we just set and display it
    lclY, lclM, lclD, _, lclHr, lclMn, lclSc, _ = localRTC.datetime()
    print(f"system_setup()  Lcl: {lclY:04}-{lclM:02}-{lclD:02} {lclHr:02}.{lclMn:02}.{lclSc:02}")
    await asyncio.sleep(0.5)
    return _geohash, _timezoneOffset

async def synchronise_watches():
    # see system_setup()
    try:
        GPS_obj.get_data()
        await asyncio.sleep(1)
        while GPS_obj.current_data.hour == 0.0 or GPS_obj.current_data.minute == 0.0 or GPS_obj.current_data.second == 0.0 or GPS_obj.current_data.time == "" or GPS_obj.latitude == None or GPS_obj.longitude == None or GPS_obj.latitude == 0.0 or GPS_obj.longitude == 0.0:
        # ensuring that we have an up-to-date time
            GPS_obj.get_data()
            await asyncio.sleep(1)
        # calculate day_of_week, required to set the Pico internal clock (UTC)

        ##### PRE
        utcY, utcM, utcD, _, utcHr, utcMn, utcSc, _ = utcRTC.datetime()
        print(f"synchronise_watches()  PRE-CHANGE    UTC: {utcY:04}-{utcM:02}-{utcD:02} {utcHr:02}.{utcMn:02}.{utcSc:02}")
        lclY, lclM, lclD, _, lclHr, lclMn, lclSc, _ = localRTC.datetime()
        print(f"synchronise_watches()  PRE-CHANGE    Lcl: {lclY:04}-{lclM:02}-{lclD:02} {lclHr:02}.{lclMn:02}.{lclSc:02}")
        ##### PRE

        #y, m, d = GPS_obj.current_data.year, GPS_obj.current_data.month, GPS_obj.current_data.day
        y, m, d = GPS_obj.date_ymd
        day_of_week = TimeCruncher.get_weekday(y, m, d)
        # set the UTC clock time from GPS data
        #hh, mm, ss = GPS_obj.current_data.hour, GPS_obj.current_data.minute, GPS_obj.current_data.second
        hh, mm, ss = GPS_obj.time_split
        utcRTC.datetime((y, m, d, day_of_week, hh, mm, ss, 0))
        # get the (UTC) datetime we just set and display it
        utcY, utcM, utcD, _, utcHr, utcMn, utcSc, _ = utcRTC.datetime()

        ###### POST
        #print(f"synchronise_watches()  UTC: {utcY:04}-{utcM:02}-{utcD:02} {utcHr:02}.{utcMn:02}.{utcSc:02}")
        print(f"synchronise_watches()  POST-CHANGE   UTC: {utcY:04}-{utcM:02}-{utcD:02} {utcHr:02}.{utcMn:02}.{utcSc:02}")
        print(f"synchronise_watches()  POST-UTC-CHNG Lcl: {lclY:04}-{lclM:02}-{lclD:02} {lclHr:02}.{lclMn:02}.{lclSc:02}")
        ###### POST

        # calculate the local time from the GPS coordinates and UTC time
        tziData = TimezoneInfo.update_localtime(float(GPS_obj.current_data.latitude), float(GPS_obj.current_data.longitude), (utcY, utcM, utcD, utcHr, utcMn, utcSc))
        print(f"synchronise_watches()  TZO: {TimezoneInfo.tz_data.zone_id} DST: {TimezoneInfo.tz_data.is_DST} Offset: {TimezoneInfo.tz_offset_minutes} mins")
        # display the adjustment to be made
        thenY, thenM, thenD, _, thenHr, thenMn, thenSc, _ = localRTC.datetime()
        print(f"synchronise_watches()  Adjusting Local RTC by: Y({tziData.local_year - thenY}) M({tziData.local_month - thenM}) D({tziData.local_day - thenD}) H({tziData.local_hour - thenHr}) M({tziData.local_minute - thenMn}) S({tziData.local_second - thenSc})")
        # set the local clock time from the converted local time from TimezoneInfo
        day_of_week = TimeCruncher.get_weekday(tziData.local_year, tziData.local_month, tziData.local_day)
        localRTC.datetime((tziData.local_year, tziData.local_month, tziData.local_day, day_of_week, tziData.local_hour, tziData.local_minute, tziData.local_second, 0))
        # get the (Local) datetime we just set and display it
        lclY, lclM, lclD, _, lclHr, lclMn, lclSc, _ = localRTC.datetime()

        ###### POST
        #print(f"synchronise_watches()  Lcl: {lclY:04}-{lclM:02}-{lclD:02} {lclHr:02}.{lclMn:02}.{lclSc:02}")
        print(f"synchronise_watches()  POST-CHANGE Lcl: {lclY:04}-{lclM:02}-{lclD:02} {lclHr:02}.{lclMn:02}.{lclSc:02}")
        ###### POST

        await asyncio.sleep(0.5)
    except Exception as e:
        print(f"synchronise_watches() failed to synchronise internal clocks to GPS time: {e} - {repr(e)}")
        await asyncio.sleep(0.5)
        return False
    # return the last successful refresh time
    _lastRefresh = TimeCruncher.now_rtc_to_epoch(localRTC.datetime())
    return _lastRefresh

async def update_display_clock():
    while True:
        _, _, _, _, hh, mm, ss, _ = localRTC.datetime()
        time_str = f"{hh:02} .{mm:02} .{ss:02}"
        disp8.set_string(time_str, "r")
        await asyncio.sleep(0.2)
        time_str = f"{hh:02} {mm:02} {ss:02}"
        # print(f"{hh:02} {mm:02} {ss:02}")
        disp8.set_string(time_str, "r")       
        await asyncio.sleep(0.8)

async def get_location(_geohash):
    # lookup location at the BoM from the geohash
    locData = BoMLocInfo.update_location(_geohash)
    await asyncio.sleep(0.5)
    _locCity = locData.loc_name
    _locState = locData.loc_state
    print(f"get_location()  {_locCity}, {_locState}, Australia")
    return _locCity, _locState

async def get_forecast_data(_geohash):
    try:
        await asyncio.sleep(0.5)
        # attempt to connect to the BoM and return the daily forecast data for the given geohash
        _forecastMeta, _forecastData = BoMForecastInfo.update_forecast(_geohash)
        await asyncio.sleep(0.5)
    except Exception as e:
        print(f"get_forecast_data() failed to retrieve new data from the BoM: {e} - {repr(e)}")
        await asyncio.sleep(0.5)
        return False
    _lastRefresh  = TimeCruncher.now_rtc_to_epoch(localRTC.datetime())
    return _lastRefresh, _forecastMeta, _forecastData

async def update_forecast(_forecastMeta, _forecastData, _timezoneOffset):
    now = TimeCruncher.now_rtc_to_epoch(localRTC.datetime())
    bulletin_time = ((TimeCruncher.parse_8601datetime(_forecastMeta.fc_issue_time)) + _timezoneOffset)
    ## wait at least 90 minutes before going back to the BoM
    bulletin_next = ((TimeCruncher.parse_8601datetime(_forecastMeta.fc_next_issue_time)) + _timezoneOffset)
    _updateMetadata = {
        "response_time": (TimeCruncher.parse_8601datetime(_forecastMeta.fc_response_timestamp)) + _timezoneOffset,
        "bulletin_time": bulletin_time,
        "bulletin_next": max(bulletin_next, (bulletin_time + BOM_MINIMUM_POLL_INTERVAL))
    }
    print(f"update_forecast()  BoM [Resp: {now - _updateMetadata["response_time"]}][Bull: {now - _updateMetadata["bulletin_time"]}][Next: {now - _updateMetadata["bulletin_next"]}]")
    # get current local date
    lclY, lclM, lclD, _, _, _, _, _ = localRTC.datetime()
    # attempt to sync the downloaded forecast data to the current date(s)
    i = None
    try:
        for x in range(7):
            chkY, chkM, chkD, _, _, _, _, _ = TimeCruncher.parse_8601localtime(_forecastData[x].fc_date, _timezoneOffset)
            print(f"update_forecast()  syncs the BoM forecast data to the current date [{chkY}/{lclY}][{chkM}/{lclM}][{chkD}/{lclD}]")
            if (chkY == lclY) and (chkM == lclM) and (chkD == lclD):
                i = x
                break
    except Exception as e:
        print(f"update_forecast() failed to sync the BoM forecast data to the current date: {e} - {repr(e)}")
        await asyncio.sleep(0.5)
        return False
    # if i is still not set by this point, there is a date mismatch between the current system date and the data from the BoM
    if i == None:
        print(f"update_forecast() has forecast data for {TimeCruncher.parse_8601localtime(_forecastData[0].fc_date, _timezoneOffset)}, but isn't today {localRTC.datetime()}?")
        return False
    await asyncio.sleep(0.5)
    # attempt to collect the correct data into return dictionary
    try:
        tdY, tdM, tdD, _, _, _, _, _  = TimeCruncher.parse_8601localtime(_forecastData[i].fc_date, _timezoneOffset)
        _forecastToday = {
            "yy": tdY,
            "mm": tdM,
            "dd": tdD,
            "max": _forecastData[i].fc_temp_max,
            "min": _forecastData[i].fc_temp_min, 
            "rain": _forecastData[i].fc_rain_chance,
            "icon": _forecastData[i].fc_icon_descriptor,
            "text": _forecastData[i].fc_short_text,
            "onlow": _forecastMeta.fc_overnight_min
        }
        if (_forecastToday["min"]) == None:
            _forecastToday["min"] = _forecastToday["onlow"]
        j = i + 1
        tmY, tmM, tmD, _, _, _, _, _  = TimeCruncher.parse_8601localtime(_forecastData[j].fc_date, _timezoneOffset)
        _forecastTomorrow = {
            "yy": tmY,
            "mm": tmM,
            "dd": tmD,
            "max": _forecastData[j].fc_temp_max,
            "min": _forecastData[j].fc_temp_min, 
            "rain": _forecastData[j].fc_rain_chance,
            "icon": _forecastData[j].fc_icon_descriptor,
            "text": _forecastData[j].fc_short_text,
            "onlow": _forecastMeta.fc_overnight_min
        }
        if (_forecastTomorrow["min"]) == None:
            _forecastTomorrow["min"] = _forecastTomorrow["onlow"]
    except Exception as e:
        print(f"update_forecast() failed to organise the BoM data into the correct structure: {e} - {repr(e)}")
        await asyncio.sleep(0.5)
        return False
    await asyncio.sleep(0.5)
    # print some forecast data
    print(f"update_forecast()  BoM Today {_forecastToday['yy']:04}-{_forecastToday['mm']:02}-{_forecastToday['dd']:02} Max: {_forecastToday['max']}°C Min: {_forecastToday['min']}°C Rain: {_forecastToday['rain']}% ({_forecastToday['text']})")
    print(f"update_forecast()  BoM Tomor {_forecastTomorrow['yy']:04}-{_forecastTomorrow['mm']:02}-{_forecastTomorrow['dd']:02} Max: {_forecastTomorrow['max']}°C Min: {_forecastTomorrow['min']}°C Rain: {_forecastTomorrow['rain']}% ({_forecastTomorrow['text']})")
    _lastRefresh = TimeCruncher.now_rtc_to_epoch(localRTC.datetime())
    return _lastRefresh, _updateMetadata, _forecastToday, _forecastTomorrow

async def update_display_temps(_todayMax, _overnighLow, _tomorrowMax):
    _, _, _, _, hh, _, _, _ =  localRTC.datetime()
    await asyncio.sleep(0.5)
    try:
        strLo = f"{_tomorrowMax}*C"
        if hh > EVENING_CUTOFF:
            strHi = f"{_overnighLow}*C"   
            print(f"update_display_temps()  Hi:[Overnight Low: {strHi}] Lo:[Tomorrow Max: {strLo}] hh:{hh}")         
        else:
            strHi = f"{_todayMax}*C"
            print(f"update_display_temps()  Hi:[Today Max: {strHi}] Lo:[Tomorrow Max: {strLo}] hh:{hh}") 
        disp4H.show_string(strHi)
        disp4L.show_string(strLo)
    except Exception as e:
        print(f"update_display_temps() failed write the temps on the displays: {e} - {repr(e)}")
        await asyncio.sleep(0.5)
        return False
    # return the last successful refresh time
    await asyncio.sleep(0.5)
    _lastRefresh = TimeCruncher.now_rtc_to_epoch(localRTC.datetime())
    return _lastRefresh

async def update_display_oleds(_forecastToday, _forecastTomorrow, _locCity):
    # lookup the day of the week
    tdDoW = TimeCruncher.get_weekday(_forecastToday['yy'],_forecastToday['mm'],_forecastToday['dd'])
    tdStrDoW = DAYS_OF_WEEK[tdDoW % 7]
    tmDoW = TimeCruncher.get_weekday(_forecastTomorrow['yy'],_forecastTomorrow['mm'],_forecastTomorrow['dd'])
    tmStrDoW = DAYS_OF_WEEK[tmDoW % 7]
    # lookup the month of the year
    tdStrMoY = MONTHS_OF_YEAR[_forecastToday['mm'] - 1]
    tmStrMoY = MONTHS_OF_YEAR[_forecastTomorrow['mm'] - 1]
    # get the hour of the day
    _, _, _, _, hh, _, _, _ =  localRTC.datetime()
    await asyncio.sleep(0.5)
    # clear the canvas and fill in the banners
    #print("clear the canvas and fill in the banners")
    mux.select_port(OLED_ID_TL)
    oledTL.fill(0)
    oledTL.fill_rect(0, 0, 128, 16, 1)
    mux.select_port(OLED_ID_BL)
    oledBL.fill(0)
    oledBL.fill_rect(0, 0, 128, 16, 1)
    mux.select_port(OLED_ID_TR)
    oledTR.fill(0)
    oledTR.fill_rect(0, 0, 128, 16, 1)
    mux.select_port(OLED_ID_BR)
    oledBR.fill(0)
    oledBR.fill_rect(0, 0, 128, 16, 1)
    await asyncio.sleep(0.5)

    # draw the canvas for OLED: top left
    date_header = f"{_forecastToday['dd']:02} {tdStrMoY} {_forecastToday['yy']:04}"
    oledTLhead.write(date_header, x=65, halign="center", y=1, fg=0, bg=1)
    oledTL23.write(tdStrDoW, halign="center", y=17, x=64)
    oledTL16.write("Rain: ", halign="left", y=50, x=4)
    str_rain_percent = f"{_forecastToday['rain']:0} %"
    oledTL23.write(str_rain_percent, halign="right", y=45, x=123)
    print(f"update_display_oleds()  TL: {date_header} / {tdStrDoW} / Rain: {str_rain_percent}")
    await asyncio.sleep(0.5)
    # draw the canvas for OLED: bottom left
    date_header = f"{_forecastTomorrow['dd']:02} {tmStrMoY} {_forecastTomorrow['yy']:04}"
    oledBLhead.write(date_header, x=65, halign="center", y=1, fg=0, bg=1)
    oledBL23.write(tmStrDoW, halign="center", y=17, x=64)
    oledBL16.write("Rain: ", halign="left", y=50, x=4)
    str_rain_percent = f"{_forecastTomorrow['rain']:0} %"
    oledBL23.write(str_rain_percent, halign="right", y=45, x=123)
    print(f"update_display_oleds()  BL: {date_header} / {tmStrDoW} / Rain: {str_rain_percent}")
    await asyncio.sleep(0.5)
    # draw the canvas for OLED: top right
    oledTRhead.write(_locCity, x=65, halign="center", y=1, fg=0, bg=1)
    icon = IconGrabber.get_icon(_forecastToday['icon'], 37, hour=hh)
    oledTR.display_pbm(icon, x_offset=84, y_offset=17)           
    descText = ezFBfont.split_text(_forecastToday['text'])
    oledTR12.write(descText, halign="center", valign="center", y=34, x=45)
    if hh > EVENING_CUTOFF or hh < MORNING_CUTOFF:
        oledTR16.write("Overnight Low:", halign="center", y=52, x=66)
        print(f"update_display_oleds()  TR: {_locCity} / {icon } / {_forecastToday['text']} / Overnight Low: / [hh={hh}]")
    else:
        str_min = str(f"Min: {_forecastToday['min']:0}°C  Max:")
        oledTR16.write(str_min, halign="center", y=52, x=66)
        print(f"update_display_oleds()  TR: {_locCity} / {icon } / {_forecastToday['text']} / Min: {_forecastToday['min']:0}°C  Max: / [hh={hh}]")
    await asyncio.sleep(0.5)
    # draw the canvas for OLED: bottom right
    oledBRhead.write(_locCity, x=65, halign="center", y=1, fg=0, bg=1)
    icon = IconGrabber.get_icon(_forecastTomorrow['icon'], 37, hour=6)
    oledBR.display_pbm(icon, x_offset=84, y_offset=17)
    descText = ezFBfont.split_text(_forecastTomorrow['text'])
    oledBR12.write(descText, halign="center", valign="center", y=34, x=45)
    str_min = str(f"Min: {_forecastTomorrow['min']:0}°C  Max:")
    oledBR16.write(str_min, halign="center", y=52, x=66)
    print(f"update_display_oleds()  BR: {_locCity} / {icon } / {_forecastTomorrow['text']} / Min: {_forecastTomorrow['min']:0}°C  Max: / [hh={hh}]")
    await asyncio.sleep(0.5)
    # write the updated canvas to the OLEDs
    try:
        mux.select_port(OLED_ID_TL)
        oledTL.show()
        mux.select_port(OLED_ID_BL)
        oledBL.show()
        mux.select_port(OLED_ID_TR)
        oledTR.show()
        mux.select_port(OLED_ID_BR)
        oledBR.show()
    except Exception as e:
        print(f"update_display_oleds() failed write the canvas to the OLEDs: {e} - {repr(e)}")
        await asyncio.sleep(0.5)
        return False
    # return the last successful refresh time
    await asyncio.sleep(0.5)
    _lastRefresh = TimeCruncher.now_rtc_to_epoch(localRTC.datetime())
    return _lastRefresh

async def main_loop(_geohash, _timezoneOffset, _locCity, _locState):
    ongoing_tasks = []
    result = None
    # kill the startup version of the clock display task
    if not startupClock.done():
        startupClock.cancel()
        try:
            await startupClock
        except asyncio.CancelledError:
            print("main_loop()  Cancelled the startup instance of update_display_clock()")
            logger.flush()
    # start ongoing updates of the clock display
    print("main_loop()  calls update_display_clock()")
    ongoing_tasks.append(asyncio.create_task(update_display_clock()))
    # start ongoing refresh scheduler loop
    print("main_loop()  calls refresh_scheduler()")
    ongoing_tasks.append(asyncio.create_task(refresh_scheduler(_geohash, _timezoneOffset, _locCity, _locState)))
    try:
        result = await asyncio.gather(*ongoing_tasks, return_exceptions=True)
    except asyncio.CancelledError:
        print("ERROR: ONGOING TASKS LOOP CANCELLED")
        logger.flush()
    print("Result: ", result)

async def refresh_scheduler(_geohash, _timezoneOffset, _locCity, _locState):
    # get the initial set of forecast data
    print("refresh_scheduler()  calls get_forecast_data()")
    firstForecastData = asyncio.create_task(get_forecast_data(_geohash))
    lastForecastDataRefresh, _forecastMeta, _forecastData = await firstForecastData
    await asyncio.sleep(1)
    # match the data to the current date
    print("refresh_scheduler()  calls update_forecast()")
    firstForecastSync = asyncio.create_task(update_forecast(_forecastMeta, _forecastData, _timezoneOffset))
    lastForecastSync, _updateMetadata, _forecastToday, _forecastTomorrow = await firstForecastSync
    await asyncio.sleep(1)
    # update the display_temps and the display_oleds (almost) immediately
    print("refresh_scheduler()  calls update_display_temps()")
    firstLedRefresh = asyncio.create_task(update_display_temps(_forecastToday['max'], _forecastToday['onlow'], _forecastTomorrow['max']))
    lastLedRefresh = await firstLedRefresh
    await asyncio.sleep(1)
    print("refresh_scheduler()  calls update_display_oleds()")
    firstOledRefresh = asyncio.create_task(update_display_oleds(_forecastToday, _forecastTomorrow, _locCity))
    lastOledRefresh = await firstOledRefresh
    await asyncio.sleep(1)
    # schedule the first wathc sync
    now = TimeCruncher.now_rtc_to_epoch(localRTC.datetime())
    lastSynchroniseWatches = now
    new_bulletin = False
    # then, run this forever
    while True:
        now = TimeCruncher.now_rtc_to_epoch(localRTC.datetime())
        y, m, d, _, hh, mm, ss, _ = localRTC.datetime()
        ram_unused = int(((gc.mem_free()) / (gc.mem_free() + gc.mem_alloc())) * 100)
        #print(f"refresh_scheduler()  Loop Start  [{y:04}-{m:02}-{d:02} {hh:02}.{mm:02}.{ss:02}][RAM:{(100 - ram_unused):02}%][FDR:{(now - lastForecastDataRefresh):05}][BT:{(now - _updateMetadata["bulletin_time"]):05}][BN:{(now >= _updateMetadata["bulletin_next"]):>1}][FS:{(now - lastForecastSync):04}][NB:{new_bulletin:>1}][FND:{_forecastToday["yy"]:04}{_forecastToday["mm"]:02}{_forecastToday["dd"]:02}/{y:04}{m:02}{d:02}][LOR:{(now - lastOledRefresh):04}][SW:{(now - lastSynchroniseWatches):04}][LLR:{(now - lastLedRefresh):04}]")
        print(f"refresh_scheduler()  Loop Start  [RAM:{(100 - ram_unused):03}%][FDR:{(now - lastForecastDataRefresh):05}][BT:{(now - _updateMetadata["bulletin_time"]):05}][BN:{(now >= _updateMetadata["bulletin_next"]):>1}][FS:{(now - lastForecastSync):04}][NB:{new_bulletin:>1}][FND:{_forecastToday["yy"]:04}{_forecastToday["mm"]:02}{_forecastToday["dd"]:02}/{y:04}{m:02}{d:02}][LOR:{(now - lastOledRefresh):04}][SW:{(now - lastSynchroniseWatches):04}][LLR:{(now - lastLedRefresh):04}]")
        await asyncio.sleep(6)
        if ((now - lastForecastDataRefresh) >= INTERVAL_FORECAST_DATA) or ((now - _updateMetadata["bulletin_time"]) >= INTERVAL_BULLETIN_AGE) or (now >= _updateMetadata["bulletin_next"]):
            print(f"refresh_scheduler()  Loop Calls  get_forecast_data()   [FDR:{(now - lastForecastDataRefresh):05}][BT:{(now - _updateMetadata["bulletin_time"]):05}][BN:{(now >= _updateMetadata["bulletin_next"]):>1}]")
            forecast = asyncio.create_task(get_forecast_data(_geohash))
            lastForecastDataRefresh = now
            lastForecastDataRefresh, _forecastMeta, _forecastData = await forecast
            new_bulletin = True
        await asyncio.sleep(6)
        if ((now - lastForecastSync) >= INTERVAL_FORECAST_SYNC) or (new_bulletin == True):
            print(f"refresh_scheduler()  Loop Calls  update_forecast() [FS:{(now - lastForecastSync):04}][NB:{new_bulletin}]")
            forecastSync = asyncio.create_task(update_forecast(_forecastMeta, _forecastData, _timezoneOffset))
            lastForecastSync = now
            lastForecastSync, _updateMetadata, _forecastToday, _forecastTomorrow = await forecastSync
        elif (_forecastToday["yy"] != y) or (_forecastToday["mm"] != m) or (_forecastToday["dd"] != d):
            print(f"refresh_scheduler()  Loop Calls  update_forecast() [FND:{_forecastToday["yy"]:04}{_forecastToday["mm"]:02}{_forecastToday["dd"]:02}/{y:04}{m:02}{d:02}]")
            forecastSync = asyncio.create_task(update_forecast(_forecastMeta, _forecastData, _timezoneOffset))
            lastForecastSync = now
            lastForecastSync, _updateMetadata, _forecastToday, _forecastTomorrow = await forecastSync
            new_bulletin = True
        await asyncio.sleep(6)
        if ((now - lastOledRefresh) >= INTERVAL_OLED_REFRESH) or (new_bulletin == True):
            print(f"refresh_scheduler()  Loop Calls  pdate_display_oleds()    [LOR:{(now - lastOledRefresh):04}][NB:{new_bulletin}]")
            oleds = asyncio.create_task(update_display_oleds(_forecastToday, _forecastTomorrow, _locCity))
            lastOledRefresh = now
            lastOledRefresh = await oleds
        await asyncio.sleep(6)
        if ((now - lastSynchroniseWatches) >= INTERVAL_SYNC_WATCHES):
            print(f"refresh_scheduler()  Loop Calls  synchronise_watches() [SW:{(now - lastSynchroniseWatches):04}]")
            sync = asyncio.create_task(synchronise_watches())
            lastSynchroniseWatches = now
            lastSynchroniseWatches = await sync
        await asyncio.sleep(6)
        if ((now - lastLedRefresh) >= INTERVAL_LED_REFRESH) or (new_bulletin == True):
            print(f"refresh_scheduler()  Loop Calls  update_display_temps()    [LLR:{(now - lastLedRefresh):04}][NB:{new_bulletin}]")
            temps = asyncio.create_task(update_display_temps(_forecastToday['max'], _forecastToday['onlow'], _forecastTomorrow['max']))
            lastLedRefresh = now
            lastLedRefresh = await temps
        if (hh == EVENING_CUTOFF) and ((mm == 0) or (mm == 1) or (mm == 2)):
            print(f"refresh_scheduler()  Loop Calls  update_display_temps()    [EVE:hh{(hh):02}mm{(mm):02}]")
            temps = asyncio.create_task(update_display_temps(_forecastToday['max'], _forecastToday['onlow'], _forecastTomorrow['max']))
            lastLedRefresh = now
            lastLedRefresh = await temps
        new_bulletin = False
        #y, m, d, _, hh, mm, ss, _ = localRTC.datetime()
        now = TimeCruncher.now_rtc_to_epoch(localRTC.datetime())
        #print(f"refresh_scheduler()  Loop End    [{y:04}-{m:02}-{d:02} {hh:02}.{mm:02}.{ss:02}][RAM:{(100 - ram_unused):02}%][FDR:{(now - lastForecastDataRefresh):05}][BT:{(now - _updateMetadata["bulletin_time"]):05}][BN:{(now >= _updateMetadata["bulletin_next"]):>1}][FS:{(now - lastForecastSync):04}][NB:{new_bulletin:>1}][FND:{_forecastToday["yy"]:04}{_forecastToday["mm"]:02}{_forecastToday["dd"]:02}/{y:04}{m:02}{d:02}][LOR:{(now - lastOledRefresh):04}][SW:{(now - lastSynchroniseWatches):04}][LLR:{(now - lastLedRefresh):04}]")
        print(f"refresh_scheduler()  Loop End    [RAM:{(100 - ram_unused):03}%][FDR:{(now - lastForecastDataRefresh):05}][BT:{(now - _updateMetadata["bulletin_time"]):05}][BN:{(now >= _updateMetadata["bulletin_next"]):>1}][FS:{(now - lastForecastSync):04}][NB:{new_bulletin:>1}][FND:{_forecastToday["yy"]:04}{_forecastToday["mm"]:02}{_forecastToday["dd"]:02}/{y:04}{m:02}{d:02}][LOR:{(now - lastOledRefresh):04}][SW:{(now - lastSynchroniseWatches):04}][LLR:{(now - lastLedRefresh):04}]")
        logger.flush()
        gc.collect()
        await asyncio.sleep(95)        

### STARTUP PROCESSES
# first, get a GPS fix (function won't return until has_fix is True)
asyncio.run(get_GPS_fix())
# TERMINAL LOGGING FUNCTION 
if ENABLE_LOGGING == 0:
    pass
else:
    filename = create_daily_log_file()
    log = open(filename, "a")
    _original_print = builtins.print
    logger = PrintLogger(log, flush_interval=60)
    def logged_print(*args, **kwargs):
        _original_print(*args, **kwargs)
        line = " ".join(str(a) for a in args)
        logger.log_line(line)
    builtins.print = logged_print
# then, proceed with system setup
print("main.py calls system_setup()")
_geohash, _timezoneOffset = asyncio.run(system_setup())
# at this point, we can display the clock (until the main loop starts)
print("main.py calls update_display_clock()")
startupClock = asyncio.create_task(update_display_clock())
# attempt to connect to WiFi
disp4H.show_string("GEt")
disp4L.show_string("&IFI")
print("main.py calls enable_Wifi()")
asyncio.run(enable_Wifi())
time.sleep(1)
while wlan.checkWiFi() == False:
    print("checkWiFi() Attempting to connect to WiFi")
    asyncio.run(enable_Wifi())
    time.sleep(1)
# lookup location from the BoM
print("main.py calls get_location()")
_locCity, _locState = asyncio.run(get_location(_geohash))
try:
    print("main.py calls main_loop()")
    asyncio.run(main_loop(_geohash, _timezoneOffset, _locCity, _locState))
except KeyboardInterrupt:
    logger.flush()
except asyncio.CancelledError:
    print("MAIN LOOP CANCELLED")
    logger.flush()
    asyncio.new_event_loop() 
finally:
    logger.flush()
    asyncio.new_event_loop()