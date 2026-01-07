# A simple library for parsing NMEA GPS data from UART GPS modules
import time

class GPSData:
    """Class to store GPS data with easy attribute access"""
    def __init__(self):
        self.has_fix = False
        self.latitude = 0.0
        self.longitude = 0.0
        self.speed_knots = 0.0
        self.speed_kph = 0.0
        self.time = ""
        self.hour = 0
        self.minute = 0
        self.second = 0
        self.date = ""
        self.day = 0
        self.month = 0
        self.year = 0
        self.satellites = 0
        self.altitude = 0.0
        self.hdop = 0.0                 # Horizontal Dilution of Precision
        self.pdop = 0.0                 # Position Dilution of Precision
        self.vdop = 0.0                 # Vertical Dilution of Precision

class GPSReader:
    """Class to handle GPS reading with non-blocking updates when getting data"""
    def __init__(self, uart):
        self.uart = uart
        self.message_buffer = ""
        self.last_data_time = time.ticks_ms()
        self.timeout_ms = 500  # 500ms timeout between message parts
        self.current_data = GPSData()
        self.new_data = GPSData()
        self.has_new_data = False
    
    def update(self):
        """Check for new GPS data and process it - non-blocking version"""
        self.has_new_data = False
        if self.uart.any():
            try:
                data = self.uart.read(self.uart.any()).decode('utf-8')
                self.message_buffer += data
                while '\n' in self.message_buffer:
                    line, self.message_buffer = self.message_buffer.split('\n', 1)
                    line = line.strip()
                    # Ignore junk / partial lines
                    if not line.startswith('$'):
                        continue
                    # Hand off complete sentence
                    self.message_buffer = line
                    self._process_buffer()
                    self.message_buffer = ""
                    self.has_new_data = True
            except Exception as e:
                print(f"Error reading GPS data: {e}")
        return self.has_new_data
    
    def get_data(self):
        """
        Get the current GPS data.
        Automatically updates before returning the data.
        
        Returns:
            GPSData: The current GPS data object with the most recent reading
        """
        self.update()
        return self.current_data
    
    def _process_buffer(self):
        """Process the complete message in buffer"""
        if not self.message_buffer:
            return
        
        self.new_data = _process_nmea_data(self.message_buffer)
        if self.new_data.has_fix == True:
            self.current_data = self.new_data
        self.message_buffer = ""
    
    # Properties for direct access to GPS data
    @property
    def latitude(self):
        """Get the current latitude"""
        self.update()
        return self.current_data.latitude
    
    @property
    def longitude(self):
        """Get the current longitude"""
        self.update()
        return self.current_data.longitude
    
    @property
    def altitude(self):
        """Get the current altitude"""
        self.update()
        return self.current_data.altitude
    
    @property
    def has_fix(self):
        """Get the current fix status"""
        self.update()
        return self.current_data.has_fix
    
    @property
    def satellites(self):
        """Get the current number of satellites"""
        self.update()
        return self.current_data.satellites
    
    @property
    def speed_knots(self):
        """Get the current speed in knots"""
        self.update()
        return self.current_data.speed_knots
    
    @property
    def speed_kph(self):
        """Get the current speed in km/h"""
        self.update()
        speed_kph = self.current_data.speed_knots * 1.852
        return speed_kph
    
    @property
    def speed_mph(self):
        """Get the current speed in mph"""
        self.update()
        speed_mph = self.current_data.speed_knots * 1.15078
        return speed_mph
    
    @property
    def time(self):
        """Get the current GPS time"""
        self.update()
        return self.current_data.time
    
    @property
    def time_split(self):
        """Get the current GPS time - split"""
        self.update()
        return self.current_data.hour, self.current_data.minute, self.current_data.second
    
    @property
    def date(self):
        """Get the current GPS date"""
        self.update()
        return self.current_data.date
    
    @property
    def date_split(self):
        """Get the current GPS date - split"""
        self.update()
        return self.current_data.day, self.current_data.month, self.current_data.year
    
    @property
    def date_ymd(self):
        """Get the current GPS date - split"""
        self.update()
        return self.current_data.year, self.current_data.month, self.current_data.day

# For backward compatibility
def parse_gps_data(nmea_chunk):
    """Legacy function to parse GPS data (for compatibility)"""
    return _process_nmea_data(nmea_chunk)

def _process_nmea_data(nmea_data):
    """Process a complete NMEA data string"""
    # Initialize data class
    new_data = GPSData()
    
    # Split the chunk into individual NMEA sentences
    sentences = nmea_data.strip().split('$')
    
    # Process each sentence
    for sentence in sentences:
        if not sentence:
            continue
            
        # Add the $ back for proper format
        sentence = '$' + sentence.strip()
        
        # Parse different sentence types
        if sentence.startswith('$GPRMC'):
            _parse_rmc(sentence, new_data)
        elif sentence.startswith('$GPGGA'):
            _parse_gga(sentence, new_data)
        elif sentence.startswith('$GPGSA'):
            _parse_gsa(sentence, new_data)
        #elif sentence.startswith('$GPGSV'):     # TO DO
        #    _parse_gsa(sentence, new_data)
    
    return new_data

def _parse_rmc(sentence, gps_data):
    """Parse RMC sentence for time, date, location, and speed"""
    
    # Split the sentence into parts
    parts = sentence.split(',')
    
    if len(parts) < 12:
        return
    
    # Check if we have a fix
    if parts[2] == 'A':
        gps_data.has_fix = True
    else:
        gps_data.has_fix = False
        # Don't return here, continue to extract time and date
    
    # Extract time (format: HHMMSS.SS) with error handling
    if parts[1] and len(parts[1]) >= 6:
        try:
            hour = parts[1][0:2]
            minute = parts[1][2:4]
            second = parts[1][4:]
            gps_data.time = f"{hour}:{minute}:{second}"
            gps_data.hour = int(hour)
            gps_data.minute = int(minute)
            gps_data.second = int(float(second))
        except (ValueError, IndexError):
            # Keep the existing time value if parsing fails
            pass
    
    # Extract date (format: DDMMYY) with error handling
    if parts[9] and len(parts[9]) >= 6:
        try:
            day = parts[9][0:2]
            month = parts[9][2:4]
            year = int("20" + parts[9][4:6])  # Assuming we're in the 2000s
            gps_data.date = f"{day}/{month}/{year}"
            gps_data.day = int(day)
            gps_data.month = int(month)
            gps_data.year = int(year)
        except (ValueError, IndexError):
            # Keep the existing date value if parsing fails
            pass

    # Only extract position and speed if we have a valid fix
    if gps_data.has_fix:
        # Extract latitude and longitude with sign based on direction
        if parts[3] and parts[5]:
            try:
                # Latitude
                lat_deg = float(parts[3][0:2])
                lat_min = float(parts[3][2:])
                lat_decimal = lat_deg + (lat_min / 60)
                
                # Apply sign based on direction (N is positive, S is negative)
                if parts[4] == 'S':
                    lat_decimal = -lat_decimal
                gps_data.latitude = lat_decimal
                
                # Longitude
                lon_deg = float(parts[5][0:3])
                lon_min = float(parts[5][3:])
                lon_decimal = lon_deg + (lon_min / 60)
                
                # Apply sign based on direction (E is positive, W is negative)
                if parts[6] == 'W':
                    lon_decimal = -lon_decimal
                gps_data.longitude = lon_decimal
            except (ValueError, IndexError):
                # If parsing fails, don't update coordinates
                pass
        
        # Extract speed in knots
        if parts[7]:
            try:
                gps_data.speed_knots = float(parts[7])
            except ValueError:
                gps_data.speed_knots = 0.0

def _parse_gga(sentence, gps_data):
    """Parse GGA sentence for satellites, altitude, and HDOP"""
    
    parts = sentence.split(',')
    
    if len(parts) < 15:
        return
    
    # Extract number of satellites
    if parts[7]:
        try:
            gps_data.satellites = int(parts[7])
        except ValueError:
            gps_data.satellites = 0
    
    # Extract HDOP (Horizontal Dilution of Precision)
    if parts[8]:
        try:
            gps_data.hdop = float(parts[8])
        except ValueError:
            gps_data.hdop = 0.0
    
    # Extract altitude
    if parts[9] and parts[10] == 'M':
        try:
            gps_data.altitude = float(parts[9])
        except ValueError:
            gps_data.altitude = 0.0

def _parse_gsa(sentence, gps_data):
    """Parse GSA sentence for PDOP, HDOP, and VDOP"""
    
    parts = sentence.split(',')
    
    if len(parts) < 18:
        return
    
    # Extract PDOP (Position Dilution of Precision)
    if parts[15]:
        try:
            gps_data.pdop = float(parts[15])
        except ValueError:
            gps_data.pdop = 0.0
            
    # Extract HDOP (Horizontal Dilution of Precision)
    if parts[16]:
        try:
            gps_data.hdop = float(parts[16])
        except ValueError:
            pass  # Keep existing value if we can't parse this one
    
    # Extract VDOP (Vertical Dilution of Precision)
    if parts[17].split('*')[0]:  # Remove checksum part
        try:
            gps_data.vdop = float(parts[17].split('*')[0])
        except ValueError:
            gps_data.vdop = 0.0