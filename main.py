import time
from machine import I2C, Pin, UART, RTC
from hardware.HT16K33LED import HT16K33LED
from hardware.gps_parser import GPSReader
import functions.timezones as AuTz

# Set up UART connection to GPS module
uart = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))

# Create a GPS reader object
GPS_obj = GPSReader(uart)

# Create 8digit LED object
i2c = I2C(0, scl=Pin(5), sda=Pin(4))
display = HT16K33LED(i2c)
display.set_brightness(15)

while True:
    gps_data = GPS_obj.get_data()
    if gps_data.has_fix == True:
        
        print(f"GPS: {gps_data.year}{gps_data.month}{gps_data.day} {gps_data.hour}.{gps_data.minute}.{gps_data.second}")
        time.sleep(1)

        timezonetime = AuTz.aus_localtime_from_gps(gps_data.latitude,gps_data.longitude,(gps_data.year, gps_data.month, gps_data.day, gps_data.hour, gps_data.minute, gps_data.second))
        print(f"GPS: {gps_data.latitude} {gps_data.longitude}")
        print(timezonetime)
        time.sleep(1)

        local_year, local_month, local_day, local_hour, local_minute, local_second = (timezonetime[k] for k in ['year','month','day','hour','minute','second'])
        print(f"AuTZ: {local_year}{local_month}{local_day} {local_hour}.{local_minute}.{local_second}")
        time.sleep(1)

        yy, mm, dd, hh, mm, ss = (local_year, local_month, local_day, local_hour, local_minute, local_second)
        epoch = time.mktime((yy, mm, dd, hh, mm, ss, 0, 0))
        weekday = time.localtime(epoch)[6]

        rtc = machine.RTC()
        rtc.datetime((yy, mm, dd, weekday, hh, mm, ss, 0))
        
        rtc_year, rtc_month, rtc_day, rtc_wd, rtc_hour, rtc_minute, rtc_second, rtc_us = rtc.datetime()
        print(f"RTC: {rtc_year}{rtc_month}{rtc_day} {rtc_hour}.{rtc_minute}.{rtc_second}")
        time.sleep(1)
        break
    time.sleep(2)

while True:

    y, m, d, wd, hh, mm, ss, us = rtc.datetime()

    time_str = f"{hh:02} .{mm:02} .{ss:02}"
    display.set_string(time_str, "r")
    time.sleep(0.5)
    time_str = f"{hh:02} {mm:02} {ss:02}"
    display.set_string(time_str, "r")
    time.sleep(0.5)
