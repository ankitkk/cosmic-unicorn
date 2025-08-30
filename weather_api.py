# weather_api.py
# Open-Meteo client: current temp/condition, daily hi/lo, sunrise/sunset, tz offset.

import urequests as requests
import gc

_DEF_HEADERS = {"Connection": "close"}
_BASE = "https://api.open-meteo.com/v1/forecast"


def fetch_weather(lat, lon, tz):
    """
    Returns dict:
      {
        "tz_offset_seconds": int,
        "temp_f": float|None,
        "cond": str,               # human text from weather_code
        "tmax": float|None,
        "tmin": float|None,
        "is_day": 0|1|None,
        "sunrise": "YYYY-MM-DDTHH:MM"|None,
        "sunset":  "YYYY-MM-DDTHH:MM"|None,
      }
    """
    url = (
        f"{_BASE}?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,weather_code,is_day"
        "&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset"
        "&temperature_unit=fahrenheit"
        f"&timezone={tz}"
    )
    resp = None
    try:
        resp = requests.get(url, headers=_DEF_HEADERS)
        data = resp.json()
    except Exception:
        _cleanup(resp)
        return None
    finally:
        _cleanup(resp)

    try:
        tz_offset_seconds = int(data.get("utc_offset_seconds", 0))
    except Exception:
        tz_offset_seconds = 0

    cur = data.get("current", {}) or {}
    daily = data.get("daily", {}) or {}

    def _first(lst):
        try:
            return lst[0]
        except Exception:
            return None

    code = cur.get("weather_code")
    return {
        "tz_offset_seconds": tz_offset_seconds,
        "temp_f": cur.get("temperature_2m"),
        "cond": weather_code_to_text(code),
        "tmax": _first(daily.get("temperature_2m_max", [None])),
        "tmin": _first(daily.get("temperature_2m_min", [None])),
        "is_day": cur.get("is_day"),
        "sunrise": _first(daily.get("sunrise", [None])),
        "sunset": _first(daily.get("sunset", [None])),
    }


def weather_code_to_text(code):
    if code is None:
        return "—"
    if code == 0:
        return "Clear"
    if code in (1, 2, 3):
        return "Cloudy"
    if code in (45, 48):
        return "Fog"
    if code in (51, 53, 55, 56, 57):
        return "Drizzle"
    if code in (61, 63, 65, 66, 67):
        return "Rain"
    if code in (71, 73, 75, 77):
        return "Snow"
    if code in (80, 81, 82):
        return "Showers"
    if code in (95, 96, 97):
        return "Storms"
    return "Weather"


def _cleanup(resp):
    try:
        if resp:
            resp.close()
    except Exception:
        pass
    gc.collect()
