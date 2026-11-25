"""Write the static dashboard (site/index.html) with the data embedded. No external libraries."""
import json
import math
import os
import shutil

from .missions import MISSIONS, THEMES

WEB = os.path.join(os.path.dirname(__file__), "web")
OPTIONAL = ["area_km2", "homicide_n", "crash_n"]  # used by the A/B tests; absent in old fixtures

LAYERS = [
    # key, button label, unit text, decimals, part of chaos score?
    ("chaos_score", "Difficulty", "difficulty score (0-100; ★ for every 20 points)", 0, False),
    ("hurricanes_per_decade", "Hurricanes", "hurricanes within 60 nm per decade", 1, True),
    ("sinkholes_per_1000km2", "Sinkholes", "sinkhole reports per 1,000 km²", 1, True),
    ("gators_per_10k_obs", "Alligators", "alligators per 10,000 wildlife sightings", 0, True),
    ("homicide_per_100k", "Homicide", "homicides per 100,000 residents", 1, True),
    ("crash_deaths_per_100k", "Road deaths", "road deaths per 100,000 residents", 1, True),
    ("home_value", "Home prices", "typical home value (Zillow)", 0, False),
    ("danger", "Danger (deaths)", "road deaths + homicides per 100,000 residents a year", 1, False),
    ("story_missions", "Story missions", "GTA 6 story missions set in the county", 0, False),
    ("biome", "Biomes", "data-driven hazard zone (k-means)", 0, False),
]

RAMP = ["#1d3f5c", "#1e6a8c", "#1c97b8", "#2ec4dd", "#a8f3ff"]  # sequential cyan for the dark neon theme: dim (low) -> bright (high)


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


def write_site(features, df, regions, findings, config, landfalls=None, headlines=None, tracks=None, biomes=None, seasons=None):
    os.makedirs(config.SITE_DIR, exist_ok=True)
    if biomes is None:
        from .analytics import biomes as _biomes
        biomes = _biomes(df, list(config.CHAOS_LAYERS))
    proj, W, H = _project(features)
    paths = {f["id"]: _path(f["geometry"], proj) for f in features}
    region_of = {}
    for r in config.REGIONS:
        for c in r["counties"]:
            region_of.setdefault(c, []).append(r["region"])

    cols = ["fips", "name", "population", "hurricanes_1950_2025", "major_hurricanes_1950_2025", "hurricanes_per_decade",
            "landfalls_since_1851", "sinkholes", "sinkholes_per_1000km2", "alligator_obs", "all_obs",
            "gators_per_10k_obs", "homicide_per_100k", "crash_deaths_per_100k", "home_value", "home_value_change_pct",
            "chaos_score", "chaos_rank"] + [k + "_pct" for k in config.CHAOS_LAYERS] + [c for c in OPTIONAL if c in df.columns]
    lf_by = {}
    if landfalls is not None and len(landfalls):
        strongest = (landfalls.sort_values("wind_kt", ascending=False)
                     .drop_duplicates(subset=["fips", "storm"]).sort_values(["wind_kt", "year"], ascending=[False, False]))
        for row in strongest.itertuples():
            name = row.name.title() if row.name != "UNNAMED" else "Unnamed"
            lf_by.setdefault(row.fips, []).append([name, int(row.year), int(row.wind_kt)])
    counties = []
    for r in df[cols].to_dict(orient="records"):
        r = {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in r.items()}
        r["path"] = paths[r["fips"]]
        r["regions"] = region_of.get(r["fips"], [])
        r["landfalls"] = lf_by.get(r["fips"], [])
        r["biome"] = biomes["labels"].get(r["fips"])
        cd, hm = r.get("crash_deaths_per_100k"), r.get("homicide_per_100k")
        r["danger"] = None if cd is None else round(cd + (hm or 0), 2)
        r["story_missions"] = sum(ch["missions"] for ch in getattr(config, "CHAPTERS", []) if ch["fips"] == r["fips"]) or None
        if seasons:
            r["dec"] = seasons["county"].get(r["fips"])
        counties.append(r)

    regs = [{k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in r.items()}
            for r in regions.to_dict(orient="records")]
    for r in regs:
        r["fips"] = next(x["counties"] for x in config.REGIONS if x["region"] == r["region"])

    headlines = headlines or []

    storm_tracks = []
    for t in tracks or []:
        pts = [[round(x, 1), round(y, 1), int(w)] for x, y, w in ((*proj(lon, lat), w) for lon, lat, w in t["pts"])]
        lf = [[round(x, 1), round(y, 1), int(w)] for x, y, w in ((*proj(lon, lat), w) for lon, lat, w in t.get("lf", []))]
        storm_tracks.append({**{k: t[k] for k in ("id", "name", "year", "landfall_kt", "counties")}, "pts": pts, "lf": lf})

    payload = {
        "tracks": storm_tracks,
        "W": round(W), "H": round(H), "counties": counties, "regions": regs,
        "layers": [{"key": k, "label": l, "unit": u, "dp": d, "chaos": c} for k, l, u, d, c in LAYERS],
        "ramp": RAMP, "headlines": headlines, "findings": findings,
        "chapters": getattr(config, "CHAPTERS", []),
        "missions": [{"ch": c, "name": n, "what": w, "theme": t} for c, n, w, t in MISSIONS],
        "themes": THEMES,
        "biomes": {k: biomes[k] for k in ("clusters", "k", "silhouette", "features")},
        "seasons": {k: seasons[k] for k in ("labels", "years", "fl_pass", "fl_major_lf")} if seasons else None,
    }
    with open(os.path.join(WEB, "index.html")) as fh:
        html = fh.read()
    html = html.replace("/*__DATA__*/null", json.dumps(payload, separators=(",", ":"), default=float))
    with open(os.path.join(config.SITE_DIR, "index.html"), "w") as fh:
        fh.write(html)
    for asset in ("style.css", "app.js"):
        shutil.copy(os.path.join(WEB, asset), os.path.join(config.SITE_DIR, asset))
