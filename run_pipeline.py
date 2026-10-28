from datetime import datetime
import os, glob

from scripts.crawl_sources import crawl_all_sources
from scripts.clean_and_aggregate import clean_and_aggregate
from scripts.build_features import build_features
from scripts.lstm_forecast import run_lstm

def clean_old_files():
    print("\n==============================")
    print("▶ CLEAN: 舊資料清除")
    print("==============================\n")

    patterns = [
        "data/raw/*.json",
        "data/processed/*.csv",
        "data/features/*.csv",
        "data/plots/*.png",
        "data/forecast/*.csv"
    ]

    removed = 0
    for p in patterns:
        for f in glob.glob(p):
            os.remove(f)
            removed += 1

    print(f"🧹 清除 {removed} 個舊檔案\n")

print("=== Election Predictor Pipeline Started ===")
print(f"Time: {datetime.now():%Y-%m-%d %H:%M:%S}")

clean_old_files()
crawl_all_sources()
clean_and_aggregate()
build_features()
run_lstm()

print("\n🎉 Pipeline 全部完成！")
