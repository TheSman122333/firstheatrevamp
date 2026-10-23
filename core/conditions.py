"Current air temperature, humidity, UV index and air quality for the Home screen."

import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from core.today import utc_time

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

WEATHER_FIELDS = ("temperature_2m", "relative_humidity_2m", "dew_point_2m", "uv_index")
AIR_FIELDS = ("us_aqi", "pm2_5")

#U.S. EPA UV Index scale, by the rounded index: highest value, level, label
UV_LEVELS = [
    (2, "low", "Low"),
    (5, "moderate", "Moderate"),
    (7, "high", "High"),
    (10, "very_high", "Very high"),
    (None, "extreme", "Extreme")
]

#U.S. EPA Air Quality Index (AirNow): highest value, level, label
AQI_LEVELS = [
    (50, "good", "Good"),
    (100, "moderate", "Moderate"),
    (150, "sensitive", "Unhealthy for sensitive groups"),
    (200, "unhealthy", "Unhealthy"),
    (300, "very_unhealthy", "Very unhealthy"),
    (None, "hazardous", "Hazardous")
]


def level_for(value, levels):
    "(level, label) for a value on a UV or AQI scale"

    for highest, level, label in levels:
        if highest is None or value <= highest:
            return level, label


#halves round up, as the EPA scales are reported
def uv_level(uv):
    return level_for(int(uv + 0.5), UV_LEVELS)


def aqi_level(aqi):
    return level_for(int(aqi + 0.5), AQI_LEVELS)


def get_json(url, params):

    try:
        with urlopen(url + "?" + urlencode(params), timeout=15) as response:
            data = json.load(response)
    except (URLError, HTTPError, TimeoutError, ValueError) as error:
        raise RuntimeError(f"COULD NOT GET CONDITIONS {error}") from error

    if data.get("error"):
        raise RuntimeError(data.get("reason", "CONDITIONS API ERROR"))

    return data


def hourly_rows(data, fields):
    "one dict per hour, with the time in UTC; missing values are None"

    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    rows = []

    for i, time in enumerate(times):
        row = {"time": utc_time(time)}

        for field in fields:
            values = hourly.get(field) or []
            row[field] = values[i] if i < len(values) else None

        rows.append(row)

    return rows


def latest(rows, field, now_utc):
    "the newest value at or before the current hour"

    hour = now_utc.replace(minute=0, second=0, microsecond=0)

    for row in reversed(rows):
        if row["time"] <= hour and row[field] is not None:
            return row[field]

    return None


def summarize_conditions(weather_rows, air_rows, now_utc, zone_name):
    """Current values plus today's high, ready for display.

    Temperatures are Fahrenheit. Anything missing is None.
    """

    zone = ZoneInfo(zone_name)
    local_date = now_utc.astimezone(zone).date()

    temperature = latest(weather_rows, "temperature_2m", now_utc)
    humidity = latest(weather_rows, "relative_humidity_2m", now_utc)
    dew_point = latest(weather_rows, "dew_point_2m", now_utc)
    uv = latest(weather_rows, "uv_index", now_utc)

    today_temps = [
        row["temperature_2m"]
        for row in weather_rows
        if row["time"].astimezone(zone).date() == local_date and row["temperature_2m"] is not None
    ]

    aqi = latest(air_rows, "us_aqi", now_utc) if air_rows else None
    pm2_5 = latest(air_rows, "pm2_5", now_utc) if air_rows else None

    uv_info = uv_level(uv) if uv is not None else (None, None)
    aqi_info = aqi_level(aqi) if aqi is not None else (None, None)

    return {
        "temperature_f": temperature,
        "high_f": max(today_temps) if today_temps else None,
        "humidity": humidity,
        "dew_point_f": dew_point,
        "uv_index": uv,
        "uv_level": uv_info[0],
        "uv_label": uv_info[1],
        "aqi": aqi,
        "aqi_level": aqi_info[0],
        "aqi_label": aqi_info[1],
        "pm2_5": pm2_5
    }


def fetch_conditions(location, now_utc=None):
    "weather is required; air quality is left out if it can't load"

    now_utc = now_utc or datetime.now(timezone.utc)

    place = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "timezone": "GMT",
        "past_days": 1,
        "forecast_days": 2
    }

    weather = get_json(FORECAST_URL, {
        **place,
        "hourly": ",".join(WEATHER_FIELDS),
        "temperature_unit": "fahrenheit"
    })

    try:
        air = hourly_rows(
            get_json(AIR_QUALITY_URL, {**place, "hourly": ",".join(AIR_FIELDS)}),
            AIR_FIELDS
        )
    except RuntimeError:
        air = None

    return summarize_conditions(
        hourly_rows(weather, WEATHER_FIELDS),
        air,
        now_utc,
        location["timezone"]
    )
