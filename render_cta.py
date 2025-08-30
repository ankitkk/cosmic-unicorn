# render_cta.py
# CTA screen: each configured row shows "<rt><dir_label>" on the left
# and a 3-character rotating token (minutes/DUE/DLY/NOA) on the right.

from display import clear, draw_text, update, text_width
from config import LINE_HEIGHT, TEXT_SCALE, CTA_TOGGLE_MS, DISPLAY_WIDTH
from cta_api import token3

def draw_cta_toggle(cta_rows_data, now_ms, x_offset=0):
    """
    cta_rows_data: list of {"prefix": str, "pen": pen, "minutes": [tokens]}
    now_ms: ticks_ms() value for selecting which token to display
    x_offset: optional horizontal shift (for slide transition)
    """
    clear()
    y = 2
    idx = (now_ms // CTA_TOGGLE_MS)
    for row in cta_rows_data:
        minutes = row["minutes"]
        tok = token3(minutes[idx % len(minutes)])  # fixed 3-char field

        tok_w = text_width(tok, TEXT_SCALE)
        tok_x = DISPLAY_WIDTH - tok_w + x_offset
        left_max_w = DISPLAY_WIDTH - tok_w - 1

        prefix = row["prefix"]
        # Trim prefix to fit the left column
        while text_width(prefix, TEXT_SCALE) > left_max_w and len(prefix) > 0:
            prefix = prefix[:-1]

        draw_text(prefix, 0 + x_offset, y, TEXT_SCALE, row["pen"], left_max_w)
        draw_text(tok, tok_x, y, TEXT_SCALE, row["pen"])
        y += LINE_HEIGHT

    update()
