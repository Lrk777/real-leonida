"""Write the static dashboard (site/index.html) with the data embedded. No external libraries."""
import json
import math
import os

import pandas as pd

LAYERS = [
    # key, button label, unit text, decimals, part of chaos score?
    ("chaos_score", "Chaos score", "Reality Score (0-100, higher = more chaotic)", 0, False),
    ("hurricanes_per_decade", "Hurricanes", "hurricanes within 60 nm per decade", 1, True),
    ("sinkholes_per_1000km2", "Sinkholes", "sinkhole reports per 1,000 km²", 1, True),
    ("gators_per_10k_obs", "Alligators", "alligators per 10,000 wildlife sightings", 0, True),
    ("homicide_per_100k", "Homicide", "homicides per 100,000 residents", 1, True),
    ("crash_deaths_per_100k", "Crash deaths", "road deaths per 100,000 residents", 1, True),
    ("home_value", "Home prices", "typical home value (Zillow)", 0, False),
]

RAMP = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]  # sequential blue, light -> dark


def _project(features):
    xs, ys = [], []
    for f in features:
        for poly in _polys(f["geometry"]):
            for x, y in poly[0]:
                xs.append(x)
                ys.append(y)
    lon0, lon1, lat0, lat1 = min(xs), max(xs), min(ys), max(ys)
    k = math.cos(math.radians((lat0 + lat1) / 2))
    W = 900
    scale = W / ((lon1 - lon0) * k)
    H = (lat1 - lat0) * scale
    return lambda x, y: ((x - lon0) * k * scale, (lat1 - y) * scale), W, H


def _polys(g):
    return [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]


def _path(geom, proj):
    out = []
    for poly in _polys(geom):
        for ring in poly:
            pts, last = [], None
            for x, y in ring:
                px, py = proj(x, y)
                p = (round(px, 1), round(py, 1))
                if p != last:
                    pts.append(p)
                    last = p
            if len(pts) >= 3:
                out.append("M" + "L".join(f"{a},{b}" for a, b in pts) + "Z")
    return "".join(out)


def write_site(features, df, regions, findings, config):
    os.makedirs(config.SITE_DIR, exist_ok=True)
    proj, W, H = _project(features)
    paths = {f["id"]: _path(f["geometry"], proj) for f in features}
    region_of = {}
    for r in config.REGIONS:
        for c in r["counties"]:
            region_of.setdefault(c, []).append(r["region"])

    cols = ["fips", "name", "population", "hurricanes_1950_2025", "major_hurricanes_1950_2025", "hurricanes_per_decade",
            "landfalls_since_1851", "sinkholes", "sinkholes_per_1000km2", "alligator_obs", "all_obs",
            "gators_per_10k_obs", "homicide_per_100k", "crash_deaths_per_100k", "home_value", "home_value_change_pct",
            "chaos_score", "chaos_rank"] + [k + "_pct" for k in config.CHAOS_LAYERS]
    counties = []
    for r in df[cols].to_dict(orient="records"):
        r = {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in r.items()}
        r["path"] = paths[r["fips"]]
        r["regions"] = region_of.get(r["fips"], [])
        counties.append(r)

    regs = [{k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in r.items()}
            for r in regions.to_dict(orient="records")]
    for r in regs:
        r["fips"] = next(x["counties"] for x in config.REGIONS if x["region"] == r["region"])

    headlines_path = os.path.join("src", "headlines.json")
    headlines = json.load(open(headlines_path)) if os.path.exists(headlines_path) else []

    payload = {
        "W": round(W), "H": round(H), "counties": counties, "regions": regs,
        "layers": [{"key": k, "label": l, "unit": u, "dp": d, "chaos": c} for k, l, u, d, c in LAYERS],
        "ramp": RAMP, "headlines": headlines, "findings": findings,
    }
    with open(os.path.join(os.path.dirname(__file__), "template.html")) as fh:
        html = fh.read()
    html = html.replace("/*__DATA__*/null", json.dumps(payload, separators=(",", ":"), default=float))
    with open(os.path.join(config.SITE_DIR, "index.html"), "w") as fh:
        fh.write(html)
