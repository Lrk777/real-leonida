"""Game-analytics style models used by the dashboard's Dev Mode.

- biomes():   k-means clustering of the 67 counties on their hazard percentiles, like the zones of an open-world map.
              k is picked by silhouette score; clusters are named after the hazard that stands out most
              ("Calm Country" when low on everything, "Hardcore Zone" when high on almost everything).
- seasons():  hurricanes per decade ("seasons"), statewide and per county, from the HURDAT2 passes.
Pure numpy so the CI needs nothing extra.
"""
import numpy as np

FEATURE_NAMES = {
    "hurricanes_per_decade": "Storm Coast",
    "sinkholes_per_1000km2": "Sinkhole Belt",
    "gators_per_10k_obs": "Gator Backcountry",
    "homicide_per_100k": "Danger Zone",
    "crash_deaths_per_100k": "Fast-Road Country",
}
CALM_NAME = "Calm Country"
HARD_NAME = "Hardcore Zone"
MIXED_NAME = "Mixed Wilds"


def _kmeans(X, k, rng, iters=100):
    # k-means++ initialisation
    c = [X[rng.integers(len(X))]]
    for _ in range(1, k):
        d = np.min(((X[:, None, :] - np.array(c)[None]) ** 2).sum(-1), axis=1)
        c.append(X[rng.choice(len(X), p=d / d.sum())] if d.sum() > 0 else X[rng.integers(len(X))])
    c = np.array(c, dtype=float)
    for _ in range(iters):
        lab = ((X[:, None, :] - c[None]) ** 2).sum(-1).argmin(1)
        new = np.array([X[lab == j].mean(0) if (lab == j).any() else c[j] for j in range(k)])
        if np.allclose(new, c):
            break
        c = new
    inertia = float(((X - c[lab]) ** 2).sum())
    return lab, c, inertia


def silhouette(X, lab):
    D = np.sqrt(((X[:, None, :] - X[None]) ** 2).sum(-1))
    s = []
    for i in range(len(X)):
        same = lab == lab[i]
        if same.sum() <= 1:
            s.append(0.0)
            continue
        a = D[i, same].sum() / (same.sum() - 1)
        b = min(D[i, lab == j].mean() for j in set(lab) if j != lab[i])
        s.append((b - a) / max(a, b))
    return float(np.mean(s))


def biomes(df, layers, k_range=(3, 6), seed=42, n_init=20):
    """Cluster counties on their layer percentiles (missing = 50, a typical county).
    Returns {"labels": {fips: id}, "clusters": [...], "k": k, "silhouette": {k: s}, "features": [...]}."""
    cols = [c + "_pct" for c in layers]
    X = df[cols].fillna(50).to_numpy(dtype=float) / 100.0
    rng = np.random.default_rng(seed)
    best, sil = None, {}
    for k in range(k_range[0], k_range[1] + 1):
        runs = [_kmeans(X, k, rng) for _ in range(n_init)]
        lab, c, inertia = min(runs, key=lambda r: r[2])
        sil[k] = round(silhouette(X, lab), 3)
        if best is None or sil[k] > best[3]:
            best = (k, lab, c, sil[k])
    k, lab, cent, _ = best
    # stable order: biggest cluster first
    order = sorted(range(k), key=lambda j: (-(lab == j).sum(), j))
    remap = {old: new for new, old in enumerate(order)}
    lab = np.array([remap[x] for x in lab])
    cent = cent[order] * 100
    # names: calmest cluster (low on everything) = Calm Country; others by their standout hazard
    names, used = [None] * k, set()
    calm = int(np.argmin(cent.mean(1)))
    if cent[calm].max() < 60:
        names[calm] = CALM_NAME
    hard = int(np.argmax(cent.mean(1)))
    if cent[hard].mean() >= 60 and not names[hard]:
        names[hard] = HARD_NAME  # high on almost everything: the "hard mode" zone
    for j in sorted(range(k), key=lambda j: -cent[j].max()):
        if names[j]:
            continue
        for f in np.argsort(-cent[j]):
            if layers[f] not in used:
                names[j] = FEATURE_NAMES[layers[f]]
                used.add(layers[f])
                break
        names[j] = names[j] or MIXED_NAME
    fips = list(df.fips)
    clusters = [{"id": j, "name": names[j], "size": int((lab == j).sum()),
                 "centroid": [round(float(v), 1) for v in cent[j]],
                 "counties": [df.name.iloc[i] for i in range(len(fips)) if lab[i] == j]} for j in range(k)]
    return {"labels": {f: int(l) for f, l in zip(fips, lab)}, "clusters": clusters, "k": k,
            "silhouette": sil, "features": list(layers)}


def seasons(passes, storms, landfalls, start=1950, end=2025, major_kt=96):
    """Hurricanes per decade. passes: {fips: {"storms": [ids], ...}}; landfalls: Florida landfall rows (DataFrame)."""
    year = {s["id"]: s["year"] for s in storms}
    decades = list(range(start - start % 10, end + 1, 10))
    years = [min(d + 9, end) - max(d, start) + 1 for d in decades]
    idx = lambda y: (y - decades[0]) // 10
    county = {}
    union = set()
    for f, v in passes.items():
        row = [0] * len(decades)
        for sid in v["storms"]:
            row[idx(year[sid])] += 1
            union.add(sid)
        county[f] = row
    fl_pass = [0] * len(decades)
    for sid in union:
        fl_pass[idx(year[sid])] += 1
    fl_major_lf = [0] * len(decades)
    if landfalls is not None and len(landfalls):
        maj = landfalls[(landfalls.wind_kt >= major_kt) & (landfalls.year >= start)]
        for sid, y in maj.drop_duplicates("storm")[["storm", "year"]].itertuples(index=False):
            fl_major_lf[idx(int(y))] += 1
    return {"labels": [f"{d}s" for d in decades], "years": years, "fl_pass": fl_pass,
            "fl_major_lf": fl_major_lf, "county": county}
