"""Write README.md from the latest outputs, so every number in it comes from the last run."""
import os

from . import config

PAGES = "https://lrk777.github.io/real-leonida/"


def _verdict(s):
    return "Not exaggerated" if s >= 60 else "Fair" if s >= 45 else "Exaggerated"


def write_readme(df, reg, heads, findings, dq_rows, path="README.md"):
    n = len(df)
    reg_rows = "\n".join(
        f"| {r.region} | {r.inspiration} | {r.counties} | {r.reality_score:.0f} | {_verdict(r.reality_score)} | {r.confidence} |"
        for r in reg.itertuples())
    top10 = "\n".join(f"| {int(r.chaos_rank)} | {r.name} | {r.chaos_score:.0f} |" for r in df.head(10).itertuples())
    calm5 = ", ".join(f"{r.name} ({r.chaos_score:.0f})" for r in df.tail(5).iloc[::-1].itertuples())
    heads_md = "\n".join(f"- **{h['big']}.** {h['text']}" for h in heads)
    hard = [r for r in dq_rows if r["severity"] == "hard"]
    soft_notes = "\n".join(f"- {r['check']}: {r['detail']}" for r in dq_rows if r["severity"] == "soft" and r["detail"])
    dw = findings["data_window"]
    text = f"""# Real Leonida: is GTA 6's Florida exaggerated?

GTA 6 (Nov 2026) is set in Leonida, Rockstar's parody of Florida. This project matches each of the game's six regions to the real counties behind them and scores all {n} Florida counties on five kinds of real-world chaos: hurricanes, sinkholes, alligators, homicide and road deaths.

**Live dashboard:** {PAGES}

What you can do there:

- Switch the Florida map between 8 layers (Reality Score, hurricanes, sinkholes, alligators, homicide, road deaths, home prices, your match) and click any county for its full profile, ranks and the strongest hurricanes that hit it.
- Replay the track of every major hurricane (Cat 3+) to make landfall in Florida since 1950, one by one, or pick a single storm.
- Use "Find your calm corner of Leonida": set how much you care about each risk and a budget, and get the best-matching counties.
- Compare the six GTA 6 regions on scorecards with a verdict (exaggerated / fair / not exaggerated), search for a county, and share a link straight to it.

## What the data says

{heads_md}

### The six regions

Reality Score = the real counties' average percentile across the five layers (0 = calmest county in Florida, 100 = most chaotic, 50 = typical). The game paints every region as chaotic, so 60+ = not exaggerated, 45-59 = fair, under 45 = exaggerated.

| GTA 6 region | Real inspiration | Counties used | Reality Score | Verdict | Match confidence |
|---|---|---|---|---|---|
{reg_rows}

### Florida's most chaotic counties

| Rank | County | Score |
|---|---|---|
{top10}

Calmest five: {calm5}.

## Method

| Layer | Source | Measure |
|---|---|---|
| Hurricanes | NOAA NHC HURDAT2 best tracks (1851-2025) | Hurricanes whose track, interpolated hourly, passed within 60 nautical miles of the county centre at ≥64 kt, {dw['hurricane_passes']}, per decade. Landfalls: distinct storms with a HURDAT2 landfall record in the county since 1851 |
| Sinkholes | Florida Geological Survey subsidence incident reports (ArcGIS REST) | Reports per 1,000 km², placed by coordinates (county field as fallback); exact duplicates removed |
| Alligators | GBIF, iNaturalist research-grade observations | Alligator observations per 10,000 observations of any species (controls for where people go looking) |
| Homicide | County Health Rankings 2025 (CDC NCHS) | Homicide deaths per 100,000; small counts suppressed by the source |
| Road deaths | County Health Rankings 2025 (CDC NCHS) | Motor-vehicle crash deaths per 100,000 |
| Home prices (context only) | Zillow Home Value Index, mid-tier, county | {dw['zillow_latest']} value and change since {dw['zillow_compared_with']} |
| Population, shapes | US Census Bureau (vintage 2024 estimates; county boundaries via Plotly's GeoJSON mirror) | Denominators and map |

Region → county matching follows published map guides and is a judgement call; confidence is shown for each region. Mount Kalaga has no real equivalent (Florida has no mountains), so it is matched loosely to North Florida's forest counties.

## Limits

- The 60 nm radius from a county centre favours central-peninsula counties, which get storms from both coasts. It measures exposure, not damage.
- Sinkhole reports are self-reported and mostly unverified; counties with more people and more reporting will look worse.
- Alligator sightings depend on where iNaturalist users go. The per-10,000 ratio reduces this but small counties have few observations.
- Homicide rates are suppressed for small counties; their score averages the other four layers.
- Percentile scores show rank, not size: a county at 90 is not "twice as dangerous" as one at 45.

## Data quality

{len(hard)} hard checks (build fails if any fail), all passed: 67 counties in every source, unique keys after the join, at least 98% of sinkhole reports and every GBIF county matched, HURDAT2 complete through 2025. Soft checks from the last run:

{soft_notes}

Full report: `outputs/dq_report.csv`. Raw files are re-downloaded on every build and their SHA-256 hashes recorded in `data/raw/manifest.json`.

## Run it

```bash
pip install -r requirements.txt
python -m pytest -q      # unit tests + an end-to-end build on synthetic data
python -m src.fetch      # downloads the public data into data/raw/
python -m src.build      # writes outputs/, site/index.html and this README
```

GitHub Actions runs the same steps on every push and publishes `site/` to GitHub Pages.

```
src/config.py      sources, parameters, region → county mapping
src/fetch.py       downloads + SHA-256 manifest
src/geo.py         point-in-polygon, areas, centroids (no GIS libraries)
src/hurricanes.py  HURDAT2 parser, hourly track interpolation, passes and landfalls
src/build.py       joins, data-quality checks, scores, findings
src/site.py        dashboard data; src/template.html is the page
outputs/           county_metrics.csv, region_scores.csv, florida_hurricane_landfalls.csv, findings.json, dq_report.csv
```

GTA 6 and Leonida belong to Rockstar Games. This is an independent fan analysis using public data.
"""
    with open(path, "w") as fh:
        fh.write(text)
