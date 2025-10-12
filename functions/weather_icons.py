import time
import functions.time_cruncher as TimeCruncher

def get_icon(icon_descriptor, pixels, timezone_offset):
    _, _, _, hh, _, _, _, _ = TimeCruncher.now_local(timezone_offset)
    icon = None
    if icon_descriptor == "sunny" or icon_descriptor == "clear":
        if hh > 17 or hh < 5:
            return f"clear-night-{pixels}"
        else:
            return f"clear-day-{pixels}"
    elif icon_descriptor == "mostly_sunny" or icon_descriptor == "partly_cloudy":
        if hh > 17 or hh < 5:
            return f"partly-cloudy-night-{pixels}"
        else:
            return f"partly-cloudy-day-{pixels}"
    elif icon_descriptor == "cloudy":
        return f"cloudy-{pixels}"
    elif icon_descriptor == "light_rain":
        return f"light-rain-{pixels}"
    elif icon_descriptor == "rain":
        return f"rain-{pixels}"
    elif icon_descriptor == "shower":
        if hh > 17 or hh < 5:
            return f"showers-night-{pixels}"
        else:
            return f"showers-day-{pixels}"
    elif icon_descriptor == "light_shower":
        if hh > 17 or hh < 5:
            return f"light-showers-night-{pixels}"
        else:
            return f"light-showers-day-{pixels}"
    elif icon_descriptor == "heavy_shower":
        return f"heavy-showers-{pixels}"
    elif icon_descriptor == "storm":
        return f"storm-{pixels}" 
    elif icon_descriptor == "hazy":
        if hh > 17 or hh < 5:
            return f"haze-night-{pixels}"
        else:
            return f"haze-day-{pixels}"
    elif icon_descriptor == "windy":
        return f"wind-{pixels}" 
    elif icon_descriptor == "fog":
        if hh > 17 or hh < 5:
            return f"fog-night-{pixels}"
        else:
            return f"fog-day-{pixels}"
    elif icon_descriptor == "dusty":
        return f"dust-{pixels}"
    elif icon_descriptor == "frost":
        return f"frost-{pixels}"
    elif icon_descriptor == "snow":
        return f"snow-{pixels}"  
    elif icon_descriptor == "cyclone":
        return f"tropicalcyclone-{pixels}" 
    else:
        return f"unknown-{pixels}"