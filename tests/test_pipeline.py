"""End-to-end run of the build on synthetic raw files (no network)."""
import csv
import json
import os

from src import build

NAMES = ["Alachua","Baker","Bay","Bradford","Brevard","Broward","Calhoun","Charlotte","Citrus","Clay","Collier",
 "Columbia","DeSoto","Dixie","Duval","Escambia","Flagler","Franklin","Gadsden","Gilchrist","Glades","Gulf","Hamilton",
 "Hardee","Hendry","Hernando","Highlands","Hillsborough","Holmes","Indian River","Jackson","Jefferson","Lafayette",
 "Lake","Lee","Leon","Levy","Liberty","Madison","Manatee","Marion","Martin","Miami-Dade","Monroe","Nassau","Okaloosa",
 "Okeechobee","Orange","Osceola","Palm Beach","Pasco","Pinellas","Polk","Putnam","St. Johns","St. Lucie","Santa Rosa",
 "Sarasota","Seminole","Sumter","Suwannee","Taylor","Union","Volusia","Wakulla","Walton","Washington"]
CODES = [f"{i:03d}" for i in range(1, 134, 2) if i != 25]
CODES = sorted(CODES[:42] + ["086"] + CODES[42:])[:67]


def make_raw(root):
    raw = os.path.join(root, "data", "raw"); os.makedirs(raw)
    fips = ["12" + c for c in CODES]
    # 67 small squares on a grid over Florida + one Georgia county
    feats = []
    for i, f in enumerate(fips):
        x0, y0 = -87.5 + (i % 12) * 0.6, 25.0 + (i // 12) * 0.9
        feats.append({"type": "Feature", "id": f, "properties": {}, "geometry": {"type": "Polygon",
                      "coordinates": [[[x0, y0], [x0 + .6, y0], [x0 + .6, y0 + .9], [x0, y0 + .9], [x0, y0]]]}})
    feats.append({"type": "Feature", "id": "13001", "properties": {}, "geometry": {"type": "Polygon",
                  "coordinates": [[[-85, 31.5], [-84, 31.5], [-84, 32], [-85, 32], [-85, 31.5]]]}})
    json.dump({"type": "FeatureCollection", "features": feats}, open(os.path.join(raw, "counties.geojson"), "w"))
    with open(os.path.join(raw, "population.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["SUMLEV", "STATE", "COUNTY", "CTYNAME", "POPESTIMATE2024"])
        w.writerow(["040", "12", "000", "Florida", "23000000"])
        for i, (c, n) in enumerate(zip(CODES, NAMES)):
            w.writerow(["050", "12", c, n + " County", 10000 + i * 1000])
    with open(os.path.join(raw, "chr_2025.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["State FIPS Code", "County FIPS Code", "5-digit FIPS Code", "Homicides raw value",
                    "Homicides numerator", "Motor Vehicle Crash Deaths raw value"])
        w.writerow(["statecode", "countycode", "fipscode", "v015_rawvalue", "v015_numerator", "v039_rawvalue"])
        w.writerow(["12", "000", "12000", "7", "1000", "15"])
        for i, c in enumerate(CODES):
            w.writerow(["12", c, "12" + c, "" if i % 9 == 0 else i % 13, i, 10 + i % 17])
    with open(os.path.join(raw, "zhvi_county.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["RegionName", "StateCodeFIPS", "MunicipalCodeFIPS", "2021-10-31", "2026-09-30", "2026-10-31"])
        for i, c in enumerate(CODES):
            w.writerow([f"C{c}", "12", c, 200000, 300000, 300000 + i * 1000])
    sinks = [{"attributes": {"REF_NUM": f"r{i}", "COUNTY": "DADE" if i == 0 else "", "EVENT_DATE": 600000000000,
                             "LONGDD": None, "LATDD": None},
              "geometry": {"x": -87.2 + (i % 12) * 0.6, "y": 25.3 + (i // 12) * 0.9}} for i in range(60)]
    sinks[0]["geometry"] = None  # falls back to the county field
    json.dump(sinks, open(os.path.join(raw, "sinkholes.json"), "w"))
    gad = {"Desoto": "DeSoto", "Saint Johns": "St. Johns", "Saint Lucie": "St. Lucie"}
    inv = {v: k for k, v in gad.items()}
    json.dump([{"gadm_gid": f"g{i}", "gadm_name": inv.get(n, n), "all_obs": 1000 + i, "alligator_obs": i}
               for i, n in enumerate(NAMES)], open(os.path.join(raw, "gbif_inat_florida.json"), "w"))
    storm = ["AL012025,               TEST,     3,", "20250901, 0000,  , HU, 25.2N,  86.0W, 100,  950,",
             "20250901, 0600, L, HU, 25.4N,  87.0W, 100,  950,", "20250901, 0700, L, HU, 25.5N,  87.1W,  95,  952,",
             "20250901, 1200,  , HU, 25.6N,  87.9W,  80,  960,"]
    filler = "\n".join(f"AL{n:02d}{1900 + n // 10},  X,  1,\n{1900 + n // 10}0101, 0000,  , TS, 10.0N,  40.0W,  30, -999," for n in range(1, 1950))
    open(os.path.join(raw, "hurdat2.txt"), "w").write(filler + "\n" + "\n".join(storm) + "\n")


def test_build_end_to_end(tmp_path, monkeypatch):
    make_raw(tmp_path)
    monkeypatch.chdir(tmp_path)
    build.main()
    out = tmp_path / "outputs"
    rows = list(csv.DictReader(open(out / "county_metrics.csv")))
    assert len(rows) == 67
    assert all(0 <= float(r["chaos_score"]) <= 100 for r in rows)
    dq = list(csv.DictReader(open(out / "dq_report.csv")))
    assert all(r["passed"] == "True" for r in dq if r["severity"] == "hard")
    regions = list(csv.DictReader(open(out / "region_scores.csv")))
    assert {r["region"] for r in regions} == {"Vice City", "Leonida Keys", "Grassrivers", "Ambrosia", "Port Gellhorn", "Mount Kalaga"}
    html = open(tmp_path / "site" / "index.html").read()
    assert "/*__DATA__*/null" not in html and '"counties"' in html
    readme = open(tmp_path / "README.md").read()
    assert "| Vice City |" in readme and "nan" not in readme.lower().replace("nanc", "")
    lf = list(csv.DictReader(open(out / "florida_hurricane_landfalls.csv")))
    assert len(lf) == 2 and {r["name"] for r in lf} == {"TEST"}  # two landfall records...
    first = next(r for r in rows if r["fips"] == "12001")
    assert first["landfalls_since_1851"] == "1"                     # ...but one storm
    payload = json.loads(html.split("const D = ", 1)[1].split(";\n", 1)[0])
    assert all(t["lf"] and len(t["lf"][0]) == 3 for t in payload["tracks"])  # replay gets landfall markers
