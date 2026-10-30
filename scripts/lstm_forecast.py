import pandas as pd
import numpy as np
import zlib
from sklearn.preprocessing import MinMaxScaler
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Input, LSTM, Dense
from tensorflow.keras.utils import set_random_seed

# 跨平台中文字型 fallback：Linux 用 Noto/文鼎，Windows 用微軟正黑
plt.rcParams["font.sans-serif"] = [
    "Noto Sans CJK TW", "Noto Sans CJK HK", "Noto Sans CJK JP",
    "AR PL UMing TW", "Droid Sans Fallback",
    "Microsoft JhengHei", "SimHei",
]
plt.rcParams["axes.unicode_minus"] = False

BASE_DIR = Path(__file__).resolve().parent.parent
FEAT_DIR = BASE_DIR / "data" / "features"
PLOT_DIR = BASE_DIR / "data" / "plots"
FORECAST_DIR = BASE_DIR / "data" / "forecast"
PLOT_DIR.mkdir(parents=True, exist_ok=True)
FORECAST_DIR.mkdir(parents=True, exist_ok=True)

def train_and_predict(city, candidate, df):
    # 每位人物使用固定種子，讓同一份輸入資料可重現。
    set_random_seed(zlib.crc32(f"{city}|{candidate}".encode("utf-8")))
    df = df.sort_values("date")
    y = df["news_count"].values.reshape(-1, 1)

    scaler = MinMaxScaler()
    y_scaled = scaler.fit_transform(y)

    # 資料少時自動縮 window，至少留 2 個 training sample
    window = min(7, max(2, len(y_scaled) - 2))
    X, Y = [], []
    for i in range(window, len(y_scaled)):
        X.append(y_scaled[i-window:i, 0])
        Y.append(y_scaled[i, 0])

    X, Y = np.array(X), np.array(Y)
    X = X.reshape(X.shape[0], X.shape[1], 1)

    model = Sequential([
        Input(shape=(window, 1)),
        LSTM(50, activation="tanh", return_sequences=False),
        Dense(1)
    ])
    model.compile(optimizer="adam", loss="mse")
    model.fit(X, Y, epochs=30, batch_size=8, verbose=0)

    # predict 7 days
    seq = y_scaled[-window:].reshape(1, window, 1)
    preds = []
    for _ in range(7):
        p = model.predict(seq, verbose=0)[0][0]
        preds.append(p)
        new_seq = np.append(seq.flatten(), p)[1:]
        seq = new_seq.reshape(1, window, 1)

    preds = scaler.inverse_transform(np.array(preds).reshape(-1, 1)).flatten()
    # 新聞提及量不可能為負；在落盤前就修正，而不是只靠前端裁切。
    preds = np.clip(preds, 0, None)
    future_dates = pd.date_range(df["date"].iloc[-1] + pd.Timedelta(days=1), periods=7)

    # CSV
    out_csv = FORECAST_DIR / f"{city}_{candidate}_forecast.csv"
    pd.DataFrame({
        "date": future_dates,
        "city": city,
        "candidate": candidate,
        "forecast_news_count": preds
    }).to_csv(out_csv, index=False, encoding="utf-8-sig")

    # PNG
    out_png = PLOT_DIR / f"{city}_{candidate}.png"
    plt.figure(figsize=(10, 5))
    plt.plot(df["date"], df["news_count"], label="Actual")
    plt.plot(future_dates, preds, "--", label="Forecast")
    plt.title(f"{city} - {candidate} LSTM 預測")
    plt.xlabel("Date")
    plt.ylabel("News Count")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()

    print(f"🖼️ 圖片 → {out_png}")
    print(f"📄 CSV → {out_csv}")

def run_lstm():
    df = pd.read_csv(FEAT_DIR / "voice_features.csv")
    df["date"] = pd.to_datetime(df["date"])

    for (city, cand), sub in df.groupby(["city", "candidate"]):
        if len(sub) >= 5:
            print(f"📈 LSTM → {city} {cand} (n={len(sub)})")
            train_and_predict(city, cand, sub)
        else:
            print(f"⚠️ LSTM 跳過 {city}-{cand}（資料 < 5 天）")
