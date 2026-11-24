"""Headline cards on the metrics from the first real run (tests/fixtures)."""
import os

import pandas as pd

from src import config
from src.build import headlines

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "county_metrics_run1.csv")


def _data():
    df = pd.read_csv(FIX, dtype={"fips": str})
    rows = []
    for r in config.REGIONS:
        sub = df[df.fips.isin(r["counties"])]
        rows.append({"region": r["region"], "counties": ", ".join(sub.name), "reality_score": sub.chaos_score.mean()})
    return df, pd.DataFrame(rows).sort_values("reality_score", ascending=False)


def test_headlines_are_complete_and_clean():
    df, reg = _data()
    h = headlines(df, reg)
    assert len(h) == 5
    for card in h:
        assert card["big"] and card["text"]
        assert "nan" not in (card["big"] + card["text"]).lower()


def test_headlines_reflect_the_data():
    df, reg = _data()
    h = headlines(df, reg)
    assert h[0]["big"].startswith(reg.iloc[0].region)
    vc = df[df.fips == "12086"].iloc[0]
    assert f"#{int(vc.chaos_rank)} of 67" in h[1]["big"]
    assert df.nlargest(1, "sinkholes_per_1000km2").iloc[0]["name"] in h[3]["text"]
