# net.py  (REPLACE your file with this)
import time
import network
import machine

from config import SPINNER_FRAMES

try:
    import ntpclient
except Exception:
    ntpclient = None

STAT_GOT_IP        = 3
STAT_CONNECT_FAIL  = -1
STAT_NO_AP_FOUND   = -2
STAT_WRONG_PASS    = -3

# NTP settings
NTP_RESYNC_MS = 6 * 60 * 60 * 1000  # 6 hours (normal throttle)
NTP_PANIC_MAX_TRIES = 5             # max forced attempts if clock is bogus
NTP_SERVERS = ("pool.ntp.org", "time.google.com", "time.cloudflare.com")

_last_ntp_sync_ms = -999_999
_last_ntp_server_idx = -1

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
try:
    wlan.config(pm=0xA11140)
except Exception:
    pass

_status_cb = None
def set_status_callback(cb):
    global _status_cb
    _status_cb = cb

def _status_screen(l1, l2=""):
    if _status_cb:
        try: _status_cb(l1, l2)
        except Exception: pass

def has_reasonable_time():
    """
    Heuristic: if the RTC year is recent (>= 2024), we consider the clock 'good'.
    """
    try:
        y, m, d, hh, mm, ss, wd, yd = time.gmtime()
        return y >= 2024
    except Exception:
        return False

def _set_ntp_server_round_robin():
    global _last_ntp_server_idx
    if ntpclient is None:
        return
    _last_ntp_server_idx = (_last_ntp_server_idx + 1) % len(NTP_SERVERS)
    try:
        ntpclient.host = NTP_SERVERS[_last_ntp_server_idx]
    except Exception:
        pass


def sync_clock(force=False, panic_if_bad=False):
    global _last_ntp_sync_ms
    now_ms = time.ticks_ms()

    # Check throttling
    if not force and time.ticks_diff(now_ms, _last_ntp_sync_ms) < NTP_RESYNC_MS:
        return
    if not wlan.isconnected():
        return
    try:
        ntpclient.settime()
        _last_ntp_sync_ms = time.ticks_ms()
    except Exception:
        if panic_if_bad:
            # Retry multiple times if RTC is bad
            for _ in range(3):
                try:
                    ntpclient.settime()
                    _last_ntp_sync_ms = time.ticks_ms()
                    return
                except Exception:
                    time.sleep(1)
    print("NTP sync complete")

def ensure_wifi(
    ssid,
    password,
    timeout_ms_per_attempt=6000,
    max_interface_time_ms=15000,
    total_deadline_ms=60000,
    backoff_ms=400,
):
    if not wlan.active():
        wlan.active(True)
    if wlan.isconnected():
        return True

    start = time.ticks_ms()
    attempt = 0

    while True:
        attempt += 1
        try:
            wlan.connect(ssid, password)
        except Exception:
            pass

        att_start = time.ticks_ms()
        frame = 0

        while True:
            s = wlan.status()
            if s == STAT_GOT_IP or wlan.isconnected():
                _status_screen("WiFi", "connected")
                # Initial: force sync and panic if the RTC is bogus.
                try:
                    sync_clock(force=True, panic_if_bad=True)
                except Exception:
                    pass
                time.sleep(0.2)
                return True

            if s in (STAT_WRONG_PASS, STAT_NO_AP_FOUND, STAT_CONNECT_FAIL):
                msg = "wrong pass" if s == STAT_WRONG_PASS else ("no AP" if s == STAT_NO_AP_FOUND else "connect fail")
                _status_screen("WiFi error", msg)
                time.sleep(1.0)
                break

            _status_screen("WiFi", f"connecting {SPINNER_FRAMES[frame]}")
            frame = (frame + 1) % len(SPINNER_FRAMES)
            time.sleep(0.12)

            if time.ticks_diff(time.ticks_ms(), att_start) >= timeout_ms_per_attempt:
                break

            if time.ticks_diff(time.ticks_ms(), start) >= total_deadline_ms:
                _status_screen("WiFi timeout", "rebooting…")
                time.sleep(1.0)
                machine.reset()

        if time.ticks_diff(time.ticks_ms(), att_start) >= max_interface_time_ms:
            try: wlan.disconnect()
            except Exception: pass
            wlan.active(False)
            time.sleep(0.2)
            wlan.active(True)
            try: wlan.config(pm=0xA11140)
            except Exception: pass

        t_end = time.ticks_add(time.ticks_ms(), backoff_ms)
        while time.ticks_diff(t_end, time.ticks_ms()) > 0:
            _status_screen("retrying…", f"attempt {attempt}")
            time.sleep(0.12)
