"""Spike detection: compare the latest window against a rolling baseline per
category, product and location, using a z-score with a minimum-volume floor.

Windows are measured in 24-hour periods back from the newest complaint, so a few
complaints arriving early on a new calendar day do not hide an ongoing spike."""
import math

import pandas as pd

WINDOW = 3          # days in the "recent" window
BASELINE = 14       # days of history before the window
Z_THRESHOLD = 2.5
MIN_RECENT = 6      # ignore spikes on tiny counts


def daily_series(df: pd.DataFrame, by: str | None = None) -> list[dict]:
    d = df.assign(day=df.created_at.dt.date)
    if by is None:
        s = d.groupby("day").size()
        return [{"day": str(k), "count": int(v)} for k, v in s.items()]
    t = d.groupby(["day", by]).size().unstack(fill_value=0)
    return [{"day": str(k), **{c: int(v) for c, v in row.items()}} for k, row in t.iterrows()]


def detect(df: pd.DataFrame, now=None) -> list[dict]:
    if df.empty:
        return []
    # Anchor at the newest complaint, but never in the future: one mis-dated row must not hide spikes.
    tmax = min(df.created_at.max(), pd.Timestamp(now or pd.Timestamp.now()))
    age = ((tmax - df.created_at) / pd.Timedelta(days=1)).apply(math.floor)  # 0 = last 24h
    if age.max() < BASELINE + WINDOW - 1:
        return []  # not enough history for a baseline; zero-filled days would fake a spike
    df = df.assign(age=age)[(age >= 0) & (age < BASELINE + WINDOW)]
    periods = range(BASELINE + WINDOW)
    alerts = []
    for dim in ["category", "product", "location"]:
        sub = df[df[dim].notna() & (df[dim] != "")]
        if sub.empty:
            continue
        counts = sub.groupby(["age", dim]).size().unstack(fill_value=0).reindex(periods, fill_value=0)
        recent, base = counts.iloc[:WINDOW], counts.iloc[WINDOW:]
        for val in counts.columns:
            mu, sd = base[val].mean(), base[val].std(ddof=0)
            r = recent[val].mean()
            z = (r - mu) / max(sd, 1.0)
            if z >= Z_THRESHOLD and recent[val].sum() >= MIN_RECENT:
                top_cat = sub[(sub[dim] == val) & (sub.age < WINDOW)].category.value_counts()
                alerts.append({
                    "dimension": dim, "value": val, "z_score": round(float(z), 2),
                    "recent_daily_avg": round(float(r), 1), "baseline_daily_avg": round(float(mu), 1),
                    "increase_pct": round(float((r - mu) / max(mu, 0.5) * 100)),
                    "dominant_category": top_cat.index[0] if len(top_cat) else None,
                    "message": f"{dim.title()} '{val}': {r:.1f}/day in last {WINDOW} days vs {mu:.1f}/day baseline "
                               f"(z={z:.1f}). Possible emerging issue.",
                })
    return sorted(alerts, key=lambda a: -a["z_score"])
