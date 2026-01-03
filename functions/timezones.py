# Micropython Australian timezone lookup from GPS + UTC
# Inputs: lat (negative in Southern Hemisphere), lon (positive East), and a UTC datetime tuple.
# Outputs: dict with zone_id, utc_offset_minutes, is_dst, and local datetime tuple.

class TimezoneData:
    def __init__(self):
        self.offset_minutes = 0
        self.zone_id = ""
        self.is_DST = False
        self.local_year = 0
        self.local_month = 0
        self.local_day = 0
        self.local_hour = 0
        self.local_minute = 0
        self.local_second = 0

class LocalTimezone:
    def __init__(self):
        self.tz_data = TimezoneData()

    def update_localtime(self, lat, lon, utc_dt):
        """
        lat, lon: float (degrees). Example Melbourne: lat=-37.8136, lon=144.9631
        utc_dt:  (year, month, day, hour, minute, second)
        returns: {
            'zone_id': str,
            'utc_offset_minutes': int,
            'is_dst': bool,
            'local_dt': (Y,M,D,hh,mm,ss)
        }
        """
        Y, M, D, hh, mm, ss = utc_dt

        # ---- helpers ----

        def is_sunday(y, m, d):
            # Zeller’s congruence (Gregorian), returns 0=Sunday
            if m < 3:
                m += 12
                y -= 1
            K = y % 100
            J = y // 100
            h = (d + (13*(m + 1))//5 + K + (K//4) + (J//4) + 5*J) % 7
            # h: 0=Saturday, 1=Sunday, 2=Monday, ... per Zeller
            return h == 1

        def first_sunday_on_or_after(y, m, d_start):
            # Find first Sunday on/after (y,m,d_start)
            d = d_start
            # Try up to 7 days
            for _ in range(7):
                if is_sunday(y, m, d):
                    return (y, m, d)
                d += 1
            return (y, m, d_start)  # fallback (won't happen)

        def days_in_month(y, m):
            if m in (1,3,5,7,8,10,12): return 31
            if m in (4,6,9,11): return 30
            # February
            leap = (y%4==0 and (y%100!=0 or y%400==0))
            return 29 if leap else 28

        def add_minutes(dt, minutes):
            # dt: (Y,M,D,hh,mm,ss) ; minutes can be negative; ss preserved
            Y,M,D,hh,mm,ss = dt
            mm += minutes
            # Normalize minutes/hours/days simply without mktime
            # Minutes -> hours
            extra_h, mm = divmod(mm, 60)
            if mm < 0:
                extra_h -= 1
                mm += 60
            hh += extra_h
            # Hours -> days
            extra_d, hh = divmod(hh, 24)
            if hh < 0:
                extra_d -= 1
                hh += 24
            # Days -> months/years
            D += extra_d
            while True:
                dim = days_in_month(Y, M)
                if D > dim:
                    D -= dim
                    M += 1
                    if M > 12:
                        M = 1
                        Y += 1
                elif D < 1:
                    M -= 1
                    if M < 1:
                        M = 12
                        Y -= 1
                    D += days_in_month(Y, M)
                else:
                    break
            return (Y,M,D,hh,mm,ss)

        def utc_transition_times(check_year):           
            season_end_year = check_year + 1
           
            # DST start: first Sunday Oct, 02:00 standard time
            s_year, s_month, s_day = first_sunday_on_or_after(check_year, 10, 1)
            s_utc = add_minutes((s_year, s_month, s_day, 2, 0, 0), -base_offset)

            # DST end: first Sunday Apr, 03:00 daylight time
            e_year, e_month, e_day = first_sunday_on_or_after(season_end_year, 4, 1)
            e_utc = add_minutes((e_year, e_month, e_day, 3, 0, 0), -(base_offset + dst_add))

            return s_utc, e_utc

        # ---- zone selection (coarse but practical) ----
        # Mainland longitude bands (approx):
        #   WA: 112.9E–129E  -> UTC+8
        #   NT/SA: 129E–141E -> UTC+9:30 (NT no DST, SA with DST)
        #   QLD/NSW/ACT/VIC/TAS: 141E–154.5E -> UTC+10 (DST varies)
        #
        # Simple region checks (bounding boxes).

        def in_box(lat, lon, lat_s, lat_n, lon_w, lon_e):
            return (lat_s <= lat <= lat_n) and (lon_w <= lon <= lon_e)
                
        def in_tweed_nsw(lat, lon):
            # Special case: Tweed Heads / Coolangatta coastal kink
            # Very approximate bounding box for the NSW bit east of Point Danger
            # Keeps Tweed Heads (south of Point Danger ridge) in NSW
            return (153.5 <= lon <= 153.6) and (-28.25 <= lat <= -28.1)

        # Lord Howe Island (31.5°S–31.95°S, 159.0°E–159.2°E)
        if in_box(lat, lon, -32.0, -31.3, 159.0, 159.3):
            zone_id = "Australia/Lord_Howe"
            base_offset = 10*60 + 30   # +10:30
            uses_dst = True
            lh_half_hour_dst = True
        
        # Eucla (very small UTC+8:45 region around ~-31.7, 128.9E)
        elif in_box(lat, lon, -33.0, -30.0, 127.6, 129.2):
            zone_id = "Australia/Eucla"
            base_offset = 8*60 + 45
            uses_dst = False
            lh_half_hour_dst = False

        # Western Australia
        elif lon < 129.0:
            zone_id = "Australia/Perth"
            base_offset = 8*60
            uses_dst = False
            lh_half_hour_dst = False

        # Broken Hill (NSW that uses SA time) ~(-30.0..-31.5, 140.0..142.0)
        elif in_box(lat, lon, -33.6, -30.5, 140.0, 143.0):
            zone_id = "Australia/Broken_Hill"
            base_offset = 9*60 + 30
            uses_dst = True
            lh_half_hour_dst = False
        
        # South Australia (DST): longitudes 129..141, lats south of ~−26.5
        elif (129.0 <= lon < 141.0):
            zone_id = "Australia/Adelaide"
            base_offset = 9*60 + 30
            uses_dst = True
            lh_half_hour_dst = False

        # NT (no DST): approx box for NT (−26..−20 to −14..−10, 129..138)
        elif in_box(lat, lon, -26.0, -10.0, 129.0, 138.0):
            zone_id = "Australia/Darwin"
            base_offset = 9*60 + 30
            uses_dst = False
            lh_half_hour_dst = False

        # Queensland (no DST): north/east mainland above the NSW border (~28°S)
        elif (141.0 <= lon <= 154.9) and (lat > -29.0) and (not in_tweed_nsw(lat, lon)):
            zone_id = "Australia/Brisbane"
            base_offset = 10*60
            uses_dst = False
            lh_half_hour_dst = False

        # Tasmania (DST): simple box
        elif in_box(lat, lon, -44.2, -39.0, 144.0, 149.0):
            zone_id = "Australia/Hobart"
            base_offset = 10*60
            uses_dst = True
            lh_half_hour_dst = False

        # ACT/NSW/VIC (DST) – fallback for the remainder of the east band
        else:
            zone_id = "Australia/Sydney"
            base_offset = 10*60
            uses_dst = True
            lh_half_hour_dst = False

        # ---- DST calculation (for zones that observe it) ----
        # Rules: First Sunday in October 02:00 local STANDARD time
        #        to First Sunday in April   03:00 local DAYLIGHT time
        is_dst = False
        if uses_dst:
            # Find transition instants in local time, then compare properly using UTC.
            # 1) Start: Oct first Sunday 02:00 STANDARD -> that equals 02:00 - base_offset in UTC.
            sY, sM, sD = first_sunday_on_or_after(Y, 10, 1)
            # 2) End: Apr first Sunday 03:00 DAYLIGHT -> that equals 03:00 - (base_offset + dst_add) in UTC.
            eY, eM, eD = first_sunday_on_or_after(Y, 4, 1)

            dst_add = 30 if lh_half_hour_dst else 60  # minutes added during DST
            
            # Determine which season bracket to check
            # If month >= July, use this year's Oct start; else use last year's Oct start.
            check_year = Y if M >= 7 else (Y - 1)
            start_utc, end_utc = utc_transition_times(check_year)

            # Compare utc_dt with [start_utc, end_utc)
            def cmp(a, b):
                return (a > b) - (a < b)
            def le(a, b): return cmp(a,b) <= 0
            def lt(a, b): return cmp(a,b) < 0
            def ge(a, b): return cmp(a,b) >= 0

            if ge(utc_dt, start_utc) and lt(utc_dt, end_utc):
                is_dst = True

        offset_minutes = base_offset + ((30 if lh_half_hour_dst else 60) if is_dst else 0)

        local_dt = add_minutes(utc_dt, offset_minutes)
        lY, lM, lD, lhh, lmm, lss = local_dt

        self.tz_data.offset_minutes = offset_minutes
        self.tz_data.zone_id = zone_id
        self.tz_data.is_DST = is_dst
        self.tz_data.local_year = lY
        self.tz_data.local_month = lM
        self.tz_data.local_day = lD
        self.tz_data.local_hour = lhh
        self.tz_data.local_minute = lmm
        self.tz_data.local_second = lss    
        return self.tz_data
    
    @property
    def tz_offset_minutes(self):
        return self.tz_data.offset_minutes

# ----------- Test Examples -----------
"""

# perth
print(f"Perth: {aus_localtime_from_gps(-31.95, 115.86, (2025,8,19,11,30,0))}")
# darwin
print(f"Darwin: {aus_localtime_from_gps(-12.46, 130.84, (2025,8,19,11,30,0))}")
# adelaide
print(f"Adelaide: {aus_localtime_from_gps(-31.93, 138.60, (2025,8,19,11,30,0))}")
# sydney
print(f"Sydney: {aus_localtime_from_gps(-33.87, 151.21, (2025,8,19,11,30,0))}")
# sydney DST
print(f"Sydney DST: {aus_localtime_from_gps(-33.87, 151.21, (2025,12,25,11,30,0))}")
# tas
print(f"Tasmania: {aus_localtime_from_gps(-33.87, 151.21, (2025,8,19,11,30,0))}")
# bris
print(f"Brisbane: {aus_localtime_from_gps(-27.47, 153.03, (2025,8,19,11,30,0))}")
# bris DST
print(f"Brisbane DST: {aus_localtime_from_gps(-27.47, 153.03, (2025,12,25,11,30,0))}")
# coolangatta
print(f"Coolangatta: {aus_localtime_from_gps(-28.16, 153.55, (2025,8,19,11,30,0))}")
# tweed heads
print(f"Tweed: {aus_localtime_from_gps(-28.18, 153.55, (2025,8,19,11,30,0))}")
# broken hill
print(f"Broken Hill: {aus_localtime_from_gps(-31.96, 141.46, (2025,8,19,11,30,0))}")
# melb
print(f"Melbourne: {aus_localtime_from_gps(-37.81, 144.96, (2025,8,19,11,30,0))}")

# melb DST
result = aus_localtime_from_gps(-37.81, 144.96, (2025,12,25,11,30,0))
local_year, local_month, local_day, local_hour, local_minute, local_second = (result[k] for k in ['year','month','day','hour','minute','second'])
print(f"Melbourne DST: {local_day}/{local_month}/{local_year} {local_hour}:{local_minute}:{local_second}")

"""