import os
import json
import glob
import pandas as pd
import yaml
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROC_DIR = BASE_DIR / "data" / "processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)

def clean_and_aggregate():
    print("\n==============================")
    print("▶ START: Clean & Aggregate News")
    print("==============================\n")

    files = sorted(glob.glob(str(RAW_DIR / "news_*.json")))
    rows = []

    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            items = json.load(f)

        for it in items:
            pub = it.get("published", "")

            try:
                # RSS 日期通常是 GMT；統一換算成台灣日期。
                date = pd.to_datetime(pub, utc=True).tz_convert("Asia/Taipei").date()
            except Exception:
                date = datetime.fromtimestamp(os.path.getmtime(fp)).date()

            rows.append({
                "date": date,
                "city": it.get("city"),
                "candidate": it.get("candidate"),
                "source": it.get("source"),
                "title": it.get("title")
            })

    df = pd.DataFrame(rows)
    df = df.dropna(subset=["city", "candidate"])
    df = df.drop_duplicates(subset=["date", "city", "candidate", "source", "title"])

    today = pd.Timestamp.now(tz="Asia/Taipei").date()
    cutoff = (pd.Timestamp.now(tz="Asia/Taipei").normalize() - pd.Timedelta(days=180)).date()
    df = df[(df["date"] >= cutoff) & (df["date"] <= today)]
    if df.empty:
        raise RuntimeError("最近 180 天沒有抓到任何可歸類的候選人新聞，保留備份並停止 Pipeline")

    observed = (
        df.groupby(["date", "city", "candidate"])
          .size()
          .reset_index(name="news_count")
    )

    # 補齊每位候選人直到今天的日曆日期，無新聞日期的聲量為 0。
    # 這可確保 rolling window 是 7 個日曆日，且預測由明天開始。
    with open(BASE_DIR / "config" / "keywords.yaml", "r", encoding="utf-8") as f:
        keywords = yaml.safe_load(f)

    start = cutoff
    full_rows = []
    if pd.notna(start):
        calendar = pd.date_range(start=start, end=today, freq="D").date
        counts = observed.set_index(["date", "city", "candidate"])["news_count"]
        for city, candidates in keywords.items():
            for candidate in candidates:
                for date in calendar:
                    full_rows.append({
                        "date": date,
                        "city": city,
                        "candidate": candidate,
                        "news_count": int(counts.get((date, city, candidate), 0)),
                    })
    vol = pd.DataFrame(full_rows)

    if vol.empty:
        raise RuntimeError("沒有抓到任何可歸類的候選人新聞，保留備份並停止 Pipeline")

    out = PROC_DIR / "daily_news_volume.csv"
    vol.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"✅ 已建立每日聲量表 → {out}")
    print(vol.tail())

    print("\n✅ FINISH: Clean & Aggregate News\n")
    return out
