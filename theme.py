# theme.py
# Computes UI theme colors and base brightness based on:
# - Open-Meteo fields: sunrise, sunset, is_day
# - Local time (via tz offset)
# Also provides a temperature→RGB helper for the weather number.

import time
from config import THEMES, DUSK_WINDOW_MIN, THEME_CHECK_MS

# Runtime state (updated by update_theme / set_tz_offset)
_tz_offset_seconds = 0
_current_theme = None
_last_theme_check_ms = 0

# Cached RGB + brightness
TIME_RGB = THEMES["day"]["time"]
HL_RGB   = THEMES["day"]["hl"]
_base_brightness = THEMES["day"].get("brightness", 0.5)

# Cached pens to avoid re-creating every frame
_TIME_PEN = None
_HL_PEN = None
_last_time_rgb = None
_last_hl_rgb = None


def set_tz_offset(sec):
    """Set local timezone offset in seconds (from weather API)."""
    global _tz_offset_seconds
    try:
        _tz_offset_seconds = int(sec or 0)
    except Exception:
        _tz_offset_seconds = 0


# -----------------------
# Utilities
# -----------------------

def _clamp(v, a, b):
    return a if v < a else b if v > b else v


def _mix_rgb(c1, c2, t):
    t = _clamp(t, 0.0, 1.0)
    r = int(c1[0] + (c2[0] - c1[0]) * t)
    g = int(c1[1] + (c2[1] - c1[1]) * t)
    b = int(c1[2] + (c2[2] - c1[2]) * t)
    return (_clamp(r, 0, 255), _clamp(g, 0, 255), _clamp(b, 0, 255))


def _ensure_pens(make_pen_func):
    global _TIME_PEN, _HL_PEN, _last_time_rgb, _last_hl_rgb
    if _TIME_PEN is None or _last_time_rgb != TIME_RGB:
        _TIME_PEN = make_pen_func(TIME_RGB)
        _last_time_rgb = TIME_RGB
    if _HL_PEN is None or _last_hl_rgb != HL_RGB:
        _HL_PEN = make_pen_func(HL_RGB)
        _last_hl_rgb = HL_RGB


def temp_to_color_f(temp_f, white=(180, 180, 180)):
    """
    Map °F to RGB: blue → soft-white → red gradient.
    Whiteness greatly reduced for better LED readability.
    Returns an RGB tuple.
    """
    if temp_f is None:
        return white

    t = _clamp((temp_f + 10) / 120.0, 0.0, 1.0)  # -10..110F → 0..1

    if t <= 0.58:
        # Cold → mild transition: deep blue → soft grayish-white
        k = t / 0.58
        r = int(0 + k * 160)           # lower peak red
        g = int(60 + k * (180 - 60))   # reduce green ramp
        b = int(220 + k * (180 - 220)) # slightly less blue fade
    else:
        # Mild → hot transition: soft grayish-white → red
        k = (t - 0.58) / (1.0 - 0.58)
        r = 255
        g = int(180 - k * (180 - 40))  # reduced green peak
        b = int(180 - k * 180)         # fade blue quicker

    return (_clamp(r, 0, 255), _clamp(g, 0, 255), _clamp(b, 0, 255))


def _hhmm_from_iso(local_iso):
    # Expect "YYYY-MM-DDTHH:MM"
    if not local_iso or len(local_iso) < 16:
        return None
    return (int(local_iso[11:13]), int(local_iso[14:16]))


def _local_now_tuple():
    secs = time.time() + _tz_offset_seconds
    return time.gmtime(secs)  # (Y, M, D, h, m, s, ...)


def _minutes(h, m):
    return h * 60 + m


def _blend_factor(now_min, edge_min):
    """
    Returns None outside the dusk/dawn window, else a 0..1 factor
    that peaks at the edge time and fades outward across DUSK_WINDOW_MIN.
    """
    delta = abs(now_min - edge_min)
    if delta >= DUSK_WINDOW_MIN:
        return None
    return 1.0 - (delta / float(DUSK_WINDOW_MIN))


# -----------------------
# Theme computation
# -----------------------

def update_theme(wx, make_pen, force=False):
    """
    Compute and cache theme pens + brightness.
    Args:
      wx: dict with keys {sunrise, sunset, is_day}
      make_pen: function(rgb_tuple) -> PicoGraphics pen
      force: bypass throttle
    Returns:
      (TIME_PEN, HL_PEN, base_brightness_float)
    """
    global _current_theme, _last_theme_check_ms, TIME_RGB, HL_RGB, _base_brightness

    now_ms = time.ticks_ms()
    if not force and time.ticks_diff(now_ms, _last_theme_check_ms) < THEME_CHECK_MS:
        _ensure_pens(make_pen)
        return (_TIME_PEN, _HL_PEN, _base_brightness)
    _last_theme_check_ms = now_ms

    # Local time
    y, m, d, hh, mm, *_ = _local_now_tuple()
    now_min = _minutes(hh, mm)

    # Sunrise/sunset minutes
    sr = _hhmm_from_iso(wx.get("sunrise"))
    ss = _hhmm_from_iso(wx.get("sunset"))
    sr_min = _minutes(sr[0], sr[1]) if sr else None
    ss_min = _minutes(ss[0], ss[1]) if ss else None

    day_cfg = THEMES["day"]
    night_cfg = THEMES["night"]

    # Prefer is_day if available
    is_day_flag = wx.get("is_day")
    base_theme = "day" if (isinstance(is_day_flag, int) and is_day_flag == 1) else None

    # Blend near sunrise (night→day)
    if sr_min is not None:
        t = _blend_factor(now_min, sr_min)
        if t is not None:
            k = t
            TIME_RGB = _mix_rgb(night_cfg["time"], day_cfg["time"], k)
            HL_RGB   = _mix_rgb(night_cfg["hl"],   day_cfg["hl"],   k)
            _base_brightness = night_cfg["brightness"] + (day_cfg["brightness"] - night_cfg["brightness"]) * k
            _current_theme = "dawn"
            _ensure_pens(make_pen)
            return (_TIME_PEN, _HL_PEN, _base_brightness)

    # Blend near sunset (day→night)
    if ss_min is not None:
        t = _blend_factor(now_min, ss_min)
        if t is not None:
            k = t
            TIME_RGB = _mix_rgb(day_cfg["time"], night_cfg["time"], k)
            HL_RGB   = _mix_rgb(day_cfg["hl"],   night_cfg["hl"],   k)
            _base_brightness = day_cfg["brightness"] + (night_cfg["brightness"] - day_cfg["brightness"]) * k
            _current_theme = "dusk"
            _ensure_pens(make_pen)
            return (_TIME_PEN, _HL_PEN, _base_brightness)

    # Outside blend windows → snap to day/night
    if base_theme is None and sr_min is not None and ss_min is not None:
        base_theme = "day" if (sr_min <= now_min < ss_min) else "night"
    if base_theme is None:
        base_theme = "day" if (7 <= hh < 19) else "night"  # conservative fallback

    cfg = day_cfg if base_theme == "day" else night_cfg
    TIME_RGB, HL_RGB = cfg["time"], cfg["hl"]
    _base_brightness = cfg.get("brightness", 0.5)
    _current_theme = base_theme

    _ensure_pens(make_pen)
    return (_TIME_PEN, _HL_PEN, _base_brightness)


def base_brightness():
    """Current scalar brightness chosen by the theme (0..1)."""
    return _base_brightness
