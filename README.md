# Chicago Transit Authority Tracker + Weather LED Display

A MicroPython app for [Pimoroni Cosmic Unicorn](https://shop.pimoroni.com/products/space-unicorns?variant=40842626596947) (32x32 LED) that rotates between a weather screen and CTA bus arrival countdowns. It themes colors by day/night, syncs time via NTP, and handles Wi-Fi setup with a minimal on-device status UI.

<img width="450" height="300" alt="image" src="https://github.com/user-attachments/assets/d6d5f419-46bd-4e84-ab16-2fccd476c1fe" />

## Features
- Weather: local time, current temp (°F, colorized), hi/lo or condition
- Transit: three configurable CTA rows with 3-char rotating tokens
- Theme: smooth day/night blending and per-mode brightness
- Transitions: brightness crossfade + sliding animation between screens
- Networking: resilient Wi-Fi connect flow with NTP sync
- Morning preference: between 08:00–10:00 local, shows the CTA screen longer

## Hardware
- Pimoroni Cosmic Unicorn (RP2040 + 32x32 RGB LED matrix)
- Runs on MicroPython (Pico W firmware)

## Setup
1. Dependencies on device (typical):
   - `cosmic`, `picographics` (from Pimoroni MicroPython build)
   - `urequests` (HTTP client; usually bundled in the build)
2. Secrets:
   - Create `lib/secrets.py` with: `WIFI_SSID`, `WIFI_PASSWORD`, `CTA_API_KEY`
3. Configure routes/weather in `config.py`:
   - Update `ROWS` for stop/route/direction/color.
   - Set `LAT`, `LON`, and `TZ` for your location.
   - Tune screen timings, brightness, and themes as needed.

## Running
- Entrypoint: `main.py` runs `app.main()`. On boot, the app:
  - Connects Wi-Fi and forces an initial NTP sync
  - Fetches weather and CTA data
  - Enters the main loop, rotating between screens with transitions

## Configuration Highlights
- Morning CTA preference in `config.py`:
  - `MORNING_CTA_START_HOUR = 8`
  - `MORNING_CTA_END_HOUR = 10`
  - `MORNING_CTA_MULTIPLIER = 2.5` (CTA duration multiplier during morning window)
- Base durations in `config.py`:
  - `WEATHER_SCREEN_SECONDS`, `CTA_SCREEN_SECONDS`
- Theme presets and dusk blending:
  - `THEMES`, `DUSK_WINDOW_MIN`, `THEME_CHECK_MS`

## Notes
- WIFI credentials/CTA API key are loaded from `lib/secrets.py` (not in repo).
- Weather API: Open-Meteo (no key needed).
- Pens are memoized to reduce GC churn and improve performance.

## Troubleshooting
- If Wi-Fi repeatedly times out, credentials may be wrong; app displays status.
- If time appears wrong at boot, ensure Wi-Fi is reachable for NTP.
- If CTA screen is blank or `NOA`, API may be unreachable or key missing.

## License
This project is licensed under the [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)



