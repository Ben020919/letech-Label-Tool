import json
import os
import streamlit as st

# --- 修改 1：使用絕對路徑，確保伺服器找得到檔案 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATS_FILE = os.path.join(BASE_DIR, "usage_stats.json")

def load_stats():
    """從 JSON 檔案讀取統計數據"""
    if not os.path.exists(STATS_FILE):
        return {}
    try:
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        # 如果讀取失敗，在後台印出錯誤
        print(f"Error loading stats: {e}")
        return {}

def save_stats(stats):
    """將統計數據寫入 JSON 檔案"""
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=4)
    except Exception as e:
        # --- 修改 2：如果有寫入錯誤，直接顯示在網頁上方便除錯 ---
        st.error(f"⚠️ 無法寫入統計數據！權限錯誤或路徑錯誤: {e}")
        print(f"Error saving stats: {e}")

def log_action(action_name):
    """
    記錄動作次數
    """
    stats = load_stats()
    current_count = stats.get(action_name, 0)
    stats[action_name] = current_count + 1
    save_stats(stats)
