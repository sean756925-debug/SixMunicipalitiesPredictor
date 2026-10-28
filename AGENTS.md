# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Commands

Run the full pipeline (crawl → clean → features → forecast):

```powershell
.\venv\Scripts\Activate.ps1
python run_pipeline.py
```

Launch the Streamlit dashboard (reads `data/` and can trigger the pipeline via a sidebar button):

```powershell
streamlit run app.py
```

Run an individual stage standalone (useful when iterating on one step without re-crawling):

```powershell
python -m scripts.crawl_sources        # not directly runnable; import only
python -m scripts.build_features       # has __main__ guard
```

To re-run a single stage without invoking the others, edit `run_pipeline.py` or call the function from a REPL — only `build_features.py` has a `__main__` entry point; the other scripts expose functions (`crawl_all_sources`, `clean_and_aggregate`, `run_lstm`) that must be imported.

No test suite, linter, or build system is configured.

## Architecture

The project is a four-stage batch pipeline orchestrated by `run_pipeline.py`. Each stage reads from the previous stage's output directory and writes to the next, so stages can be re-run independently as long as upstream artifacts exist.

```
config/keywords.yaml  →  crawl_sources  →  data/raw/news_<ts>.json
                                          ↓
                                  clean_and_aggregate
                                          ↓
                          data/processed/daily_news_volume.csv
                                          ↓
                                    build_features
                                          ↓
                          data/features/voice_features.csv
                                          ↓
                                       run_lstm
                                          ↓
                  data/forecast/<city>_<cand>_forecast.csv + data/plots/*.png
```

Key behaviors to know:

- **`run_pipeline.py` deletes prior outputs** (`data/raw|processed|features|plots|forecast/*`) via `clean_old_files()` at every run. Re-running the full pipeline is destructive to previous artifacts — work off a copy if you need history.
- **`crawl_sources.py`** pulls from hardcoded Taiwanese politics RSS feeds (LTN, TVBS, SET, UDN, FTV) plus a Google News search per (city, candidate) from `config/keywords.yaml`. The `news_rss_sources.yaml` config exists but is **not currently read** — RSS URLs are inline in the script.
- **`clean_and_aggregate.py`** expects per-item `city`, `candidate`, `source` fields, but `crawl_sources.py` does **not** tag items with these fields. As a result, the cleaning step's `dropna(subset=["city","candidate"])` drops everything from the RSS feeds and most Google News items — this is a known gap, not a bug to "fix" without understanding the intended tagging logic.
- **`build_features.py`** computes 7-day rolling news volume and momentum per (city, candidate). All sentiment/poll/engagement features (`positive_ratio`, `poll_support`, etc.) are stubbed to constants — placeholders for future signal sources.
- **`lstm_forecast.py`** trains a fresh per-(city, candidate) Keras LSTM (window=7, 30 epochs) from scratch on each run, forecasts 7 days ahead via autoregressive rollout, and skips series with <10 data points. Chinese characters in plots require the `Microsoft JhengHei` font (Windows-only by default).

## Environment

- Windows-only paths and conventions; `venv/` is the expected virtualenv directory.
- Stack: `feedparser`, `pandas`, `pyyaml`, `scikit-learn`, `tensorflow` (Keras), `matplotlib`.
- All scripts use `Path(__file__).resolve().parent.parent` as the base dir, so they can be run from any CWD.
