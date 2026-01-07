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

async def get_GPS_fix():
    print("running: get_GPS_fix()")
    t = 0.1
    while not GPS_obj.has_fix:
        GPS_obj.get_data()
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
        GPS_obj.get_data()
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
    print(f"Lat: [{GPS_obj.current_data.latitude}] Long: [{GPS_obj.current_data.longitude}] Alt: [{GPS_obj.current_data.altitude}]")
    temp_string = f"{GPS_obj.current_data.latitude:08}"
    disp8.set_string(temp_string, "r")
    await asyncio.sleep(0.5)
    temp_string = f"{GPS_obj.current_data.longitude:08}"
    disp8.set_string(temp_string, "r")
    await asyncio.sleep(0.5)
    # get geohash code from GPS coordinates
    _geohash = Geohash.encode(float(GPS_obj.current_data.latitude), float(GPS_obj.current_data.longitude), precision=7)
    print(f"geohash: [{_geohash}]")
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
    print(f"UTC: Y{utcY} M{utcM} D{utcD} H{utcHr} M{utcMn} S{utcSc}")
    await asyncio.sleep(0.5)
    # calculate the local time from the GPS coordinates and UTC time
    tziData = TimezoneInfo.update_localtime(float(GPS_obj.current_data.latitude), float(GPS_obj.current_data.longitude), (utcY, utcM, utcD, utcHr, utcMn, utcSc))
    print(f"Tzi: Y{tziData.local_year} M{tziData.local_month} D{tziData.local_day} H{tziData.local_hour} M{tziData.local_minute} S{tziData.local_second}")
    temp_string = f"{tziData.local_year:04}{tziData.local_month:02}{tziData.local_day:02}"
    disp8.set_string(temp_string, "r")
    await asyncio.sleep(1)
    # set timezone offset (in seconds)
    _timezoneOffset = TimezoneInfo.tz_offset_minutes * 60
    print(f"Tzo: {TimezoneInfo.tz_offset_minutes}mins [{TimezoneInfo.tz_data.zone_id}] DST:{TimezoneInfo.tz_data.is_DST}")
    # set the local clock time from the converted local time from TimezoneInfo
    localRTC.datetime((tziData.local_year, tziData.local_month, tziData.local_day, day_of_week, tziData.local_hour, tziData.local_minute, tziData.local_second, 0))
    await asyncio.sleep(0.5)
    # get the (Local) datetime we just set and display it
    lclY, lclM, lclD, _, lclHr, lclMn, lclSc, _ = localRTC.datetime()
    print(f"Lcl: Y{lclY} M{lclM} D{lclD} H{lclHr} M{lclMn} S{lclSc}")
    await asyncio.sleep(0.5)
    return _geohash, _timezoneOffset

async def synchronise_watches():
    # see system_setup()
    try:
        GPS_obj.get_data()
        await asyncio.sleep(2)
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
        print(f"UTC: Y{utcY} M{utcM} D{utcD} H{utcHr} M{utcMn} S{utcSc}")
        await asyncio.sleep(0.5)
        # calculate the local time from the GPS coordinates and UTC time
        tziData = TimezoneInfo.update_localtime(float(GPS_obj.current_data.latitude), float(GPS_obj.current_data.longitude), (utcY, utcM, utcD, utcHr, utcMn, utcSc))
        print(f"Tzi: Y{tziData.local_year} M{tziData.local_month} D{tziData.local_day} H{tziData.local_hour} M{tziData.local_minute} S{tziData.local_second}")
        await asyncio.sleep(0.5)
        print(f"Tzo: {TimezoneInfo.tz_offset_minutes}mins [{TimezoneInfo.tz_data.zone_id}] DST:{TimezoneInfo.tz_data.is_DST}")
        # set the local clock time from the converted local time from TimezoneInfo
        localRTC.datetime((tziData.local_year, tziData.local_month, tziData.local_day, day_of_week, tziData.local_hour, tziData.local_minute, tziData.local_second, 0))
        await asyncio.sleep(0.5)
        # get the (Local) datetime we just set and display it
        lclY, lclM, lclD, _, lclHr, lclMn, lclSc, _ = localRTC.datetime()
        print(f"Lcl: Y{lclY} M{lclM} D{lclD} H{lclHr} M{lclMn} S{lclSc}")
        await asyncio.sleep(0.5)
    except Exception as e:
        print(f"synchronise_watches() failed to synchronise internal clocks to GPS time: {e} - {repr(e)}")
        await asyncio.sleep(0.5)
        return False
    # return the last successful refresh time
    _lastRefresh = time.mktime(localRTC.datetime())
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
    print(f"Location: {_locCity}, {_locState}, Australia")
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
    _lastRefresh = time.mktime(localRTC.datetime())
    return _lastRefresh, _forecastMeta, _forecastData

async def update_forecast(_forecastMeta, _forecastData, _timezoneOffset):
    _updateMetadata = {
        "response_time": (TimeCruncher.parse_8601datetime(_forecastMeta.fc_response_timestamp)),
        "bulletin_time": (TimeCruncher.parse_8601datetime(_forecastMeta.fc_issue_time)),
        "bulletin_next": (TimeCruncher.parse_8601datetime(_forecastMeta.fc_next_issue_time))
    }
    # get current local date
    lclY, lclM, lclD, _, _, _, _, _ = localRTC.datetime()
    # attempt to sync the downloaded forecast data to the current date(s)
    i = None
    try:
        for x in range(7):
            chkY, chkM, chkD, _, _, _, _, _ = TimeCruncher.parse_8601localtime(_forecastData[x].fc_date, _timezoneOffset)
            print(f"update_forecast() is comparing [{chkY}/{lclY}], [{chkM}/{lclM}], and [{chkD}/{lclD}]")
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
    except Exception as e:
        print(f"update_forecast() failed to organise the BoM data into the correct structure: {e} - {repr(e)}")
        await asyncio.sleep(0.5)
        return False
    await asyncio.sleep(0.5)
    # print some forecast data
    print(f"Today {_forecastToday['yy']}-{_forecastToday['mm']}-{_forecastToday['dd']} Max:{_forecastToday['max']}°C Min:{_forecastToday['min']}°C Rain:{_forecastToday['rain']}% ({_forecastToday['text']})")
    print(f"Tomor {_forecastTomorrow['yy']}-{_forecastTomorrow['mm']}-{_forecastTomorrow['dd']} Max:{_forecastTomorrow['max']}°C Min:{_forecastTomorrow['min']}°C Rain:{_forecastTomorrow['rain']}% ({_forecastTomorrow['text']})")
    _lastRefresh = time.mktime(localRTC.datetime())
    return _lastRefresh, _updateMetadata, _forecastToday, _forecastTomorrow

async def update_display_temps(_todayMax, _overnighLow, _tomorrowMax):
    _, _, _, _, hh, _, _, _ =  localRTC.datetime()
    await asyncio.sleep(0.5)
    try:
        if hh > 18:
            strHi = f"{_overnighLow}*C"
            strLo = f"{_tomorrowMax}*C"
        elif hh < 2:
            strHi = f"{_overnighLow}*C"
            strLo = f"{_todayMax}*C"
        else:
            strHi = f"{_todayMax}*C"
            strLo = f"{_tomorrowMax}*C"
        await asyncio.sleep(0.5)
        disp4H.show_string(strHi)
        disp4L.show_string(strLo)
    except Exception as e:
        print(f"update_display_temps() failed write the temps on the displays: {e} - {repr(e)}")
        await asyncio.sleep(0.5)
        return False
    # return the last successful refresh time
    _lastRefresh = time.mktime(localRTC.datetime())
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
    #print("rendering canvas")
    date_header = f"{_forecastToday['dd']:02} {tdStrMoY} {_forecastToday['yy']:04}"
    oledTLhead.write(date_header, x=65, halign="center", y=1, fg=0, bg=1)
    oledTL23.write(tdStrDoW, halign="center", y=17, x=64)
    oledTL16.write("Rain: ", halign="left", y=50, x=4)
    str_rain_percent = f"{_forecastToday['rain']:0} %"
    oledTL23.write(str_rain_percent, halign="right", y=45, x=123)
    await asyncio.sleep(0.5)
    # draw the canvas for OLED: bottom left
    date_header = f"{_forecastTomorrow['dd']:02} {tmStrMoY} {_forecastTomorrow['yy']:04}"
    oledBLhead.write(date_header, x=65, halign="center", y=1, fg=0, bg=1)
    oledBL23.write(tmStrDoW, halign="center", y=17, x=64)
    oledBL16.write("Rain: ", halign="left", y=50, x=4)
    str_rain_percent = f"{_forecastTomorrow['rain']:0} %"
    oledBL23.write(str_rain_percent, halign="right", y=45, x=123)
    await asyncio.sleep(0.5)
    # draw the canvas for OLED: top right
    oledTRhead.write(_locCity, x=65, halign="center", y=1, fg=0, bg=1)
    icon = IconGrabber.get_icon(_forecastToday['icon'], 37, hour=hh)
    oledTR.display_pbm(icon, x_offset=84, y_offset=17)           
    descText = ezFBfont.split_text(_forecastToday['text'])
    oledTR12.write(descText, halign="center", valign="center", y=34, x=40)
    if hh < 2 or hh > 18:
        oledTR16.write("Overnight Low:", halign="center", y=52, x=65)
    else:
        str_min = str(f"Min: {_forecastToday['min']:0}°C  Max:")
        oledTR16.write(str_min, halign="center", y=52, x=66)
    await asyncio.sleep(0.5)
    # draw the canvas for OLED: bottom right
    oledBRhead.write(_locCity, x=65, halign="center", y=1, fg=0, bg=1)
    icon = IconGrabber.get_icon(_forecastTomorrow['icon'], 37, hour=6)
    oledBR.display_pbm(icon, x_offset=84, y_offset=17)
    descText = ezFBfont.split_text(_forecastTomorrow['text'])
    oledBR12.write(descText, halign="center", valign="center", y=34, x=40)
    str_min = str(f"Min: {_forecastTomorrow['min']:0}°C  Max:")
    oledBR16.write(str_min, halign="center", y=52, x=66)
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
    _lastRefresh = time.mktime(localRTC.datetime())
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
            print("Startup version of update_display_clock() is cancelled.")
    # start ongoing updates of the clock display
    ongoing_tasks.append(asyncio.create_task(update_display_clock()))
    # start ongoing refresh scheduler loop
    ongoing_tasks.append(asyncio.create_task(refresh_scheduler(_geohash, _timezoneOffset, _locCity, _locState)))
    try:
        result = await asyncio.gather(*ongoing_tasks, return_exceptions=True)
    except asyncio.CancelledError:
        print("ONGOING TASKS LOOP CANCELLED")
    print("Result: ", result)

async def refresh_scheduler(_geohash, _timezoneOffset, _locCity, _locState):
    # get the initial set of forecast data
    firstForecastData = asyncio.create_task(get_forecast_data(_geohash))
    lastForecastDataRefresh, _forecastMeta, _forecastData = await firstForecastData
    await asyncio.sleep(0.5)
    # match the data to the current date
    firstForecastSync = asyncio.create_task(update_forecast(_forecastMeta, _forecastData, _timezoneOffset))
    lastForecastSync, _updateMetadata, _forecastToday, _forecastTomorrow = await firstForecastSync
    await asyncio.sleep(0.5)
    # update the display_temps and the display_oleds (almost) immediately
    asyncio.create_task(update_display_temps(_forecastToday['max'], _forecastToday['onlow'], _forecastTomorrow['max']))
    await asyncio.sleep(0.5)
    asyncio.create_task(update_display_oleds(_forecastToday, _forecastTomorrow, _locCity))
    await asyncio.sleep(0.5)
    # schedule the first round of updates
    now = time.mktime(localRTC.datetime())
    lastLedRefresh = now
    lastOledRefresh = now
    lastSynchroniseWatches = now
    # then, run this forever
    print("refresh_scheduler() is commencing")
    while True:
        now = time.mktime(localRTC.datetime())
        y, m, d, _, hh, mm, ss, _ = localRTC.datetime()
        await asyncio.sleep(0.5)
        if ((now - lastForecastDataRefresh) >= 86400) or ((now - _updateMetadata["bulletin_time"]) >= 46800) or (now >= _updateMetadata["bulletin_next"]):
            print("refresh_scheduler() calls: get_forecast_data()")
            forecast = asyncio.create_task(get_forecast_data(_geohash))
            lastForecastDataRefresh, _forecastMeta, _forecastData = await forecast
            new_bulletin = True
        await asyncio.sleep(0.5)
        if ((now - lastForecastSync) >= 600) or (new_bulletin == True):
            print("refresh_scheduler() calls: update_forecast()")
            forecastSync = asyncio.create_task(update_forecast(_forecastMeta, _forecastData, _timezoneOffset))
            lastForecastSync, _updateMetadata, _forecastToday, _forecastTomorrow = await forecastSync
        elif (_forecastToday["yy"] != y) or (_forecastToday["mm"] != m) or (_forecastToday["dd"] != d):
            print("refresh_scheduler() calls: update_forecast()")
            forecastSync = asyncio.create_task(update_forecast(_forecastMeta, _forecastData, _timezoneOffset))
            lastForecastSync, _updateMetadata, _forecastToday, _forecastTomorrow = await forecastSync
            new_bulletin = True
        await asyncio.sleep(0.5)
        if ((now - lastOledRefresh) >= 1800) or (new_bulletin == True):
            print("refresh_scheduler() calls: update_display_oleds()")
            oleds = asyncio.create_task(update_display_oleds(_forecastToday, _forecastTomorrow, _locCity))
            lastLedRefresh = await oleds
        await asyncio.sleep(0.5)
        if ((now - lastSynchroniseWatches) >= 1440):
            print("refresh_scheduler() calls: synchronise_watches()")
            sync = asyncio.create_task(synchronise_watches())
            lastSynchroniseWatches = await sync
        await asyncio.sleep(0.5)
        if ((now - lastLedRefresh) >= 900) or (new_bulletin == True):
            print("refresh_scheduler() calls: update_display_temps()")
            temps = asyncio.create_task(update_display_temps(_forecastToday['max'], _forecastToday['onlow'], _forecastTomorrow['max']))
            lastLedRefresh = await temps
        new_bulletin = False
        await asyncio.sleep(60)        

### STARTUP PROCESSES
# first, get a GPS fix (function won't return until has_fix is True)
asyncio.run(get_GPS_fix())
# then, proceed with system setup
_geohash, _timezoneOffset = asyncio.run(system_setup())
# at this point, we can display the clock (until the main loop starts)
startupClock = asyncio.create_task(update_display_clock())
# attempt to connect to WiFi
disp4H.show_string("GEt")
disp4L.show_string("&IFI")
asyncio.run(enable_Wifi())
time.sleep(1)
while wlan.checkWiFi() == False:
    print("Attempting to connect to WiFi")
    asyncio.run(enable_Wifi())
    time.sleep(1)
# lookup location from the BoM
_locCity, _locState = asyncio.run(get_location(_geohash))
try:
    asyncio.run(main_loop(_geohash, _timezoneOffset, _locCity, _locState))
except asyncio.CancelledError:
    print("MAIN LOOP CANCELLED")
    asyncio.new_event_loop() 
finally:
    asyncio.new_event_loop()