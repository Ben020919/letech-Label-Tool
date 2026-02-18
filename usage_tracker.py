import json
import os
import streamlit as st

STATS_FILE = "usage_stats.json"

def load_stats():
    """從 JSON 檔案讀取統計數據"""
    if not os.path.exists(STATS_FILE):
        return {}
    try:
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_stats(stats):
    """將統計數據寫入 JSON 檔案"""
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving stats: {e}")

def log_action(action_name):
    """
    記錄動作次數
    用法: log_action("Yummy_Upload")
    """
    stats = load_stats()
    current_count = stats.get(action_name, 0)
    stats[action_name] = current_count + 1
    save_stats(stats)