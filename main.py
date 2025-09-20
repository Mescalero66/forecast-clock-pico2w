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

TIMEZONE_OFFSET = 0
GPS_DATA = None
GPS_FIX = asyncio.Event()
NEW_FORECAST = asyncio.Event()
CY = 0
CM = 0
CD = 0
CLN = ""
CLS = ""

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

def parse_iso8601(ts: str) -> int:
    # Example input: "2025-09-20T19:00:00Z"
    date, timepart = ts.split("T")
    year, month, day = map(int, date.split("-"))
    hh, mm, ss = map(int, timepart.rstrip("Z").split(":"))
    # return epoch (UTC)
    return time.mktime((year, month, day, hh, mm, ss, 0, 0))

async def check_Wifi():
    if wlan.checkWiFi() == True:
        return
    wlan.connectWiFi(retries=5, wait_per_try=20)

async def get_GPS_fix():
    if GPS_obj.has_fix == True:
        return
    if not GPS_FIX.is_set():
        while GPS_obj.has_fix == False:
            GPS_obj.get_data()
            NumOfSats = (f"GPSSAT {GPS_obj.satellites}")
            asyncio.create_task(update_8dig_disp(NumOfSats, "l"))
            await asyncio.sleep(1)
        GPS_FIX.set()
    await GPS_FIX.wait()
    return

async def get_GPS_data():
    global GPS_DATA, GPS_FIX
    if GPS_obj.has_fix == False:
        GPS_FIX.clear()
        await get_GPS_fix()
    GPS_DATA = GPS_obj.get_data()
    return

async def update_GPS_data():
    global GPS_DATA, GPS_FIX
    while True:
        if GPS_obj.has_fix == False:
            GPS_FIX.clear()
            await get_GPS_fix()
        GPS_DATA = GPS_obj.get_data()
        await asyncio.sleep(30)

async def sync_time():
    global GPS_DATA, GPS_FIX, TIMEZONE_OFFSET
    while True:
        if GPS_obj.has_fix == False:
            GPS_FIX.clear()
            await get_GPS_fix()
        epoch = time.mktime((GPS_DATA.year, GPS_DATA.month, GPS_DATA.day, GPS_DATA.hour, GPS_DATA.minute, GPS_DATA.second, 0, 0))
        weekday = time.localtime(epoch)[6]
        pico_rtc.datetime((GPS_DATA.year, GPS_DATA.month, GPS_DATA.day, weekday, GPS_DATA.hour, GPS_DATA.minute, GPS_DATA.second, 0))
        TimezoneInfo.update_localtime(GPS_DATA.latitude,GPS_DATA.longitude,(GPS_DATA.year, GPS_DATA.month, GPS_DATA.day, GPS_DATA.hour, GPS_DATA.minute, GPS_DATA.second))
        TIMEZONE_OFFSET = TimezoneInfo.tz_offset_minutes * 60
        await asyncio.sleep(32)

async def check_new_forecast():
    while True:
        now = time.time()
        if now > parse_iso8601(BoMForecastInfo.fc_metadata.fc_next_issue_time):
            asyncio.create_task(get_location())
            await asyncio.sleep(2)
            asyncio.create_task(get_forecast())
            await asyncio.sleep(2)
        await asyncio.sleep(900)

async def get_location():
    global GPS_DATA, GPS_FIX
    while True:
        if GPS_obj.has_fix == False:
            GPS_FIX.clear()
            await get_GPS_fix()
        geohash = Geohash.encode(GPS_DATA.latitude, GPS_DATA.longitude, precision=7)
        if geohash != BoMLocInfo.loc_current_data.loc_geohash:
            BoMLocInfo.update_location(geohash)
            LocName = BoMLocInfo.loc_name
            LocState = BoMLocInfo.loc_state
            asyncio.create_task(display_location(LocName, LocState))

async def display_location(LocName, LocState):
    global CLN, CLS
    if (LocName == CLN and LocState == CLS):
        return
    # else, update the screen with the correct location name and state

async def display_time():
    while True:
        y, m, d, hh, mm, ss, wd, yd = now_local()
        asyncio.create_task(display_date(y, m, d, wd))
        time_str = f"{hh:02} .{mm:02} .{ss:02}"
        disp8.set_string(time_str, "r")
        await asyncio.sleep(0.5)
        time_str = f"{hh:02} {mm:02} {ss:02}"
        disp8.set_string(time_str, "r")       
        await asyncio.sleep(0.5)

async def display_date(y, m, d, wd):
    global CY, CM, CD
    if (y == CY and m == CM and d == CD):
        return
    # else, update the screen with the correct date

async def get_forecast():
    global GPS_DATA
    while True:
        if GPS_obj.has_fix == False:
            GPS_FIX.clear()
            await get_GPS_fix()
        # get the forecast from the thing
        # update some displays or something

async def display_temperatures():
    # do something
    test = 0

async def display_forecasts():
    # do something
    test = 0

async def update_8dig_disp(disp_string, alignment = "l"):
    disp8.set_string(disp_string, alignment)

async def main():
    # do something
    test = 0

asyncio.run(get_GPS_fix())

while True:
    gps_data = GPS_obj.get_data()
    sat_string = (f"GPSSAT {gps_data.satellites}")
    disp8.set_string(sat_string, "l")
    if gps_data.has_fix == True:
        
        print(f"GPS: {gps_data.year}{gps_data.month}{gps_data.day} {gps_data.hour}.{gps_data.minute}.{gps_data.second}")

        timezonetime = TimezoneInfo.update_localtime(gps_data.latitude,gps_data.longitude,(gps_data.year, gps_data.month, gps_data.day, gps_data.hour, gps_data.minute, gps_data.second))
        print(f"GPS: {gps_data.latitude} {gps_data.longitude}")
        print(TimezoneInfo.tz_offset_minutes)
        # DO NOT DELETE
        TIMEZONE_OFFSET = timezonetime.offset_minutes * 60

        # local_year, local_month, local_day, local_hour, local_minute, local_second = (timezonetime[k] for k in ['year','month','day','hour','minute','second'])
        # print(f"Austimezone: {local_year}{local_month}{local_day} {local_hour}.{local_minute}.{local_second}")
        # time.sleep(1)

        # yy, mm, dd, hr, mn, sc = (local_year, local_month, local_day, local_hour, local_minute, local_second)
        # epoch = time.mktime((yy, mm, dd, hr, mn, sc, 0, 0))
        # weekday = time.localtime(epoch)[6]

        epoch = time.mktime((gps_data.year, gps_data.month, gps_data.day, gps_data.hour, gps_data.minute, gps_data.second, 0, 0))
        weekday = time.localtime(epoch)[6]

        pico_rtc.datetime((gps_data.year, gps_data.month, gps_data.day, weekday, gps_data.hour, gps_data.minute, gps_data.second, 0))
        
        rtc_year, rtc_month, rtc_day, rtc_wd, rtc_hour, rtc_minute, rtc_second, rtc_us = pico_rtc.datetime()
        print(f"RTC: {rtc_year}{rtc_month}{rtc_day} {rtc_hour}.{rtc_minute}.{rtc_second}")

        gh_output = Geohash.encode(gps_data.latitude, gps_data.longitude, precision=7)
        print(f"GeoHash: {gh_output}")

        BoMLocInfo.update_location(gh_output)
        print(f"Location: {BoMLocInfo.loc_name}")

        fc_meta, fc_data = BoMForecastInfo.update_forecast(gh_output)
        print(f"Forecast NIT: {fc_meta.fc_next_issue_time}")
        print(f"Forecast TIMESTAMP: {fc_meta.fc_issue_time}")
        print(f"Time Time: {time.time()}")
        print(f"Forecast NIT parsed: {parse_iso8601(fc_meta.fc_next_issue_time)}")
        print(f"Local Time: {now_local()}")
        print(f"UTC Time: {now_utc()}")
        print(f"Day 0 Max: {fc_data[0].fc_temp_max}")
        print(f"Day 1 Max: {fc_data[1].fc_temp_max}")
        print(f"Day 2 Max: {fc_data[2].fc_temp_max}")
        time.sleep(1)

        break
    time.sleep(2)
while True:

    # y, m, d, wd, hh, mm, ss, us = pico_rtc.datetime()
    y, m, d, hh, mm, ss, wd, yd = now_local()
    # print(f"y: {y} m: {m} d: {d} wd: {wd} hh: {hh} mm: {mm} ss: {ss} wd: {wd} yd: {yd}")

    m_str = f"{d:02}.{m:02}"
    y_str = f"{y:04}"
    disp4H.show_string(m_str)
    disp4L.show_string(y_str)
    
    # oledTL.fill(0)
    # oledTL.banner_text_inverted(ss * y)
    # oledTR.fill(0)
    # oledTR.banner_text(ss * m)
    # oledBL.fill(0)
    # oledBL.date_text(ss * d)
    # oledBR.fill(0)
    # oledBR.text_inverted(ss * hh, x=25,y=48)

    # mux.select_port(OLED_ID_TL)
    # oledTL.show()
    # mux.select_port(OLED_ID_TR)
    # oledTR.show()
    # mux.select_port(OLED_ID_BL)
    # oledBL.show()
    # mux.select_port(OLED_ID_BR)
    # oledBR.show()

    time_str = f"{hh:02} .{mm:02} .{ss:02}"
    disp8.set_string(time_str, "r")
    time.sleep(0.5)
    time_str = f"{hh:02} {mm:02} {ss:02}"
    disp8.set_string(time_str, "r")
    time.sleep(0.5)
