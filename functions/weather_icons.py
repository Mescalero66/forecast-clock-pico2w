def get_icon(icon_descriptor, pixels, hour=6):  
    if icon_descriptor == "sunny" or icon_descriptor == "clear":
        if hour > 18 or hour < 4:
            return f"clear-night-{pixels}"
        else:
            return f"clear-day-{pixels}"
    elif icon_descriptor == "mostly_sunny" or icon_descriptor == "partly_cloudy":
        if hour > 18 or hour < 4:
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
        if hour > 18 or hour < 4:
            return f"shower-night-{pixels}"
        else:
            return f"shower-day-{pixels}"
    elif icon_descriptor == "light_shower":
        if hour > 18 or hour < 4:
            return f"light-shower-night-{pixels}"
        else:
            return f"light-shower-day-{pixels}"
    elif icon_descriptor == "heavy_shower":
        return f"heavy-shower-{pixels}"
    elif icon_descriptor == "storm":
        return f"storm-{pixels}" 
    elif icon_descriptor == "hazy":
        if hour > 18 or hour < 4:
            return f"hazy-night-{pixels}"
        else:
            return f"hazy-day-{pixels}"
    elif icon_descriptor == "windy":
        return f"windy-{pixels}" 
    elif icon_descriptor == "fog":
        if hour > 18 or hour < 4:
            return f"fog-night-{pixels}"
        else:
            return f"fog-day-{pixels}"
    elif icon_descriptor == "dusty":
        return f"dusty-{pixels}"
    elif icon_descriptor == "frost":
        return f"frost-{pixels}"
    elif icon_descriptor == "snow":
        return f"snow-{pixels}"  
    elif icon_descriptor == "cyclone":
        return f"cyclone-{pixels}" 
    else:
        return f"unknown-{pixels}"