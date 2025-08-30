# config.py
# Central configuration for timing, display, and data sources.

# ---- CTA ----
CTA_API_KEY = "dXbfpRPHTUYqhk4RfW7m7j4Gz"
ROWS = [
    {"stpid": "8844", "rt": "50", "dir_label": "S", "rtdir": "Southbound", "color": (0, 255, 255)},  # 50 Southbound
    {"stpid": "4100", "rt": "73", "dir_label": "W", "rtdir": "Westbound",  "color": (255, 255, 0)},  # 73 Westbound
    {"stpid": "4065", "rt": "73", "dir_label": "E", "rtdir": "Eastbound",  "color": (255, 128, 0)},  # 73 Eastbound
]
CTA_POLL_SECONDS = 30
CTA_TOGGLE_MS = 2500  # toggle token every 2.5s

# ---- Weather (Open-Meteo; Chicago lat/lon) ----
LAT, LON = 41.8781, -87.6298
TZ = "America/Chicago"
WEATHER_POLL_SECONDS = 600  # every 10 minutes

# ---- Screen rotation ----
WEATHER_SCREEN_SECONDS = 8
CTA_SCREEN_SECONDS = 22

# ---- Transition (slide)
TRANSITION_MS = 900  # smooth slide duration

# ---- Display / text ----
DISPLAY_WIDTH = 32
DISPLAY_HEIGHT = 32
FONT = "bitmap8"
TEXT_SCALE = 1          # default scale for normal text (temps, CTA rows)
CLOCK_TEXT_SCALE = 1    # bigger font just for the time (readable far away)
LINE_HEIGHT = 9
FRAME_DELAY = 0.04

# ---- Dusk blending window (minutes around sunrise/sunset) ----
DUSK_WINDOW_MIN = 45  # fade between day<->night across this window

# ---- Per-mode brightness: CTA is dimmer than Weather ----
CTA_BRIGHTNESS_FACTOR = 0.65   # CTA brightness = theme base * factor

# ---- Theme presets (cyan + lime) ----
THEMES = {
    "day": {   # bright cyan for time, lime highlight
        "time": (0, 255, 255),
        "hl":   (190, 255, 70),
        "brightness": 0.60,   # slightly brighter by default for legibility
    },
    "night": { # darker cyan + softer lime
        "time": (0, 120, 120),
        "hl":   (120, 200, 60),
        "brightness": 0.42,
    },
}

# ---- Theme refresh throttle ----
THEME_CHECK_MS = 10000  # recompute blend about every 10s

# ---- Spinner frames for Wi-Fi status ----
SPINNER_FRAMES = ["|", "/", "-", "\\"]
