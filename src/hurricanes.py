"""Parse HURDAT2 and count hurricanes per county.

Two measures:
  * passes: distinct hurricanes (1950-2025) whose track, interpolated hourly, came within
    60 nautical miles of the county's centroid while at hurricane strength (>= 64 kt).
  * landfalls: HURDAT2 landfall records ('L') at hurricane status (1851-2025), assigned
    to the county they fall in (or the nearest county within 25 km for points just offshore).
"""
from datetime import datetime, timedelta

from . import config
from .geo import haversine_km

TROPICAL = {"HU", "TS", "TD", "SS", "SD"}


def _coord(s):
    s = s.strip()
    v = float(s[:-1])
    return -v if s[-1] in "WS" else v


def parse_hurdat2(text):
    """Return list of storms: {id, name, year, points:[{t, rec, status, lat, lon, wind}]}."""
    storms = []
    current = None
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split(",")]
        if parts[0][:2].isalpha():  # header line, e.g. AL011851
            current = {"id": parts[0], "name": parts[1], "year": int(parts[0][4:8]), "points": []}
            storms.append(current)
            continue
        t = datetime.strptime(parts[0] + parts[1].zfill(4), "%Y%m%d%H%M")
        current["points"].append({
            "t": t,
            "rec": parts[2],
            "status": parts[3],
            "lat": _coord(parts[4]),
            "lon": _coord(parts[5]),
            "wind": int(parts[6]),
        })
    return storms


def interpolate(points, step_hours=1):
    """Linear interpolation between consecutive fixes. Yields (lon, lat, wind, tropical)."""
    for a, b in zip(points, points[1:]):
        hours = (b["t"] - a["t"]) / timedelta(hours=1)
        trop = a["status"] in TROPICAL and b["status"] in TROPICAL
        n = max(1, int(round(hours / step_hours)))
        for k in range(n):
            f = k / n
            yield (a["lon"] + f * (b["lon"] - a["lon"]),
                   a["lat"] + f * (b["lat"] - a["lat"]),
                   a["wind"] + f * (b["wind"] - a["wind"]),
                   trop)
    if points:
        p = points[-1]
        yield p["lon"], p["lat"], p["wind"], p["status"] in TROPICAL


def county_passes(storms, centroids, start_year=config.PASS_START_YEAR,
                  radius_km=config.PASS_RADIUS_KM):
    """centroids: {fips: (lon, lat)}. Returns {fips: {"hurricanes": n, "major": n, "storms": [ids]}}."""
    out = {f: {"hurricanes": 0, "major": 0, "storms": []} for f in centroids}
    # loose bbox around the counties to skip far-away storms fast
    lons = [c[0] for c in centroids.values()]
    lats = [c[1] for c in centroids.values()]
    pad = 2.5
    box = (min(lons) - pad, min(lats) - pad, max(lons) + pad, max(lats) + pad)
    for s in storms:
        if s["year"] < start_year:
            continue
        if not any(box[0] <= p["lon"] <= box[2] and box[1] <= p["lat"] <= box[3] for p in s["points"]):
            continue
        best_wind = {}
        for lon, lat, wind, trop in interpolate(s["points"]):
            if not trop or wind < config.HURRICANE_KT:
                continue
            if not (box[0] <= lon <= box[2] and box[1] <= lat <= box[3]):
                continue
            for f, (cx, cy) in centroids.items():
                if abs(cy - lat) > 1.2 or abs(cx - lon) > 1.4:
                    continue
                if haversine_km(lon, lat, cx, cy) <= radius_km:
                    best_wind[f] = max(best_wind.get(f, 0), wind)
        for f, w in best_wind.items():
            out[f]["hurricanes"] += 1
            out[f]["storms"].append(s["id"])
            if w >= config.MAJOR_KT:
                out[f]["major"] += 1
    return out


def county_landfalls(storms, index, snap_km=config.LANDFALL_SNAP_KM):
    """Returns ({fips: count}, list of landfall rows) for hurricane-strength landfalls."""
    counts = {}
    rows = []
    for s in storms:
        for p in s["points"]:
            if p["rec"] != "L" or p["status"] != "HU":
                continue
            fips = index.locate(p["lon"], p["lat"], snap_km=snap_km)
            if fips is None:
                continue
            counts[fips] = counts.get(fips, 0) + 1
            rows.append({"storm": s["id"], "name": s["name"], "year": s["year"],
                         "date": p["t"].strftime("%Y-%m-%d"), "fips": fips,
                         "wind_kt": p["wind"], "lon": p["lon"], "lat": p["lat"]})
    return counts, rows
