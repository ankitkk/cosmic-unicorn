 # cta_api.py
# CTA Bus Tracker: fetch predictions for a stop/route and format minutes.

import urequests as requests
import gc

CTA_API_BASE = "http://www.ctabustracker.com/bustime/api/v2/getpredictions"
_DEF_HEADERS = {"Connection": "close"}


def fetch_predictions(api_key, stpid, rt):
    """
    Fetch predictions for a given stop id (stpid) and route (rt).

    Returns:
      None on network/parse failure, or
      {"error": "message"} if API returned an error, or
      {"preds": [...]} where each item is a CTA prediction dict.
    """
    url = f"{CTA_API_BASE}?key={api_key}&stpid={stpid}&rt={rt}&format=json"
    resp = None
    try:
        resp = requests.get(url, headers=_DEF_HEADERS)
        data = resp.json()
    except Exception:
        _cleanup(resp)
        return None
    finally:
        _cleanup(resp)

    bustime = data.get("bustime-response", {}) or {}
    if "error" in bustime:
        # Typically a list of { "msg": "..." }
        try:
            msg = bustime["error"][0].get("msg", "API error")
        except Exception:
            msg = "API error"
        return {"error": msg}
    return {"preds": bustime.get("prd", [])}


def extract_minutes_list(preds, rtdir=None, max_items=5):
    """
    Extract a compact list of countdown tokens (strings) from predictions.
    If rtdir is given, filter to that direction ("Southbound", "Westbound", etc).
    """
    if not preds:
        return ["NOA"]
    if rtdir:
        preds = [p for p in preds if p.get("rtdir") == rtdir]
    out = []
    for p in preds[:max_items]:
        cd = p.get("prdctdn", "?")
        # CTA sends "DUE", "DLY", "??", or minute numbers as strings
        if isinstance(cd, str) and cd.isdigit():
            v = min(int(cd), 99)
            out.append(str(v))
        else:
            out.append(str(cd).upper())
    return out or ["NOA"]


def token3(s):
    """
    Normalize a token to exactly 3 characters:
    - right-aligned numeric minutes (cap at 99)
    - canonical "DUE", "DLY", "NOA"
    - otherwise first 3 chars uppercased
    """
    if s is None:
        return "NOA"
    s = str(s).strip().upper()
    if s in ("", "-", "—"):
        return "NOA"
    if s.isdigit():
        n = min(int(s), 99)
        return f"{n:>3}"
    if s.startswith("DU"):
        return "DUE"
    if s.startswith("DL"):
        return "DLY"
    if s.startswith("NO"):
        return "NOA"
    return (s + "   ")[:3]


def _cleanup(resp):
    try:
        if resp:
            resp.close()
    except Exception:
        pass
    gc.collect()
