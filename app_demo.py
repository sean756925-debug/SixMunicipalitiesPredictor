"""Streamlit demo — 2026 六都選舉聲量戰情室。

這是給一般使用者看的 demo 版：先講結論，再讓使用者往下看資料與模型。
原始 app.py 保留不動。

執行：
    source venv/bin/activate
    streamlit run app_demo.py --server.address 0.0.0.0 --server.port 8502
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
FEAT_CSV = BASE_DIR / "data" / "features" / "voice_features.csv"
FORECAST_DIR = BASE_DIR / "data" / "forecast"
PLOT_DIR = BASE_DIR / "data" / "plots"

st.set_page_config(
    page_title="2026 六都選舉聲量戰情室",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
:root {
  --bg: #0b1020;
  --panel: rgba(255,255,255,.075);
  --panel-strong: rgba(255,255,255,.11);
  --text-soft: rgba(255,255,255,.72);
  --accent: #38bdf8;
  --hot: #fb7185;
  --up: #34d399;
  --down: #f59e0b;
}
.stApp {
  background:
    radial-gradient(circle at top left, rgba(56,189,248,.28), transparent 32rem),
    radial-gradient(circle at 78% 12%, rgba(251,113,133,.20), transparent 28rem),
    linear-gradient(135deg, #08111f 0%, #0b1020 45%, #111827 100%);
  color: #f8fafc;
}
[data-testid="stHeader"] { background: rgba(8,17,31,.60); backdrop-filter: blur(10px); }
.block-container { padding-top: 2.0rem; max-width: 1280px; }
h1, h2, h3 { letter-spacing: -.03em; }
.hero {
  border: 1px solid rgba(255,255,255,.14);
  border-radius: 28px;
  padding: 28px 30px;
  background: linear-gradient(135deg, rgba(255,255,255,.12), rgba(255,255,255,.05));
  box-shadow: 0 24px 80px rgba(0,0,0,.30);
  margin-bottom: 18px;
}
.hero .eyebrow { color: #93c5fd; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; font-size: 13px; }
.hero .title { font-size: 48px; line-height: 1.05; font-weight: 900; margin: 8px 0 10px; }
.hero .subtitle { color: var(--text-soft); font-size: 18px; max-width: 860px; }
.badge-row { display:flex; gap:10px; flex-wrap:wrap; margin-top:18px; }
.badge { border:1px solid rgba(255,255,255,.16); background: rgba(15,23,42,.65); padding:7px 12px; border-radius: 999px; color:#dbeafe; font-size:13px; }
.story-card {
  border: 1px solid rgba(255,255,255,.13);
  background: var(--panel);
  border-radius: 22px;
  padding: 18px 20px;
  min-height: 148px;
}
.story-card strong { font-size: 34px; display:block; line-height:1.05; margin: 6px 0; }
.story-card span { color: var(--text-soft); font-size: 14px; }
.story-card .label { color:#bfdbfe; font-weight:800; font-size:14px; }
.city-card {
  border: 1px solid rgba(255,255,255,.13);
  border-radius: 20px;
  padding: 16px;
  background: rgba(15,23,42,.58);
  margin-bottom: 10px;
}
.city-card .city { font-size: 20px; font-weight: 850; }
.city-card .leader { font-size: 28px; font-weight: 900; margin-top: 8px; }
.city-card .meta { color: var(--text-soft); font-size: 13px; margin-top: 5px; }
.insight {
  border-left: 4px solid var(--accent);
  background: rgba(56,189,248,.10);
  padding: 12px 16px;
  border-radius: 14px;
  color: #e0f2fe;
  margin: 12px 0;
}
.risk {
  border-left-color: var(--down);
  background: rgba(245,158,11,.10);
  color: #fef3c7;
}
[data-testid="stMetric"] {
  background: rgba(255,255,255,.07);
  border: 1px solid rgba(255,255,255,.12);
  padding: 14px 16px;
  border-radius: 18px;
}
.stDataFrame, [data-testid="stTable"] { border-radius: 18px; overflow: hidden; }
.small-note { color: rgba(255,255,255,.62); font-size: 13px; }
</style>
""",
    unsafe_allow_html=True,
)


def file_mtime(path: Path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


@st.cache_data(show_spinner=False)
def load_features(mtime: float) -> pd.DataFrame:
    if not FEAT_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(FEAT_CSV)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "city", "candidate"])
    for col in ["news_count", "news_7d", "news_7d_prev", "news_momentum"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df.sort_values(["city", "candidate", "date"])


@st.cache_data(show_spinner=False)
def load_forecast(city: str, candidate: str, mtime: float) -> pd.DataFrame:
    fp = FORECAST_DIR / f"{city}_{candidate}_forecast.csv"
    if not fp.exists():
        return pd.DataFrame()
    df = pd.read_csv(fp)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.dropna(subset=["date"]).sort_values("date")


def latest_candidate_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    latest = df.sort_values("date").groupby(["city", "candidate"], as_index=False).tail(1).copy()
    total = df.groupby(["city", "candidate"], as_index=False)["news_count"].sum().rename(columns={"news_count": "total_news"})
    days = df.groupby(["city", "candidate"], as_index=False).size().rename(columns={"size": "sample_days"})
    latest = latest.merge(total, on=["city", "candidate"], how="left").merge(days, on=["city", "candidate"], how="left")
    latest["heat_score"] = latest["news_7d"] * 2 + latest["news_momentum"].clip(lower=0) + latest["news_count"]
    return latest.sort_values("heat_score", ascending=False)


def city_leaders(latest: pd.DataFrame) -> pd.DataFrame:
    if latest.empty:
        return latest
    return latest.sort_values(["city", "heat_score"], ascending=[True, False]).groupby("city", as_index=False).head(1)


def trend_word(momentum: float) -> str:
    if momentum >= 20:
        return "暴增"
    if momentum >= 5:
        return "升溫"
    if momentum <= -10:
        return "降溫"
    if momentum <= -1:
        return "微降"
    return "穩定"


def candidate_sentence(row: pd.Series) -> str:
    return (
        f"{row['city']}目前由 {row['candidate']} 取得最高聲量熱度，"
        f"近 7 日聲量 {int(row['news_7d'])}，"
        f"週對比動能 {int(row['news_momentum']):+d}，趨勢判讀為「{trend_word(row['news_momentum'])}」。"
    )


def make_city_chart(df: pd.DataFrame, city: str, candidates: list[str], days: int = 45) -> pd.DataFrame:
    city_df = df[(df["city"] == city) & (df["candidate"].isin(candidates))].copy()
    if city_df.empty:
        return pd.DataFrame()
    latest_date = city_df["date"].max()
    cutoff = latest_date - pd.Timedelta(days=days)
    chart = city_df[city_df["date"] >= cutoff].pivot_table(
        index="date", columns="candidate", values="news_count", aggfunc="sum", fill_value=0
    )
    return chart.sort_index()


def make_forecast_chart(city: str, candidates: list[str]) -> pd.DataFrame:
    chart = pd.DataFrame()
    for cand in candidates:
        fp = FORECAST_DIR / f"{city}_{cand}_forecast.csv"
        fc = load_forecast(city, cand, file_mtime(fp))
        if not fc.empty and "forecast_news_count" in fc.columns:
            one = fc[["date", "forecast_news_count"]].rename(columns={"forecast_news_count": cand}).set_index("date")
            chart = one if chart.empty else chart.join(one, how="outer")
    return chart.sort_index()


df = load_features(file_mtime(FEAT_CSV))

with st.sidebar:
    st.header("資料與操作")
    st.caption("這是 demo 版，不會覆蓋原本 app.py。")
    st.write(f"特徵表：{'✅' if FEAT_CSV.exists() else '❌'}")
    st.write(f"預測檔：{len(list(FORECAST_DIR.glob('*.csv')))} 個")
    if FEAT_CSV.exists():
        st.caption(f"更新時間戳：{int(file_mtime(FEAT_CSV))}")
    if st.button("重新跑 Pipeline", type="primary"):
        with st.spinner("Pipeline 執行中，可能需要數分鐘…"):
            proc = subprocess.run(
                [sys.executable, str(BASE_DIR / "run_pipeline.py")],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        if proc.returncode == 0:
            st.success("Pipeline 完成")
            st.cache_data.clear()
        else:
            st.error(f"Pipeline 失敗：exit {proc.returncode}")
        with st.expander("執行紀錄", expanded=proc.returncode != 0):
            st.code((proc.stdout or "") + "\n" + (proc.stderr or ""), language="text")

if df.empty:
    st.markdown(
        """
<div class="hero">
  <div class="eyebrow">Election Voice Radar</div>
  <div class="title">2026 六都選舉聲量戰情室</div>
  <div class="subtitle">目前找不到特徵資料，請先跑 pipeline 產生 data/features/voice_features.csv。</div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.stop()

latest = latest_candidate_rows(df)
leaders = city_leaders(latest)
top_hot = latest.iloc[0]
_risers = latest.sort_values("news_momentum", ascending=False)
_distinct_risers = _risers[_risers["candidate"] != top_hot["candidate"]]
top_riser = (_distinct_risers.iloc[0] if not _distinct_risers.empty else _risers.iloc[0])
_totals = latest.sort_values("total_news", ascending=False)
_distinct_totals = _totals[~_totals["candidate"].isin([top_hot["candidate"], top_riser["candidate"]])]
top_total = (_distinct_totals.iloc[0] if not _distinct_totals.empty else _totals.iloc[0])
latest_date = df["date"].max()

st.markdown(
    f"""
<div class="hero">
  <div class="eyebrow">Election Voice Radar · 2026</div>
  <div class="title">六都選舉聲量戰情室</div>
  <div class="subtitle">
    不先看模型、不先看表格。先回答：今天誰最熱、誰正在升溫、哪個城市最有看點。
    資料更新至 <b>{latest_date:%Y-%m-%d}</b>。
  </div>
  <div class="badge-row">
    <div class="badge">📡 新聞聲量監測</div>
    <div class="badge">🔥 近 7 日熱度</div>
    <div class="badge">📈 週對比動能</div>
    <div class="badge">🧪 LSTM 放在模型頁</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(
        f"""
<div class="story-card">
  <div class="label">今日最熱候選人</div>
  <strong>{top_hot['candidate']}</strong>
  <span>{top_hot['city']} · 近 7 日 {int(top_hot['news_7d'])} 則 · 動能 {int(top_hot['news_momentum']):+d}</span>
</div>
""",
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f"""
<div class="story-card">
  <div class="label">本週升溫最快</div>
  <strong>{top_riser['candidate']}</strong>
  <span>{top_riser['city']} · 週對比動能 {int(top_riser['news_momentum']):+d} · 趨勢 {trend_word(top_riser['news_momentum'])}</span>
</div>
""",
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f"""
<div class="story-card">
  <div class="label">累計曝光最高</div>
  <strong>{top_total['candidate']}</strong>
  <span>{top_total['city']} · 累計新聞 {int(top_total['total_news'])} 則 · 樣本 {int(top_total['sample_days'])} 天</span>
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown(f"<div class='insight'>一句話：{candidate_sentence(top_hot)}</div>", unsafe_allow_html=True)
if int(top_hot["sample_days"]) < 10:
    st.markdown(
        "<div class='insight risk'>注意：目前最熱候選人的樣本天數偏少，可能被單一新聞事件拉高；建議搭配城市戰情頁觀察趨勢線。</div>",
        unsafe_allow_html=True,
    )

tab_overview, tab_city, tab_model = st.tabs(["總覽", "城市戰情", "資料來源 / 模型"])

with tab_overview:
    st.subheader("六都目前戰況")
    cols = st.columns(3)
    for i, (_, row) in enumerate(leaders.sort_values("city").iterrows()):
        with cols[i % 3]:
            st.markdown(
                f"""
<div class="city-card">
  <div class="city">{row['city']}</div>
  <div class="leader">{row['candidate']}</div>
  <div class="meta">近 7 日 {int(row['news_7d'])} · 動能 {int(row['news_momentum']):+d} · {trend_word(row['news_momentum'])}</div>
</div>
""",
                unsafe_allow_html=True,
            )

    left, right = st.columns([1.15, 1])
    with left:
        st.subheader("今日聲量榜 Top 10")
        ranking = latest.head(10).copy()
        ranking["趨勢"] = ranking["news_momentum"].map(trend_word)
        st.dataframe(
            ranking[["city", "candidate", "news_7d", "news_momentum", "total_news", "sample_days", "趨勢"]].rename(
                columns={
                    "city": "城市",
                    "candidate": "候選人",
                    "news_7d": "近 7 日聲量",
                    "news_momentum": "週對比動能",
                    "total_news": "累計新聞",
                    "sample_days": "樣本天數",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
    with right:
        st.subheader("升溫 / 降溫雷達")
        risers = latest.sort_values("news_momentum", ascending=False).head(5)
        fallers = latest.sort_values("news_momentum", ascending=True).head(5)
        st.markdown("**升溫最快**")
        st.dataframe(
            risers[["city", "candidate", "news_momentum", "news_7d"]].rename(
                columns={"city": "城市", "candidate": "候選人", "news_momentum": "動能", "news_7d": "近 7 日"}
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("**降溫 / 低動能**")
        st.dataframe(
            fallers[["city", "candidate", "news_momentum", "news_7d"]].rename(
                columns={"city": "城市", "candidate": "候選人", "news_momentum": "動能", "news_7d": "近 7 日"}
            ),
            use_container_width=True,
            hide_index=True,
        )

with tab_city:
    cities = sorted(df["city"].dropna().unique().tolist())
    default_city = "台北市" if "台北市" in cities else cities[0]
    city = st.selectbox("選擇城市", cities, index=cities.index(default_city), key="city_select")
    city_latest = latest[latest["city"] == city].sort_values("heat_score", ascending=False)
    cands = city_latest["candidate"].tolist()
    selected = st.multiselect("候選人", cands, default=cands[: min(4, len(cands))])
    if not selected:
        st.info("請至少選一位候選人。")
    else:
        leader = city_latest[city_latest["candidate"].isin(selected)].iloc[0]
        st.markdown(f"<div class='insight'>{candidate_sentence(leader)}</div>", unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("城市領先聲量", leader["candidate"], f"近 7 日 {int(leader['news_7d'])}")
        k2.metric("週對比動能", f"{int(leader['news_momentum']):+d}", trend_word(leader["news_momentum"]))
        k3.metric("候選人數", len(cands))
        k4.metric("最新日期", f"{latest_date:%m/%d}")

        city_chart = make_city_chart(df, city, selected, days=60)
        st.subheader("近 60 日每日聲量")
        if city_chart.empty:
            st.info("沒有足夠資料可以繪圖。")
        else:
            st.line_chart(city_chart)

        st.subheader("候選人比較")
        compare = city_latest[city_latest["candidate"].isin(selected)].copy()
        compare["趨勢判讀"] = compare["news_momentum"].map(trend_word)
        st.dataframe(
            compare[["candidate", "news_7d", "news_momentum", "total_news", "sample_days", "趨勢判讀"]].rename(
                columns={
                    "candidate": "候選人",
                    "news_7d": "近 7 日聲量",
                    "news_momentum": "週對比動能",
                    "total_news": "累計新聞",
                    "sample_days": "樣本天數",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

with tab_model:
    st.subheader("資料與模型：放在最後，不搶首頁主角")
    st.markdown(
        """
<div class="small-note">
這頁給懂技術的人看：目前資料來源是新聞/RSS/Google News 類型資料，特徵表含 7 日 rolling 聲量與週對比動能；
LSTM 只作為未來 7 日聲量推估，不等於民調或勝率。
</div>
""",
        unsafe_allow_html=True,
    )
    cities = sorted(df["city"].dropna().unique().tolist())
    model_city = st.selectbox("查看模型城市", cities, index=cities.index("台北市") if "台北市" in cities else 0, key="model_city")
    model_cands = latest[latest["city"] == model_city].sort_values("heat_score", ascending=False)["candidate"].tolist()
    model_selected = st.multiselect("查看預測候選人", model_cands, default=model_cands[: min(3, len(model_cands))], key="model_candidates")
    fc_chart = make_forecast_chart(model_city, model_selected)
    if fc_chart.empty:
        st.info("所選候選人目前沒有 LSTM 預測檔。資料天數不足時會被模型跳過。")
    else:
        st.line_chart(fc_chart)

    with st.expander("原始 LSTM 預測圖"):
        if not model_selected:
            st.caption("請先選候選人。")
        cols = st.columns(2)
        for i, cand in enumerate(model_selected):
            png = PLOT_DIR / f"{model_city}_{cand}.png"
            if png.exists():
                cols[i % 2].image(str(png), caption=f"{model_city} · {cand}")
            else:
                cols[i % 2].info(f"{cand}：無預測圖")

    with st.expander("原始特徵資料"):
        st.dataframe(
            df.sort_values("date", ascending=False).head(300),
            use_container_width=True,
            hide_index=True,
        )
