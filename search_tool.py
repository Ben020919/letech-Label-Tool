import streamlit as st
import pandas as pd
import os
import urllib.parse
import re
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ================= 匯入追蹤工具 =================
try:
    from usage_tracker import log_action 
except ImportError:
    def log_action(action_name): pass

# ================= 核心設定 =================
DEFAULT_DB_FILE = "Barcode.xlsx.csv"

@st.cache_data
def load_data():
    if not os.path.exists(DEFAULT_DB_FILE): return None
    try:
        df = pd.read_csv(DEFAULT_DB_FILE, dtype=str)
        for col in ['ProductCode', 'Name', 'Barcode']:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str).str.strip()
                if col in ['ProductCode', 'Barcode']:
                    df[col] = df[col].apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)
        return df
    except Exception: return None

# ================= 🌟 速度優化：重用瀏覽器資源 =================
@st.cache_resource
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox") 
    chrome_options.add_argument("--disable-dev-shm-usage") 
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.page_load_strategy = 'eager' # 快速加載模式
    
    if shutil.which("chromium"): chrome_options.binary_location = shutil.which("chromium")
    elif shutil.which("chromium-browser"): chrome_options.binary_location = shutil.which("chromium-browser")
    
    driver_path = shutil.which("chromedriver") or shutil.which("chromedriver-linux64")
    service = Service(driver_path) if driver_path else Service(ChromeDriverManager().install())
    service.log_path = os.devnull
    
    return webdriver.Chrome(service=service, options=chrome_options)

# ================= 🌟 圖片搜尋邏輯 (7波段進化) =================
@st.cache_data(show_spinner=False, ttl=86400)
def get_hktvmall_image_url(original_name):
    driver = get_driver()
    
    # 1. 前置處理：切掉結尾的 "x 2"、"x2"
    # 這能解決 "泰國 雙豬嘜 脆豬肉絲 150g x 2" 搜尋失敗的問題
    clean_name = re.sub(r'\s*[xX*]\s*\d+\s*$', '', original_name).strip()
    
    def do_search(keyword):
        try:
            encoded_name = urllib.parse.quote(str(keyword).strip())
            driver.get(f"https://www.hktvmall.com/hktv/zh/search_a?keyword={encoded_name}")
            wait = WebDriverWait(driver, 3) # 縮短等待時間
            selectors = ".product-brief img, img[itemprop='image'], .productImage, .item-image img"
            img_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selectors)))
            return img_element.get_attribute("src")
        except: return None

    # 執行波段搜尋
    # 波段 1: 原名搜尋 (含括號)
    res = do_search(clean_name)
    if res: return res
    
    # 波段 2: 脫掉前面的括號
    step2 = re.sub(r'^[\(（].*?[\)）]\s*', '', clean_name).strip()
    if step2 != clean_name:
        res = do_search(step2)
        if res: return res
        
    # 波段 3: 脫掉後面的括號
    step3 = re.sub(r'\s*[\(（][^()（）]*[\)）]$', '', step2).strip()
    if step3 != step2:
        res = do_search(step3)
        if res: return res
        
    # 波段 4: 砍掉連字號 (-)
    step4 = re.sub(r'\s*[-－].*$', '', step3).strip()
    if step4 != step3:
        res = do_search(step4)
        if res: return res

    # 波段 5: 砍掉重量容量與國家
    step5 = re.sub(r'^(韓國|日本|美國|澳洲|英國|德國|法國|台灣|泰國|紐西蘭)\s*', '', step4)
    step5 = re.sub(r'\s*\d+(\.\d+)?\s*(ml|g|kg|l|oz|毫升|克|件|片|樽|罐|包|人份).*$', '', step5, flags=re.IGNORECASE).strip()
    if step5 != step4:
        res = do_search(step5)
        if res: return res
        
    # 波段 6: 純中文打擊 (解決特殊品牌名如「雙豬嘜」)
    chinese_only = "".join(re.findall(r'[\u4e00-\u9fff]+', step5))
    if len(chinese_only) >= 3:
        res = do_search(chinese_only)
        if res: return res
        
    return None

# ================= UI 組件 =================
def generate_card_html(row, img_html):
    return f"""
    <div class="result-card">
        <div class="card-img-container">{img_html}</div>
        <div class="card-info">
            <div class="card-label">SKU (ProductCode)</div>
            <div class="card-value">{row['ProductCode']}</div>
            <div class="card-label">Barcode</div>
            <div class="card-value">{row['Barcode']}</div>
            <div class="card-name">{row['Name']}</div>
        </div>
    </div>
    """

def show_search_barcode_page():
    st.markdown("""
        <style>
            .result-card { display: flex; flex-direction: row; align-items: center; background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 15px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
            .card-img-container { width: 110px; height: 110px; flex-shrink: 0; margin-right: 20px; display: flex; align-items: center; justify-content: center; background-color: #f8f9fa; border-radius: 8px; border: 1px solid #eee; overflow: hidden; }
            .card-img-container img { max-width: 100%; max-height: 100%; object-fit: contain; }
            .loading-text { color: #007bff; font-size: 12px; font-weight: bold; animation: pulse 1.5s infinite; }
            @keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } }
            .card-info { flex-grow: 1; min-width: 0; }
            .card-label { color: #888; font-size: 11px; font-weight: bold; margin-bottom: 2px; text-transform: uppercase; }
            .card-value { color: #333; font-size: 15px; margin-bottom: 8px; font-family: monospace; }
            .card-name { color: #2c3e50; font-weight: 700; font-size: 16px; line-height: 1.4; border-top: 1px solid #eee; padding-top: 10px; }
            @media screen and (max-width: 768px) { .result-card { flex-direction: column; align-items: flex-start; } .card-img-container { margin-right: 0; margin-bottom: 15px; width: 100%; height: 120px; } }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🔍 Search Barcode System")
    df = load_data()
    if df is None:
        st.error(f"❌ 找不到資料庫 `{DEFAULT_DB_FILE}`")
        return

    user_input = st.text_input("Please Enter SKU / Barcode / Name:", placeholder="Enter Terms...")

    if user_input:
        log_action("Search_Action") 
        query = user_input.strip()
        mask = (df['ProductCode'].str.contains(query, case=False, na=False) | 
                df['Barcode'].str.contains(query, case=False, na=False) |
                df['Name'].str.contains(query, case=False, na=False))
        results = df[mask]

        if not results.empty:
            st.success(f"✅ Found {len(results)} Data")
            
            # 🌟 秒出文字資料
            placeholders = []
            for _, row in results.iterrows():
                ph = st.empty()
                ph.markdown(generate_card_html(row, '<span class="loading-text">⏳ 加載中...</span>'), unsafe_allow_html=True)
                placeholders.append((ph, row))

            # 🌟 背景快速抓圖
            for ph, row in placeholders:
                current_name = str(row['Name'])
                img_url = get_hktvmall_image_url(current_name)
                final_html = f'<img src="{img_url}" />' if img_url else '<span style="color:#ccc">暫無圖片</span>'
                ph.markdown(generate_card_html(row, final_html), unsafe_allow_html=True)
        else:
            st.warning("❌ No Data Found")
