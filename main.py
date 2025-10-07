import time
import asyncio
import machine
from machine import I2C, Pin, UART, RTC
from hardware.LED8_HT16K33 import HT16K33LED
from hardware.GPS_PARSER import GPSReader
from hardware.LED4_TM1650 import LED4digdisp
from hardware.MUX_TCA9548A import I2CMultiplex
from hardware.OLED_SSD1306 import SSD1306_I2C
from hardware.WLAN import WLAN
import functions.timezones as AusTimeZones
import functions.geohash as Geohash
import functions.forecast as BoMdata

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

ADDR_MUX = 0x70

OLED_RES_X = 128
OLED_RES_Y = 64
OLED_ID_TL = 2
OLED_ID_TR = 3
OLED_ID_BL = 0
OLED_ID_BR = 1

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

TIMEZONE_OFFSET = 0
GEOHASH = None
GPS_DATA = None

VALID_WIFI_CONNECTION = False
VALID_GPS_FIX = False
VALID_GPS_DATA = False
VALID_GEOHASH_DATA = False
VALID_LOCATION_DATA = False
VALID_FORECAST_DATA = False

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

wlan = WLAN()                                                                               # create WLAN object

pico_rtc = RTC()                                                                            # create Real Time Clock

uart = UART(0, baudrate=9600, tx=Pin(PIN_UART_TX), rx=Pin(PIN_UART_RX))                     # Set up UART connection to GPS module
i2c = I2C(0, scl=Pin(PIN_LED8_SCL), sda=Pin(PIN_LED8_SDA))                                  # Set up I2C connection
 
mux = I2CMultiplex(ADDR_MUX, I2Cbus=1, scl_pin=PIN_MUX_SCL, sda_pin=PIN_MUX_SDA)            # Set up I2C multiplexer

GPS_obj = GPSReader(uart)                                                                   # Create a GPS reader object   
disp8 = HT16K33LED(i2c)                                                                     # Create 8digit LED object
disp4H = LED4digdisp(1, PIN_LED4H_SCL, PIN_LED4H_SDA)                                       # Create 4digit LED object (HIGH)         
disp4L = LED4digdisp(2, PIN_LED4L_SCL, PIN_LED4L_SDA)                                       # Create 4digit LED object (LOW)

BoMLocInfo = BoMdata.BoMLocation()                                                          # Create the BoM Location data structure
BoMForecastInfo = BoMdata.BoMForecast()                                                     # Create the BoM Forecast data structure
TimezoneInfo = AusTimeZones.LocalTimezone()                                                 # Create the Timezone data structure

mux.select_port(OLED_ID_TL)                                                                 # select the correct mux port
oledTL = SSD1306_I2C(OLED_RES_X, OLED_RES_Y, mux.i2c)                                       # and create the OLED object
mux.select_port(OLED_ID_TR)
oledTR = SSD1306_I2C(OLED_RES_X, OLED_RES_Y, mux.i2c)
mux.select_port(OLED_ID_BL)
oledBL = SSD1306_I2C(OLED_RES_X, OLED_RES_Y, mux.i2c)
mux.select_port(OLED_ID_BR)
oledBR = SSD1306_I2C(OLED_RES_X, OLED_RES_Y, mux.i2c)

def now_utc():
    return time.time()

def now_local():
    return time.localtime(time.time() + TIMEZONE_OFFSET)

def to_local(epoch_seconds):
    return time.localtime(epoch_seconds + TIMEZONE_OFFSET)

def to_epoch(time_tuple):
    return time.mktime(time_tuple)

def get_weekday(GPSy, GPSm, GPSd):
    y, m, d = GPSy, GPSm, GPSd
    if m < 3:
        m += 12
        y -= 1
    K = y % 100
    J = y // 100
    weekday = (d + (13*(m+1))//5 + K + K//4 + J//4 + 5*J) % 7
    weekday = (weekday + 6) % 7
    return weekday

def parse_iso8601_datetime(ts: str) -> int:
    try:
        date, timepart = ts.split("T")
    except ValueError:
        raise ValueError("Invalid ISO8601 string: %s" % ts)

    year, month, day = map(int, date.split("-"))

    # Remove trailing Z if present
    timepart = timepart.rstrip("Z")

    # Handle fractional seconds by splitting on "."
    if "." in timepart:
        timepart, _ = timepart.split(".", 1)  # drop fraction

    parts = list(map(int, timepart.split(":")))
    if len(parts) == 2:      # "HH:MM"
        hh, mm = parts
        ss = 0
    elif len(parts) == 3:    # "HH:MM:SS"
        hh, mm, ss = parts
    else:
        raise ValueError("Invalid time part in: %s" % ts)

    # Build time tuple for mktime
    return time.mktime((year, month, day, hh, mm, ss, 0, 0))

def parse_iso8601_date(ts: str):
    if not ts or not ts.strip():
        raise ValueError("Empty date string")
    ts = ts.strip()
    try:
        date_part = ts.split("T")[0]   # ignore time
        year, month, day = map(int, date_part.split("-"))
    except Exception as e:
        raise ValueError(f"Invalid date string '{ts}': {e}")
    return year, month, day

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
    global VALID_GPS_FIX
    print("get_GPS_fix()")
    if GPS_obj.has_fix:
        VALID_GPS_FIX = True
        return
    else:
        VALID_GPS_FIX = False
        while not GPS_obj.has_fix:
            GPS_obj.get_data()
            print("get_GPS_fix() listens for satellites...")
            await asyncio.sleep(0.25)
            NoS = f"oSats {GPS_obj.satellites}°"
            disp8.set_string(NoS, "r")
            await asyncio.sleep(0.25)
            NoS = f"°Sats {GPS_obj.satellites}o"
            disp8.set_string(NoS, "r")
            GPS_obj.get_data()
            await asyncio.sleep(0.25)
            NoS = f"oSats {GPS_obj.satellites}°"
            disp8.set_string(NoS, "r")
            await asyncio.sleep(0.25)
            NoS = f"°Sats {GPS_obj.satellites}o"
            disp8.set_string(NoS, "r")
        VALID_GPS_FIX = True
    return

async def get_GPS_data():
    global GPS_DATA, VALID_GPS_DATA, GEOHASH, VALID_GEOHASH_DATA
    print("get_GPS_data()")
    if not VALID_GPS_FIX:
        VALID_GPS_DATA = False
        await get_GPS_fix()
    GPS_obj.get_data()
    GPS_DATA = GPS_obj.get_data()
    print(f"Lat: [{GPS_DATA.latitude}] Long: [{GPS_DATA.longitude}] Alt: [{GPS_DATA.altitude}]")
    lat = float(GPS_DATA.latitude)
    long = float(GPS_DATA.longitude)
    GEOHASH = Geohash.encode(lat, long, precision=7)
    if not GPS_DATA.year == None:
        VALID_GPS_DATA = True
    if not GEOHASH == None:
        VALID_GEOHASH_DATA = True
    return

async def update_GPS_data():
    global GPS_DATA, VALID_GPS_DATA, VALID_GPS_FIX
    print("update_GPS_data()")
    VALID_GPS_DATA = False
    while True:
        if not VALID_GPS_FIX:
            VALID_GPS_FIX = False
            print("update_GPS_data() dreams of a VALID_GPS_FIX...")
            await asyncio.sleep(15)
            if not GPS_obj.has_fix:
                await get_GPS_fix()
        GPS_DATA = GPS_obj.get_data()
        await asyncio.sleep(1)
        if not GPS_DATA.year == None:
            VALID_GPS_DATA = True
        else:
            VALID_GPS_DATA = False

async def update_time_sync(initial):
    global GPS_DATA, TIMEZONE_OFFSET, C_Y, C_M, C_D, C_WD
    while True:
        print("update_time_sync()")
        while not VALID_GPS_DATA:
            print("update_time_sync() dreams of VALID_GPS_DATA...")
            await asyncio.sleep(7)
        GPS_DATA = GPS_obj.get_data()
        weekday = get_weekday(GPS_DATA.year, GPS_DATA.month, GPS_DATA.day)
        pico_rtc.datetime((GPS_DATA.year, GPS_DATA.month, GPS_DATA.day, weekday, GPS_DATA.hour, GPS_DATA.minute, GPS_DATA.second, 0))
        TimezoneInfo.update_localtime(GPS_DATA.latitude,GPS_DATA.longitude,(GPS_DATA.year, GPS_DATA.month, GPS_DATA.day, GPS_DATA.hour, GPS_DATA.minute, GPS_DATA.second))
        TIMEZONE_OFFSET = TimezoneInfo.tz_offset_minutes * 60
        C_Y, C_M, C_D, _, _, _, C_WD, _ = now_local()
        if TIMEZONE_OFFSET == None:
            await asyncio.sleep(5)
        else:
            if initial:
                return
            await asyncio.sleep(60)

async def update_new_forecast_data():
    await asyncio.sleep(10)
    while True:
        print("update_new_forecast_data()")
        now = time.time()
        next_issue_time = BoMForecastInfo.fc_metadata.fc_next_issue_time
        if not next_issue_time:
            next_issue_time = "2013-10-143T10:25:00Z"
        if now > parse_iso8601_datetime(next_issue_time):
            await get_location()
            while not VALID_GEOHASH_DATA:
                print("update_new_forecast_data() dreams of VALID_GEOHASH_DATA...")
                await asyncio.sleep(5)
                await get_location()
            asyncio.create_task(get_forecast())
        await asyncio.sleep(900)

async def get_location():
    global GPS_DATA, C_LN, C_LS, VALID_GEOHASH_DATA, VALID_LOCATION_DATA
    print(f"get_location()")
    if not GEOHASH:
        await get_GPS_data()
    if BoMLocInfo == None:
        VALID_LOCATION_DATA = False
    while not VALID_GPS_DATA:
        print("get_location() dreams of VALID_GPS_DATA...")
        await asyncio.sleep(7)
    try:
        LocationData = BoMLocInfo.update_location(GEOHASH)
        await asyncio.sleep(2)
        if LocationData.loc_id == None:
            print(f"Where in the world is Geohash San Diego?: {GEOHASH}")
            VALID_LOCATION_DATA = False
            return
        C_LN = LocationData.loc_name
        C_LS = LocationData.loc_state
        VALID_LOCATION_DATA = True
        print("Location: ", C_LN, C_LS)
    except Exception as e:
        print(f"Error in get_location(), location could not be got: {e}")
        VALID_LOCATION_DATA = False

async def update_clock_display():
    global GPS_DATA
    while TIMEZONE_OFFSET == None:
        print("update_clock_display() dreams of a non-zero TIMEZONE_OFFSET...")
        await asyncio.sleep(7)
    while True:
        y, m, d, hh, mm, ss, wd, _ = now_local()
        time_str = f"{hh:02} .{mm:02} .{ss:02}"
        disp8.set_string(time_str, "r")
        await asyncio.sleep(0.2)
        time_str = f"{hh:02} {mm:02} {ss:02}"
        disp8.set_string(time_str, "r")       
        await asyncio.sleep(0.8)
        if ss == 0:
            asyncio.create_task(date_check(y, m, d, wd))

async def date_check(y, m, d, wd):
    global C_Y, C_M, C_D, C_WD
    # print("date_check()")
    if (y, m, d != C_Y, C_M, C_D):
        C_Y, C_M, C_D, C_WD = y, m, d, wd
        asyncio.create_task(refresh_left_oleds())
    return

async def get_forecast():
    global VALID_FORECAST_DATA
    global TD_Y, TD_M, TD_M, TD_MAX, TD_MIN, TD_RAIN, TD_ICON, TD_TEXT
    global ON_LOW
    global TM_Y, TM_M, TM_D, TM_MAX, TM_MIN, TM_RAIN, TM_ICON, TM_TEXT
    print("get_forecast()")
    if BoMForecastInfo.fc_metadata.fc_response_timestamp == None:
        VALID_FORECAST_DATA = False
    while not VALID_GEOHASH_DATA:
        print("get_forecast() dreams of VALID_GEOHASH_DATA...")
        await asyncio.sleep(24)
    validText = None
    fc_meta, fc_data = BoMForecastInfo.update_forecast(GEOHASH)
    TD_Y, TD_M, TD_M, _, _, _, _, _  = to_local(parse_iso8601_datetime(fc_data[0].fc_date))
    TM_Y, TM_M, TM_D, _, _, _, _, _  = to_local(parse_iso8601_datetime(fc_data[1].fc_date))
    TD_MAX = fc_data[0].fc_temp_max
    TD_MIN = fc_data[0].fc_temp_min
    TD_RAIN = fc_data[0].fc_rain_chance
    TD_ICON = fc_data[0].fc_icon_descriptor
    TD_TEXT = fc_data[0].fc_short_text
    validText = fc_data[0].fc_short_text 
    ON_LOW = fc_meta.fc_overnight_min
    TM_MAX = fc_data[1].fc_temp_max
    TM_MIN = fc_data[1].fc_temp_min
    TM_RAIN = fc_data[1].fc_rain_chance
    TM_ICON = fc_data[1].fc_icon_descriptor
    TM_TEXT = fc_data[1].fc_short_text
    if not validText == None:
        VALID_FORECAST_DATA = True

async def update_temperature_display():
    while not VALID_FORECAST_DATA:
        print("update_temperature_display() dreams of VALID_FORECAST_DATA...")
        await asyncio.sleep(20)
    while True:
        print("update_temperature_display()")
        _, _, _, hh, _, _, _, _ = now_local()
        if hh < 4 or hh > 17:
            str_onl = f"{ON_LOW}*C"
            disp4H.show_string(str_onl)
        else:
            str_tdy = f"{TD_MAX}*C"
            disp4H.show_string(str_tdy)
        str_tmr = f"{TM_MAX:02}*C"
        disp4L.show_string(str_tmr)
        await asyncio.sleep(300)

async def refresh_left_oleds():
    print("refresh_left_oleds()")
    await asyncio.sleep(0)

    while not VALID_LOCATION_DATA or not VALID_FORECAST_DATA:
        print("refresh_left_oleds() dreams of VALID_FORECAST_DATA and/or VALID_LOCATION_DATA")
        await asyncio.sleep(15)

    str_td_dow = DAYS_OF_WEEK[C_WD % 7]
    str_tm_dow = DAYS_OF_WEEK[(C_WD + 1) % 7]
    
    oledTL.fill(0)
    oledTL.banner_text_inverted(str_td_dow)
    str_td_date = f"{C_D:02} / {C_M:02} / {C_Y:04}"
    oledTL.custom_text(str_td_date, y=16, font_width=16, font_height=16, scale=1, c=1)
    oledTL.custom_text(C_LN, y=48, font_width=12, font_height=12, scale=1, c=1)

    oledBL.fill(0)
    oledBL.banner_text_inverted(str_tm_dow)
    str_tm_date = f"{TM_D:02} / {TM_M:02} / {TM_Y:04}"
    oledBL.custom_text(str_tm_date, y=16, font_width=16, font_height=16, scale=1, c=1)
    oledBL.custom_text(C_LN, y=48, font_width=12, font_height=12, scale=2, c=1)

    await asyncio.sleep(0)

    print("refreshing left LEDs")
    mux.select_port(OLED_ID_TL)
    oledTL.show()
    mux.select_port(OLED_ID_BL)
    oledBL.show()

async def refresh_right_oleds():
    # do something
    test = 0

async def main():
    await check_Wifi()
    time.sleep(1)
    await get_GPS_fix()                                                               # get an initial GPS fix
    time.sleep(3)
    await get_GPS_data()                                                              # populate the initial GPS data
    time.sleep(3)

    oledBL.fill(0)
    text = "Getting GPS data......"
    oledBL.text(text, x=1, y=16, c=1)
    print("GPS Year: ", GPS_DATA.year)
    mux.select_port(OLED_ID_BL)
    oledBL.show()

    if not VALID_GPS_DATA:
        await get_GPS_data()                                                    # if the GPS data didn't make it, try one more time
    
    time.sleep(2)

    oledBL.fill(0)
    oledBL.text("GPS data is valid.", x=1, y=16, c=1)
    oledBL.text("Synchronising time zone......", x=1, y=32, c=1)
    mux.select_port(OLED_ID_BL)
    oledBL.show()

    time.sleep(2)

    await update_time_sync(initial=True)
    time.sleep(3)
    print("Timezone Offset: ", TIMEZONE_OFFSET)

    oledBL.fill(0)
    oledBL.text("GPS data is valid.", x=1, y=16, c=1)
    oledBL.text("Timezone set.", x=1, y=32, c=1)
    oledBL.text("Getting location data......", x=1, y=48, c=1)
    mux.select_port(OLED_ID_BL)
    oledBL.show()

    await get_location()
    time.sleep(3)
    print("geoHash: ", GEOHASH)
    print("Location: ", C_LN, " [", C_LS,"]")
    
    oledBL.fill(0)
    vG = f"geoHash Valid: {GEOHASH}"
    vL = f"Location: {C_LN} [{C_LS}]"
    oledBL.text(vG, x=1, y=16, c=1)
    oledBL.text(vL, x=1, y=32, c=1)
    oledBL.text("Getting forecast for location.......", x=1, y=48, c=1)
    mux.select_port(OLED_ID_BL)
    oledBL.show()
    
    await get_forecast()
    time.sleep(3)
    vF = f"Forecast: {TD_D:02} / {TD_M:02} / {TD_Y:04}"
    print("Forecast Date: ", vF)
    
    oledBL.fill(0)
    vG = f"geoHash Valid: {GEOHASH}"
    vL = f"Location: {C_LN} [{C_LS}]"
    vF = f"Forecast: {TD_D:02} / {TD_M:02} / {TD_Y:04}"
    oledBL.text(vG, x=1, y=16, c=1)
    oledBL.text(vL, x=1, y=32, c=1)
    oledBL.text(vF, x=1, y=48, c=1)
    mux.select_port(OLED_ID_BL)
    oledBL.show()

    tasks = []

    tasks.append(asyncio.create_task(update_clock_display()))
    tasks.append(asyncio.create_task(update_temperature_display()))
    tasks.append(asyncio.create_task(update_time_sync()))
    tasks.append(asyncio.create_task(update_new_forecast_data()))

    # tasks.append(asyncio.create_task(update_GPS_data()))
    print("ALL TASKS STARTED!")

#wlan.disconnectWiFi()
networks = wlan.scanWiFi()                                                                  # scan for the WLAN
wlan.connectWiFi()                                                                          # connect to the WLAN
print("WiFi Connected:", wlan.checkWiFi())                                                  # and double check

disp8.set_brightness(15)                                    # TURN ON THE 8 DIGIT DISPLAY WITH MAX BRIGHTNESS
disp4H.display_on(0)                                        # TURN ON THE UPPER 4 DIGIT DISPLAY WITH MAX BRIGHTNESS
disp4H.show_string("_")                                     # display underscore placeholder
disp4L.display_on(0)                                        # TURN ON THE LOWER 4 DIGIT DISPLAY WITH MAX BRIGHTNESS
disp4L.show_string("_")                                     # display underscore placeholder

mux.select_port(OLED_ID_TL)                                                                 # select the correct mux port
oledTL.subbanner_text("TL",64,32,1)                                                               # display placeholder
oledTL.show()
mux.select_port(OLED_ID_TR)
oledTR.date_text("TR",16,1)                                                               # display placeholder
oledTR.show()
mux.select_port(OLED_ID_BL)
oledBL.date_text("BL",16,1)                                                                    # display placeholder
oledBL.show()
mux.select_port(OLED_ID_BR)
oledBR.year_text("BR")                                                    # display placeholder
oledBR.show()

asyncio.run(main())                                                   # start the main thing

# try:
#     main()
# except Exception as e:
#     print("Error in main loop. Pico will reboot!")
#     print(e)
#     time.sleep(5)
#     print("Pico will reboot!")
#     time.sleep(3)
#     #machine.reset()

print("If you can read this, it's gone wrong.")

# while True:
#     gps_data = GPS_obj.get_data()
#     sat_string = (f"GPSSAT {gps_data.satellites}")
#     disp8.set_string(sat_string, "l")
#     if gps_data.has_fix == True:
        
#         print(f"GPS: {gps_data.year}{gps_data.month}{gps_data.day} {gps_data.hour}.{gps_data.minute}.{gps_data.second}")

#         timezonetime = TimezoneInfo.update_localtime(gps_data.latitude,gps_data.longitude,(gps_data.year, gps_data.month, gps_data.day, gps_data.hour, gps_data.minute, gps_data.second))
#         print(f"GPS: {gps_data.latitude} {gps_data.longitude}")
#         print(TimezoneInfo.tz_offset_minutes)
#         # DO NOT DELETE
#         TIMEZONE_OFFSET = timezonetime.offset_minutes * 60

#         # local_year, local_month, local_day, local_hour, local_minute, local_second = (timezonetime[k] for k in ['year','month','day','hour','minute','second'])
#         # print(f"Austimezone: {local_year}{local_month}{local_day} {local_hour}.{local_minute}.{local_second}")
#         # time.sleep(1)

#         # yy, mm, dd, hr, mn, sc = (local_year, local_month, local_day, local_hour, local_minute, local_second)
#         # epoch = time.mktime((yy, mm, dd, hr, mn, sc, 0, 0))
#         # weekday = time.localtime(epoch)[6]

#         epoch = time.mktime((gps_data.year, gps_data.month, gps_data.day, gps_data.hour, gps_data.minute, gps_data.second, 0, 0))
#         weekday = time.localtime(epoch)[6]

#         pico_rtc.datetime((gps_data.year, gps_data.month, gps_data.day, weekday, gps_data.hour, gps_data.minute, gps_data.second, 0))
        
#         rtc_year, rtc_month, rtc_day, rtc_wd, rtc_hour, rtc_minute, rtc_second, rtc_us = pico_rtc.datetime()
#         print(f"RTC: {rtc_year}{rtc_month}{rtc_day} {rtc_hour}.{rtc_minute}.{rtc_second}")

#         gh_output = Geohash.encode(gps_data.latitude, gps_data.longitude, precision=7)
#         print(f"GeoHash: {gh_output}")

#         BoMLocInfo.update_location(gh_output)
#         print(f"Location: {BoMLocInfo.loc_name}")

#         fc_meta, fc_data = BoMForecastInfo.update_forecast(gh_output)
#         print(f"Day 0 Max: {fc_data[0].fc_temp_max}")
#         print(f"Day 1 Max: {fc_data[1].fc_temp_max}")
#         print(f"Day 2 Max: {fc_data[2].fc_temp_max}")
#         time.sleep(1)

#         break
#     time.sleep(2)
# while True:

#     # y, m, d, wd, hh, mm, ss, us = pico_rtc.datetime()
#     y, m, d, hh, mm, ss, wd, yd = now_local()
#     # print(f"y: {y} m: {m} d: {d} wd: {wd} hh: {hh} mm: {mm} ss: {ss} wd: {wd} yd: {yd}")

#     m_str = f"{d:02}.{m:02}"
#     y_str = f"{y:04}"
#     disp4H.show_string(m_str)
#     disp4L.show_string(y_str)
    
#     # oledTL.fill(0)
#     # oledTL.banner_text_inverted(ss * y)
#     # oledTR.fill(0)
#     # oledTR.banner_text(ss * m)
#     # oledBL.fill(0)
#     # oledBL.date_text(ss * d)
#     # oledBR.fill(0)
#     # oledBR.text_inverted(ss * hh, x=25,y=48)

#     # mux.select_port(OLED_ID_TL)
#     # oledTL.show()
#     # mux.select_port(OLED_ID_TR)
#     # oledTR.show()
#     # mux.select_port(OLED_ID_BL)
#     # oledBL.show()
#     # mux.select_port(OLED_ID_BR)
#     # oledBR.show()

#     time_str = f"{hh:02} .{mm:02} .{ss:02}"
#     disp8.set_string(time_str, "r")
#     time.sleep(0.5)
#     time_str = f"{hh:02} {mm:02} {ss:02}"
#     disp8.set_string(time_str, "r")
#     time.sleep(0.5)
