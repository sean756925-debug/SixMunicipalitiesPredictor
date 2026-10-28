import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROC_DIR = BASE_DIR / "data" / "processed"
FEAT_DIR = BASE_DIR / "data" / "features"
FEAT_DIR.mkdir(parents=True, exist_ok=True)


def build_features():
    print("\n==============================")
    print("▶ START: Build Features")
    print("==============================\n")

    df = pd.read_csv(PROC_DIR / "daily_news_volume.csv")
    df["date"] = pd.to_datetime(df["date"])

    # 依 city, candidate 排序
    df = df.sort_values(["city", "candidate", "date"]).reset_index(drop=True)

    # --- 避免 MultiIndex 的安全寫法 ---
    df["news_7d"] = 0
    df["news_7d_prev"] = 0

    for (city, cand), sub in df.groupby(["city", "candidate"]):
        idx = sub.index

        # 轉成普通序列
        counts = sub["news_count"].values

        # rolling sum 7-day
        news_7d = pd.Series(counts).rolling(7, min_periods=1).sum().values

        # shift 7 days + rolling
        shifted = pd.Series(counts).shift(7)
        news_7d_prev = shifted.rolling(7, min_periods=1).sum().fillna(0).values

        df.loc[idx, "news_7d"] = news_7d
        df.loc[idx, "news_7d_prev"] = news_7d_prev

    df["news_momentum"] = df["news_7d"] - df["news_7d_prev"]

    # 其他特徵先補 0（之後可改有內容的版本）
    df["positive_ratio"] = 0.0
    df["negative_ratio"] = 0.0
    df["neutral_ratio"] = 1.0
    df["engagement_score"] = 0.0
    df["search_trend"] = 0.0
    df["poll_support"] = 0.0
    df["event_flag"] = 0

    out = FEAT_DIR / "voice_features.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"✅ 特徵表已建立 → {out}")
    print(df.tail())

    print("\n✅ FINISH: Build Features\n")
    return out


if __name__ == "__main__":
    build_features()
