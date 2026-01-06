import time
import asyncio
import machine
from machine import I2C, Pin, UART, RTC
from collections import deque

from hardware.LED8_HT16K33 import HT16K33LED
from hardware.GPS_PARSER import GPSReader
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
## OLED RESOLUTIONS
OLED_RES_X = 128
OLED_RES_Y = 64
OLED_ID_TL = 2
OLED_ID_TR = 3
OLED_ID_BL = 0
OLED_ID_BR = 1
## CONSTANTS
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS_OF_YEAR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
## GLOBALS
MAX_FORECAST_DATA_AGE = 24 * 3600
RETRY_TIME_NO_REPLY = 30 * 60
LAST_ISSUE_TIME = None
LAST_CONNECTION_TIME = None
TIMEZONE_OFFSET = None
GEOHASH = None
GPS_DATA = None
VALID_WIFI_CONNECTION = False
VALID_GPS_FIX = False
VALID_GPS_DATA = False
VALID_LOCATION_DATA = False
VALID_FORECAST_DATA = False
REQUIRE_REFRESH = False
C_Y = None
C_M = None
C_D = None
C_WD = None
C_LN = None
C_LS = None
TD_Y = None
TD_M = None
TD_D = None
TD_MAX = None
TD_MIN = None
TD_RAIN = None
TD_ICON = None
TD_TEXT = None
ON_LOW = None
TM_Y = None
TM_M = None
TM_D = None
TM_MAX = None
TM_MIN = None
TM_RAIN = None
TM_ICON = None
TM_TEXT = None
## EVENT QUEUE
OLED_EVENT_QUEUE = deque((), 10)
## EVENTS
EV_STARTUP = 1
EV_TIME_TICK = 2
EV_DATE_CHANGE = 3
EV_LOCATION_UPD = 4
EV_FORECAST_UPD = 5
EV_FORECAST_FAIL = 6

## HARDWARE
wlan = WLAN()                                                                               # create WLAN object
pico_rtc = machine.RTC()                                                                    # create Real Time Clock
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

disp8.set_brightness(15)                                        # TURN ON THE 8 DIGIT DISPLAY WITH MAX BRIGHTNESS
disp4H.display_on(0)                                            # TURN ON THE UPPER 4 DIGIT DISPLAY WITH MAX BRIGHTNESS
disp4H.show_string("__*C")                                     
disp4L.display_on(0)
disp4L.show_string("__*C")

def oled_event(event):
    OLED_EVENT_QUEUE.append((event, time.time()))


async def check_Wifi():
    global VALID_WIFI_CONNECTION
    VALID_WIFI_CONNECTION = False
    if wlan.checkWiFi() == True:
        VALID_WIFI_CONNECTION = True
        return
    else:
        wlan.connectWiFi(retries=3, wait_per_try=5)
        if wlan.checkWiFi() == True:
            VALID_WIFI_CONNECTION = True
        else:
            VALID_WIFI_CONNECTION = False
    return

async def get_GPS_fix():
    global VALID_GPS_FIX, GPS_DATA
    print("get_GPS_fix()")
    if GPS_obj.has_fix:
        VALID_GPS_FIX = True
        return
    else:
        VALID_GPS_FIX = False
        t = 0.1
        while not GPS_obj.has_fix:
            GPS_DATA = GPS_obj.get_data()
            NoS = f"- {GPS_obj.satellites} GPS-"
            disp8.set_string(NoS, "r")
            disp4H.show_string(" _# ")
            disp4L.show_string(" ~~ ")
            await asyncio.sleep(t)
            print("get_GPS_fix() listens for satellites...")
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
            NoS = f"- {GPS_obj.satellites} GPS-"
            disp8.set_string(NoS, "r")
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
        GPS_DATA = GPS_obj.get_data()
        VALID_GPS_FIX = True
    return

async def get_GPS_data():
    global GPS_DATA, VALID_GPS_DATA, GEOHASH, TIMEZONE_OFFSET, C_Y, C_M, C_D, C_WD
    # this now does everything, as the catch-all initial populating of required variables
    print("get_GPS_data()")
    if not VALID_GPS_FIX:
        VALID_GPS_DATA = False
        print("get_GPS_data() awaits a GPS fix.....")
        await get_GPS_fix()
    
    # this is the showstopper for getting a valid initial set of data:
    while GPS_DATA.latitude == None or GPS_DATA.longitude == None or GPS_DATA.latitude == 0.0 or GPS_DATA.longitude == 0.0:
        await asyncio.sleep(1)
        GPS_DATA = GPS_obj.get_data()
    print(f"Lat: [{GPS_DATA.latitude}] Long: [{GPS_DATA.longitude}] Alt: [{GPS_DATA.altitude}]")
        
    # get and set the geohash
    GPS_DATA = GPS_obj.get_data()
    GEOHASH = Geohash.encode(float(GPS_DATA.latitude), float(GPS_DATA.longitude), precision=7)
    
    # get and set the pico's internal clock [UTC]
    weekday = TimeCruncher.get_weekday(GPS_DATA.year, GPS_DATA.month, GPS_DATA.day)
    pico_rtc.datetime((GPS_DATA.year, GPS_DATA.month, GPS_DATA.day, weekday, GPS_DATA.hour, GPS_DATA.minute, GPS_DATA.second, 0))
    
    # get and set the timezone offset
    # GPS_DATA = GPS_obj.get_data()
    print(f"Y{GPS_DATA.year} M{GPS_DATA.month} D{GPS_DATA.day} H{GPS_DATA.hour} M{GPS_DATA.minute} S{GPS_DATA.second}")
    TimezoneInfo.update_localtime(GPS_DATA.latitude,GPS_DATA.longitude,(GPS_DATA.year, GPS_DATA.month, GPS_DATA.day, GPS_DATA.hour, GPS_DATA.minute, GPS_DATA.second))
    TIMEZONE_OFFSET = TimezoneInfo.tz_offset_minutes * 60
    
    # get and set the local date
    C_Y, C_M, C_D, hhh, mmm, sss, C_WD, _ = TimeCruncher.now_local(TIMEZONE_OFFSET)
    # print(f"LY{C_Y} LM{C_M} LD{C_D} isDST{TimezoneInfo.tz_data.is_DST} LHH{hhh} MM{mmm} LSS{sss} LWD{C_WD}")
    
    if not GPS_DATA.year == None:
        VALID_GPS_DATA = True
    return

async def update_GPS_data():
    global GPS_DATA, VALID_GPS_DATA, VALID_GPS_FIX
    print("update_GPS_data()")
    if not VALID_GPS_FIX:
        VALID_GPS_FIX = False
        VALID_GPS_DATA = False
        print("update_GPS_data() dreams of a VALID_GPS_FIX...")
        return
    else:
        GPS_obj.get_data()
        GPS_DATA = GPS_obj.get_data()
        if not GPS_DATA.year == None:
            VALID_GPS_DATA = True
            print("update_GPS_data() has updated the GPS_DATA.")
        else:
            VALID_GPS_DATA = False
        return    

async def update_time_sync():
    global GPS_DATA, TIMEZONE_OFFSET, C_Y, C_M, C_D, C_WD
    while True:
        if not VALID_GPS_DATA:
            print("update_time_sync() dreams of VALID_GPS_DATA...")
        else:
            if GPS_obj.has_new_data:
                gps_snap = GPS_obj.get_data()
                fields = [gps_snap.year, gps_snap.month, gps_snap.day, gps_snap.hour, gps_snap.minute, gps_snap.second]
                if any(f is None for f in fields) or any(f == 0 for f in fields):
                    print("GPS snapshot invalid or incomplete - skipping RTC sync.")
                    await asyncio.sleep(15)
                    continue
                gps_age_ms = None
                if hasattr(GPS_obj, "last_data_time"):
                    try:
                        gps_age_ms = time.ticks_diff(time.ticks_ms(), GPS_obj.last_data_time)
                    except Exception:
                        pass
                if gps_age_ms is not None and gps_age_ms > 3000:
                    print(f"GPS data too old ({gps_age_ms} ms) - skipping RTC sync.")
                    await asyncio.sleep(15)
                    continue
                weekday = TimeCruncher.get_weekday(gps_snap.year, gps_snap.month, gps_snap.day)
                pico_rtc.datetime(gps_snap.year, gps_snap.month, gps_snap.day, weekday, gps_snap.hour, gps_snap.minute, gps_snap.second, 0)
                print(f"RTC updated to {gps_snap.hour:02}:{gps_snap.minute:02}:{gps_snap.second:02} UTC")
                if TIMEZONE_OFFSET == None:
                    TimezoneInfo.update_localtime(GPS_DATA.latitude,GPS_DATA.longitude,(GPS_DATA.year, GPS_DATA.month, GPS_DATA.day, GPS_DATA.hour, GPS_DATA.minute, GPS_DATA.second))
                    TIMEZONE_OFFSET = TimezoneInfo.tz_offset_minutes * 60
                    print("update_time_sync() has re-calculated the TIMEZONE_OFFSET.")    
                C_Y, C_M, C_D, hh, mm, ss, C_WD, _ = TimeCruncher.now_local(TIMEZONE_OFFSET)
                print(f"update_time_sync() has re-calculated the time as {hh:02} {mm:02} {ss:02}")
                GPS_obj.has_new_data = False
        await asyncio.sleep(15)

async def update_new_forecast_data():
    global LAST_ISSUE_TIME, LAST_CONNECTION_TIME
    await asyncio.sleep(10)
    while True:
        print("update_new_forecast_data()")
        LAST_CONNECTION_TIME = time.time()
        LAST_ISSUE_TIME = TimeCruncher.parse_8601datetime(BoMForecastInfo.fc_metadata.fc_issue_time)
        now = time.time()
        raw_next = BoMForecastInfo.fc_metadata.fc_next_issue_time or "2013-10-14T10:25:00Z"
        next = TimeCruncher.parse_8601datetime(raw_next)
        issue_time = TimeCruncher.parse_8601datetime(BoMForecastInfo.fc_metadata.fc_issue_time)
        response_time = TimeCruncher.parse_8601datetime(BoMForecastInfo.fc_metadata.fc_response_timestamp)
        # Update from the BoM's scheduled next forecast
        if now > next:
            print("update_new_forecast_data() suggests it's time for a new forecast.")
            asyncio.create_task(get_forecast())
            await asyncio.sleep(60)
            continue
        # Update if there was no response from the server
        if (now - LAST_CONNECTION_TIME) > RETRY_TIME_NO_REPLY:
            print("update_new_forecast_data() didn't get a response from the BoM last time.")
            asyncio.create_task(get_forecast())
            await asyncio.sleep(60)
            continue
        # Update if the data is older than 24 hours
        if (now - issue_time) > MAX_FORECAST_DATA_AGE:
            print("update_new_forecast_data() has forecast data that's older than 24 hours.")
            asyncio.create_task(get_forecast())
            await asyncio.sleep(60)
            continue
    
        waiting_time = min(next - now, MAX_FORECAST_DATA_AGE)
        print(f"update_new_forecast_data() thinks the next forecast update is {(waiting_time / 60):01} mins away.")
        await asyncio.sleep(max(waiting_time, 60))

async def get_location():
    global GPS_DATA, C_LN, C_LS, VALID_LOCATION_DATA
    print(f"get_location()")
    if not VALID_GPS_DATA:
        print("get_location() dreams of VALID_GPS_DATA...")
    else:
        GPS_DATA = GPS_obj.get_data()
        LocationData = BoMLocInfo.update_location(GEOHASH)
        await asyncio.sleep(2)
        if LocationData.loc_id == None:
            VALID_LOCATION_DATA = False
            return
        else:
            C_LN = LocationData.loc_name
            C_LS = LocationData.loc_state
            VALID_LOCATION_DATA = True
            oled_event(EV_LOCATION_UPD)
            print("get_location() has an updated Location:", C_LN, C_LS)
    return

async def update_clock_display():
    while True:
        _, _, _, hh, mm, ss, _, _ = TimeCruncher.now_local(TIMEZONE_OFFSET)
        time_str = f"{hh:02} .{mm:02} .{ss:02}"
        disp8.set_string(time_str, "r")
        await asyncio.sleep(0.2)
        time_str = f"{hh:02} {mm:02} {ss:02}"
        # print(f"{hh:02} {mm:02} {ss:02}")
        disp8.set_string(time_str, "r")       
        await asyncio.sleep(0.8)
        if ss == 0:
            y, m, d, _, _, _, wd, _ = TimeCruncher.now_local(TIMEZONE_OFFSET)
            asyncio.create_task(date_check(y, m, d, wd))

async def date_check(y, m, d, wd):
    global C_Y, C_M, C_D, C_WD
    if (y, m, d) != (C_Y, C_M, C_D):
        # print(f"date_check() thinks the date has changed. It was {C_Y}-{C_M}-{C_D}, now it's {y}-{m}-{d}")
        C_Y, C_M, C_D, C_WD = y, m, d, wd
        await asyncio.sleep(1)
        asyncio.create_task(sync_forecast())
        await asyncio.sleep(3)
        oled_event(EV_DATE_CHANGE)
    return

async def sync_forecast():
    global TD_Y, TD_M, TD_D, TD_MAX, TD_MIN, TD_RAIN, TD_ICON, TD_TEXT
    global ON_LOW
    global TM_Y, TM_M, TM_D, TM_MAX, TM_MIN, TM_RAIN, TM_ICON, TM_TEXT
    i = None
    validText = None
    if not VALID_FORECAST_DATA:
        oled_event(EV_FORECAST_FAIL)
        print("sync_forecast() dreams of VALID_FORECAST_DATA...")
        return
    else:
        fc_meta, fc_data = BoMForecastInfo.fc_metadata, BoMForecastInfo.fc_current_data
        for idx in range(5):
            _, chkM, chkD, _, _, _, _, _ = TimeCruncher.parse_8601localtime(fc_data[idx].fc_date, TIMEZONE_OFFSET)
            # print(f"sync_forecast() is comparing {chkM} to {C_M}, and {chkD} to {C_D}")
            if (C_D == chkD) and (C_M == chkM):
                i = idx
                break  
        # print(f"sync_forecast() has identified the correct day as #{i}")
        if i == None:
            print(f"sync_forecast() has a forecast for {TimeCruncher.parse_8601localtime(fc_data[0].fc_date)}, but isn't today {C_D}/{C_M}/{C_Y}???")
            await get_forecast()
            return
        TD_Y, TD_M, TD_D, _, _, _, _, _  = TimeCruncher.parse_8601localtime(fc_data[i].fc_date, TIMEZONE_OFFSET)
        TM_Y, TM_M, TM_D, _, _, _, _, _  = TimeCruncher.parse_8601localtime(fc_data[i + 1].fc_date, TIMEZONE_OFFSET)        
        TD_MAX = fc_data[i].fc_temp_max
        TD_MIN = fc_data[i].fc_temp_min
        TD_RAIN = fc_data[i].fc_rain_chance
        TD_ICON = fc_data[i].fc_icon_descriptor
        TD_TEXT = fc_data[i].fc_short_text
        ON_LOW = fc_meta.fc_overnight_min
        TM_MAX = fc_data[i + 1].fc_temp_max
        TM_MIN = fc_data[i + 1].fc_temp_min
        TM_RAIN = fc_data[i + 1].fc_rain_chance
        TM_ICON = fc_data[i + 1].fc_icon_descriptor
        TM_TEXT = fc_data[i + 1].fc_short_text
        validText = TM_TEXT
        print(f"TD: {TD_Y}{TD_M}{TD_D} Max:{TD_MAX} Min:{TD_MIN} {TD_TEXT}")
        print(f"TM: {TM_Y}{TM_M}{TM_D} Max:{TM_MAX} Min:{TM_MIN} {TM_TEXT}")
        oled_event(EV_FORECAST_UPD)
        if not validText == None:
            print("sync_forecast() has synced the forecast.")
        else:
            print("sync_forecast() has failed to sync the current forecast to the current day.")
            return

async def get_forecast():
    global VALID_FORECAST_DATA, LAST_CONNECTION_TIME, LAST_ISSUE_TIME
    print("get_forecast()")
    if not GEOHASH:
        print("get_forecast() dreams of VALID_GEOHASH_DATA...")
        return
    else:
        try:
            fc_meta, fc_data = BoMForecastInfo.update_forecast(GEOHASH)
        except:
            print("get_forecast() has failed to retrieve a valid forecast from the BoM")
            await asyncio.sleep(2)
            oled_event(EV_FORECAST_FAIL)
            return
        LAST_CONNECTION_TIME = TimeCruncher.parse_8601datetime(fc_meta.fc_response_timestamp)
        new_issue = TimeCruncher.parse_8601datetime(fc_meta.fc_issue_time)
        if new_issue != LAST_ISSUE_TIME:
            print(f"get_forecast() has a valid forecast from the BoM that was issued at {fc_meta.fc_issue_time}")
            LAST_ISSUE_TIME = new_issue
            oled_event(EV_FORECAST_UPD)
        if not fc_data[0].fc_short_text == None:
            await sync_forecast()
            await asyncio.sleep(6)
            VALID_FORECAST_DATA = True
            oled_event(EV_FORECAST_UPD)
            print("get_forecast() has updated the forecast.")

async def update_temperature_display():
    print("update_temperature_display()")
    if not VALID_FORECAST_DATA:
        print("update_temperature_display() dreams of VALID_FORECAST_DATA...")
        asyncio.create_task(get_forecast())
        await asyncio.sleep(30)    
    while True:
        print("update_temperature_display()")
        _, _, _, hh, _, _, _, _ = TimeCruncher.now_local(TIMEZONE_OFFSET)
        if hh < 4 or hh > 18:
            str_onl = f"{ON_LOW}*C"
            disp4H.show_string(str_onl)
        else:
            str_tdy = f"{TD_MAX}*C"
            disp4H.show_string(str_tdy)
        str_tmr = f"{TM_MAX}*C"
        disp4L.show_string(str_tmr)
        await asyncio.sleep(300)

async def oled_refresh_scheduler():
    last_render = 0
    MIN_REFRESH = 30
    MAX_REFRESH = 300
    while True:
        now = time.time()
        if now - last_render > MAX_REFRESH:
            while OLED_EVENT_QUEUE:
                OLED_EVENT_QUEUE.popleft()
            await render_oleds()
            last_render = now
            continue
        if OLED_EVENT_QUEUE:
            if now - last_render < MIN_REFRESH:
                await asyncio.sleep(MIN_REFRESH)
                continue
            while OLED_EVENT_QUEUE:
                OLED_EVENT_QUEUE.popleft()
            await render_oleds()
            last_render = now
            continue
        await asyncio.sleep(15)

async def render_oleds():
    # get the days of the week
    str_td_dow = DAYS_OF_WEEK[C_WD % 7]
    str_tm_dow = DAYS_OF_WEEK[(C_WD + 1) % 7]

    # get the months of the year
    str_td_moy = MONTHS_OF_YEAR[TD_M - 1]
    str_tm_moy = MONTHS_OF_YEAR[TM_M - 1]

    # get the hour of the day
    _, _, _, hh, _, _, _, _ = TimeCruncher.now_local(TIMEZONE_OFFSET)

    # clear the screens and fill in the banners
    mux.select_port(OLED_ID_TL)
    oledTL.fill(0)
    oledTL.fill_rect(0, 0, 128, 16, 1)
    oledBL.fill(0)
    oledBL.fill_rect(0, 0, 128, 16, 1)
    oledTR.fill(0)
    oledTR.fill_rect(0, 0, 128, 16, 1)
    oledBR.fill(0)
    oledBR.fill_rect(0, 0, 128, 16, 1)

    # top left
    date_header = f"{TD_D:02} {str_td_moy} {TD_Y:04}"
    oledTLhead.write(date_header, x=64, halign="center", y=1, fg=0, bg=1)
    oledTL23.write(str_td_dow, halign="center", y=17, x=64)
    oledTL16.write("Rain: ", halign="left", y=46, x=4)
    str_rain_percent = f"{TD_RAIN:0}%"
    oledTL23.write(str_rain_percent, halign="right", y=41, x=123)

    # bottom left
    date_header = f"{TM_D:02} {str_tm_moy} {TM_Y:04}"
    oledBLhead.write(date_header, x=64, halign="center", y=1, fg=0, bg=1)
    oledBL23.write(str_tm_dow, halign="center", y=17, x=64)
    oledBL16.write("Rain: ", halign="left", y=47, x=4)
    str_rain_percent = f"{TM_RAIN:0}%"
    oledBL23.write(str_rain_percent, halign="right", y=42, x=123)

    # top right
    oledTRhead.write(C_LN, x=64, halign="center", y=1, fg=0, bg=1)
    icon = IconGrabber.get_icon(TD_ICON, 37, TIMEZONE_OFFSET, day=0)
    oledTR.display_pbm(icon, x_offset=5, y_offset=17)           
    test_text = ezFBfont.split_text(TD_TEXT)
    oledTR12.write(test_text, halign="center", valign="center", y=34, x=90)
    if hh < 4 or hh > 18:
        oledTR12.write("Overnight Low:", halign="left", y=54, x=46)
    else:
        oledTR12.write("Min:", halign="left", y=54, x=55)
        str_min = f"{TD_MIN:0}°C"
        oledTR16.write(str_min, halign="right", y=53, x=122)

    # bottom right
    oledBRhead.write(C_LN, x=64, halign="center", y=1, fg=0, bg=1)
    icon = IconGrabber.get_icon(TM_ICON, 37, TIMEZONE_OFFSET, day=1)
    oledBR.display_pbm(icon, x_offset=5, y_offset=17)
    test_text = ezFBfont.split_text(TM_TEXT)
    oledBR12.write(test_text, halign="center", valign="center", y=34, x=90)
    oledBR12.write("Min:", halign="left", y=54, x=55)
    str_min = f"{TM_MIN:0}°C"
    oledBR16.write(str_min, halign="right", y=53, x=122)

    # print("writing data to OLEDs")
    mux.select_port(OLED_ID_TL)
    oledTL.show()
    mux.select_port(OLED_ID_BL)
    oledBL.show()
    mux.select_port(OLED_ID_TR)
    oledTR.show()
    mux.select_port(OLED_ID_BR)
    oledBR.show()

async def refresh_oleds():
    global REQUIRE_REFRESH
    while True:
        while not REQUIRE_REFRESH:
            # print("refresh_oleds() doesn't think the OLEDs need a refresh")
            await asyncio.sleep(60)
        
        # get the days of the week
        str_td_dow = DAYS_OF_WEEK[C_WD % 7]
        str_tm_dow = DAYS_OF_WEEK[(C_WD + 1) % 7]

        # get the months of the year
        str_td_moy = MONTHS_OF_YEAR[TD_M - 1]
        str_tm_moy = MONTHS_OF_YEAR[TM_M - 1]

        # get the hour of the day
        _, _, _, hh, _, _, _, _ = TimeCruncher.now_local(TIMEZONE_OFFSET)

        # clear the screens and fill in the banners
        mux.select_port(OLED_ID_TL)
        oledTL.fill(0)
        oledTL.fill_rect(0, 0, 128, 16, 1)
        oledBL.fill(0)
        oledBL.fill_rect(0, 0, 128, 16, 1)
        oledTR.fill(0)
        oledTR.fill_rect(0, 0, 128, 16, 1)
        oledBR.fill(0)
        oledBR.fill_rect(0, 0, 128, 16, 1)

        # top left
        date_header = f"{TD_D:02} {str_td_moy} {TD_Y:04}"
        oledTLhead.write(date_header, x=64, halign="center", y=1, fg=0, bg=1)
        oledTL23.write(str_td_dow, halign="center", y=17, x=64)
        oledTL16.write("Rain: ", halign="left", y=46, x=4)
        str_rain_percent = f"{TD_RAIN:0}%"
        oledTL23.write(str_rain_percent, halign="right", y=41, x=123)

        # bottom left
        date_header = f"{TM_D:02} {str_tm_moy} {TM_Y:04}"
        oledBLhead.write(date_header, x=64, halign="center", y=1, fg=0, bg=1)
        oledBL23.write(str_tm_dow, halign="center", y=17, x=64)
        oledBL16.write("Rain: ", halign="left", y=47, x=4)
        str_rain_percent = f"{TM_RAIN:0}%"
        oledBL23.write(str_rain_percent, halign="right", y=42, x=123)

        # top right
        oledTRhead.write(C_LN, x=64, halign="center", y=1, fg=0, bg=1)
        icon = IconGrabber.get_icon(TD_ICON, 37, TIMEZONE_OFFSET, day=0)
        oledTR.display_pbm(icon, x_offset=5, y_offset=17)           
        test_text = ezFBfont.split_text(TD_TEXT)
        oledTR12.write(test_text, halign="center", valign="center", y=34, x=90)
        if hh < 4 or hh > 18:
            oledTR12.write("Overnight Low:", halign="left", y=54, x=46)
        else:
            oledTR12.write("Min:", halign="left", y=54, x=55)
            str_min = f"{TD_MIN:0}°C"
            oledTR16.write(str_min, halign="right", y=53, x=122)

        # bottom right
        oledBRhead.write(C_LN, x=64, halign="center", y=1, fg=0, bg=1)
        icon = IconGrabber.get_icon(TM_ICON, 37, TIMEZONE_OFFSET, day=1)
        oledBR.display_pbm(icon, x_offset=5, y_offset=17)
        test_text = ezFBfont.split_text(TM_TEXT)
        oledBR12.write(test_text, halign="center", valign="center", y=34, x=90)
        oledBR12.write("Min:", halign="left", y=54, x=55)
        str_min = f"{TM_MIN:0}°C"
        oledBR16.write(str_min, halign="right", y=53, x=122)

        # print("writing data to OLEDs")
        mux.select_port(OLED_ID_TL)
        oledTL.show()
        mux.select_port(OLED_ID_BL)
        oledBL.show()
        mux.select_port(OLED_ID_TR)
        oledTR.show()
        mux.select_port(OLED_ID_BR)
        oledBR.show()

        REQUIRE_REFRESH = False

        await asyncio.sleep(120)

async def main():
    tasks = []
    result = None

    if not startup_clock_display.done():
        startup_clock_display.cancel()
        try:
            await startup_clock_display
        except asyncio.CancelledError:
            print("Startup version of update_clock_display() is cancelled.")
    
    tasks.append(asyncio.create_task(update_clock_display()))
    await asyncio.sleep(2)
    
    tasks.append(asyncio.create_task(update_time_sync()))
    await asyncio.sleep(2)    

    tasks.append(asyncio.create_task(update_temperature_display()))
    await asyncio.sleep(2)

    tasks.append(asyncio.create_task(update_new_forecast_data()))
    
    await asyncio.sleep(7)
    # tasks.append(asyncio.create_task(refresh_oleds()))
    tasks.append(asyncio.create_task(oled_refresh_scheduler()))
    # tasks.append(asyncio.create_task(render_oleds()))
    await asyncio.sleep(2)

    print("ALL ONGOING TASKS STARTED!")

    try:
        result = await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        print("ONGOING TASKS LOOP CANCELLED")
    print('Result: ', result)

# START UP PROCEDURE
tasks = []
oled_event(EV_STARTUP)
asyncio.run(get_GPS_fix())

while VALID_GPS_FIX is False:
    print("Retry get_GPS_fix()")
    time.sleep(1)
    asyncio.run(get_GPS_fix())

asyncio.run(get_GPS_data())

while GEOHASH is None or TIMEZONE_OFFSET is None or C_Y is None:
    print("Retry get_GPS_data()")
    time.sleep(1)
    asyncio.run(get_GPS_data())

startup_clock_display = asyncio.create_task(update_clock_display())
asyncio.sleep(1)

disp4H.show_string("GEt")
disp4L.show_string("UIFI")
asyncio.run(check_Wifi())

while VALID_WIFI_CONNECTION is False:
    print("Retry check_Wifi()")
    time.sleep(1)
    asyncio.run(check_Wifi())

asyncio.run(get_location())

while VALID_LOCATION_DATA is False:
    print("Retry get_location()")
    time.sleep(1)
    asyncio.run(get_location())

asyncio.run(get_forecast())

while VALID_FORECAST_DATA is False:
    print("Retry get_forecast()")
    time.sleep(1)
    asyncio.run(get_forecast())

asyncio.run(sync_forecast())

while TD_TEXT is None:
    print("Retry sync_forecast()")
    time.sleep(1)
    asyncio.run(get_forecast())
    time.sleep(1)
    asyncio.run(sync_forecast())

try:
    asyncio.run(main())
except asyncio.CancelledError:
    print('MAIN LOOP CANCELLED')
    asyncio.new_event_loop() 
finally:
    asyncio.new_event_loop()
