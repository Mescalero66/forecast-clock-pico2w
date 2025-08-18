from machine import Pin, UART
import time
import hardware.gps_parser as gps_parser

# Set up UART connection to GPS module
uart = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))

# Create a GPS reader object
GPS_obj = gps_parser.GPSReader(uart)

while True:
    gps_data = GPS_obj.get_data()
    if gps_data.has_fix == True:
        output_string = f"Time: {gps_data.hour:02}:{gps_data.minute:02}:{gps_data.second:02} Date: {gps_data.day:02}/{gps_data.month:02}/{gps_data.year} Lat: {gps_data.latitude} Long: {gps_data.longitude} Sats: {gps_data.satellites}"
        print(output_string)
    
    """
    if uart.any():
        gps_reading = uart.read().decode('utf-8')
        print(gps_reading)    
    
    gps_data = GPS_obj.get_data()
    print(gps_data.has_fix, "[", gps_data.satellites, "]", gps_data.latitude, gps_data.longitude, gps_data.time)
    """
    
    time.sleep(1)