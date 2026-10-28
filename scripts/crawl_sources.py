import os
import json
import feedparser
import requests
from datetime import datetime
from urllib.parse import quote
import yaml

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) ElectionPredictor/1.0"
}


def fetch_feed(url, label):
    """Fetch RSS with an explicit timeout, then parse the complete response body."""
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if feed.bozo and not feed.entries:
            raise ValueError(f"RSS 解析失敗: {feed.bozo_exception}")
        return feed.entries
    except Exception as e:
        print(f"⚠️ RSS 抓取失敗：{label}\n理由: {e}")
        return []


def crawl_all_sources():
    # 讀關鍵字
    with open("config/keywords.yaml", "r", encoding="utf-8") as f:
        keywords = yaml.safe_load(f)

    items = []

    # 可直接解析的官方政治 RSS。TVBS、SET、FTV 的舊端點截至
    # 2026-10-21 已改回傳 404/HTML/防護頁；其新聞仍會由下方的
    # Google News 候選人查詢涵蓋，避免每次執行等待失效端點。
    rss_feeds = [
        ("LTN",  "https://news.ltn.com.tw/rss/politics.xml"),
        ("UDN",  "https://udn.com/rssfeed/news/2/6638?ch=news"),
    ]

    rss_items = []
    for source, url in rss_feeds:
        print(f"📡 RSS：{source}")
        for entry in crawl_rss(url):
            entry["source"] = source
            rss_items.append(entry)

    # RSS 是綜合政治新聞，沒有預先標定 city/candidate，
    # 用 keywords.yaml 的關鍵字在標題中比對來標 tag；
    # 一篇可能命中多組 (city, candidate)，每組各算一筆。
    for entry in rss_items:
        title = entry.get("title", "")
        matched = False
        for city, candidates in keywords.items():
            for candidate in candidates:
                # 只以候選人姓名歸類；若只命中城市，不能把同一篇新聞
                # 複製到該城市的每位候選人，否則聲量會被灌成相同數字。
                if candidate in title:
                    tagged = dict(entry)
                    tagged["city"] = city
                    tagged["candidate"] = candidate
                    items.append(tagged)
                    matched = True
        if not matched:
            # 沒命中任何關鍵字的綜合政治新聞，保留但不 tag
            items.append(entry)

    # Google News: 每組 query 直接帶上對應的 city/candidate
    for city, candidates in keywords.items():
        for candidate in candidates:
            query = f"{city} {candidate}"
            print(f"🔎 Google News：{query}")
            for entry in crawl_google_news(query):
                entry["city"] = city
                entry["candidate"] = candidate
                entry["source"] = "GoogleNews"
                items.append(entry)

    # 儲存
    os.makedirs("data/raw", exist_ok=True)
    fname = datetime.now().strftime("news_%Y%m%d_%H%M%S.json")
    fpath = f"data/raw/{fname}"

    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Done. Saved → {os.path.abspath(fpath)} (共 {len(items)} 筆)")
    print("✅ FINISH: Crawl News\n")


def crawl_rss(url):
    return [{
        "title": entry.title,
        "link": entry.link,
        "published": entry.get("published", ""),
    } for entry in fetch_feed(url, url)]


def crawl_google_news(query):
    # Google News 的時間條件必須放在 q 參數內；獨立的 &when= 會被忽略。
    search_query = f"{query} when:180d"
    url = f"https://news.google.com/rss/search?q={quote(search_query)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    return [{
        "title": entry.title,
        "link": entry.link,
        "published": entry.get("published", "")
    } for entry in fetch_feed(url, f"Google News / {query}")]
