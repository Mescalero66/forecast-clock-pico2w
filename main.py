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
import functions.forecast as BoMData
import functions.time_cruncher as TimeCruncher
import functions.weather_icons as IconGrabber

from functions.string_writer import ezFBfont as ezFBfont
from fonts import spleen8, spleen12, spleen16, spleen23, helvetica15bold, helvetica18bold, schoolbook16, schoolbook16bold

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
MONTHS_OF_YEAR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

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

wlan = WLAN()                                                                               # create WLAN object

pico_rtc = RTC()                                                                            # create Real Time Clock

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
            NoS = f"-Sats {GPS_obj.satellites}-"
            disp8.set_string(NoS, "r")
            disp4H.show_string(" _# ")
            disp4L.show_string(" ~~ ")
            await asyncio.sleep(t)
            print("get_GPS_fix() listens for satellites...")
            disp4H.show_string(" _=>")
            await asyncio.sleep(t)
            disp4H.show_string(" __=")
            await asyncio.sleep(t)
            disp4H.show_string(" __ ")
            disp4L.show_string(" ~~>")
            await asyncio.sleep(t)
            disp4L.show_string(" ~>=")
            await asyncio.sleep(t)
            disp4L.show_string(" ~# ")
            await asyncio.sleep(t)
            NoS = f"-Sats {GPS_obj.satellites}-"
            disp8.set_string(NoS, "r")
            disp4L.show_string(" #~ ")
            await asyncio.sleep(t)
            disp4L.show_string("=>~ ")
            await asyncio.sleep(t)
            disp4L.show_string(">~~ ")
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
    
    # get the data
    GPS_DATA = GPS_obj.get_data()
    print(f"Lat: [{GPS_DATA.latitude}] Long: [{GPS_DATA.longitude}] Alt: [{GPS_DATA.altitude}]")

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
    GPS_DATA = GPS_obj.get_data()
    print(f"Y{GPS_DATA.year} M{GPS_DATA.month} D{GPS_DATA.day} H{GPS_DATA.hour} M{GPS_DATA.minute} S{GPS_DATA.second}")
    TimezoneInfo.update_localtime(GPS_DATA.latitude,GPS_DATA.longitude,(GPS_DATA.year, GPS_DATA.month, GPS_DATA.day, GPS_DATA.hour, GPS_DATA.minute, GPS_DATA.second))
    TIMEZONE_OFFSET = TimezoneInfo.tz_offset_minutes * 60
    
    # get and set the local date
    C_Y, C_M, C_D, _, _, _, C_WD, _ = TimeCruncher.now_local(TIMEZONE_OFFSET)
    print(f"LY{C_Y} LM{C_M} LD{C_D} LWD{C_WD}")
    
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
            GPS_DATA = GPS_obj.get_data()
            weekday = TimeCruncher.get_weekday(GPS_DATA.year, GPS_DATA.month, GPS_DATA.day)
            pico_rtc.datetime((GPS_DATA.year, GPS_DATA.month, GPS_DATA.day, weekday, GPS_DATA.hour, GPS_DATA.minute, GPS_DATA.second, 0))
            if TIMEZONE_OFFSET == None:
                TimezoneInfo.update_localtime(GPS_DATA.latitude,GPS_DATA.longitude,(GPS_DATA.year, GPS_DATA.month, GPS_DATA.day, GPS_DATA.hour, GPS_DATA.minute, GPS_DATA.second))
                TIMEZONE_OFFSET = TimezoneInfo.tz_offset_minutes * 60
                print("update_time_sync() has re-calculated the TIMEZONE_OFFSET.")         
            C_Y, C_M, C_D, _, _, _, C_WD, _ = TimeCruncher.now_local(TIMEZONE_OFFSET)
            print("update_time_sync() has re-calculated the TIME.")  
        await asyncio.sleep(900)

async def update_new_forecast_data():
    await asyncio.sleep(10)
    while True:
        print("update_new_forecast_data()")
        now = time.time()
        raw_next = BoMForecastInfo.fc_metadata.fc_next_issue_time or "2013-10-14T10:25:00Z"
        next = TimeCruncher.parse_8601datetime(raw_next)
        waiting_time = max((next - now), 0)
        if now > next:
            print("update_new_forecast_data() suggests it's time for a new forecast.")
            asyncio.create_task(get_forecast())
            await asyncio.sleep(60)
        await asyncio.sleep(waiting_time)

async def get_location():
    global GPS_DATA, C_LN, C_LS, VALID_LOCATION_DATA, REQUIRE_REFRESH
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
            REQUIRE_REFRESH = True
            print("get_location() has updated the Location: ", C_LN, C_LS)
    return

async def update_clock_display():
    global GPS_DATA
    while TIMEZONE_OFFSET == None:
        print("update_clock_display() dreams of a non-zero TIMEZONE_OFFSET...")
        await asyncio.sleep(7)
    while True:
        y, m, d, hh, mm, ss, wd, _ = TimeCruncher.now_local(TIMEZONE_OFFSET)
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
    global REQUIRE_REFRESH
    # print("date_check()")
    if (y, m, d != C_Y, C_M, C_D):
        C_Y, C_M, C_D, C_WD = y, m, d, wd
        REQUIRE_REFRESH = True
    return

async def get_forecast():
    global VALID_FORECAST_DATA, REQUIRE_REFRESH
    global TD_Y, TD_M, TD_D, TD_MAX, TD_MIN, TD_RAIN, TD_ICON, TD_TEXT
    global ON_LOW
    global TM_Y, TM_M, TM_D, TM_MAX, TM_MIN, TM_RAIN, TM_ICON, TM_TEXT
    print("get_forecast()")
    if not VALID_GPS_DATA:
        print("get_location() dreams of VALID_GPS_DATA...")
        return
    elif not GEOHASH:
        print("get_forecast() dreams of VALID_GEOHASH_DATA...")
        return
    else:
        validText = None
        fc_meta, fc_data = BoMForecastInfo.update_forecast(GEOHASH)
        TD_Y, TD_M, TD_D, _, _, _, _, _  = TimeCruncher.parse_8601localtime(fc_data[0].fc_date, TIMEZONE_OFFSET)
        TM_Y, TM_M, TM_D, _, _, _, _, _  = TimeCruncher.parse_8601localtime(fc_data[1].fc_date, TIMEZONE_OFFSET)
        
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
        print(f"TD: {TD_Y}{TD_M}{TD_D} Max:{TD_MAX} Min:{TD_MIN} {TD_TEXT}")
        print(f"TM: {TM_Y}{TM_M}{TM_D} Max:{TM_MAX} Min:{TM_MIN} {TM_TEXT}")
        if not validText == None:
            VALID_FORECAST_DATA = True
            REQUIRE_REFRESH = True
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
        if hh < 4 or hh > 17:
            str_onl = f"{ON_LOW}*C"
            disp4H.show_string(str_onl)
        else:
            str_tdy = f"{TD_MAX}*C"
            disp4H.show_string(str_tdy)
        str_tmr = f"{TM_MAX:02}*C"
        disp4L.show_string(str_tmr)
        await asyncio.sleep(300)

async def refresh_oleds():
    while True:
        while not REQUIRE_REFRESH:
            await asyncio.sleep(30)
        
        # get the days of the week
        str_td_dow = DAYS_OF_WEEK[C_WD % 7]
        str_tm_dow = DAYS_OF_WEEK[(C_WD + 1) % 7]

        # get the months of the year
        str_td_moy = MONTHS_OF_YEAR[TD_M]
        str_tm_moy = MONTHS_OF_YEAR[TM_M]

        # clear the screens
        oledTL.fill(0)
        oledTL.rect(0, 0, 128, 16, 1)
        oledBL.fill(0)
        oledBL.rect(0, 0, 128, 16, 1)
        oledTR.fill(0)
        oledTR.rect(0, 0, 128, 16, 1)
        oledBR.fill(0)
        oledBR.rect(0, 0, 128, 16, 1)

        # top left
        oledTL.banner_text_inverted(str_td_dow, scale=14)
        str_td_date = f"{C_D:02} {str_td_moy}"
        str_td_yy = f"{C_Y:04}"
        oledTL.input_text(str_td_date, y_start=20, x_scale=2, y_scale=4)
        oledTL.input_text(str_td_yy, y_start=55, x_scale=1, y_scale=1)

        # bottom left
        oledBL.banner_text_inverted(str_tm_dow, scale=14)
        str_tm_date = f"{TM_D:02} {str_tm_moy}"
        str_tm_yy = f"{TM_Y:04}"
        oledBL.input_text(str_tm_date, y_start=20, x_scale=2, y_scale=4)
        oledBL.input_text(str_tm_yy, y_start=55, x_scale=1, y_scale=1)

        # top right
        oledTR.banner_text_inverted(C_LN, scale=11)

        # bottom right
        oledBR.banner_text_inverted(C_LN, scale=11)

        print("refreshing OLEDs")
        mux.select_port(OLED_ID_TL)
        oledTL.show()
        mux.select_port(OLED_ID_BL)
        oledBL.show()
        mux.select_port(OLED_ID_TR)
        oledTR.show()
        mux.select_port(OLED_ID_BR)
        oledBR.show()

        await asyncio.sleep(60)

async def refresh_right_oleds():
    # do something
    test = 0

async def main():
    await check_Wifi()
    time.sleep(1)
    await get_GPS_fix()                                                               # get an initial GPS fix
    time.sleep(1)
    await get_GPS_data()                                                              # populate the initial GPS data
    time.sleep(1)

    if not VALID_GPS_DATA:
        await get_GPS_data()                                                    # if the GPS data didn't make it, try one more time

    print("geoHash: ", GEOHASH)
    time.sleep(1)

    await get_location()
    time.sleep(1)
    print("Location: ", C_LN, " [", C_LS,"]")

    await get_forecast()
    time.sleep(3)
    vF = f"Forecast: {TD_D:02}/{TD_M:02}/{TD_Y:04}"
    print("Forecast Date: ", vF)
    
    asyncio.create_task(update_time_sync())
    await asyncio.sleep(10)
    print("Timezone Offset: ", TIMEZONE_OFFSET)

    asyncio.create_task(update_clock_display())
    await asyncio.sleep(10)
    print("update_clock_display() has commenced.")

    asyncio.create_task(update_temperature_display())
    await asyncio.sleep(10)
    print("update_temperature_display() has commenced.")

    asyncio.create_task(update_new_forecast_data())
    await asyncio.sleep(10)
    print("update_new_forecast_data() has commenced.")

    await asyncio.sleep(10)
    print("FORCE MANUAL UPDATE OF OLEDS!!!!!!! - NOT FOR PRODUCTION")

    # tasks.append(asyncio.create_task(update_GPS_data()))
    print("ALL TASKS STARTED!")

disp8.set_brightness(15)                                        # TURN ON THE 8 DIGIT DISPLAY WITH MAX BRIGHTNESS
disp4H.display_on(0)                                            # TURN ON THE UPPER 4 DIGIT DISPLAY WITH MAX BRIGHTNESS
disp4H.show_string("*o*o")                                      # display underscore placeholder
disp4L.display_on(0)                                            # TURN ON THE LOWER 4 DIGIT DISPLAY WITH MAX BRIGHTNESS
disp4L.show_string("o*o*")                                      # display underscore placeholder

# NOT FOR PRODUCTION - NOT FOR PRODUCTION - NOT FOR PRODUCTION - NOT FOR PRODUCTION - NOT FOR PRODUCTION - NOT FOR PRODUCTION
C_WD = 2
TD_D = 7
TD_M = 10
TD_Y = 2025
TM_D = 8
TM_Y = 2025
TD_M = 5
TM_M = 6
C_LN = "Huntingdale"
C_LS = "Vic"
TD_MAX = 21
TD_MIN = 10
TD_RAIN = 90
TD_ICON = "shower"
TD_TEXT = "Shower or two."
ON_LOW = 10
TM_MAX = 20
TM_MIN = 10
TM_RAIN = 95
TM_ICON = "partly_cloudy"
TM_TEXT = "Showers increasing."
TIMEZONE_OFFSET = 39600
pico_rtc.datetime((2025, 10, 14, 2, 6, 46, 1, 0))

oledTL.fill(0)
oledTL.fill_rect(0, 0, 128, 16, 1)
oledBL.fill(0)
oledBL.fill_rect(0, 0, 128, 16, 1)
oledTR.fill(0)
oledTR.fill_rect(0, 0, 128, 16, 1)
oledBR.fill(0)
oledBR.fill_rect(0, 0, 128, 16, 1)

str_td_dow = DAYS_OF_WEEK[C_WD % 7]
str_tm_dow = DAYS_OF_WEEK[(C_WD + 1) % 7]

# get the months of the year
str_td_moy = MONTHS_OF_YEAR[TD_M]
str_tm_moy = MONTHS_OF_YEAR[TM_M]

# top left - this is the model for the below
# oledTL.banner_text_inverted(str_td_dow, scale=14)
oledTLhead.write(str_td_dow, x=64, halign="center", y=1, fg=0, bg=1)
str_td_date = f"{TD_D:02} {TD_M:02} {TD_Y:04}"
oledTL23.write(str_td_date, y=16, x=64)
# oledTL.input_text(str_td_date, y_start=21, x_scale=2, y_scale=3)
# oledTL.input_text(str_td_yy, y_start=49, x_scale=2, y_scale=2)
oledTL16.write(TD_TEXT, halign="center", valign="bottom", x=63, y=50)
oledTL16.write(TM_TEXT, halign="center", valign="bottom", x=63, y=64)

# bottom left
# oledBL.banner_text_inverted(str_tm_dow, scale=14)
oledBL16.write(str_tm_dow, x=64, halign="center", y=1, fg=0, bg=1)
str_tm_date = f"{TM_D:02} {str_tm_moy}"
str_tm_yy = f"{TM_Y:04}"
oledBL16.write(str_tm_date, y= 21, x=64)
# oledBL.input_text(str_tm_date, y_start=21, x_scale=2, y_scale=3)
oledBL12.write(str_tm_yy, y= 49, x=64)
# oledBL.input_text(str_tm_yy, y_start=49, x_scale=2, y_scale=2)

# top right
# oledTR.banner_text_inverted(C_LN, scale=11)
oledTR16.write(C_LN, x=64, halign="center", y=1, fg=0, bg=1)
# oledTR.fill_rect(0, 16, 128, 2, 0)
icon = IconGrabber.get_icon(TD_ICON, 37, TIMEZONE_OFFSET)
oledTR.display_pbm(icon, x_offset=5, y_offset=17)
oledTR.input_text("RAIN", x_start=56, y_start=17, spacer=0, x_scale=1, y_scale=1)
str_rain_percent = f"{TD_RAIN:0}%"
oledTR.input_text(str_rain_percent, x_start=56, y_start=20, spacer=0, x_scale=1, y_scale=2)
oledTR.input_text("MIN", x_start=92, y_start=17, spacer=0, x_scale=2, y_scale=2)
str_min = f"{TM_MIN:0}-C"
oledTR.input_text(str_min, x_start=92, y_start=25, spacer=0, x_scale=1, y_scale=2)
# oledTR.input_text(TD_TEXT, y_start=56, x_scale=1, spacer=0, y_scale=1)
oledTR12.write(TD_TEXT, halign="center", x=64, y=52)


# bottom right
# oledBR.banner_text_inverted(C_LN, scale=11)
oledBR16.write(C_LN, x=64, halign="center", y=1, fg=0, bg=1)
icon = IconGrabber.get_icon(TM_ICON, 37, TIMEZONE_OFFSET)
oledBR.display_pbm(icon, x_offset=5, y_offset=17)
str_rain_percent = f"{TM_RAIN:0}%"
oledBR.input_text(str_rain_percent, x_start=80, y_start=20, spacer=0, x_scale=1, y_scale=1)
str_min = f"{TM_MIN:0}*C"
oledBR.input_text(str_min, x_start=80, y_start=20, spacer=0, x_scale=1, y_scale=2)
oledBR.display_pbm("min_temp-35", x_offset=70, y_offset=16)

oledBR.input_text(TM_TEXT, y_start=56, x_scale=1, spacer=-2, y_scale=1)


print("refreshing OLEDs")
mux.select_port(OLED_ID_TL)
oledTL.show()
mux.select_port(OLED_ID_BL)
oledBL.show()
mux.select_port(OLED_ID_TR)
oledTR.show()
mux.select_port(OLED_ID_BR)
oledBR.show()
# NOT FOR PRODUCTION - NOT FOR PRODUCTION - NOT FOR PRODUCTION - NOT FOR PRODUCTION - NOT FOR PRODUCTION - NOT FOR PRODUCTION

#wlan.disconnectWiFi()
networks = wlan.scanWiFi()                                                                  # scan for the WLAN
wlan.connectWiFi()                                                                          # connect to the WLAN
print("WiFi Connected:", wlan.checkWiFi())                                                  # and double check

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
