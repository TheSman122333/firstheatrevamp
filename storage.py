"Save FirstHeat settings and acclimation details on the device"

import json
import math
from datetime import date
from zoneinfo import ZoneInfo


SETTINGS_KEY = "firstheat.settings.v1"
PERSON_KEY = "firstheat.me.v1"

TRACKER_KEY = "firstheat.tracker.v1"

#bump the version when the disclaimer text changes so it shows again
DISCLAIMER_KEY = "firstheat.disclaimer"
DISCLAIMER_VERSION = "2026.1"


#location settings
def default_settings():
    return {
        "name": "Detroit",
        "state": "Michigan",
        "latitude": 42.3314,
        "longitude": -83.0458,
        "timezone": "America/Detroit",
        "region": 2
    }


def check_settings(settings):

    if not isinstance(settings, dict):
        raise ValueError("INVALID SETTINGS")

    if settings.get("region") not in (1, 2, 3):
        raise ValueError("INVALID SPORTS REIGON")

    if not isinstance(settings.get("name"), str) or not settings["name"].strip():
        raise ValueError("CITY IS MISSING")

    if not isinstance(settings.get("state"), str):
        raise ValueError("STATE IS MISSING")

    latitude = float(settings["latitude"])
    longitude = float(settings["longitude"])

    if not math.isfinite(latitude) or not -90 <= latitude <= 90:
        raise ValueError("INVALID latitude")

    if not math.isfinite(longitude) or not -180 <= longitude <= 180:
        raise ValueError("INVALID longitude")

    ZoneInfo(settings["timezone"])
    return settings


async def load_settings(prefs):

    try:
        saved = await prefs.get(SETTINGS_KEY)

        if saved:
            return check_settings(json.loads(saved))

    except (ValueError, TypeError, KeyError, OverflowError, OSError, RuntimeError):
        pass

    return default_settings()


async def save_settings(prefs, settings):

    check_settings(settings)

    if not await prefs.set(SETTINGS_KEY, json.dumps(settings)):
        raise RuntimeError("Could not save settings")


#personal settings
def default_person():
    return {
        "role": "worker",
        "experienced": False,
        "normal_minutes": 480,
        "sessions": []
    }


def check_person_data(person):

    if not isinstance(person, dict):
        raise ValueError("INVALID PERSON DATA")

    if person.get("role") not in ("worker", "athlete"):
        raise ValueError("INVALID ROLE")

    if type(person.get("experienced")) is not bool:
        raise ValueError("INVALID EXPERIENCE SETTING")

    minutes = person.get("normal_minutes")

    if type(minutes) is not int or not 1 <= minutes <= 1440:
        raise ValueError("SHIFT MINUTES MUST BE IN BETWEEN 1 and 1440")

    sessions = person.get("sessions")

    if not isinstance(sessions, list):
        raise ValueError("INVALID ATTENDANCE RECORDS")

    for session in sessions:

        if not isinstance(session, dict):
            raise ValueError("INVALID ATTENDANCE RECORDS")

        day = session.get("day")

        if not isinstance(day, str) or date.fromisoformat(day).isoformat() != day:
            raise ValueError("INVALID SESSION DATE")

        if type(session.get("minutes")) is not int or not 1 <= session["minutes"] <= 1440:
            raise ValueError("INVALID SESSION DURATION")

        if person["role"] == "worker":
            allowed = ("work",)
        else:
            allowed = ("practice", "walkthrough")

        if session.get("kind") not in allowed:
            raise ValueError("INVALID SESSION TYPE")

        if type(session.get("heat_wave")) is not bool:
            raise ValueError("INVALID HEAT-WAVE SETTING")

        #optional break reminder results from the activity tracker
        reminders = session.get("reminders")

        if reminders is not None:
            if not isinstance(reminders, dict) or any(
                type(reminders.get(key)) is not int or reminders[key] < 0
                for key in ("done", "missed")
            ):
                raise ValueError("INVALID REMINDER RECORD")

    return person


#load attendance
async def load_person(prefs):

    #use defaults if browser storage isn't available
    try:
        saved = await prefs.get(PERSON_KEY)
    except RuntimeError:
        return default_person()

    if not saved:
        return default_person()
    #check saved attendance before loading
    try:
        return check_person_data(json.loads(saved))

    except (ValueError, TypeError, KeyError) as error:
        raise ValueError(
            "Saved attendance could not be read. "
            "Your data was not erased."
        ) from error


#save personal settings and attendance
async def save_person(prefs, person):

    check_person_data(person)

    saved = await prefs.set(
        PERSON_KEY,
        json.dumps(person)
    )

    if saved is False:
        raise RuntimeError("Could not save attendance.")


#first-launch safety disclaimer
async def load_disclaimer(prefs):
    "True once this version of the disclaimer was accepted on this device"

    #show it again if browser storage isn't available
    try:
        return await prefs.get(DISCLAIMER_KEY) == DISCLAIMER_VERSION
    except RuntimeError:
        return False


async def save_disclaimer(prefs):

    if await prefs.set(DISCLAIMER_KEY, DISCLAIMER_VERSION) is False:
        raise RuntimeError("Could not save the disclaimer choice.")


#activity tracker, kept so a reconnect can pick up where it left off
def check_tracker(state):

    if not isinstance(state, dict):
        raise ValueError("INVALID TRACKER")

    date.fromisoformat(state["day"])

    for key in ("elapsed", "every", "break", "next", "done", "missed"):
        value = state[key]

        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError("INVALID TRACKER")

    started = state.get("started")

    if started is not None and (isinstance(started, bool) or not isinstance(started, (int, float))):
        raise ValueError("INVALID TRACKER")

    return state


async def load_tracker(prefs):

    try:
        saved = await prefs.get(TRACKER_KEY)

        if saved:
            return check_tracker(json.loads(saved))

    except (ValueError, TypeError, KeyError, RuntimeError):
        pass

    return None


async def save_tracker(prefs, state):

    check_tracker(state)

    if await prefs.set(TRACKER_KEY, json.dumps(state)) is False:
        raise RuntimeError("Could not save the tracker.")
