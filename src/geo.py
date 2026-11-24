"""Small pure-Python geometry helpers (no GIS libraries needed).

Coordinates are (lon, lat) in degrees, as in GeoJSON.
"""
import math

EARTH_R_KM = 6371.0088


def haversine_km(lon1, lat1, lon2, lat2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R_KM * math.asin(math.sqrt(a))


def _polygons(geometry):
    """Yield polygons as lists of rings for Polygon / MultiPolygon."""
    if geometry["type"] == "Polygon":
        yield geometry["coordinates"]
    elif geometry["type"] == "MultiPolygon":
        for poly in geometry["coordinates"]:
            yield poly
    else:
        raise ValueError(f"unsupported geometry {geometry['type']}")


def _point_in_ring(x, y, ring):
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y):
            x_cross = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < x_cross:
                inside = not inside
        j = i
    return inside


def point_in_geometry(lon, lat, geometry):
    for rings in _polygons(geometry):
        if _point_in_ring(lon, lat, rings[0]) and not any(_point_in_ring(lon, lat, h) for h in rings[1:]):
            return True
    return False


def bbox(geometry):
    xs, ys = [], []
    for rings in _polygons(geometry):
        for x, y in rings[0]:
            xs.append(x)
            ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def _ring_area_centroid(ring, lat0):
    """Shoelace on a local equirectangular projection (km). Returns signed area, cx, cy in degrees."""
    kx = 111.320 * math.cos(math.radians(lat0))
    ky = 110.574
    a = cx = cy = 0.0
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i][0] * kx, ring[i][1] * ky
        x2, y2 = ring[(i + 1) % n][0] * kx, ring[(i + 1) % n][1] * ky
        cross = x1 * y2 - x2 * y1
        a += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    a *= 0.5
    if a == 0:
        return 0.0, ring[0][0], ring[0][1]
    return a, (cx / (6 * a)) / kx, (cy / (6 * a)) / ky


def area_centroid(geometry):
    """Area in km² and area-weighted centroid (lon, lat)."""
    _, ymin, _, ymax = bbox(geometry)
    lat0 = (ymin + ymax) / 2
    total = sx = sy = 0.0
    for rings in _polygons(geometry):
        for k, ring in enumerate(rings):
            a, cx, cy = _ring_area_centroid(ring, lat0)
            a = abs(a) if k == 0 else -abs(a)  # outer ring adds, holes subtract
            total += a
            sx += a * cx
            sy += a * cy
    return total, sx / total, sy / total


def min_vertex_distance_km(lon, lat, geometry):
    best = float("inf")
    for rings in _polygons(geometry):
        for x, y in rings[0]:
            d = haversine_km(lon, lat, x, y)
            if d < best:
                best = d
    return best


class CountyIndex:
    """Point -> county lookup with a bbox pre-filter and optional nearest-county snapping."""

    def __init__(self, features):
        self.items = [(f["id"], f["geometry"], bbox(f["geometry"])) for f in features]

    def locate(self, lon, lat, snap_km=0.0):
        for fips, geom, (x0, y0, x1, y1) in self.items:
            if x0 <= lon <= x1 and y0 <= lat <= y1 and point_in_geometry(lon, lat, geom):
                return fips
        if snap_km > 0:
            best, best_d = None, snap_km
            for fips, geom, (x0, y0, x1, y1) in self.items:
                # cheap reject: more than ~1 degree away from the bbox
                if lon < x0 - 1 or lon > x1 + 1 or lat < y0 - 1 or lat > y1 + 1:
                    continue
                d = min_vertex_distance_km(lon, lat, geom)
                if d <= best_d:
                    best, best_d = fips, d
            return best
        return None
