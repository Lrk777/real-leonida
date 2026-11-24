"""Download every raw input once and record a SHA-256 manifest.

Run:  python -m src.fetch
Needs internet (GitHub Actions has it). Files land in data/raw/.
"""
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from . import config

UA = {"User-Agent": "real-leonida/1.0 (portfolio data project; github.com/Lrk777)"}


def get(url, params=None, retries=4):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as e:  # network hiccups / rate limits
            last = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"failed to fetch {url}: {last}")


def get_json(url, params=None):
    return json.loads(get(url, params).decode("utf-8"))


def fetch_sinkholes():
    """Page through the ArcGIS layer (1,000 records per page)."""
    feats, offset = [], 0
    while True:
        page = get_json(config.SOURCES["sinkholes"], {
            "where": "1=1",
            "outFields": "OBJECTID,REF_NUM,EVENT_DATE,TRUE_SINK,COUNTY,LONGDD,LATDD",
            "returnGeometry": "true",
            "outSR": "4326",
            "orderByFields": "OBJECTID",
            "resultOffset": offset,
            "resultRecordCount": 1000,
            "f": "json",
        })
        if "error" in page:
            raise RuntimeError(page["error"])
        batch = page.get("features", [])
        feats.extend(batch)
        if not batch or not page.get("exceededTransferLimit"):
            break
        offset += len(batch)
    expected = get_json(config.SOURCES["sinkholes"], {"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"]
    if len(feats) != expected:
        raise RuntimeError(f"sinkholes: got {len(feats)} of {expected}")
    return feats


def fetch_gbif():
    """iNaturalist research-grade observation counts per Florida county (GADM level 2):
    all species, and alligators only. Also resolves each GADM id to a county name."""
    base = config.SOURCES["gbif"]
    common = {"gadmGid": config.GBIF_FLORIDA_GID, "datasetKey": config.GBIF_INAT_DATASET,
              "limit": 0, "facet": "gadmLevel2Gid", "facetLimit": 100}
    all_obs = get_json(base, common)["facets"][0]["counts"]
    gators = get_json(base, {**common, "taxonKey": config.GBIF_ALLIGATOR_TAXON})["facets"][0]["counts"]
    names = {}
    for c in all_obs:
        r = get_json(base, {"gadmLevel2Gid": c["name"], "limit": 1})
        names[c["name"]] = r["results"][0]["gadm"]["level2"]["name"]
        time.sleep(0.2)
    g = {c["name"]: c["count"] for c in gators}
    return [{"gadm_gid": c["name"], "gadm_name": names[c["name"]],
             "all_obs": c["count"], "alligator_obs": g.get(c["name"], 0)} for c in all_obs]


def main():
    os.makedirs(config.RAW_DIR, exist_ok=True)
    manifest = {"retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "files": {}}

    def save(name, data, source):
        path = os.path.join(config.RAW_DIR, name)
        with open(path, "wb") as fh:
            fh.write(data)
        manifest["files"][name] = {"source": source, "bytes": len(data),
                                   "sha256": hashlib.sha256(data).hexdigest()}
        print(f"saved {name} ({len(data):,} bytes)")

    for key, name in [("hurdat2", "hurdat2.txt"), ("counties", "counties.geojson"),
                      ("population", "population.csv"), ("chr", "chr_2025.csv"), ("zhvi", "zhvi_county.csv")]:
        save(name, get(config.SOURCES[key]), config.SOURCES[key])

    sink = fetch_sinkholes()
    save("sinkholes.json", json.dumps(sink).encode(), config.SOURCES["sinkholes"])

    gbif = fetch_gbif()
    save("gbif_inat_florida.json", json.dumps(gbif, indent=1).encode(), config.SOURCES["gbif"])

    with open(os.path.join(config.RAW_DIR, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)


if __name__ == "__main__":
    main()
