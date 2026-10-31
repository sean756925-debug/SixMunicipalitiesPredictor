"""2026 六都選戰媒體雷達（公開唯讀版）。

產品口徑：解釋新聞注意力、議題與事件脈絡；不把聲量解讀為支持度、民調或勝率。
"""
from __future__ import annotations

from datetime import datetime
from html import escape
import glob
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import altair as alt
import pandas as pd
import streamlit as st
import yaml

BASE_DIR = Path(__file__).resolve().parent
FEAT_CSV = BASE_DIR / "data" / "features" / "voice_features.csv"
RAW_DIR = BASE_DIR / "data" / "raw"
FORECAST_DIR = BASE_DIR / "data" / "forecast"
PLOT_DIR = BASE_DIR / "data" / "plots"
KEYWORDS_YAML = BASE_DIR / "config" / "keywords.yaml"
POLICIES_JSON = BASE_DIR / "data" / "candidate_policies.json"
CITY_ORDER = ["台北市", "新北市", "桃園市", "台中市", "台南市", "高雄市"]

TOPIC_RULES = {
    "選戰攻防": r"選舉|參選|提名|初選|選戰|民調|造勢|競選|藍綠|國民黨|民進黨|民眾黨|黨內|辯論|罷免",
    "市政治理": r"市政|市府|議會|施政|預算|里長|區長|公共服務|行政",
    "交通建設": r"交通|捷運|道路|公路|鐵路|高鐵|機場|停車|通勤|公車|快速道路",
    "產業經濟": r"產業|經濟|就業|招商|園區|企業|觀光|市場|財政|投資|科技",
    "住宅育兒": r"住宅|居住|房價|社宅|育兒|托育|少子|婚育|教育|學校|長照|社福",
    "治安司法": r"治安|警察|司法|檢調|法院|起訴|判刑|弊案|貪污|詐騙|京華城",
    "環境能源": r"環境|能源|核電|空污|垃圾|淨零|氣候|光電|風電|水資源",
    "兩岸國防": r"兩岸|中國|國防|國安|共軍|台海|統戰|軍演|國軍",
}

st.set_page_config(
    page_title="2026 六都選戰媒體雷達",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

with st.container(key="theme_menu"):
    with st.popover("⋮", help="網站顯示設定", key="display_settings"):
        st.markdown("#### 🎨 網站配色")
        color_theme = st.radio(
            "網站配色",
            ["紫羅蘭", "海洋藍", "深夜"],
            key="color_theme",
            label_visibility="collapsed",
        )

st.markdown(
    """
<style>
:root {
  --ink:#16151c; --muted:#6f6b7a; --line:#e7e4ec; --paper:#fbfafc;
  --violet:#4c1d95; --violet2:#7c3aed; --blue:#2563eb; --rose:#e11d48;
  --green:#059669; --amber:#d97706;
}
.stApp { background:linear-gradient(180deg,#f7f4ff 0,#fff 440px); color:var(--ink); }
[data-testid="stHeader"] { background:rgba(255,255,255,.82); backdrop-filter:blur(14px); }
[data-testid="stMainMenuButton"] { display:none !important; }
.st-key-theme_menu {
  position:fixed !important; top:8px; right:16px; z-index:1000000;
  width:54px !important;
}
.st-key-theme_menu [data-testid="stPopoverButton"] {
  width:44px; height:40px; min-height:40px; padding:0; border-radius:12px;
  display:grid; place-items:center; line-height:1;
}
[data-testid="stPopoverBody"] {
  position:fixed !important; left:auto !important; right:12px !important; top:60px !important;
  transform:none !important; width:min(300px,calc(100vw - 24px)) !important;
  max-width:calc(100vw - 24px) !important;
}
.block-container { max-width:1280px; padding-top:1.5rem; padding-bottom:4rem; }
h1,h2,h3 { letter-spacing:-.035em; color:var(--ink); }
.hero { background:linear-gradient(130deg,#23123d 0%,#4c1d95 55%,#6d28d9 100%); color:white;
  border-radius:26px; padding:30px 32px; margin-bottom:14px; overflow:hidden; position:relative; }
.hero:after { content:""; position:absolute; width:300px; height:300px; border-radius:50%;
  right:-70px; top:-150px; background:rgba(255,255,255,.12); }
.eyebrow { font:600 12px/1.4 ui-monospace,monospace; letter-spacing:.14em; text-transform:uppercase; opacity:.72; }
.hero h1 { color:white; font-size:clamp(34px,5vw,58px); line-height:1; margin:10px 0 12px; }
.hero p { max-width:850px; font-size:17px; line-height:1.65; color:rgba(255,255,255,.82); margin:0; }
.chips { display:flex; flex-wrap:wrap; gap:8px; margin-top:18px; position:relative; z-index:1; }
.chip { display:inline-block; border:1px solid rgba(255,255,255,.25); border-radius:999px; padding:7px 12px;
  font-size:12px; color:white !important; text-decoration:none !important; transition:.18s ease; }
.chip:hover { background:rgba(255,255,255,.18); border-color:rgba(255,255,255,.62); transform:translateY(-1px); }
.section-anchor { scroll-margin-top:76px; }
[data-testid="stAppViewContainer"] { scroll-behavior:smooth; }
.back-to-top { position:fixed; right:18px; bottom:22px; z-index:9999; display:inline-flex; align-items:center;
  gap:5px; padding:10px 14px; border-radius:999px; background:#4c1d95; color:white !important;
  text-decoration:none !important; font-size:13px; font-weight:800; box-shadow:0 8px 24px rgba(76,29,149,.28); }
.back-to-top:hover { background:#6d28d9; transform:translateY(-1px); }
.section-nav { display:flex; justify-content:space-between; align-items:center; gap:10px; margin:24px 0 30px;
  padding-top:18px; border-top:1px solid var(--line); }
.section-nav a { flex:1; border:1px solid #ddd6fe; border-radius:14px; padding:10px 12px; color:#4c1d95 !important;
  background:#faf8ff; text-decoration:none !important; text-align:center; font-size:13px; font-weight:750; }
.section-nav a:hover { background:#ede9fe; border-color:#c4b5fd; }
.mobile-nav { display:none; }
.fresh { border-radius:16px; padding:12px 16px; margin:12px 0 18px; border:1px solid; font-size:14px; }
.fresh.ok { background:#ecfdf5; border-color:#a7f3d0; color:#065f46; }
.fresh.warn { background:#fff7ed; border-color:#fed7aa; color:#9a3412; }
.story { background:white; border:1px solid var(--line); border-radius:22px; padding:20px; min-height:164px; }
.story-link { display:block; color:inherit !important; text-decoration:none !important; }
.story-link .story { transition:.18s ease; }
.story-link:hover .story { border-color:#b9a4e8; box-shadow:0 10px 26px rgba(76,29,149,.10); transform:translateY(-2px); }
.story-link .meta:after { content:"  查看詳情 →"; color:var(--violet2); font-weight:700; white-space:nowrap; }
.story .label { color:var(--violet2); font-size:12px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; }
.story .big { font-size:30px; font-weight:800; letter-spacing:-.04em; margin:7px 0; }
.story .meta { color:var(--muted); font-size:14px; line-height:1.5; }
.forecast-shell { background:linear-gradient(135deg,#fff 0%,#f5f3ff 100%); border:1px solid #ddd6fe;
  border-radius:26px; padding:22px; margin:12px 0 18px; box-shadow:0 12px 34px rgba(76,29,149,.08); }
.forecast-head { display:flex; align-items:flex-start; justify-content:space-between; gap:18px; margin-bottom:16px; }
.forecast-head h2 { margin:2px 0 5px; font-size:30px; }
.forecast-head p { color:var(--muted); margin:0; font-size:14px; line-height:1.55; }
.countdown { flex:0 0 auto; min-width:145px; padding:13px 16px; border-radius:18px; text-align:center;
  color:white; background:linear-gradient(135deg,var(--violet),var(--violet2)); }
.countdown b { display:block; font-size:31px; line-height:1; margin-bottom:5px; }
.countdown span { font-size:12px; font-weight:750; opacity:.86; }
.forecast-card { background:white; border:1px solid var(--line); border-radius:18px; padding:15px 16px; margin-bottom:12px; min-height:142px; }
.forecast-card .city { color:var(--violet2); font-size:12px; font-weight:800; letter-spacing:.08em; }
.forecast-card .person { font-size:23px; font-weight:850; margin:5px 0; }
.forecast-card .value { color:var(--muted); font-size:13px; line-height:1.5; }
.forecast-card .delta-up { color:var(--rose); font-weight:800; }
.forecast-card .delta-down { color:var(--green); font-weight:800; }
.forecast-note { color:var(--muted); font-size:12px; line-height:1.55; margin-top:7px; }
.city-card { background:white; border:1px solid var(--line); border-radius:22px; padding:18px; margin-bottom:12px; min-height:190px; }
.city-title { font-size:21px; font-weight:800; margin-bottom:12px; }
.match-row { display:flex; justify-content:space-between; gap:8px; font-size:14px; margin:7px 0; }
.share-track { height:9px; border-radius:999px; background:#eeeaf5; overflow:hidden; margin:7px 0 12px; }
.share-fill { height:100%; background:linear-gradient(90deg,var(--violet2),#a78bfa); border-radius:999px; }
.share-fill.secondary { background:linear-gradient(90deg,#2563eb,#93c5fd); }
.city-note { color:var(--muted); font-size:12px; line-height:1.45; border-top:1px solid var(--line); padding-top:10px; }
.callout { background:#f5f3ff; border-left:4px solid var(--violet2); border-radius:14px; padding:13px 16px; margin:10px 0 16px; }
.topic-pill { display:inline-block; background:#ede9fe; color:#5b21b6; padding:4px 9px; border-radius:999px; font-size:12px; margin:2px; }
.headline { background:white; border:1px solid var(--line); border-radius:18px; padding:15px 17px; margin:9px 0; }
.headline a { color:#24143d; text-decoration:none; font-size:16px; font-weight:700; line-height:1.5; }
.headline a:hover { color:var(--blue); }
.headline-meta { color:var(--muted); font-size:12px; margin-top:8px; }
.source-grid { display:flex; gap:8px; flex-wrap:wrap; }
.source { background:#f5f4f7; border-radius:12px; padding:8px 11px; font-size:12px; }
[data-testid="stMetric"] { background:white; border:1px solid var(--line); padding:13px 15px; border-radius:18px; }
[data-testid="stTabs"] button { font-weight:700; }
.small { color:var(--muted); font-size:13px; line-height:1.65; }
.policy-intro { background:white; border:1px solid var(--line); border-radius:20px; padding:18px 20px; margin:10px 0 16px; }
.policy-status { display:inline-block; border-radius:999px; padding:5px 10px; margin-bottom:8px; background:#ede9fe; color:#5b21b6; font-size:12px; font-weight:800; }
.policy-card { background:white; border:1px solid var(--line); border-radius:18px; padding:17px; min-height:190px; }
.policy-card h4 { color:var(--ink); font-size:17px; margin:0 0 9px; }
.policy-card p { color:var(--muted); font-size:14px; line-height:1.6; min-height:68px; }
.policy-card a { color:var(--violet2) !important; font-size:13px; font-weight:750; text-decoration:none !important; }
.policy-note { color:var(--muted); background:#f5f4f7; border-radius:13px; padding:11px 13px; font-size:12px; line-height:1.55; margin-top:12px; }
.policy-city-title { margin:30px 0 12px; padding:12px 16px; border-radius:16px; color:white; background:linear-gradient(100deg,var(--violet),var(--violet2)); font-size:22px; font-weight:850; }
.policy-jumps { display:flex; flex-wrap:wrap; gap:8px; margin:8px 0 18px; }
.policy-jumps a { border:1px solid var(--line); border-radius:999px; padding:7px 12px; background:white; color:var(--violet) !important; font-size:13px; font-weight:800; text-decoration:none !important; }
.policy-jumps a:hover { border-color:var(--violet2); background:#f5f3ff; }
.policy-person { background:white; border:1px solid var(--line); border-radius:20px; padding:18px; margin-bottom:14px; min-height:430px; box-shadow:0 7px 22px rgba(35,18,61,.05); }
.policy-person h3 { margin:2px 0 7px; font-size:23px; }
.policy-person-summary { color:var(--muted); font-size:13px; line-height:1.6; min-height:42px; margin-bottom:12px; }
.policy-item { border-top:1px solid var(--line); padding:11px 0 8px; }
.policy-item b { display:block; color:var(--ink); font-size:15px; margin-bottom:4px; }
.policy-item p { color:var(--muted); font-size:13px; line-height:1.55; margin:0 0 5px; min-height:auto; }
.policy-item a { color:var(--violet2) !important; font-size:12px; font-weight:750; text-decoration:none !important; }
.policy-person .policy-note { margin-top:8px; }
@media(max-width:700px){
  .hero{padding:24px 20px}.block-container{padding-left:1rem;padding-right:1rem;padding-bottom:7rem}.story{min-height:auto}
  .hero .chips { display:flex; flex-wrap:nowrap; overflow-x:auto; padding-bottom:5px; scrollbar-width:thin;
    -webkit-overflow-scrolling:touch; }
  .hero .chip { flex:0 0 auto; white-space:nowrap; }
  .back-to-top { right:14px; bottom:76px; padding:9px 12px; font-size:12px; }
  .section-nav { margin:18px 0 24px; gap:6px; }
  .section-nav a { padding:9px 5px; font-size:11px; }
  .mobile-nav { position:fixed; left:0; right:0; bottom:0; z-index:9998; display:flex; align-items:stretch; justify-content:space-around;
    padding:7px max(6px,env(safe-area-inset-right)) calc(7px + env(safe-area-inset-bottom)) max(6px,env(safe-area-inset-left));
    background:rgba(255,255,255,.96); border-top:1px solid #ddd6fe; box-shadow:0 -6px 22px rgba(35,18,61,.12);
    backdrop-filter:blur(14px); }
  .mobile-nav a { flex:1 1 0; min-width:0; min-height:49px; color:#4c1d95 !important; text-decoration:none !important;
    display:flex; flex-direction:column; align-items:center; justify-content:center; gap:2px;
    text-align:center; font-size:10px; font-weight:800; line-height:1.1; }
  .mobile-nav .nav-icon { width:24px; height:24px; display:grid; place-items:center; margin:0;
    font-family:Arial,"Noto Sans Symbols 2",sans-serif; font-size:18px; font-weight:400; line-height:1; }
  .forecast-shell { padding:17px; }
  .forecast-head { display:block; }
  .forecast-head h2 { font-size:25px; }
  .countdown { margin-top:13px; width:100%; }
}
</style>
""",
    unsafe_allow_html=True,
)

if color_theme == "海洋藍":
    st.markdown(
        """
<style>
:root { --violet:#075985; --violet2:#0284c7; --blue:#0ea5e9; --line:#ccecf4; }
.stApp { background:linear-gradient(180deg,#e6f9ff 0,#ffffff 480px); }
.hero { background:linear-gradient(130deg,#083344 0%,#0369a1 55%,#0891b2 100%); }
.back-to-top { background:#0369a1; box-shadow:0 8px 24px rgba(3,105,161,.28); }
.section-nav a { color:#075985 !important; background:#f0f9ff; border-color:#bae6fd; }
.section-nav a:hover { background:#e0f2fe; border-color:#7dd3fc; }
.callout { background:#ecfeff; border-left-color:#0891b2; }
.topic-pill,.policy-status { background:#cffafe; color:#155e75; }
.share-fill { background:linear-gradient(90deg,#0284c7,#22d3ee); }
.policy-city-title { background:linear-gradient(100deg,#075985,#06b6d4); }
@media(max-width:700px){.mobile-nav{border-top-color:#bae6fd}.mobile-nav a{color:#075985 !important}}
</style>
""",
        unsafe_allow_html=True,
    )
elif color_theme == "深夜":
    st.markdown(
        """
<style>
:root { --ink:#f4f0ff; --muted:#c4bdd2; --line:#40384d; --paper:#17131d; --violet:#7c3aed; --violet2:#c4b5fd; }
.stApp { background:linear-gradient(180deg,#1c1329 0,#120f16 440px); color:var(--ink); }
[data-testid="stHeader"] { background:rgba(18,15,22,.88); }
.hero { background:linear-gradient(130deg,#111827 0%,#312e81 55%,#6d28d9 100%); }
.story,.city-card,.headline,.policy-intro,.policy-card,.policy-person,.policy-jumps a,[data-testid="stMetric"] { background:#211b29; box-shadow:none; }
.forecast-shell { background:linear-gradient(135deg,#211b29 0%,#292035 100%); border-color:#514263; box-shadow:none; }
.forecast-card { background:#211b29; }
.section-nav a { background:#251d31; border-color:#514263; color:#ddd6fe !important; }
.section-nav a:hover { background:#352643; }
.callout { background:#2b2038; }
.topic-pill,.policy-status { background:#3a2850; color:#ddd6fe; }
.headline a { color:#f4f0ff; }
.source,.policy-note { background:#2d2735; }
.share-track { background:#40384d; }
.fresh.ok { background:#12342b; border-color:#26735a; color:#a7f3d0; }
.fresh.warn { background:#3d2818; border-color:#8f5d2b; color:#fed7aa; }
@media(max-width:700px){.mobile-nav{background:rgba(24,19,30,.97);border-top-color:#514263}.mobile-nav a{color:#ddd6fe !important}}
</style>
""",
        unsafe_allow_html=True,
    )


def file_mtime(path: Path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


def active_candidate_map() -> dict[str, list[str]]:
    if not KEYWORDS_YAML.exists():
        return {}
    with KEYWORDS_YAML.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return {city: raw[city] for city in CITY_ORDER if city in raw}


@st.cache_data(show_spinner=False)
def load_policies(mtime: float) -> dict:
    if not POLICIES_JSON.exists():
        return {"updated_at": "", "disclaimer": "", "people": []}
    with POLICIES_JSON.open("r", encoding="utf-8") as f:
        data = json.load(f)
    data["people"] = [p for p in data.get("people", []) if p.get("city") and p.get("name")]
    return data


@st.cache_data(show_spinner=False)
def load_features(mtime: float) -> pd.DataFrame:
    if not FEAT_CSV.exists():
        return pd.DataFrame()
    frame = pd.read_csv(FEAT_CSV)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.dropna(subset=["date", "city", "candidate"])
    for col in ["news_count", "news_7d", "news_7d_prev", "news_momentum"]:
        frame[col] = pd.to_numeric(frame.get(col, 0), errors="coerce").fillna(0)
    return frame.sort_values(["city", "candidate", "date"])


def latest_raw_file() -> Path | None:
    files = sorted(RAW_DIR.glob("news_*.json"))
    return files[-1] if files else None


def clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", str(title or "")).strip()
    return re.sub(r"\s+-\s+[^-]{2,35}$", "", title).strip()


def publisher_from_title(title: str, source: str) -> str:
    match = re.search(r"\s+-\s+([^-]{2,35})$", str(title or ""))
    return match.group(1).strip() if match else str(source or "未知來源")


def topic_labels(title: str) -> list[str]:
    labels = [label for label, pattern in TOPIC_RULES.items() if re.search(pattern, title)]
    return labels or ["其他"]


@st.cache_data(show_spinner=False)
def load_articles(path_str: str, mtime: float, active_pairs: tuple[tuple[str, str], ...]) -> pd.DataFrame:
    if not path_str:
        return pd.DataFrame()
    path = Path(path_str)
    with path.open("r", encoding="utf-8") as f:
        items = json.load(f)
    allowed = set(active_pairs)
    rows = []
    now = pd.Timestamp.now(tz="Asia/Taipei")
    for item in items:
        city, candidate = item.get("city"), item.get("candidate")
        if (city, candidate) not in allowed:
            continue
        published = pd.to_datetime(item.get("published"), utc=True, errors="coerce")
        if pd.isna(published):
            continue
        published = published.tz_convert("Asia/Taipei")
        if published.year < 2020 or published > now + pd.Timedelta(days=1):
            continue
        title_raw = str(item.get("title") or "").strip()
        if not title_raw:
            continue
        title = clean_title(title_raw)
        link = str(item.get("link") or "").strip()
        rows.append({
            "published_at": published,
            "date": published.tz_localize(None).normalize(),
            "city": city,
            "candidate": candidate,
            "source": str(item.get("source") or "未知來源"),
            "publisher": publisher_from_title(title_raw, item.get("source")),
            "title": title,
            "title_raw": title_raw,
            "link": link,
            "direct_mention": candidate in title_raw,
            "topics": topic_labels(title),
        })
    if not rows:
        return pd.DataFrame()
    articles = pd.DataFrame(rows)
    articles["dedupe_key"] = articles["title"].str.lower().str.replace(r"\W+", "", regex=True)
    return articles.sort_values("published_at", ascending=False)


@st.cache_data(show_spinner=False)
def load_forecast(city: str, candidate: str, mtime: float) -> pd.DataFrame:
    path = FORECAST_DIR / f"{city}_{candidate}_forecast.csv"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["forecast_news_count"] = pd.to_numeric(frame["forecast_news_count"], errors="coerce").clip(lower=0)
    return frame.dropna(subset=["date", "forecast_news_count"]).sort_values("date")


def forecast_snapshot(current: pd.DataFrame, candidate_map: dict[str, list[str]]) -> pd.DataFrame:
    """Aggregate each candidate's seven-day forecast for homepage storytelling."""
    rows = []
    for city, candidates in candidate_map.items():
        for candidate in candidates:
            path = FORECAST_DIR / f"{city}_{candidate}_forecast.csv"
            forecast = load_forecast(city, candidate, file_mtime(path))
            if forecast.empty:
                continue
            rows.append({
                "city": city,
                "candidate": candidate,
                "forecast_7d": float(forecast["forecast_news_count"].sum()),
                "forecast_daily_peak": float(forecast["forecast_news_count"].max()),
                "forecast_start": forecast["date"].min(),
                "forecast_end": forecast["date"].max(),
            })
    if not rows:
        return pd.DataFrame()
    result = pd.DataFrame(rows).merge(
        current[["city", "candidate", "news_7d"]], on=["city", "candidate"], how="left"
    )
    result["news_7d"] = result["news_7d"].fillna(0)
    result["forecast_change"] = result["forecast_7d"] - result["news_7d"]
    result["city_forecast_total"] = result.groupby("city")["forecast_7d"].transform("sum")
    result["forecast_share"] = result["forecast_7d"].div(
        result["city_forecast_total"].replace(0, pd.NA)
    ).fillna(0) * 100
    result["city"] = pd.Categorical(result["city"], categories=CITY_ORDER, ordered=True)
    return result.sort_values(["city", "forecast_7d"], ascending=[True, False])


def candidate_snapshot(frame: pd.DataFrame) -> pd.DataFrame:
    latest = frame.sort_values("date").groupby(["city", "candidate"], as_index=False).tail(1).copy()
    totals = frame.groupby(["city", "candidate"], as_index=False).agg(
        article_mentions=("news_count", "sum"),
        active_days=("news_count", lambda s: int((s > 0).sum())),
        coverage_days=("date", "nunique"),
    )
    latest = latest.merge(totals, on=["city", "candidate"], how="left")
    latest["city_7d_total"] = latest.groupby("city")["news_7d"].transform("sum")
    latest["city_prev_total"] = latest.groupby("city")["news_7d_prev"].transform("sum")
    latest["mention_share"] = latest["news_7d"].div(latest["city_7d_total"].replace(0, pd.NA)).fillna(0) * 100
    latest["prev_share"] = latest["news_7d_prev"].div(latest["city_prev_total"].replace(0, pd.NA)).fillna(0) * 100
    latest["share_change"] = latest["mention_share"] - latest["prev_share"]
    return latest.sort_values(["city", "news_7d"], ascending=[True, False])


def trend_text(value: float) -> str:
    if value >= 10:
        return "明顯升溫"
    if value > 0:
        return "小幅升溫"
    if value <= -10:
        return "明顯降溫"
    if value < 0:
        return "小幅降溫"
    return "持平"


def city_matchups(snapshot: pd.DataFrame) -> list[dict]:
    result = []
    for city in CITY_ORDER:
        group = snapshot[snapshot["city"] == city]
        if group.empty:
            continue
        group = group.sort_values("mention_share", ascending=False)
        first = group.iloc[0]
        second = group.iloc[1] if len(group) > 1 else None
        gap = float(first["mention_share"] - second["mention_share"]) if second is not None else 100.0
        result.append({"city": city, "first": first, "second": second, "gap": gap})
    return sorted(result, key=lambda x: x["gap"])


def actual_and_forecast_rolling(
    frame: pd.DataFrame, city: str, candidates: list[str], history_days: int = 28
) -> pd.DataFrame:
    """Join historical 7-day rolling mentions to a rolling forecast extension."""
    rows: list[dict] = []
    city_frame = frame[frame["city"] == city]
    if city_frame.empty:
        return pd.DataFrame()
    latest = city_frame["date"].max()
    cutoff = latest - pd.Timedelta(days=history_days - 1)
    for candidate in candidates:
        actual = city_frame[city_frame["candidate"] == candidate].sort_values("date")
        path = FORECAST_DIR / f"{city}_{candidate}_forecast.csv"
        forecast = load_forecast(city, candidate, file_mtime(path))
        if actual.empty or forecast.empty:
            continue
        for _, point in actual[actual["date"] >= cutoff].iterrows():
            rows.append({
                "date": point["date"], "candidate": candidate,
                "rolling_mentions": float(point["news_7d"]), "phase": "歷史實績",
            })
        daily = pd.concat([
            actual[["date", "news_count"]].rename(columns={"news_count": "count"}),
            forecast[["date", "forecast_news_count"]].rename(columns={"forecast_news_count": "count"}),
        ]).sort_values("date")
        daily["rolling_mentions"] = daily["count"].rolling(7, min_periods=1).sum()
        projected = daily[daily["date"] > latest]
        # Repeat the latest actual point so the dashed model line connects to history.
        rows.append({
            "date": latest, "candidate": candidate,
            "rolling_mentions": float(actual.iloc[-1]["news_7d"]), "phase": "模型延伸",
        })
        for _, point in projected.iterrows():
            rows.append({
                "date": point["date"], "candidate": candidate,
                "rolling_mentions": float(point["rolling_mentions"]), "phase": "模型延伸",
            })
    return pd.DataFrame(rows)


def topic_summary(articles: pd.DataFrame) -> pd.DataFrame:
    if articles.empty:
        return pd.DataFrame(columns=["議題", "去重標題數"])
    exploded = articles.drop_duplicates("dedupe_key").explode("topics")
    return exploded.groupby("topics").size().sort_values(ascending=False).rename("去重標題數").reset_index().rename(columns={"topics": "議題"})


def key_headlines(articles: pd.DataFrame, limit: int = 8) -> pd.DataFrame:
    if articles.empty:
        return articles
    direct = articles[articles["direct_mention"]].copy()
    pool = direct if not direct.empty else articles.copy()
    return pool.drop_duplicates("dedupe_key").sort_values("published_at", ascending=False).head(limit)


def render_headlines(articles: pd.DataFrame, limit: int = 6) -> None:
    rows = key_headlines(articles, limit)
    if rows.empty:
        st.info("目前沒有可顯示的新聞標題。")
        return
    for _, row in rows.iterrows():
        title = escape(row["title"])
        link = escape(row["link"], quote=True)
        tags = "".join(f"<span class='topic-pill'>{escape(t)}</span>" for t in row["topics"][:2])
        link_html = f"<a href='{link}' target='_blank' rel='noopener'>{title}</a>" if link else f"<b>{title}</b>"
        dt = row["published_at"].strftime("%m/%d %H:%M")
        st.markdown(
            f"<div class='headline'>{link_html}<div class='headline-meta'>{dt} · {escape(row['publisher'])} · {escape(row['candidate'])}　{tags}</div></div>",
            unsafe_allow_html=True,
        )


candidate_map = active_candidate_map()
active_pairs = tuple((city, cand) for city, cands in candidate_map.items() for cand in cands)
active_candidates = {cand for _, cand in active_pairs}
df = load_features(file_mtime(FEAT_CSV))
if not df.empty and active_pairs:
    df = df[df.apply(lambda r: (r["city"], r["candidate"]) in set(active_pairs), axis=1)].copy()
raw_file = latest_raw_file()
articles = load_articles(str(raw_file) if raw_file else "", file_mtime(raw_file) if raw_file else 0, active_pairs)
policy_data = load_policies(file_mtime(POLICIES_JSON))
policies = policy_data.get("people", [])
policies = [p for p in policies if (p.get("city"), p.get("name")) in set(active_pairs)]

with st.sidebar:
    st.header("資料狀態")
    st.write(f"追蹤城市：{len(candidate_map)}")
    st.write(f"確定參選人（本站追蹤）：{len(active_pairs)}／23")
    st.write(f"候選人－新聞標記：{len(articles):,}")
    st.write(f"有政策資料的候選人：{len(policies)}")
    st.caption("公開唯讀版，不提供重新抓取或覆蓋資料的操作。")
    st.divider()
    st.caption("指標口徑：本系統歸類至各候選人的新聞結果數；不代表支持、好感或投票意向。本站追蹤的 12 位均為中選會審定的確定參選人，但不是完整 23 人名單。")

if df.empty:
    st.error("目前找不到可用的聲量特徵資料，請先執行 Pipeline。")
    st.stop()

snapshot = candidate_snapshot(df)
forecast_summary = forecast_snapshot(snapshot, candidate_map)
latest_date = df["date"].max()
today = pd.Timestamp.now(tz="Asia/Taipei").tz_localize(None).normalize()
stale_days = max(0, int((today - latest_date.normalize()).days))
election_day = pd.Timestamp("2026-11-28")
days_to_election = max(0, int((election_day - today).days))
matchups = city_matchups(snapshot)
attention = snapshot.sort_values(["news_7d", "news_momentum"], ascending=False).iloc[0]
rising_pool = snapshot[snapshot["news_momentum"] > 0].sort_values("news_momentum", ascending=False)
riser = rising_pool.iloc[0] if not rising_pool.empty else snapshot.sort_values("news_momentum", ascending=False).iloc[0]
closest = matchups[0]

def nav_chip(section_id: str, label: str) -> str:
    """Return an in-page anchor so navigation never reloads the Streamlit app."""
    return f'<a class="chip" href="#{section_id}">{label}</a>'

st.markdown(
    """
<div id="top" class="section-anchor"></div>
<a class="back-to-top" href="#top" aria-label="回到頁面頂端">↑ 回頂端</a>
<nav class="mobile-nav" aria-label="手機版主要導覽">
  <a href="#top"><span class="nav-icon" aria-hidden="true">⌂</span><span>首頁</span></a>
  <a href="#forecast"><span class="nav-icon" aria-hidden="true">⌁</span><span>預測</span></a>
  <a href="#overview"><span class="nav-icon" aria-hidden="true">▦</span><span>六都</span></a>
  <a href="#city"><span class="nav-icon" aria-hidden="true">◎</span><span>城市</span></a>
  <a href="#policies"><span class="nav-icon" aria-hidden="true">☷</span><span>政見</span></a>
</nav>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<div class="hero">
  <div class="eyebrow">Election Media Radar · Taiwan 2026</div>
  <h1>六都選戰媒體雷達</h1>
  <p>選戰最後 30 天：用歷史新聞標記量推估未來 7 日媒體注意力，再比較六都追蹤候選人、議題變化與帶動聲量的關鍵事件。</p>
  <div class="chips">
    {nav_chip("forecast", "未來 7 日預測")}{nav_chip("overview", "六都候選人比較")}{nav_chip("city", "7 日媒體注意力")}
    {nav_chip("policies", "政見與公開主張")}{nav_chip("news", "新聞與議題")}{nav_chip("method", "資料口徑與方法")}
  </div>
</div>
""",
    unsafe_allow_html=True,
)

fresh_class = "ok" if stale_days <= 1 else "warn"
fresh_message = "資料為最新或僅延遲 1 天" if stale_days <= 1 else f"資料已延遲 {stale_days} 天，閱讀時請留意時效"
st.markdown(
    f"<div class='fresh {fresh_class}'><b>資料截至 {latest_date:%Y-%m-%d}</b> · {fresh_message}。本頁衡量的是候選人相關新聞標記量，不是民調、支持度或勝選機率。</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='callout'><b>確定參選範圍：</b>依中選會 2026-10-16 資格審定資料，六都市長確定參選人共 23 位；本站目前追蹤其中 12 位，這 12 位均已確定參選，但本站不是完整候選人名單。"
    " <a href='https://web.cec.gov.tw/central/article/65213' target='_blank' rel='noopener'>查看中選會審定公告 ↗</a></div>",
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"<a class='story-link' href='#city'><div class='story'><div class='label'>近 7 日最受關注</div><div class='big'>{escape(attention['candidate'])}</div><div class='meta'>{attention['city']} · {int(attention['news_7d'])} 筆標記 · 本站同城占比 {attention['mention_share']:.1f}%</div></div></a>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<a class='story-link' href='#city'><div class='story'><div class='label'>最近 7 日增幅最大</div><div class='big'>{escape(riser['candidate'])}</div><div class='meta'>{riser['city']} · 較前 7 日 {int(riser['news_momentum']):+d} 次 · {trend_text(riser['news_momentum'])}</div></div></a>", unsafe_allow_html=True)
with c3:
    second_name = closest["second"]["candidate"] if closest["second"] is not None else "—"
    st.markdown(f"<a class='story-link' href='#overview'><div class='story'><div class='label'>媒體注意力最接近</div><div class='big'>{closest['city']}</div><div class='meta'>{escape(closest['first']['candidate'])} vs {escape(second_name)} · 占比差 {closest['gap']:.1f} 個百分點</div></div></a>", unsafe_allow_html=True)

st.markdown("<div class='callout'>真正值得看的不是「誰聲量大」，而是：哪個城市突然升溫、由哪些議題或新聞事件帶動，以及媒體注意力是否持續。</div>", unsafe_allow_html=True)

st.markdown("<div id='forecast' class='section-anchor'></div>", unsafe_allow_html=True)
if forecast_summary.empty:
    st.info("目前沒有可用的未來 7 日預測資料。")
else:
    forecast_start = forecast_summary["forecast_start"].min()
    forecast_end = forecast_summary["forecast_end"].max()
    st.markdown(
        f"""
<div class="forecast-shell">
  <div class="forecast-head">
    <div><div class="eyebrow" style="color:var(--violet2)">CORE FORECAST · LSTM</div>
    <h2>未來 7 日聲量預測</h2>
    <p>根據各候選人歷史每日新聞標記量，逐日推估 {forecast_start:%m/%d}–{forecast_end:%m/%d} 的媒體注意力。數字是模型估計值，不是支持度或選票。</p></div>
    <div class="countdown"><b>{days_to_election}</b><span>天後投票 · 11/28</span></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    national_leader = forecast_summary.sort_values("forecast_7d", ascending=False).iloc[0]
    biggest_rise = forecast_summary.sort_values("forecast_change", ascending=False).iloc[0]
    total_forecast = forecast_summary["forecast_7d"].sum()
    f1, f2, f3 = st.columns(3)
    f1.metric("7 日模型估計值最高", national_leader["candidate"], f"{national_leader['city']} · 約 {national_leader['forecast_7d']:.0f} 次")
    f2.metric("模型估計增幅最大", biggest_rise["candidate"], f"較最近 7 日 {biggest_rise['forecast_change']:+.0f} 次")
    f3.metric(f"{len(forecast_summary)} 位具預測資料候選人估計值加總", f"約 {total_forecast:.0f} 次", f"{forecast_start:%m/%d}–{forecast_end:%m/%d}")

    st.markdown("#### 六都預測焦點 × 7 日滾動新聞標記趨勢")
    st.caption("先看各城市的預測焦點，再沿著最近 28 日實績曲線觀察模型延伸。虛線為加入每日模型估計後的 7 日滾動量；前 6 個未來點仍包含部分歷史實績。")
    city_leaders = forecast_summary.groupby("city", sort=False, observed=True).head(1)
    forecast_tabs = st.tabs(city_leaders["city"].tolist())
    for city_tab, (_, row) in zip(forecast_tabs, city_leaders.iterrows()):
        with city_tab:
            delta_class = "delta-up" if row["forecast_change"] >= 0 else "delta-down"
            delta_word = "增加" if row["forecast_change"] >= 0 else "減少"
            card = f"""
<div class="forecast-card"><div class="city">{escape(row['city'])} · 預測聲量最高</div>
<div class="person">{escape(row['candidate'])}</div>
<div class="value">未來 7 日約 <b>{row['forecast_7d']:.0f}</b> 次 · 本站同城預測占比 {row['forecast_share']:.1f}%<br>
較最近 7 日 <span class="{delta_class}">{delta_word} {abs(row['forecast_change']):.0f} 次</span></div></div>"""
            st.markdown(card, unsafe_allow_html=True)
            available = forecast_summary[forecast_summary["city"] == row["city"]].sort_values("forecast_7d", ascending=False)
            default_people = available["candidate"].head(min(3, len(available))).tolist()
            forecast_people = st.multiselect(
                "比較候選人", available["candidate"].tolist(), default=default_people,
                key=f"forecast_people_{row['city']}"
            )
            combined = actual_and_forecast_rolling(df, row["city"], forecast_people)
            if combined.empty:
                st.info("請至少選擇一位有歷史與預測資料的候選人。")
            else:
                trend = alt.Chart(combined).mark_line(point=False, strokeWidth=3).encode(
                    x=alt.X("date:T", title=None, axis=alt.Axis(format="%m/%d", labelAngle=0)),
                    y=alt.Y("rolling_mentions:Q", title="7 日滾動新聞標記"),
                    color=alt.Color("candidate:N", title="追蹤候選人"),
                    strokeDash=alt.StrokeDash(
                        "phase:N", title="區間",
                        scale=alt.Scale(domain=["歷史實績", "模型延伸"], range=[[1, 0], [7, 5]]),
                    ),
                    tooltip=[
                        alt.Tooltip("date:T", title="日期", format="%Y-%m-%d"),
                        alt.Tooltip("candidate:N", title="候選人"),
                        alt.Tooltip("phase:N", title="區間"),
                        alt.Tooltip("rolling_mentions:Q", title="7 日滾動新聞標記", format=".1f"),
                    ],
                ).properties(height=350)
                boundary = alt.Chart(pd.DataFrame({"date": [latest_date]})).mark_rule(
                    color="#7c3aed", strokeDash=[3, 3], strokeWidth=2
                ).encode(x="date:T")
                st.altair_chart((trend + boundary).interactive(), width="stretch")
                forecast_table = available[available["candidate"].isin(forecast_people)].copy()
                forecast_table["模型方向"] = forecast_table["forecast_change"].map(lambda x: "升溫" if x > 0 else ("降溫" if x < 0 else "持平"))
                st.dataframe(
                    forecast_table[["candidate", "news_7d", "forecast_7d", "forecast_change", "forecast_share", "模型方向"]].rename(columns={
                        "candidate":"追蹤候選人", "news_7d":"最近 7 日", "forecast_7d":"未來 7 日預測", "forecast_change":"預測增減", "forecast_share":"本站同城預測占比 %"
                    }),
                    hide_index=True, width="stretch",
                    column_config={
                        "未來 7 日預測":st.column_config.NumberColumn(format="%.1f"),
                        "預測增減":st.column_config.NumberColumn(format="%+.1f"),
                        "本站同城預測占比 %":st.column_config.NumberColumn(format="%.1f"),
                    },
                )
    st.markdown("<div class='forecast-note'>模型用途：提早發現媒體注意力可能升溫或降溫的候選人，供後續追查議題與事件。單變量 LSTM 無法預知辯論、提名、司法與突發事件，因此不提供勝率，也不把預測聲量當成支持度。</div>", unsafe_allow_html=True)

st.markdown(
    "<div class='section-nav'><a href='#top'>← 回首頁</a><a href='#top'>↑ 回頂端</a><a href='#overview'>六都比較 →</a></div>",
    unsafe_allow_html=True,
)

st.markdown("<div id='overview' class='section-anchor'></div>", unsafe_allow_html=True)
st.subheader("六都追蹤候選人媒體注意力比較")
st.caption("占比＝該候選人近 7 日新聞標記 ÷ 同城市本站追蹤候選人近 7 日新聞標記；只描述本站追蹤範圍內的媒體注意力。")
cols = st.columns(3)
for index, item in enumerate(sorted(matchups, key=lambda x: CITY_ORDER.index(x["city"]))):
    first, second = item["first"], item["second"]
    second_html = "尚無第二位追蹤候選人"
    if second is not None:
        second_html = (
            f"<div class='match-row'><span>{escape(second['candidate'])}</span>"
            f"<b>{second['mention_share']:.1f}% · {int(second['news_7d'])} 次</b></div>"
            f"<div class='share-track'><div class='share-fill secondary' "
            f"style='width:{min(100,second['mention_share']):.1f}%'></div></div>"
        )
    note = f"兩位追蹤候選人占比差 {item['gap']:.1f} 個百分點；{escape(first['candidate'])}最近 7 日較前 7 日{trend_text(first['news_momentum'])}。"
    html = f"""
<div class='city-card'><div class='city-title'>{item['city']}</div>
<div class='match-row'><span>{escape(first['candidate'])}</span><b>{first['mention_share']:.1f}% · {int(first['news_7d'])} 次</b></div>
<div class='share-track'><div class='share-fill' style='width:{min(100,first['mention_share']):.1f}%'></div></div>
{second_html}<div class='city-note'>{note}</div></div>"""
    with cols[index % 3]:
        st.markdown(html, unsafe_allow_html=True)

left, right = st.columns([1.2, 1])
with left:
    st.subheader("12 位追蹤候選人近 7 日新聞標記排行")
    table = snapshot.sort_values("news_7d", ascending=False).copy()
    table["趨勢"] = table["news_momentum"].map(trend_text)
    st.dataframe(
        table[["city", "candidate", "news_7d", "mention_share", "news_momentum", "趨勢"]].rename(columns={
            "city":"城市", "candidate":"追蹤候選人", "news_7d":"7 日標記", "mention_share":"本站同城占比 %", "news_momentum":"較前 7 日"
        }), hide_index=True, width="stretch", column_config={"本站同城占比 %":st.column_config.NumberColumn(format="%.1f")}
    )
with right:
    st.subheader("最近 14 日跨城市新聞議題")
    topics = topic_summary(articles[articles["date"] >= latest_date - pd.Timedelta(days=13)] if not articles.empty else articles)
    if topics.empty:
        st.info("沒有可用的新聞標題。")
    else:
        st.bar_chart(topics.set_index("議題")["去重標題數"], horizontal=True)
        st.caption("僅涵蓋本站追蹤候選人；依標題關鍵字分類，一篇可涉及多個議題，同一事件的不同標題仍可能分別計入。")

st.markdown(
    "<div class='section-nav'><a href='#top'>← 回首頁</a><a href='#top'>↑ 回頂端</a><a href='#city'>城市分析 →</a></div>",
    unsafe_allow_html=True,
)

st.markdown("<div id='city' class='section-anchor'></div>", unsafe_allow_html=True)
cities = [city for city in candidate_map if city in set(df["city"])]
default_index = cities.index("台北市") if "台北市" in cities else 0
city = st.selectbox("選擇城市", cities, index=default_index)
city_snapshot = snapshot[snapshot["city"] == city].sort_values("mention_share", ascending=False)
candidates = city_snapshot["candidate"].tolist()
selected = st.multiselect("比較候選人", candidates, default=candidates)
if not selected:
    st.info("請至少選擇一位候選人。")
else:
    selected_rows = city_snapshot[city_snapshot["candidate"].isin(selected)]
    k1, k2, k3, k4 = st.columns(4)
    lead = selected_rows.iloc[0]
    k1.metric("7 日新聞標記最多", lead["candidate"], f"{int(lead['news_7d'])} 次")
    k2.metric("新聞標記占比", f"{lead['mention_share']:.1f}%", f"{lead['share_change']:+.1f}pp")
    k3.metric("最近 7 日較前 7 日", f"{int(lead['news_momentum']):+d}", trend_text(lead["news_momentum"]))
    city_articles = articles[articles["city"] == city] if not articles.empty else pd.DataFrame()
    city_unique_headlines = city_articles.drop_duplicates("dedupe_key") if not city_articles.empty else city_articles
    k4.metric("可追溯去重標題", f"{len(city_unique_headlines):,}", "標題與原文")

    compare = selected_rows.copy()
    compare["趨勢"] = compare["news_momentum"].map(trend_text)
    st.subheader("追蹤候選人比較")
    st.dataframe(compare[["candidate", "news_7d", "mention_share", "share_change", "news_momentum", "active_days", "趨勢"]].rename(columns={
        "candidate":"追蹤候選人", "news_7d":"7 日標記", "mention_share":"本站同城占比 %", "share_change":"占比變化 pp",
        "news_momentum":"較前 7 日", "active_days":"全期間有標記天數"
    }), hide_index=True, width="stretch", column_config={"本站同城占比 %":st.column_config.NumberColumn(format="%.1f"), "占比變化 pp":st.column_config.NumberColumn(format="%+.1f")})

    st.markdown(
        f"<div class='callout'><b>{escape(city)}新聞脈絡：</b>目前有 {len(city_articles):,} 筆可追溯標題。為避免重複，議題分布與新聞原文統一放在下方「新聞與議題」區。 "
        "<a href='#news'>前往查看與篩選 ↓</a></div>",
        unsafe_allow_html=True,
    )

st.markdown(
    "<div class='section-nav'><a href='#overview'>← 六都比較</a><a href='#top'>↑ 回頂端</a><a href='#policies'>政見主張 →</a></div>",
    unsafe_allow_html=True,
)

st.markdown("<div id='policies' class='section-anchor'></div>", unsafe_allow_html=True)
st.subheader("政見與公開主張")
st.caption("先看候選人主張，再對照媒體注意力。卡片狀態描述政策資料類型，不代表參選資格；本頁顯示者均為本站追蹤且已確定參選的候選人。")
if not policies:
    st.info("目前沒有可顯示的政策資料。")
else:
    policy_cities = [c for c in candidate_map if any(p["city"] == c for p in policies)]
    city_links = "".join(f"<a href='#policy-{escape(c)}'>{escape(c)}</a>" for c in policy_cities)
    st.markdown(f"<div class='policy-jumps'>{city_links}</div>", unsafe_allow_html=True)
    for policy_city in policy_cities:
        city_policies = [p for p in policies if p["city"] == policy_city]
        st.markdown(
            f"<div id='policy-{escape(policy_city)}' class='policy-city-title section-anchor'>{escape(policy_city)}｜{len(city_policies)} 位確定參選人</div>",
            unsafe_allow_html=True,
        )
        policy_cols = st.columns(2)
        for index, person in enumerate(city_policies):
            item_html = ""
            for item in person.get("items", []):
                source_url = escape(str(item.get("source_url", "")), quote=True)
                source_name = escape(str(item.get("source_name", "查看來源")))
                source_link = f"<a href='{source_url}' target='_blank' rel='noopener'>來源：{source_name} ↗</a>" if source_url else ""
                item_html += (
                    f"<div class='policy-item'><b>{escape(item['title'])}</b>"
                    f"<p>{escape(item['content'])}</p>{source_link}</div>"
                )
            note_html = f"<div class='policy-note'><b>閱讀提醒：</b>{escape(person['note'])}</div>" if person.get("note") else ""
            card = (
                f"<div class='policy-person'><span class='policy-status'>{escape(person['status'])}</span>"
                f"<h3>{escape(person['name'])}</h3>"
                f"<div class='policy-person-summary'>{escape(person['summary'])}</div>"
                f"{item_html}{note_html}</div>"
            )
            with policy_cols[index % 2]:
                st.markdown(card, unsafe_allow_html=True)
    st.caption(f"政策資料更新：{policy_data.get('updated_at', '未標示')}。{policy_data.get('disclaimer', '')}")

st.markdown(
    "<div class='section-nav'><a href='#city'>← 城市分析</a><a href='#top'>↑ 回頂端</a><a href='#news'>新聞與議題 →</a></div>",
    unsafe_allow_html=True,
)

st.markdown("<div id='news' class='section-anchor'></div>", unsafe_allow_html=True)
st.subheader("新聞與議題")
st.caption("城市與議題篩選會同時更新議題分布、來源分布及新聞原文，避免在不同段落重複呈現同一批資料。")
filter_city = st.selectbox("城市篩選", ["全部六都"] + list(candidate_map.keys()), key="news_city")
view = articles.copy()
if filter_city != "全部六都" and not view.empty:
    view = view[view["city"] == filter_city]
topic_options = ["全部議題"] + list(TOPIC_RULES.keys()) + ["其他"]
selected_topic = st.selectbox("議題篩選", topic_options)
if selected_topic != "全部議題" and not view.empty:
    view = view[view["topics"].apply(lambda labels: selected_topic in labels)]

left, right = st.columns([1.25, .75])
with left:
    st.subheader("新聞原文")
    render_headlines(view, 12)
with right:
    st.subheader("議題分布")
    summary = topic_summary(view)
    if not summary.empty:
        st.bar_chart(summary.set_index("議題")["去重標題數"], horizontal=True)
    st.subheader("來源分布")
    if not view.empty:
        source_counts = view.drop_duplicates("dedupe_key")["publisher"].value_counts().head(10)
        st.bar_chart(source_counts, horizontal=True)
    st.markdown("<div class='small'>標題分類僅用於導覽，不判斷新聞正負面，也不代表候選人的政見或立場。Google News 搜尋結果可能包含未直接出現姓名的相關新聞；首頁與頭條優先呈現直接姓名命中的項目。</div>", unsafe_allow_html=True)

st.markdown(
    "<div class='section-nav'><a href='#city'>← 城市分析</a><a href='#top'>↑ 回頂端</a><a href='#method'>資料方法 →</a></div>",
    unsafe_allow_html=True,
)

st.markdown("<div id='method' class='section-anchor'></div>", unsafe_allow_html=True)
st.subheader("資料口徑與限制")
st.markdown(
    """
- 本頁統計本系統歸類至各候選人的新聞結果；部分 Google News 相關結果未必在標題直接出現姓名，因此不等同嚴格的姓名提及次數，也不是支持度、好感度或投票意向。
- 同一則新聞若同時涉及多人，可能分別計入；新聞清單會以標題去重後呈現。
- Google News 有搜尋結果上限與相關性擴張，累計數不適合當成長期人氣排行。
- 議題分類來自標題關鍵字，可一篇多標籤；沒有進行情緒或立場判定。
- 六都市長官方資格審定名單共 23 人；本站追蹤其中 12 位確定參選人，並非完整候選人名單。
- 政策頁依公開資料區分正式政見、現任施政重點、近期公開主張與尚待公布；摘要不等於候選人完整政見書。
"""
)
q1, q2, q3, q4 = st.columns(4)
q1.metric("資料涵蓋", f"{df['date'].min():%Y-%m-%d}", f"至 {latest_date:%Y-%m-%d}")
q2.metric("確定參選人（本站追蹤）", f"{len(active_pairs)}／23")
q3.metric("特徵資料", f"{len(df):,} 列")
q4.metric("原始標記新聞", f"{len(articles):,} 筆")

with st.expander("預測模型說明與限制"):
    st.markdown("""
- 模型：各候選人獨立的單變量 LSTM，以最近 7 個日曆日序列逐日遞迴預測未來 7 日新聞標記量。
- 用途：找出值得優先追蹤的媒體注意力變化，不是選票、民調、支持度或勝選機率。
- 限制：目前沒有納入候選人行程、民調、議題情緒或突發事件，也尚未展示正式回測誤差與可信區間。
- 解讀：預測上升代表模型依歷史軌跡推估報導可能增加；實際結果仍可能因事件快速改變。
""")

with st.expander("資料品質檢查"):
    feature_people = set(df["candidate"].unique())
    raw_people = set(articles["candidate"].unique()) if not articles.empty else set()
    st.write(f"設定候選人數：{len(active_candidates)}；特徵資料候選人數：{len(feature_people)}；新聞資料候選人數：{len(raw_people)}")
    missing_raw = sorted(feature_people - raw_people)
    if missing_raw:
        st.warning("沒有原始新聞可追溯：" + "、".join(missing_raw))
    else:
        st.success("所有目前顯示候選人都有原始新聞資料可追溯。")
    st.caption(f"原始檔：{raw_file.name if raw_file else '無'}")

st.markdown(
    "<div class='section-nav'><a href='#news'>← 新聞與議題</a><a href='#top'>↑ 回頂端</a><a href='#overview'>六都比較 →</a></div>",
    unsafe_allow_html=True,
)
