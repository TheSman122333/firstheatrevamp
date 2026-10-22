"Get current-hour WBGT and today's peak for any saved city."

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from core.rules import get_category, load_rules


def utc_time(text):

    when = datetime.fromisoformat(
        text.replace("Z", "+00:00")
    )

    if when.tzinfo is None:
        return when.replace(tzinfo=timezone.utc)

    return when.astimezone(timezone.utc)


def summarize_today(readings, now_utc=None, location=None):

    from storage import default_settings

    location = location or default_settings()
    now_utc = now_utc or datetime.now(timezone.utc)

    if now_utc.tzinfo is None:
        raise ValueError("TIME NEEDS A TIMEZONE")

    zone = ZoneInfo(location["timezone"])

    local_date = now_utc.astimezone(zone).date()

    current_hour = now_utc.astimezone(timezone.utc).replace(
        minute=0, second=0, microsecond=0
    )

    today = []
    current = None

    for reading in readings:

        utc = utc_time(reading["time"])
        local = utc.astimezone(zone)

        if local.date() != local_date:
            continue

        today.append((local, reading))

        if utc == current_hour:
            current = (local, reading)

    if not today:
        raise ValueError("Missing daily weather for this location")

    if current is None:
        raise ValueError("Missing current Detroit hour or chosen location hour")

    peak_time, peak = max(
        today,
        key=lambda item: item[1]["wbgt"]
    )

    current_time, hour = current
    region = location["region"]

    category = get_category(
        hour["wbgt"], f"sports_{region}"
    )

    peak_category = get_category(
        peak["wbgt"], f"sports_{region}"
    )

    #every hour of today for the day chart
    hourly = [
        {
            "time": local,
            "wbgt": reading["wbgt"],
            "category": get_category(
                reading["wbgt"], f"sports_{region}"
            )["category"]
        }
        for local, reading in today
    ]

    thresholds = load_rules()["sports"]["regions"][str(region)]["minimums"]

    return {
        "current_time": current_time,
        "current_wbgt": hour["wbgt"],
        "category": category["category"],
        "guidance": category["guidance"],
        "peak_time": peak_time,
        "peak_wbgt": peak["wbgt"],
        "peak_category": peak_category["category"],
        "region": region,
        "hourly": hourly,
        "thresholds_f": thresholds,
        "weather_source": "Open-Meteo hourly forecast",
        "rule_source": category["source"]
    }


def fetch_today_summary(location=None):
    "fetch weather and calculate today's estimated WBGT"

    from core.weather import FORECAST_URL, get_weather_data
    from core.wbgt import calculate_hourly_wbgt
    from storage import default_settings

    default_location = location is None
    location = location or default_settings()

    #include previous UTC day to cover local time
    weather = get_weather_data(
        location["latitude"],
        location["longitude"],
        FORECAST_URL,
        forecast_days=2,
        past_days=1
    )

    readings = calculate_hourly_wbgt(
        weather,
        location["latitude"],
        location["longitude"]
    )

    if default_location:
        return summarize_today(readings)

    return summarize_today(readings, location=location)
