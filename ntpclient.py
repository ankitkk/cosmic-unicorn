# ntpclient.py
# Lightweight NTP client for MicroPython (sets RTC directly)

import socket
import struct
import time
import machine

NTP_DELTA = 2208988800  # seconds between 1900 and 1970
NTP_PORT = 123
NTP_PACKET = b'\x1b' + 47 * b'\0'

DEFAULT_SERVERS = (
    "pool.ntp.org",
    "time.google.com",
    "time.cloudflare.com",
)

def get_ntp_time(host="pool.ntp.org", timeout=3):
    addr = socket.getaddrinfo(host, NTP_PORT)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        s.sendto(NTP_PACKET, addr)
        msg = s.recv(48)
    finally:
        s.close()

    val = struct.unpack("!I", msg[40:44])[0]
    return val - NTP_DELTA  # seconds since 1970 UTC

def settime(servers=DEFAULT_SERVERS):
    """
    Tries multiple servers until success. Sets Pico's RTC in UTC.
    """
    rtc = machine.RTC()
    last_error = None
    for server in servers:
        try:
            t = get_ntp_time(server)
            tm = time.gmtime(t)
            rtc.datetime((tm[0], tm[1], tm[2], tm[6]+1, tm[3], tm[4], tm[5], 0))
            return True
        except Exception as e:
            last_error = e
            time.sleep(0.5)
    raise last_error
