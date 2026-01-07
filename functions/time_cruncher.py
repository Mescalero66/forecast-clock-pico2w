import time

def now_utc():
    return time.time()

def now_local(timezone_offset):
    return time.localtime(time.time() + timezone_offset)

def to_local(epoch_seconds, timezone_offset):
    return time.localtime(epoch_seconds + timezone_offset)

def to_local_epoch(timezone_offset):
    return (time.time() + timezone_offset)

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
    return weekday - 1

def parse_8601datetime(ts: str) -> int:
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

def parse_8601date(ts: str):
    if not ts or not ts.strip():
        raise ValueError("Empty date string")
    ts = ts.strip()
    try:
        date_part = ts.split("T")[0]   # ignore time
        year, month, day = map(int, date_part.split("-"))
    except Exception as e:
        raise ValueError(f"Invalid date string '{ts}': {e}")
    return year, month, day

def parse_8601localtime(ts: str, timezone_offset) -> int:
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

    epoch_seconds = time.mktime((year, month, day, hh, mm, ss, 0, 0))

    return time.localtime(epoch_seconds + timezone_offset)
