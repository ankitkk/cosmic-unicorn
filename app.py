# app.py
# Orchestrates the app: Wi-Fi, polling (weather/CTA), theme updates,
# screen rotation, and per-mode brightness.

import time
import gc

from config import (
    ROWS, CTA_POLL_SECONDS,
    LAT, LON, TZ, WEATHER_POLL_SECONDS,
    WEATHER_SCREEN_SECONDS, CTA_SCREEN_SECONDS,
    TRANSITION_MS, FRAME_DELAY, CTA_BRIGHTNESS_FACTOR,
    DISPLAY_WIDTH,
    MORNING_CTA_START_HOUR, MORNING_CTA_END_HOUR, MORNING_CTA_MULTIPLIER,
)

# not in git
from lib.secrets import WIFI_SSID, WIFI_PASSWORD, CTA_API_KEY
import net
import display as disp
from display import make_pen
from theme import update_theme, base_brightness, set_tz_offset
from cta_api import fetch_predictions, extract_minutes_list
from weather_api import fetch_weather
from render_weather import draw_weather_static
from render_cta import draw_cta_toggle


# Modes
MODE_WEATHER, MODE_CTA, MODE_TRANSITION = 0, 1, 2

# Runtime state
mode = MODE_WEATHER
next_mode = MODE_CTA
transition_start_ms = None

# Timers
last_weather_poll_ms = -999_999
last_cta_poll_ms = -999_999
last_mode_switch_ms = 0

# NEW: app-level throttle to ping NTP (sync is throttled inside net.sync_clock)
APP_NTP_PING_MS = 60_000  # check once per minute
_last_ntp_ping_ms = -999_999

# Caches
weather_cache = {
    "temp_f": None, "cond": "—", "tmax": None, "tmin": None,
    "is_day": 1, "sunrise": None, "sunset": None, "tz_offset_seconds": 0,
}
cta_rows_data = [
    {"prefix": "…", "pen": make_pen((255, 255, 255)), "minutes": ["…"]} for _ in range(3)
]

# Precompute row pens once
for r in ROWS:
    r["pen"] = make_pen(r["color"])


def _apply_mode_brightness(current_mode, upcoming_mode=None, t_progress=1.0):
    """Brightness curve: CTA slightly dimmer than Weather; tween during transitions."""
    b_weather = base_brightness()
    b_cta = b_weather * CTA_BRIGHTNESS_FACTOR

    if current_mode == MODE_TRANSITION and upcoming_mode is not None:
        p = max(0.0, min(1.0, t_progress))
        if upcoming_mode == MODE_CTA:
            b = b_weather * (1.0 - p) + b_cta * p
        else:
            b = b_cta * (1.0 - p) + b_weather * p
    else:
        b = b_weather if current_mode == MODE_WEATHER else b_cta

    disp.set_brightness(b)


def _build_cta_rows_data():
    rows = []
    for cfg in ROWS:
        if not CTA_API_KEY:
            result = {"error": "no key"}
        else:
            result = fetch_predictions(CTA_API_KEY, cfg["stpid"], cfg["rt"]) or {}
        if not result or "error" in result:
            mins = ["NOA"]
        else:
            mins = extract_minutes_list(result.get("preds", []), cfg.get("rtdir"))
        rows.append({
            "prefix": f"{cfg['rt']}{cfg['dir_label']}",
            "pen": cfg["pen"],
            "minutes": mins,
        })
    return rows


def _set_transition(nmode, now_ms):
    global next_mode, mode, transition_start_ms
    next_mode = nmode
    mode = MODE_TRANSITION
    transition_start_ms = now_ms


def _enter_next_mode(now_ms):
    global mode, last_mode_switch_ms, transition_start_ms
    mode = next_mode
    last_mode_switch_ms = now_ms
    transition_start_ms = None


def main():
    global last_mode_switch_ms, last_weather_poll_ms, last_cta_poll_ms
    global cta_rows_data, weather_cache, _last_ntp_ping_ms

    # Hook up status UI for Wi-Fi
    net.set_status_callback(disp.status_screen)

    # Connect Wi-Fi (reboots on hard timeout per net.ensure_wifi)
    net.ensure_wifi(WIFI_SSID, WIFI_PASSWORD)

    # >>> NEW: force an initial NTP sync right after we know Wi-Fi is up
    net.sync_clock(force=True)
    _last_ntp_ping_ms = time.ticks_ms()

    # Initial pulls
    w = fetch_weather(LAT, LON, TZ)
    if w:
        weather_cache.update(w)
        set_tz_offset(w.get("tz_offset_seconds", 0))

    # Theme pens (time + highlight) — computed & cached in theme
    time_pen, hl_pen, _ = update_theme(weather_cache, make_pen, force=True)

    # CTA rows
    rows = _build_cta_rows_data()
    if rows:
        cta_rows_data = rows

    last_mode_switch_ms = time.ticks_ms()

    while True:
        now_ms = time.ticks_ms()

        # >>> NEW: Periodic NTP resync "ping"
        # Call sync_clock() frequently; it will only sync if 6h elapsed (throttle inside net).
        if time.ticks_diff(now_ms, _last_ntp_ping_ms) >= APP_NTP_PING_MS and net.wlan.isconnected():
            try:
                net.sync_clock(force=False)
            except Exception:
                pass
            _last_ntp_ping_ms = now_ms

        # Rotate screens (CTA lasts longer in the morning window)
        tz_off = weather_cache.get("tz_offset_seconds", 0) or 0
        local_secs = time.time() + tz_off
        hh = time.gmtime(local_secs)[3]

        if mode == MODE_WEATHER:
            # Weather uses its normal duration
            if time.ticks_diff(now_ms, last_mode_switch_ms) >= WEATHER_SCREEN_SECONDS * 1000:
                _set_transition(MODE_CTA, now_ms)

        elif mode == MODE_CTA:
            # CTA gets extended duration during morning commute window
            cta_secs = CTA_SCREEN_SECONDS
            if MORNING_CTA_START_HOUR <= hh < MORNING_CTA_END_HOUR:
                cta_secs = int(CTA_SCREEN_SECONDS * MORNING_CTA_MULTIPLIER)
            if time.ticks_diff(now_ms, last_mode_switch_ms) >= cta_secs * 1000:
                _set_transition(MODE_WEATHER, now_ms)

        # Poll WEATHER (only if showing Weather soon/recently)
        if (mode in (MODE_WEATHER, MODE_TRANSITION) or next_mode == MODE_WEATHER) and \
           time.ticks_diff(now_ms, last_weather_poll_ms) >= WEATHER_POLL_SECONDS * 1000:
            if net.ensure_wifi(WIFI_SSID, WIFI_PASSWORD):
                w = fetch_weather(LAT, LON, TZ)
                if w:
                    weather_cache.update(w)
                    set_tz_offset(w.get("tz_offset_seconds", weather_cache.get("tz_offset_seconds", 0)))
                # Force theme refresh after new weather (sunrise/sunset may change)
                time_pen, hl_pen, _ = update_theme(weather_cache, make_pen, force=True)
            last_weather_poll_ms = now_ms

        # Poll CTA (only if showing CTA soon/recently)
        if (mode in (MODE_CTA, MODE_TRANSITION) or next_mode == MODE_CTA) and \
           time.ticks_diff(now_ms, last_cta_poll_ms) >= CTA_POLL_SECONDS * 1000:
            if net.ensure_wifi(WIFI_SSID, WIFI_PASSWORD):
                try:
                    rows = _build_cta_rows_data()
                    if rows:
                        cta_rows_data = rows
                except Exception:
                    pass
            last_cta_poll_ms = now_ms

        # Keep theme fresh (throttled internally)
        time_pen, hl_pen, _ = update_theme(weather_cache, make_pen)

        # Draw + brightness
        if mode == MODE_TRANSITION and transition_start_ms is not None:
            t = time.ticks_diff(now_ms, transition_start_ms)
            if t >= TRANSITION_MS:
                _enter_next_mode(now_ms)
            else:
                # Brightness crossfade; swap frame halfway for a simple, pleasant handoff.
                progress = t / float(TRANSITION_MS)
                _apply_mode_brightness(MODE_TRANSITION, upcoming_mode=next_mode, t_progress=progress)

                # Slide transition: current screen moves left, next slides in from right
                # Compute pixel offsets
                offset = int(DISPLAY_WIDTH * progress)
                if next_mode == MODE_CTA:
                    # Weather -> CTA
                    # Draw current (weather) shifted left
                    draw_weather_static(time_pen, hl_pen, weather_cache.get("tz_offset_seconds", 0), weather_cache, x_offset=-offset, clear_first=True)
                    # Draw next (CTA) coming in from right
                    draw_cta_toggle(cta_rows_data, now_ms, x_offset=(DISPLAY_WIDTH - offset), clear_first=False)
                else:
                    # CTA -> Weather
                    draw_cta_toggle(cta_rows_data, now_ms, x_offset=-offset, clear_first=True)
                    draw_weather_static(time_pen, hl_pen, weather_cache.get("tz_offset_seconds", 0), weather_cache, x_offset=(DISPLAY_WIDTH - offset), clear_first=False)
        else:
            if mode == MODE_WEATHER:
                _apply_mode_brightness(MODE_WEATHER)
                draw_weather_static(time_pen, hl_pen, weather_cache.get("tz_offset_seconds", 0), weather_cache)
            else:
                _apply_mode_brightness(MODE_CTA)
                draw_cta_toggle(cta_rows_data, now_ms)

        disp.update()
        time.sleep(FRAME_DELAY)
        gc.collect()
