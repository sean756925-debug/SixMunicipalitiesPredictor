# 2026 六都選戰媒體雷達

以新聞資料追蹤台灣六都市長選戰人物的媒體提及、城市內注意力占比、聲量動能、熱門議題與新聞原文。

> 本專案衡量的是媒體報導提及，不是民調、支持度、好感度或勝選機率。

## 功能

- 追蹤台北、新北、桃園、台中、台南、高雄六都
- 顯示近 7 日媒體提及與城市內注意力占比
- 比較候選人聲量動能與 7 日滾動趨勢
- 依標題關鍵字整理熱門議題
- 保留新聞標題、來源與原文連結
- 提供桌面與手機版單頁導覽
- 實驗性 LSTM 未來 7 日報導量估計（不是選情預測）

## 專案結構

```text
config/keywords.yaml
        ↓
scripts/crawl_sources.py
        ↓
data/raw/news_<timestamp>.json
        ↓
scripts/clean_and_aggregate.py
        ↓
data/processed/daily_news_volume.csv
        ↓
scripts/build_features.py
        ↓
data/features/voice_features.csv
        ↓
scripts/lstm_forecast.py
        ↓
data/forecast/*.csv + data/plots/*.png
```

主要入口：

- `app_public.py`：公開唯讀 Streamlit 介面
- `app.py`：管理／開發介面
- `run_pipeline.py`：抓取、清理、特徵與預測的完整 Pipeline
- `config/keywords.yaml`：六都及追蹤人物設定

Repository 內保留提交當下的資料快照、預測 CSV 與圖表，因此 clone 後可直接查看介面；重新執行 Pipeline 才會抓取最新資料。

## 安裝

建議使用 Python 3.11：

```bash
python3.11 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 啟動公開網站

```bash
source venv/bin/activate
streamlit run app_public.py
```

預設網址：`http://localhost:8501`

## 更新資料

```bash
source venv/bin/activate
python run_pipeline.py
```

注意：`run_pipeline.py` 開始時會清除 `data/raw`、`processed`、`features`、`forecast` 與 `plots` 內的舊輸出，再重建完整資料。若需要保留歷史快照，請先自行備份。

## 資料與模型限制

- 新聞 RSS 與 Google News 搜尋結果可能有來源上限、延遲或相關性擴張。
- 同一事件可能被多家媒體報導；介面顯示新聞時會以標題鍵值去重。
- 議題分類採標題關鍵字規則，不代表新聞情緒、候選人立場或政策判定。
- LSTM 僅依歷史報導量進行實驗性估計，無法預知提名、司法、辯論或突發事件。
- 追蹤名單是本站設定，不等於中選會正式登記或資格認定。

## 技術

Python、Streamlit、pandas、feedparser、TensorFlow/Keras、scikit-learn、matplotlib。
