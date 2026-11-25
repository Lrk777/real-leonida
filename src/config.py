"""Sources, parameters and the GTA 6 region -> county mapping.

Everything that is a judgement call lives here so it is easy to see and change.
"""

RAW_DIR = "data/raw"
OUT_DIR = "outputs"
SITE_DIR = "site"

SOURCES = {
    # NOAA National Hurricane Center, Atlantic best track (HURDAT2), revised Sept 2026
    "hurdat2": "https://www.nhc.noaa.gov/data/hurdat/hurdat2-1851-2025-092326.txt",
    # US county shapes (Census cartographic boundaries, GeoJSON mirror kept by Plotly on GitHub)
    "counties": "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json",
    # Census Bureau county population estimates, vintage 2024
    "population": "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/totals/co-est2024-alldata.csv",
    # County Health Rankings 2025 analytic data (homicide + motor-vehicle crash death rates, CDC NCHS)
    "chr": "https://www.countyhealthrankings.org/sites/default/files/media/document/analytic_data2025_v3.csv",
    # Zillow Home Value Index, mid-tier, smoothed + seasonally adjusted, county, monthly
    "zhvi": "https://files.zillowstatic.com/research/public_csvs/zhvi/County_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
    # Florida Geological Survey subsidence (sinkhole) incident reports, ArcGIS REST layer
    "sinkholes": "https://ca.dep.state.fl.us/arcgis/rest/services/OpenData/FGS_SUBSIDENCE/MapServer/0/query",
    # GBIF occurrence API (iNaturalist research-grade observations)
    "gbif": "https://api.gbif.org/v1/occurrence/search",
}

GBIF_INAT_DATASET = "50c9509d-22c7-4a22-a47d-8c48425ef4a7"  # iNaturalist research-grade
GBIF_ALLIGATOR_TAXON = 2441370  # Alligator mississippiensis
GBIF_FLORIDA_GID = "USA.10_1"

STATE_FIPS = "12"

# Hurricane parameters
HURRICANE_KT = 64          # Saffir-Simpson Cat 1 threshold (knots)
MAJOR_KT = 96              # Cat 3+
PASS_RADIUS_KM = 111.12    # 60 nautical miles, the default radius NOAA's Historical Hurricane Tracks tool uses
PASS_START_YEAR = 1950     # aircraft-reconnaissance era; earlier tracks are less reliable
LANDFALL_SNAP_KM = 25      # landfall points just offshore snap to the nearest county within this distance

# Housing: compare latest month with the same month 5 years earlier
HOUSING_YEARS_BACK = 5

# GTA 6 region -> real counties (FIPS). Press consensus, checked 2026-11-24.
# Confidence is shown on the dashboard and in the README.
REGIONS = [
    {"region": "Vice City", "inspiration": "Miami", "counties": ["12086"], "confidence": "high"},
    {"region": "Leonida Keys", "inspiration": "Florida Keys", "counties": ["12087"], "confidence": "high"},
    {"region": "Grassrivers", "inspiration": "The Everglades / Big Cypress", "counties": ["12021", "12087"], "confidence": "medium"},
    {"region": "Ambrosia", "inspiration": "Lake Okeechobee sugar country (Clewiston)", "counties": ["12051", "12043"], "confidence": "medium"},
    {"region": "Port Gellhorn", "inspiration": "Panama City / Panhandle Gulf coast", "counties": ["12005"], "confidence": "medium"},
    {"region": "Mount Kalaga", "inspiration": "North Florida forests (+ Providence Canyon, Georgia)", "counties": ["12083", "12077"], "confidence": "low"},
]

# GTA 6 story chapters (91 missions) per fan walkthrough guides (KeenGamer / PC Gamer mission lists, Nov 2026; not an
# official Rockstar list). Spoiler-light: chapter names and opening missions only. Chapter 5's location isn't given in
# the guides, so the site uses it as a statewide finale instead of pinning it to a county.
CHAPTERS = [
    {"n": 1, "title": "Just Like Paradise", "region": "Leonida Keys", "missions": 22, "fips": "12087",
     "hook": "Opens in the Keys: fishing, diving and boat jobs (“Gone Fishing”, “Island Dreams”).",
     "stats": ["landfalls_since_1851", "major_hurricanes_1950_2025", "gators_per_10k_obs"]},
    {"n": 2, "title": "Paradise Lost", "region": "Port Gellhorn", "missions": 11, "fips": "12005",
     "hook": "A rundown Gulf-coast town and a motel, with an ambulance job (“Ambulance Chaser”).",
     "stats": ["strongest_landfall", "crash_deaths_per_100k", "home_value"]},
    {"n": 3, "title": "Vice City arrival", "region": "Vice City", "missions": 26, "fips": "12086",
     "hook": "Arrival in the city (“Welcome to Vice City”), car thefts and a bank job.",
     "stats": ["homicide_per_100k", "home_value", "chaos_score"]},
    {"n": 4, "title": "Vice City, Baby", "region": "Vice City", "missions": 25, "fips": "12086",
     "hook": "Ocean Beach, nightclubs and a job at the airport.",
     "stats": ["hurricanes_1950_2025", "alligator_obs", "crash_deaths_per_100k"]},
    {"n": 5, "title": "Top of the World, Ma", "region": None, "missions": 7, "fips": None,
     "hook": "The final 7 missions. No spoilers here: this page's finale is the whole state.",
     "stats": []},
]

# The five "chaos" layers that make up the Reality Score (higher = more chaotic)
CHAOS_LAYERS = {
    "hurricanes_per_decade": "Hurricanes passing within 60 nm, per decade (1950-2025)",
    "sinkholes_per_1000km2": "Reported sinkholes per 1,000 km²",
    "gators_per_10k_obs": "Alligators per 10,000 iNaturalist wildlife observations",
    "homicide_per_100k": "Homicides per 100,000 residents (CDC via County Health Rankings 2025)",
    "crash_deaths_per_100k": "Motor-vehicle crash deaths per 100,000 (CDC via County Health Rankings 2025)",
}
