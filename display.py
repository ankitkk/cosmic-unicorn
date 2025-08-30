# display.py
# Thin wrapper around CosmicUnicorn + PicoGraphics with a few drawing helpers.

from cosmic import CosmicUnicorn
from picographics import PicoGraphics, DISPLAY_COSMIC_UNICORN
from config import DISPLAY_WIDTH, DISPLAY_HEIGHT, FONT

# Initialize hardware
unicorn = CosmicUnicorn()
graphics = PicoGraphics(display=DISPLAY_COSMIC_UNICORN)

graphics.set_font(FONT)
unicorn.set_brightness(0.5)

# Common pens
WHITE = graphics.create_pen(255, 255, 255)
BLACK = graphics.create_pen(0, 0, 0)


def make_pen(rgb):
    """Create a PicoGraphics pen from an (r, g, b) tuple."""
    r, g, b = rgb
    return graphics.create_pen(r, g, b)


def set_brightness(b):
    """Set panel brightness (0..1)."""
    try:
        unicorn.set_brightness(b)
    except Exception:
        pass


def text_width(s, scale=1):
    """Measure text width (fallback assumes 8px/char for bitmap8)."""
    try:
        return int(graphics.measure_text(s, scale))
    except Exception:
        return int(len(s) * 8 * scale)


def center_x(s, scale=1):
    """X coordinate to center a string on the 32px-wide display."""
    w = text_width(s, scale)
    return max(0, (DISPLAY_WIDTH - w) // 2)


def clear(pen=None):
    """Clear screen to pen (default BLACK)."""
    graphics.set_pen(pen or BLACK)
    graphics.clear()

def draw_text_with_shadow(txt, x, y, scale, fg_pen, bg_pen):
    # Draw shadow (1px offset)
    graphics.set_pen(bg_pen)
    graphics.text(txt, x+1, y+1, 256, scale)
    # Draw main text
    graphics.set_pen(fg_pen)
    graphics.text(txt, x, y, 256, scale)
    

def draw_text(s, x, y, scale=1, pen=None, wrap=256):
    """Draw text with optional pen and wrap width."""
    if pen is not None:
        graphics.set_pen(pen)
    graphics.text(s, x, y, wrap, scale)


def update():
    """Flush the frame to the panel."""
    unicorn.update(graphics)


def status_screen(line1, line2="", scale=1):
    """
    Minimal two-line status UI (used by net.ensure_wifi).
    Renders centered white text on black.
    """
    clear()
    graphics.set_pen(WHITE)
    y = 6 if line2 else 10
    draw_text(line1, center_x(line1, scale), y, scale)
    if line2:
        draw_text(line2, center_x(line2, scale), y + 9, scale)
    update()
