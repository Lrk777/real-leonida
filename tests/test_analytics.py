"""Biome clustering and seasons."""
import numpy as np
import pandas as pd

from src.analytics import biomes, seasons, silhouette

LAYERS = ["hurricanes_per_decade", "sinkholes_per_1000km2", "gators_per_10k_obs", "homicide_per_100k", "crash_deaths_per_100k"]


def _df():
    rng = np.random.default_rng(0)
    rows = []
    centres = [(90, 10, 10, 10, 10), (10, 90, 10, 10, 10), (10, 10, 10, 10, 10)]  # storm, sinkhole, calm
    for g, c in enumerate(centres):
        for i in range(20):
            v = np.clip(np.array(c) + rng.normal(0, 4, 5), 0, 100)
            rows.append({"fips": f"{g}{i:02d}", "name": f"C{g}{i}", **{L + "_pct": x for L, x in zip(LAYERS, v)}})
    return pd.DataFrame(rows)


def test_biomes_recover_clear_groups_and_name_them():
    df = _df()
    b = biomes(df, LAYERS, k_range=(2, 5))
    assert b["k"] == 3 and sorted(c["size"] for c in b["clusters"]) == [20, 20, 20]
    assert {c["name"] for c in b["clusters"]} == {"Storm Coast", "Sinkhole Belt", "Calm Country"}
    lab = b["labels"]
    assert len({lab[f] for f in df.fips[:20]}) == 1                     # each true group lands in one cluster
    assert biomes(df, LAYERS, k_range=(2, 5))["labels"] == lab          # deterministic


def test_silhouette_is_high_for_separated_and_low_for_random():
    X = np.vstack([np.zeros((10, 2)), np.ones((10, 2)) * 10])
    assert silhouette(X, np.array([0] * 10 + [1] * 10)) > 0.9
    assert silhouette(X, np.array([0, 1] * 10)) < 0.1


def test_seasons_counts_per_decade():
    storms = [{"id": "A", "year": 1955}, {"id": "B", "year": 2004}, {"id": "C", "year": 2024}]
    passes = {"12001": {"storms": ["A", "B"]}, "12003": {"storms": ["B", "C"]}}
    lf = pd.DataFrame([{"storm": "B", "year": 2004, "wind_kt": 120}, {"storm": "B", "year": 2004, "wind_kt": 110}, {"storm": "C", "year": 2024, "wind_kt": 80}])
    s = seasons(passes, storms, lf)
    assert s["labels"][0] == "1950s" and s["labels"][-1] == "2020s" and s["years"][-1] == 6
    assert s["county"]["12001"][0] == 1 and s["county"]["12003"][-1] == 1
    assert sum(s["fl_pass"]) == 3 and sum(s["fl_major_lf"]) == 1    # B counted once
