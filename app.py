"""Streamlit 儀表板 — 選舉新聞聲量 / LSTM 預測。

執行：
    source venv/bin/activate
    streamlit run app.py
"""
from __future__ import annotations

import io
import sys
import subprocess
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
PROC_CSV = BASE_DIR / "data" / "processed" / "daily_news_volume.csv"
FEAT_CSV = BASE_DIR / "data" / "features" / "voice_features.csv"
FORECAST_DIR = BASE_DIR / "data" / "forecast"
PLOT_DIR = BASE_DIR / "data" / "plots"

st.set_page_config(page_title="選舉預測儀表板", page_icon="🗳️", layout="wide")
st.title("🗳️ 選舉新聞聲量與 LSTM 預測")


# ---------- 資料載入 ----------
@st.cache_data(show_spinner=False)
def load_features(mtime: float) -> pd.DataFrame:
    # mtime 當 cache key，檔案更新時自動失效
    if not FEAT_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(FEAT_CSV)
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data(show_spinner=False)
def load_forecast(city: str, candidate: str, mtime: float) -> pd.DataFrame:
    fp = FORECAST_DIR / f"{city}_{candidate}_forecast.csv"
    if not fp.exists():
        return pd.DataFrame()
    df = pd.read_csv(fp)
    df["date"] = pd.to_datetime(df["date"])
    return df


def file_mtime(p: Path) -> float:
    return p.stat().st_mtime if p.exists() else 0.0


# ---------- Sidebar：pipeline 觸發 ----------
with st.sidebar:
    st.header("⚙️ Pipeline")
    st.caption("離線跑：`python run_pipeline.py`\n線上跑：按下方按鈕（會 block 數分鐘）")

    if st.button("🔄 立即重新跑 Pipeline", type="primary"):
        log_area = st.empty()
        with st.spinner("Pipeline 執行中，LSTM 訓練可能要幾分鐘…"):
            import os as _os
            env = _os.environ.copy()
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            proc = subprocess.run(
                [sys.executable, str(BASE_DIR / "run_pipeline.py")],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
        if proc.returncode == 0:
            st.success("✅ Pipeline 完成")
        else:
            st.error(f"❌ Pipeline 失敗 (exit {proc.returncode})")
        with st.expander("執行紀錄", expanded=(proc.returncode != 0)):
            st.code((proc.stdout or "") + "\n" + (proc.stderr or ""), language="text")
        st.cache_data.clear()

    st.divider()
    st.caption("資料狀態")
    st.write(f"特徵表：{'✅' if FEAT_CSV.exists() else '❌ 尚未產生'}")
    st.write(f"預測檔：{len(list(FORECAST_DIR.glob('*.csv')))} 個")


# ---------- 主畫面 ----------
df = load_features(file_mtime(FEAT_CSV))

if df.empty:
    st.warning("還沒有特徵資料。請在左側按「立即重新跑 Pipeline」，或在終端機執行 `python run_pipeline.py`。")
    st.stop()

cities = sorted(df["city"].dropna().unique().tolist())
default_city = "台北市" if "台北市" in cities else cities[0]
col1, col2 = st.columns([1, 2])
with col1:
    city = st.selectbox("城市", cities, index=cities.index(default_city))
with col2:
    cands = sorted(df[df["city"] == city]["candidate"].dropna().unique().tolist())
    selected = st.multiselect("候選人（預設全選，可取消不想看的人）", cands, default=cands)

if not selected:
    st.info("請至少選一位候選人")
    st.stop()

# 圖表顯示範圍（模型仍用全部資料訓練，這裡只控制畫面）
chart_days = st.slider("圖表顯示天數（往回看；模型訓練仍用全部資料）", 14, 180, 30, step=7)
latest_date = df[df["city"] == city]["date"].max()
cutoff = latest_date - pd.Timedelta(days=chart_days)

# 提示哪些候選人沒有預測檔（資料 < 10 天會被 LSTM 跳過）
missing_fc = [c for c in selected if not (FORECAST_DIR / f"{city}_{c}_forecast.csv").exists()]
if missing_fc:
    st.warning(
        f"⚠️ {'、'.join(missing_fc)} 沒有 LSTM 預測線："
        f"資料 < 10 天會被跳過。可累積更多新聞後重跑 pipeline。"
    )

# KPI：每位候選人一行
st.subheader("📊 各候選人指標")
kpi_rows = []
for cand in selected:
    s = df[(df["city"] == city) & (df["candidate"] == cand)].sort_values("date")
    kpi_rows.append({
        "候選人": cand,
        "累計新聞數": int(s["news_count"].sum()),
        "近 7 日聲量": int(s["news_7d"].iloc[-1]) if not s.empty else 0,
        "聲量動能 (週對比)": int(s["news_momentum"].iloc[-1]) if not s.empty else 0,
        "樣本天數": len(s),
    })
st.dataframe(pd.DataFrame(kpi_rows), use_container_width=True, hide_index=True)

# 疊圖：每位候選人「實際」「預測」各一條線
st.subheader("📈 每日聲量 + 未來 7 天預測 (可比較多人)")
chart_df = pd.DataFrame()
for cand in selected:
    s = df[(df["city"] == city) & (df["candidate"] == cand) & (df["date"] >= cutoff)].sort_values("date")
    actual = s[["date", "news_count"]].rename(columns={"news_count": f"{cand} 實際"}).set_index("date")
    chart_df = actual if chart_df.empty else chart_df.join(actual, how="outer")

    fc = load_forecast(city, cand, file_mtime(FORECAST_DIR / f"{city}_{cand}_forecast.csv"))
    if not fc.empty:
        fcol = fc[["date", "forecast_news_count"]].rename(columns={"forecast_news_count": f"{cand} 預測"}).set_index("date")
        chart_df = chart_df.join(fcol, how="outer")
st.line_chart(chart_df)

# matplotlib 疊圖版 LSTM 預測（多人實際線 + 虛線預測，同色系一組）
st.subheader("🧪 LSTM 預測疊圖 (matplotlib)")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = [
    "Noto Sans CJK TW", "Noto Sans CJK HK", "Noto Sans CJK JP",
    "AR PL UMing TW", "Droid Sans Fallback",
    "Microsoft JhengHei", "SimHei",
]
plt.rcParams["axes.unicode_minus"] = False

fig, ax = plt.subplots(figsize=(10, 5))
colors = plt.cm.tab10.colors
plotted = False
for i, cand in enumerate(selected):
    color = colors[i % len(colors)]
    s = df[(df["city"] == city) & (df["candidate"] == cand) & (df["date"] >= cutoff)].sort_values("date")
    if not s.empty:
        ax.plot(s["date"], s["news_count"], color=color, label=f"{cand} 實際", linewidth=1.8)
        plotted = True
    fc = load_forecast(city, cand, file_mtime(FORECAST_DIR / f"{city}_{cand}_forecast.csv"))
    if not fc.empty:
        ax.plot(fc["date"], fc["forecast_news_count"], color=color, linestyle="--",
                label=f"{cand} 預測", linewidth=1.8)
if plotted:
    ax.set_title(f"{city} — LSTM 7 天預測比較")
    ax.set_xlabel("日期")
    ax.set_ylabel("News Count")
    ax.legend(loc="best")
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    st.pyplot(fig)
else:
    st.info("無可繪製資料")
plt.close(fig)

with st.expander("LSTM 原始預測圖 (每人單張)"):
    cols = st.columns(min(len(selected), 2))
    for i, cand in enumerate(selected):
        png = PLOT_DIR / f"{city}_{cand}.png"
        if png.exists():
            cols[i % len(cols)].image(str(png), caption=cand)
        else:
            cols[i % len(cols)].info(f"{cand}：無預測圖（資料 < 10 天）")

# 明細
with st.expander("聲量明細"):
    detail = df[(df["city"] == city) & (df["candidate"].isin(selected))].sort_values(["candidate", "date"])
    st.dataframe(
        detail[["date", "candidate", "news_count", "news_7d", "news_7d_prev", "news_momentum"]],
        use_container_width=True, hide_index=True,
    )

with st.expander("預測明細"):
    rows = []
    for cand in selected:
        fc = load_forecast(city, cand, file_mtime(FORECAST_DIR / f"{city}_{cand}_forecast.csv"))
        if not fc.empty:
            rows.append(fc)
    if rows:
        st.dataframe(pd.concat(rows, ignore_index=True), use_container_width=True, hide_index=True)
    else:
        st.caption("所選候選人皆無預測資料")
