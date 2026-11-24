from datetime import datetime

from src.build import norm
from src.geo import CountyIndex, area_centroid, haversine_km, point_in_geometry
from src.hurricanes import county_landfalls, county_passes, interpolate, parse_hurdat2

SQUARE = {"type": "Polygon", "coordinates": [[[-82, 27], [-81, 27], [-81, 28], [-82, 28], [-82, 27]]]}
HOLED = {"type": "Polygon", "coordinates": [SQUARE["coordinates"][0],
                                            [[-81.6, 27.4], [-81.4, 27.4], [-81.4, 27.6], [-81.6, 27.6], [-81.6, 27.4]]]}

HURDAT = """AL091992,             ANDREW,     3,
19920824, 0600,  , HU, 25.4N,  79.0W, 140,  922,
19920824, 0905, L, HU, 25.5N,  80.3W, 145,  922,
19920824, 1200,  , HU, 25.6N,  81.2W, 115,  937,
AL011900,            UNNAMED,     2,
19000901, 0000,  , TS, 27.5N,  81.5W,  50, -999,
19000901, 0600,  , TS, 27.6N,  81.6W,  50, -999,
"""


def test_haversine_one_degree_lat():
    assert abs(haversine_km(-81, 27, -81, 28) - 111.2) < 0.5


def test_point_in_polygon_with_hole():
    assert point_in_geometry(-81.8, 27.2, HOLED)
    assert not point_in_geometry(-81.5, 27.5, HOLED)  # inside the hole
    assert not point_in_geometry(-80.5, 27.5, HOLED)


def test_area_and_centroid_of_square():
    area, cx, cy = area_centroid(SQUARE)
    assert abs(cx + 81.5) < 1e-6 and abs(cy - 27.5) < 1e-6
    assert 10000 < area < 11500  # ~98.7 km x 110.6 km


def test_parse_hurdat2():
    storms = parse_hurdat2(HURDAT)
    assert [s["name"] for s in storms] == ["ANDREW", "UNNAMED"]
    a = storms[0]["points"][1]
    assert a["rec"] == "L" and a["lon"] == -80.3 and a["wind"] == 145
    assert a["t"] == datetime(1992, 8, 24, 9, 5)


def test_interpolation_is_hourly():
    storms = parse_hurdat2(HURDAT)
    pts = list(interpolate(storms[0]["points"]))
    assert 6 <= len(pts) <= 8  # 6 hours of track, one point per hour + last fix


def test_passes_respect_radius_and_strength():
    storms = parse_hurdat2(HURDAT)
    cents = {"near": (-80.4, 25.6), "far": (-84.0, 30.0), "weak_only": (-81.55, 27.55)}
    out = county_passes(storms, cents, start_year=1900)
    assert out["near"]["hurricanes"] == 1 and out["near"]["major"] == 1
    assert out["far"]["hurricanes"] == 0
    assert out["weak_only"]["hurricanes"] == 0  # 1900 storm was only a tropical storm


def test_landfall_assignment_and_snap():
    storms = parse_hurdat2(HURDAT)
    box = {"type": "Polygon", "coordinates": [[[-80.6, 25.3], [-80.35, 25.3], [-80.35, 25.8], [-80.6, 25.8], [-80.6, 25.3]]]}
    idx = CountyIndex([{"id": "12086", "geometry": box}])
    counts, rows = county_landfalls(storms, idx, snap_km=25)
    assert counts == {"12086": 1} and rows[0]["name"] == "ANDREW"


def test_name_normalisation():
    assert norm("St. Johns County") == norm("Saint Johns") == norm("ST. JOHNS")
    assert norm("DeSoto") == norm("Desoto")
    assert norm("DADE") == norm("Miami-Dade")
