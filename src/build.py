"""Turn the raw files into county metrics, region Reality Scores and findings.

Run:  python -m src.build      (after python -m src.fetch)
Writes outputs/*.csv|json and site/index.html.
"""
import json
import os
import re
from datetime import datetime, timedelta

import pandas as pd

from . import config
from .geo import CountyIndex, area_centroid
from .hurricanes import county_landfalls, county_passes, parse_hurdat2

RAW = config.RAW_DIR
OUT = config.OUT_DIR


def norm(name):
    """Normalise county names across sources: 'St. Johns County' / 'Saint Johns' / 'DeSoto' -> 'stjohns' / 'desoto'."""
    n = name.strip().lower().replace(" county", "")
    if n == "dade":
        n = "miami-dade"
    n = re.sub(r"^(saint|st\.?)\s+", "st", n)
    return re.sub(r"[^a-z]", "", n)


class DQ:
    """Collects data-quality checks. Hard failures stop the build; soft ones are reported."""

    def __init__(self):
        self.rows = []

    def check(self, name, ok, detail="", hard=True):
        self.rows.append({"check": name, "passed": bool(ok), "severity": "hard" if hard else "soft", "detail": detail})
        if hard and not ok:
            raise AssertionError(f"DQ FAIL {name}: {detail}")


def load_counties(dq):
    with open(os.path.join(RAW, "counties.geojson")) as fh:
        gj = json.load(fh)
    all_feats = gj["features"]
    fl = [f for f in all_feats if f["id"].startswith(config.STATE_FIPS)]
    dq.check("67 Florida counties in shapes", len(fl) == 67, f"found {len(fl)}")
    rows = []
    for f in fl:
        area, cx, cy = area_centroid(f["geometry"])
        rows.append({"fips": f["id"], "area_km2": area, "cen_lon": cx, "cen_lat": cy})
    return all_feats, fl, pd.DataFrame(rows)


def load_population(dq):
    df = pd.read_csv(os.path.join(RAW, "population.csv"), encoding="latin1", dtype=str)
    df = df[(df.STATE == config.STATE_FIPS) & (df.COUNTY != "000")].copy()
    df["fips"] = df.STATE + df.COUNTY
    df["name"] = df.CTYNAME.str.replace(" County", "", regex=False)
    df["population"] = df.POPESTIMATE2024.astype(int)
    dq.check("population: 67 counties", len(df) == 67, f"found {len(df)}")
    dq.check("population: all positive", (df.population > 0).all())
    return df[["fips", "name", "population"]]


def load_chr(dq):
    df = pd.read_csv(os.path.join(RAW, "chr_2025.csv"), dtype=str, skiprows=[1])
    df = df[(df["State FIPS Code"] == config.STATE_FIPS) & (df["County FIPS Code"] != "000")].copy()
    df["fips"] = df["5-digit FIPS Code"]
    df["homicide_per_100k"] = pd.to_numeric(df["Homicides raw value"], errors="coerce")
    df["homicide_n"] = pd.to_numeric(df["Homicides numerator"], errors="coerce")
    df["crash_deaths_per_100k"] = pd.to_numeric(df["Motor Vehicle Crash Deaths raw value"], errors="coerce")
    # raw death counts (numerators) let the dashboard's A/B tests put confidence ranges on rate differences
    num = "Motor Vehicle Crash Deaths numerator"
    df["crash_n"] = pd.to_numeric(df[num], errors="coerce") if num in df.columns else float("nan")
    dq.check("CHR: 67 counties", len(df) == 67, f"found {len(df)}")
    dq.check("CHR: crash-death rate present for every county", df.crash_deaths_per_100k.notna().all(),
             f"{df.crash_deaths_per_100k.isna().sum()} missing", hard=False)
    dq.check("CHR: homicide rate present", df.homicide_per_100k.notna().sum() >= 60,
             f"{df.homicide_per_100k.isna().sum()} suppressed (small counts)", hard=False)
    return df[["fips", "homicide_per_100k", "homicide_n", "crash_deaths_per_100k", "crash_n"]]


def load_zhvi(dq):
    df = pd.read_csv(os.path.join(RAW, "zhvi_county.csv"), dtype={"StateCodeFIPS": str, "MunicipalCodeFIPS": str})
    df = df[df.StateCodeFIPS.str.zfill(2) == config.STATE_FIPS].copy()
    df["fips"] = df.StateCodeFIPS.str.zfill(2) + df.MunicipalCodeFIPS.str.zfill(3)
    months = [c for c in df.columns if re.match(r"\d{4}-\d{2}-\d{2}", c)]
    latest = months[-1]
    y, m = int(latest[:4]), latest[5:7]
    past = next(c for c in months if c.startswith(f"{y - config.HOUSING_YEARS_BACK}-{m}"))
    df["home_value"] = df[latest]
    df["home_value_change_pct"] = (df[latest] / df[past] - 1) * 100
    dq.check("Zillow: Florida counties covered", len(df) >= 60, f"{len(df)} counties", hard=False)
    return df[["fips", "home_value", "home_value_change_pct"]], latest, past


def load_sinkholes(index, names, dq):
    with open(os.path.join(RAW, "sinkholes.json")) as fh:
        feats = json.load(fh)
    rows = []
    for f in feats:
        a = f["attributes"]
        g = f.get("geometry") or {}
        lon, lat = g.get("x", a.get("LONGDD")), g.get("y", a.get("LATDD"))
        fips = index.locate(lon, lat, snap_km=5) if lon is not None and lat is not None else None
        rows.append({"ref": a.get("REF_NUM"), "county_field": (a.get("COUNTY") or "").strip(),
                     "lon": lon, "lat": lat, "fips": fips,
                     "year": (datetime(1970, 1, 1) + timedelta(milliseconds=a["EVENT_DATE"])).year if a.get("EVENT_DATE") else None})
    df = pd.DataFrame(rows)
    dups = df.ref.notna() & df.duplicated(subset=["ref", "lon", "lat"], keep="first")
    dq.check("sinkholes: exact duplicate reports removed", True, f"{int(dups.sum())} removed", hard=False)
    df = df[~dups].copy()
    dq.check("sinkholes: report numbers unique after de-duplication", not df.ref.dropna().duplicated().any(),
             f"{df.ref.dropna().duplicated().sum()} report numbers reused at different locations (kept)", hard=False)
    # fall back to the county field when the point is missing / outside Florida
    lookup = {norm(n): f for f, n in names.items()}
    miss = df.fips.isna()
    df.loc[miss, "fips"] = df.loc[miss, "county_field"].map(lambda c: lookup.get(norm(c)) if c else None)
    located = df.fips.notna().mean()
    dq.check("sinkholes: >= 98% assigned to a county", located >= 0.98, f"{located:.1%} assigned")
    # agreement between point-in-polygon and the agency's county field (quality signal)
    both = df[df.county_field.ne("") & df.fips.notna()]
    agree = (both.county_field.map(lambda c: lookup.get(norm(c))) == both.fips).mean()
    dq.check("sinkholes: point location agrees with county field", agree >= 0.9, f"{agree:.1%} agree", hard=False)
    return df


def load_gbif(names, dq):
    with open(os.path.join(RAW, "gbif_inat_florida.json")) as fh:
        g = pd.DataFrame(json.load(fh))
    lookup = {norm(n): f for f, n in names.items()}
    g["fips"] = g.gadm_name.map(lambda n: lookup.get(norm(n)))
    dq.check("GBIF: every county name matched", g.fips.notna().all(),
             f"unmatched: {g.loc[g.fips.isna(), 'gadm_name'].tolist()}")
    dq.check("GBIF: 67 counties", g.fips.nunique() == 67, f"{g.fips.nunique()}")
    g["gators_per_10k_obs"] = g.alligator_obs / g.all_obs * 10000
    return g[["fips", "all_obs", "alligator_obs", "gators_per_10k_obs"]]


REGION_OF = {c: r["region"] for r in config.REGIONS for c in r["counties"]}


def _in_game(fips):
    r = [x["region"] for x in config.REGIONS if fips in x["counties"]]
    return f" (GTA 6: {' / '.join(r)})" if r else ""


def headlines(df, reg, min_obs=20000):
    """Plain-English headline cards, computed from the data so they stay true after every rebuild."""
    out = []
    n = len(df)
    top = reg.iloc[0]
    worst_c = df[df.fips.isin(next(r["counties"] for r in config.REGIONS if r["region"] == top.region))].iloc[0]
    out.append({"big": f"{top.region} is the real chaos capital",
                "text": f"Its real counties ({top.counties}) score {top.reality_score:.0f}/100, the highest of the six regions. "
                        f"{worst_c['name']} is #{int(worst_c.chaos_rank)} of {n} Florida counties."})
    vc = df[df.fips == "12086"].iloc[0]
    rk = lambda col: int(df[col].rank(ascending=False, method="min")[df.fips == "12086"].iloc[0])
    out.append({"big": f"Real Vice City ranks #{int(vc.chaos_rank)} of {n}",
                "text": f"Miami-Dade scores {vc.chaos_score:.0f}/100, close to a typical Florida county. Homicide rate: #{rk('homicide_per_100k')} of "
                        f"{int(df.homicide_per_100k.notna().sum())}. Road deaths: #{rk('crash_deaths_per_100k')} of {n}. Home prices: #{rk('home_value')}."})
    lf = df.nlargest(1, "landfalls_since_1851").iloc[0]
    out.append({"big": f"{int(lf.landfalls_since_1851)} hurricanes came ashore",
                "text": f"More hurricanes have made landfall in {lf['name']} County{_in_game(lf.fips)} since 1851 than in any other Florida county."})
    sk = df.nlargest(1, "sinkholes_per_1000km2").iloc[0]
    sk_regions = [c for c in df.nlargest(5, "sinkholes_per_1000km2").fips if c in REGION_OF]
    out.append({"big": f"{sk.sinkholes_per_1000km2:.0f} sinkholes per 1,000 km²",
                "text": f"{sk['name']} County{_in_game(sk.fips)} leads Florida for reported sinkholes. "
                        + ("None of the top 5 sinkhole counties is in a GTA 6 region." if not sk_regions
                           else "")})
    big = df[df.all_obs >= min_obs]
    if big.empty:  # tiny test datasets
        big, min_obs = df, 0
    g = big.nlargest(1, "gators_per_10k_obs").iloc[0]
    out.append({"big": f"1 in {10000 / g.gators_per_10k_obs:.0f} wildlife sightings is a gator",
                "text": f"In {g['name']} County{_in_game(g.fips)}, alligators make up {g.gators_per_10k_obs / 100:.1f}% of all iNaturalist wildlife observations, "
                        f"the most of any county with {min_obs:,}+ observations."})
    return out


def pct_rank(s):
    return s.rank(pct=True, method="average") * 100


def main():
    os.makedirs(OUT, exist_ok=True)
    dq = DQ()

    all_feats, fl_feats, shapes = load_counties(dq)
    pop = load_population(dq)
    names = dict(zip(pop.fips, pop.name))
    fl_index = CountyIndex(fl_feats)
    us_index = CountyIndex(all_feats)

    # Hurricanes
    with open(os.path.join(RAW, "hurdat2.txt")) as fh:
        storms = parse_hurdat2(fh.read())
    dq.check("HURDAT2: parsed storms", len(storms) > 1900, f"{len(storms)} storms")
    dq.check("HURDAT2: latest season present", max(s["year"] for s in storms) >= 2025)
    centroids = {r.fips: (r.cen_lon, r.cen_lat) for r in shapes.itertuples()}
    passes = county_passes(storms, centroids)
    lf_counts, lf_rows = county_landfalls(storms, us_index)
    lf = pd.DataFrame(lf_rows)
    lf_fl = lf[lf.fips.str.startswith(config.STATE_FIPS)] if len(lf) else lf
    years = 2025 - config.PASS_START_YEAR + 1
    hur = pd.DataFrame([{"fips": f, "hurricanes_1950_2025": v["hurricanes"], "major_hurricanes_1950_2025": v["major"]}
                        for f, v in passes.items()])
    hur["hurricanes_per_decade"] = hur.hurricanes_1950_2025 / years * 10
    # a storm can cross several Keys and log more than one landfall record: count distinct storms
    lf_storms = lf_fl.groupby("fips").storm.nunique() if len(lf_fl) else pd.Series(dtype=int)
    hur["landfalls_since_1851"] = hur.fips.map(lf_storms).fillna(0).astype(int)

    sink = load_sinkholes(fl_index, names, dq)
    sk = sink.groupby("fips").size().rename("sinkholes").reset_index()

    gb = load_gbif(names, dq)
    chr_ = load_chr(dq)
    zh, zh_latest, zh_past = load_zhvi(dq)

    df = (pop.merge(shapes, on="fips").merge(hur, on="fips").merge(sk, on="fips", how="left")
          .merge(gb, on="fips", how="left").merge(chr_, on="fips", how="left").merge(zh, on="fips", how="left"))
    df["sinkholes"] = df.sinkholes.fillna(0).astype(int)
    df["sinkholes_per_1000km2"] = df.sinkholes / df.area_km2 * 1000
    dq.check("joined table: 67 rows, unique FIPS", len(df) == 67 and df.fips.is_unique)

    for col in config.CHAOS_LAYERS:
        df[col + "_pct"] = pct_rank(df[col])
    pct_cols = [c + "_pct" for c in config.CHAOS_LAYERS]
    df["layers_available"] = df[pct_cols].notna().sum(axis=1)
    df["chaos_score"] = df[pct_cols].mean(axis=1)
    df["chaos_rank"] = df.chaos_score.rank(ascending=False, method="min").astype(int)
    df["home_value_pct"] = pct_rank(df.home_value)
    df = df.sort_values("chaos_rank")

    # Regions
    reg_rows = []
    for r in config.REGIONS:
        sub = df[df.fips.isin(r["counties"])]
        row = {"region": r["region"], "inspiration": r["inspiration"], "confidence": r["confidence"],
               "counties": ", ".join(sub.name), "population": int(sub.population.sum()),
               "reality_score": sub.chaos_score.mean()}
        for col in config.CHAOS_LAYERS:
            row[col + "_pct"] = sub[col + "_pct"].mean()
        reg_rows.append(row)
    reg = pd.DataFrame(reg_rows).sort_values("reality_score", ascending=False)

    # Findings (plain facts computed from the table; the README words them)
    top = lambda col, n=5: df.nlargest(n, col)[["name", col]].round(2).values.tolist()
    mia = df[df.fips == "12086"].iloc[0]
    findings = {
        "data_window": {"hurricane_passes": f"{config.PASS_START_YEAR}-2025", "landfalls": "1851-2025",
                        "zillow_latest": zh_latest, "zillow_compared_with": zh_past},
        "statewide": {
            "hurricanes_making_landfall_in_florida_since_1851": int(lf_fl.storm.nunique()) if len(lf_fl) else 0,
            "sinkhole_reports": int(len(sink)),
            "inat_alligator_obs": int(df.alligator_obs.sum()),
            "inat_all_obs": int(df.all_obs.sum()),
        },
        "most_chaotic_counties": df.head(10)[["name", "chaos_score"]].round(1).values.tolist(),
        "least_chaotic_counties": df.tail(5)[["name", "chaos_score"]].round(1).values.tolist(),
        "top_hurricanes_per_decade": top("hurricanes_per_decade"),
        "top_major_hurricanes": top("major_hurricanes_1950_2025"),
        "top_landfalls": top("landfalls_since_1851"),
        "top_sinkholes_per_1000km2": top("sinkholes_per_1000km2"),
        "top_gators_per_10k_obs": top("gators_per_10k_obs"),
        "top_homicide_per_100k": top("homicide_per_100k"),
        "top_crash_deaths_per_100k": top("crash_deaths_per_100k"),
        "top_home_value": top("home_value"),
        "miami_dade": {
            "chaos_rank": int(mia.chaos_rank), "chaos_score": round(mia.chaos_score, 1),
            **{c: (None if pd.isna(mia[c]) else round(float(mia[c]), 2)) for c in config.CHAOS_LAYERS},
            **{c + "_rank": int(df[c].rank(ascending=False, method="min")[df.fips == "12086"].iloc[0])
               for c in config.CHAOS_LAYERS},
            "home_value": round(float(mia.home_value), 0),
            "home_value_rank": int(df.home_value.rank(ascending=False, method="min")[df.fips == "12086"].iloc[0]),
        },
        "regions": reg.round(1).to_dict(orient="records"),
        "florida_median": {c: round(float(df[c].median()), 2) for c in list(config.CHAOS_LAYERS) + ["home_value"]},
    }

    # Write outputs
    keep = ["fips", "name", "population", "area_km2", "hurricanes_1950_2025", "major_hurricanes_1950_2025",
            "hurricanes_per_decade", "landfalls_since_1851", "sinkholes", "sinkholes_per_1000km2", "all_obs",
            "alligator_obs", "gators_per_10k_obs", "homicide_n", "homicide_per_100k", "crash_deaths_per_100k",
            "home_value", "home_value_change_pct", "crash_n"] + pct_cols + ["home_value_pct", "layers_available",
                                                               "chaos_score", "chaos_rank"]
    df[keep].round(3).to_csv(os.path.join(OUT, "county_metrics.csv"), index=False)
    reg.round(2).to_csv(os.path.join(OUT, "region_scores.csv"), index=False)
    if len(lf_fl):
        lf_fl.sort_values("date").to_csv(os.path.join(OUT, "florida_hurricane_landfalls.csv"), index=False)

    # Dev Mode models: k-means "biomes" on the hazard percentiles, and hurricanes per decade ("seasons")
    from .analytics import biomes, seasons
    bio = biomes(df, list(config.CHAOS_LAYERS))
    sea = seasons(passes, storms, lf_fl)
    dq.check("biomes: every county clustered", len(bio["labels"]) == 67, f"k={bio['k']}, silhouette={bio['silhouette']}", hard=False)
    findings["biomes"] = {"k": bio["k"], "silhouette": bio["silhouette"],
                          "clusters": [{k: c[k] for k in ("name", "size", "centroid")} for c in bio["clusters"]]}
    findings["seasons"] = {k: sea[k] for k in ("labels", "years", "fl_pass", "fl_major_lf")}

    heads = headlines(df, reg)
    findings["headlines"] = heads
    pd.DataFrame(dq.rows).to_csv(os.path.join(OUT, "dq_report.csv"), index=False)
    with open(os.path.join(OUT, "findings.json"), "w") as fh:
        json.dump(findings, fh, indent=2, default=float)

    # Site data: county paths + metrics
    from .site import write_site
    # Tracks of every major hurricane (Cat 3+ at landfall) to hit Florida since 1950, for the map overlay
    major_ids = set(lf_fl[(lf_fl.wind_kt >= config.MAJOR_KT) & (lf_fl.year >= config.PASS_START_YEAR)].storm) if len(lf_fl) else set()
    tracks = []
    for s in storms:
        if s["id"] in major_ids:
            fl_pts = lf_fl[lf_fl.storm == s["id"]]
            tracks.append({"id": s["id"], "name": s["name"].title(), "year": s["year"],
                           "landfall_kt": int(fl_pts.wind_kt.max()),
                           "counties": sorted(set(names[f] for f in fl_pts.fips)),
                           "lf": [[r.lon, r.lat, int(r.wind_kt)] for r in fl_pts.itertuples()],
                           "pts": [[p["lon"], p["lat"], p["wind"]] for p in s["points"]]})
    tracks.sort(key=lambda t: t["year"])
    write_site(fl_feats, df, reg, findings, config, landfalls=lf_fl, headlines=heads, tracks=tracks,
               biomes=bio, seasons=sea)
    from .readme import write_readme
    write_readme(df, reg, heads, findings, dq.rows)
    print(f"built: {len(df)} counties, {len(reg)} regions, {sum(r['passed'] for r in dq.rows)}/{len(dq.rows)} DQ checks passed")


if __name__ == "__main__":
    main()
