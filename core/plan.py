"Find lower-heat hours for the next seven days"

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from core.rules import get_category, load_rules
from core.today import utc_time


def find_window(hours):
    "find the longest stretch of green or yellow hours"

    windows = []
    current = []

    for time, reading, category in hours:

        if category not in ("green", "yellow"):
            if current:
                windows.append(current)
            current = []
            continue

        #start a new window if hours aren't consecutive
        if current:
            gap = (
                time.astimezone(timezone.utc)
                - current[-1][0].astimezone(timezone.utc)
            )

            if gap != timedelta(hours=1):
                windows.append(current)
                current = []

        current.append((time, reading))

    if current:
        windows.append(current)

    if not windows:
        return None

    #prefer longer windows, then lower temperatures
    best = min(
        windows,
        key=lambda window: (
            -len(window),
            max(hour["wbgt"] for _, hour in window)
        )
    )

    start = best[0][0]
    end = (
        best[-1][0].astimezone(timezone.utc)
        + timedelta(hours=1)
    ).astimezone(start.tzinfo)

    return start, end


def summarize_week(readings, location, now_utc=None):
    "organize hourly weather into seven local days."

    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    if now_utc.tzinfo is None:
        raise ValueError("CURRENT TIME NEEDS A TIMEZONE")

    zone = ZoneInfo(location["timezone"])
    local_now = now_utc.astimezone(zone)
    start = local_now.date()

    days = {}

    #sort hours into local dates
    for reading in readings:

        time = utc_time(reading["time"]).astimezone(zone)
        day = time.date()

        if not start <= day < start + timedelta(days=7):
            continue

        category = get_category(
            reading["wbgt"],
            f"sports_{location['region']}"
        )["category"]

        days.setdefault(day, []).append(
            (time, reading, category)
        )

    thresholds = load_rules()["sports"]["regions"][str(location["region"])]["minimums"]

    results = []

    for i in range(7):

        day = start + timedelta(days=i)
        hours = sorted(days.get(day, []), key=lambda x: x[0])

        if not hours:
            raise ValueError(f"NO WEATHER DATA FOR {day}")

        peak = max(hours, key=lambda x: x[1]["wbgt"])

        #daytime hours only, excluding past hours
        daytime = [
            hour for hour in hours
            if 6 <= hour[0].hour < 20
            and (day != start or hour[0] >= local_now)
        ]

        results.append({
            "date": day,
            "peak_time": peak[0],
            "peak_wbgt": peak[1]["wbgt"],
            "peak_category": peak[2],
            "window": find_window(daytime),
            #every hour of the day for the day chart
            "hourly": [
                {"time": time, "wbgt": reading["wbgt"], "category": category}
                for time, reading, category in hours
            ],
            "thresholds_f": thresholds
        })

    return results


def fetch_week_plan(location):
    "fetch weather and calculate the seven-day plan."

    from core.weather import FORECAST_URL, get_weather_data
    from core.wbgt import calculate_hourly_wbgt

    #extra UTC days cover local midnight
    weather = get_weather_data(
        location["latitude"],
        location["longitude"],
        FORECAST_URL,
        forecast_days=8,
        past_days=1
    )

    readings = calculate_hourly_wbgt(
        weather,
        location["latitude"],
        location["longitude"]
    )

    return summarize_week(readings, location)
