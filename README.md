# Real Leonida: is GTA 6's Florida exaggerated?

GTA 6 (Nov 2026) is set in Leonida, Rockstar's parody of Florida. This project matches each of the game's six regions to the real counties behind them and scores all 67 Florida counties on five kinds of real-world chaos: hurricanes, sinkholes, alligators, homicide and road deaths.

**Live dashboard:** https://lrk777.github.io/real-leonida/

What you can do there:

- Switch the Florida map between 8 layers (Reality Score, hurricanes, sinkholes, alligators, homicide, road deaths, home prices, your match) and click any county for its full profile, ranks and the strongest hurricanes that hit it.
- Replay the track of every major hurricane (Cat 3+) to make landfall in Florida since 1950, one by one, or pick a single storm.
- Use "Find your calm corner of Leonida": set how much you care about each risk and a budget, and get the best-matching counties.
- Compare the six GTA 6 regions on scorecards with a verdict (exaggerated / fair / not exaggerated), search for a county, and share a link straight to it.

## What the data says

- **Ambrosia is the real chaos capital.** Its real counties (Glades, Hendry) score 74/100, the highest of the six regions. Glades is #2 of 67 Florida counties.
- **Real Vice City ranks #29 of 67.** Miami-Dade scores 54/100, close to a typical Florida county. Homicide rate: #15 of 58. Road deaths: #64 of 67. Home prices: #4.
- **22 hurricanes came ashore.** More hurricanes have made landfall in Monroe County (GTA 6: Leonida Keys / Grassrivers) since 1851 than in any other Florida county.
- **291 sinkholes per 1,000 km².** Citrus County leads Florida for reported sinkholes. None of the top 5 sinkhole counties is in a GTA 6 region.
- **1 in 37 wildlife sightings is a gator.** In Collier County (GTA 6: Grassrivers), alligators make up 2.7% of all iNaturalist wildlife observations, the most of any county with 20,000+ observations.

### The six regions

Reality Score = the real counties' average percentile across the five layers (0 = calmest county in Florida, 100 = most chaotic, 50 = typical). The game paints every region as chaotic, so 60+ = not exaggerated, 45-59 = fair, under 45 = exaggerated.

| GTA 6 region | Real inspiration | Counties used | Reality Score | Verdict | Match confidence |
|---|---|---|---|---|---|
| Ambrosia | Lake Okeechobee sugar country (Clewiston) | Glades, Hendry | 74 | Not exaggerated | medium |
| Vice City | Miami | Miami-Dade | 54 | Fair | high |
| Mount Kalaga | North Florida forests (+ Providence Canyon, Georgia) | Marion, Liberty | 50 | Fair | low |
| Leonida Keys | Florida Keys | Monroe | 47 | Fair | high |
| Grassrivers | The Everglades / Big Cypress | Monroe, Collier | 44 | Exaggerated | medium |
| Port Gellhorn | Panama City / Panhandle Gulf coast | Bay | 44 | Exaggerated | medium |

### Florida's most chaotic counties

| Rank | County | Score |
|---|---|---|
| 1 | Okeechobee | 75 |
| 2 | Glades | 74 |
| 3 | Hendry | 74 |
| 4 | Hardee | 73 |
| 5 | Orange | 72 |
| 6 | Dixie | 69 |
| 7 | Putnam | 66 |
| 8 | Hillsborough | 66 |
| 9 | Highlands | 65 |
| 10 | Polk | 65 |

Calmest five: Santa Rosa (19), St. Johns (28), Flagler (28), Clay (29), Bradford (33).

## Method

| Layer | Source | Measure |
|---|---|---|
| Hurricanes | NOAA NHC HURDAT2 best tracks (1851-2025) | Hurricanes whose track, interpolated hourly, passed within 60 nautical miles of the county centre at ≥64 kt, 1950-2025, per decade. Landfalls: distinct storms with a HURDAT2 landfall record in the county since 1851 |
| Sinkholes | Florida Geological Survey subsidence incident reports (ArcGIS REST) | Reports per 1,000 km², placed by coordinates (county field as fallback); exact duplicates removed |
| Alligators | GBIF, iNaturalist research-grade observations | Alligator observations per 10,000 observations of any species (controls for where people go looking) |
| Homicide | County Health Rankings 2025 (CDC NCHS) | Homicide deaths per 100,000; small counts suppressed by the source |
| Road deaths | County Health Rankings 2025 (CDC NCHS) | Motor-vehicle crash deaths per 100,000 |
| Home prices (context only) | Zillow Home Value Index, mid-tier, county | 2026-10-31 value and change since 2021-10-31 |
| Population, shapes | US Census Bureau (vintage 2024 estimates; county boundaries via Plotly's GeoJSON mirror) | Denominators and map |

Region → county matching follows published map guides and is a judgement call; confidence is shown for each region. Mount Kalaga has no real equivalent (Florida has no mountains), so it is matched loosely to North Florida's forest counties.

## Limits

- The 60 nm radius from a county centre favours central-peninsula counties, which get storms from both coasts. It measures exposure, not damage.
- Sinkhole reports are self-reported and mostly unverified; counties with more people and more reporting will look worse.
- Alligator sightings depend on where iNaturalist users go. The per-10,000 ratio reduces this but small counties have few observations.
- Homicide rates are suppressed for small counties; their score averages the other four layers.
- Percentile scores show rank, not size: a county at 90 is not "twice as dangerous" as one at 45.

## Data quality

10 hard checks (build fails if any fail), all passed: 67 counties in every source, unique keys after the join, at least 98% of sinkhole reports and every GBIF county matched, HURDAT2 complete through 2025. Soft checks from the last run:

- sinkholes: exact duplicate reports removed: 0 removed
- sinkholes: report numbers unique after de-duplication: 10 report numbers reused at different locations (kept)
- sinkholes: point location agrees with county field: 99.1% agree
- CHR: crash-death rate present for every county: 0 missing
- CHR: homicide rate present: 9 suppressed (small counts)
- Zillow: Florida counties covered: 67 counties
- biomes: every county clustered: k=4, silhouette={3: 0.206, 4: 0.226, 5: 0.213, 6: 0.208}

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
