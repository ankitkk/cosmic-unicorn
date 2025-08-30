# render_weather.py
# Weather screen: shows local time (24h), current temp (°F) colorized,
# and either today's hi/lo or the condition text.

import time
from display import clear, draw_text, update, center_x, make_pen,draw_text_with_shadow
from theme import temp_to_color_f
from config import LINE_HEIGHT, TEXT_SCALE,CLOCK_TEXT_SCALE


def _format_clock_local(tz_offset_seconds):
    secs = time.time() + (tz_offset_seconds or 0)
    tm = time.gmtime(secs)
    return "{:02d}:{:02d}".format(tm[3], tm[4])  # 24h HH:MM


def draw_weather_static(time_pen, hl_pen, tz_offset_seconds, wx):
    """
    time_pen: PicoGraphics pen for the clock (theme TIME color)
    hl_pen:   PicoGraphics pen for highlight (theme HL color)
    tz_offset_seconds: int (local offset from UTC)
    wx: dict with keys: temp_f, tmax, tmin, cond
    """
    line1 = _format_clock_local(tz_offset_seconds)

    temp_f = wx.get("temp_f")
    line2 = f"{int(temp_f)}°F" if temp_f is not None else "--°F"

    tmax, tmin = wx.get("tmax"), wx.get("tmin")
    line3 = (
        f"{int(tmax)}°/{int(tmin)}°"
        if (tmax is not None and tmin is not None)
        else (wx.get("cond") or "—")
    )

    y1, y2, y3 = 3, 3 + LINE_HEIGHT, 3 + 2 * LINE_HEIGHT

    clear()
    # Clock
    draw_text(line1, center_x(line1, CLOCK_TEXT_SCALE), y1, CLOCK_TEXT_SCALE, time_pen)
    # Temp (colorized by temp)
    temp_rgb = temp_to_color_f(temp_f)
    draw_text(line2, center_x(line2, TEXT_SCALE), y2, TEXT_SCALE, make_pen(temp_rgb))
    # Hi/Lo or condition
    draw_text(line3, center_x(line3, TEXT_SCALE), y3, TEXT_SCALE, hl_pen)

    update()
