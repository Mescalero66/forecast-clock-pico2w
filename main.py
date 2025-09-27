import time
import asyncio
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
GPS_FIX = asyncio.Event()
NEW_FORECAST = asyncio.Event()

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
networks = wlan.scanWiFi()                                                                  # scan for the WLAN
wlan.connectWiFi()                                                                          # connect to the WLAN
print("WiFi Connected:", wlan.checkWiFi())                                                  # and double check

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

disp8.set_brightness(15)
disp4H.display_on(0)
disp4L.display_on(0)

mux.select_port(OLED_ID_TL)
oledTL = SSD1306_I2C(OLED_RES_X, OLED_RES_Y, mux.i2c)
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


def parse_iso8601_date(ts: str) -> int:
    date, timepart = ts.split("T")
    year, month, day = map(int, date.split("-"))
    return year, month, day


async def check_Wifi():
    if wlan.checkWiFi() == True:
        return
    wlan.connectWiFi(retries=5, wait_per_try=20)


async def get_GPS_fix():
    print("get_GPS_fix()")
    if GPS_obj.has_fix == True:
        return
    if not GPS_FIX.is_set():
        while GPS_obj.has_fix == False:
            GPS_obj.get_data()
            NumOfSats = (f"GPSSAT {GPS_obj.satellites}")
            print("update_8dig_disp(NumOfSats)")
            asyncio.create_task(update_8dig_disp(NumOfSats, "l"))
            await asyncio.sleep(1)
        GPS_FIX.set()
    await GPS_FIX.wait()
    return


async def get_GPS_data():
    global GPS_DATA, GPS_FIX
    print("get_GPS_data()")
    if GPS_obj.has_fix == False:
        GPS_FIX.clear()
        await get_GPS_fix()
    GPS_DATA = GPS_obj.get_data()
    return


async def update_GPS_data():
    global GPS_DATA, GPS_FIX
    while True:
        print("update_GPS_data()")
        if GPS_obj.has_fix == False:
            GPS_FIX.clear()
            await get_GPS_fix()
        GPS_DATA = GPS_obj.get_data()
        await asyncio.sleep(30)


async def update_time_sync():
    global GPS_DATA, GPS_FIX, TIMEZONE_OFFSET
    while True:
        print("update_time_sync()")
        if GPS_obj.has_fix == False:
            GPS_FIX.clear()
            await get_GPS_fix()
        epoch = time.mktime((GPS_DATA.year, GPS_DATA.month, GPS_DATA.day, GPS_DATA.hour, GPS_DATA.minute, GPS_DATA.second, 0, 0))
        weekday = time.localtime(epoch)[6]
        pico_rtc.datetime((GPS_DATA.year, GPS_DATA.month, GPS_DATA.day, weekday, GPS_DATA.hour, GPS_DATA.minute, GPS_DATA.second, 0))
        TimezoneInfo.update_localtime(GPS_DATA.latitude,GPS_DATA.longitude,(GPS_DATA.year, GPS_DATA.month, GPS_DATA.day, GPS_DATA.hour, GPS_DATA.minute, GPS_DATA.second))
        TIMEZONE_OFFSET = TimezoneInfo.tz_offset_minutes * 60
        await asyncio.sleep(32)


async def update_new_forecast_data():
    while True:
        print("update_new_forecast_data()")
        now = time.time()
        next_issue_time = BoMForecastInfo.fc_metadata.fc_next_issue_time
        if not next_issue_time:
            next_issue_time = (time.time() - 60)
        if now > parse_iso8601_datetime(next_issue_time):
            asyncio.create_task(get_location())
            await asyncio.sleep(2)
            asyncio.create_task(get_forecast())
            await asyncio.sleep(2)
        await asyncio.sleep(900)


async def get_location():
    global GPS_FIX, GEOHASH, C_LN, C_LS
    print("get_location()")
    if GPS_obj.has_fix == False:
        GPS_FIX.clear()
        await get_GPS_fix()
    GEOHASH = Geohash.encode(GPS_DATA.latitude, GPS_DATA.longitude, precision=7)
    if GEOHASH != BoMLocInfo.loc_current_data.loc_geohash:
        BoMLocInfo.update_location(GEOHASH)
        C_LN = BoMLocInfo.loc_name
        C_LS = BoMLocInfo.loc_state


async def update_clock_display():
    while True:
        y, m, d, hh, mm, ss, wd, yd = now_local()
        if mm == 0 or hh == 0:
            await date_check(y, m, d, wd)
        time_str = f"{hh:02} .{mm:02} .{ss:02}"
        disp8.set_string(time_str, "r")
        await asyncio.sleep(0.3)
        time_str = f"{hh:02} {mm:02} {ss:02}"
        disp8.set_string(time_str, "r")       
        await asyncio.sleep(0.7)


async def date_check(y, m, d, wd):
    global C_Y, C_M, C_D, C_WD
    print("date_check()")
    if (y == C_Y and m == C_M and d == C_D):
        return
    else:
        C_Y = y
        C_M = m
        C_D = d
        C_WD = wd
        asyncio.create_task(refresh_left_oleds())


async def get_forecast():
    print("get_forecast()")
    fc_meta, fc_data = BoMForecastInfo.update_forecast(GEOHASH)
    ny, nm, nd = time.gmtime()
    tdy, tdm, tdd = parse_iso8601_date(fc_data[0].fc_date)
    if ny != tdy or nm != tdm or nd != tdd:
        print("BoM JSON Data Out of Sync with Current Date")
        await asyncio.sleep(600)
        asyncio.create_task(get_forecast)
        return
    
    global TD_Y, TD_M, TD_M, TD_MAX, TD_MIN, TD_RAIN, TD_ICON, TD_TEXT
    global ON_LOW
    global TM_Y, TM_M, TM_D, TM_MAX, TM_MIN, TM_RAIN, TM_ICON, TM_TEXT

    TD_Y, TD_M, TD_M = to_local(parse_iso8601_date(fc_data[0].fc_date))
    TM_Y, TM_M, TM_D = to_local(parse_iso8601_date(fc_data[1].fc_date))

    TD_MAX = fc_data[0].fc_temp_max
    TD_MIN = fc_data[0].fc_temp_min
    TD_RAIN = fc_data[0].fc_rain_chance
    TD_ICON = fc_data[0].fc_icon_descriptor
    TD_TEXT = fc_data[0].fc_short_text
    ON_LOW = fc_meta.fc_overnight_min
    TM_MAX = fc_data[1].fc_temp_max
    TM_MIN = fc_data[1].fc_temp_min
    TM_RAIN = fc_data[1].fc_rain_chance
    TM_ICON = fc_data[1].fc_icon_descriptor
    TM_TEXT = fc_data[1].fc_short_text


async def update_temperature_display():
     while True:
        print("update_temperature_display()")
        if TD_MAX != None:
            y, m, d, hh, mm, ss, wd, yd = now_local()
            str_tmr = TM_MAX + "*c"
            disp4L.show_string(str_tmr)
            if hh < 3 or hh > 17:
                str_onl = ON_LOW + "*c"
                disp4H.show_string(str_onl)
            else:
                str_tdy = TD_MAX + "*c"
                disp4H.show_string(str_tdy)
            await asyncio.sleep(60)
        await asyncio.sleep(10)

async def refresh_left_oleds():
    print("refresh_left_oleds()")
    str_td_dow = DAYS_OF_WEEK[C_WD % 7]
    str_tm_dow = DAYS_OF_WEEK[(C_WD + 1) % 7]
    
    oledTL.fill(0)
    oledTL.banner_text_inverted(str_td_dow)
    str_td_date = C_Y + " / " + C_M + " / " + C_D
    oledTL.subbanner_text(str_td_date)
    oledTL.subbanner_text(C_LN, y=48)

    oledBL.fill(0)
    oledBL.banner_text_inverted(str_tm_dow)
    str_tm_date = TM_Y + " / " + TM_M + " / " + TM_D
    oledBL.subbanner_text(str_tm_date)
    oledBL.subbanner_text(C_LN, y=48)

    oledTL.show()
    oledBL.show()


async def refresh_right_oleds():
    # do something
    test = 0

async def update_8dig_disp(disp_string, alignment = "l"):
    disp8.set_string(disp_string, alignment)

async def main():
    await get_GPS_fix()
    await get_GPS_data()
    asyncio.create_task(update_GPS_data())
    await asyncio.sleep(2)
    asyncio.create_task(update_time_sync())
    await asyncio.sleep(2)
    asyncio.create_task(update_clock_display())
    await asyncio.sleep(2)
    asyncio.create_task(update_new_forecast_data())
    await asyncio.sleep(2)
    asyncio.create_task(update_temperature_display())
    await asyncio.sleep(2)
    print("Everything should be started now!")

asyncio.run(main())

print("this line should never be printed.")

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
