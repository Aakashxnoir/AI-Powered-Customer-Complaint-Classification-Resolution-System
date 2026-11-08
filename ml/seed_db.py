"""Load the 60-day demo complaint stream into the database through the full pipeline."""
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.pipeline import process  # noqa: E402

BATCH = 100

if __name__ == "__main__":
    if "--reset" in sys.argv:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    df = pd.read_csv(ROOT / "data" / "processed" / "live_complaints.csv", parse_dates=["created_at"])
    df = df.sort_values("created_at")
    t = time.time()
    with SessionLocal() as db:
        for i in range(0, len(df), BATCH):
            chunk = df.iloc[i:i + BATCH]
            process(db, [{"text": r.text, "channel": "seed", "customer": r.customer, "created_at": r.created_at.to_pydatetime()}
                         for r in chunk.itertuples()])
            print(f"{i + len(chunk)}/{len(df)}  {time.time() - t:.0f}s", flush=True)
