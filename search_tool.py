import streamlit as st
import pandas as pd
import os
import urllib.parse
import re
import shutil
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import streamlit.components.v1 as components

# ================= 匯入追蹤工具 =================
try:
    from usage_tracker import log_action 
except ImportError:
    def log_action(action_name): pass

# ================= 設定固定檔案名稱 =================
DEFAULT_DB_FILE = "Barcode.xlsx.csv"

@st.cache_data
def load_data():
    if not os.path.exists(DEFAULT_DB_FILE): return None
    try:
        df = pd.read_csv(DEFAULT_DB_FILE, dtype=str)
        cols_to_ensure = ['ProductCode', 'Name', 'Barcode']
        for col in cols_to_ensure:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str).str.strip()
                if col in ['ProductCode', 'Barcode']:
                    df[col] = df[col].apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)
            else:
                df[col] = ""
        return df
    except Exception: return None

# ================= 🌟 採用你提供的 15 秒長等待邏輯 =================
@st.cache_data(show_spinner=False, ttl=604800)
def get_hktvmall_image_final(original_product_name):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    if shutil.which("chromium"): chrome_options.binary_location = shutil.which("chromium")
    elif shutil.which("chromium-browser"): chrome_options.binary_location = shutil.which("chromium-browser")
        
    driver_path = shutil.which("chromedriver") or shutil.which("chromedriver-linux64")
    service = Service(driver_path) if driver_path else Service(ChromeDriverManager().install())
    service.log_path = os.devnull
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    def do_search(keyword):
        if not keyword: return None
        encoded_name = urllib.parse.quote(str(keyword).strip())
        search_url = f"https://www.hktvmall.com/hktv/zh/search_a?keyword={encoded_name}"
        driver.get(search_url)
        try:
            # 使用你成功腳本中的 15 秒長等待
            wait = WebDriverWait(driver, 15)
            css_selectors = ".product-brief img, img[itemprop='image'], .productImage, .item-image img"
            img_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selectors)))
            
            # 優先嘗試 data-src，解決澳洲原糖的延遲加載問題
            real_url = img_element.get_attribute("data-src") or img_element.get_attribute("src")
            if real_url and real_url.startswith("//"):
                real_url = "https:" + real_url
            return real_url
        except:
            return None

    try:
        # 優先用原名搜尋 (不做任何修改)
        res = do_search(original_product_name)
        if res: return res
        
        # 備用：清理 x2 等字眼
        clean_name = re.sub(r'\s*[xX*]\s*\d+\s*$', '', original_product_name).strip()
        if clean_name != original_product_name:
            res = do_search(clean_name)
            if res: return res
            
        return None
    finally:
        driver.quit()

# ================= HTML 卡片產生器 =================
def generate_card_html(row, img_html):
    name = row.get('Name', 'Unknown')
    sku = row.get('ProductCode', 'N/A')
    barcode = row.get('Barcode', 'N/A')
    
    return f"""
    <div class="result-card">
        <div class="card-img-container">{img_html}</div>
        <div class="card-info">
            <div class="card-label">SKU</div>
            <div class="card-value">{sku}</div>
            <div class="card-label">Barcode</div>
            <div class="card-value">{barcode}</div>
            <div class="card-name">{name}</div>
        </div>
    </div>
    """

# ================= 🌟 重要：確保函數名稱與 main.py 一致 =================
def show_search_barcode_page():
    st.markdown("""
        <style>
            .result-card { display: flex; flex-direction: row; align-items: center; background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 15px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
            .card-img-container { width: 110px; height: 110px; flex-shrink: 0; margin-right: 20px; display: flex; align-items: center; justify-content: center; background-color: #f8f9fa; border-radius: 8px; border: 1px solid #eee; overflow: hidden; }
            .card-img-container img { max-width: 100%; max-height: 100%; object-fit: contain; }
            .loading-text { color: #007bff; font-size: 13px; font-weight: bold; animation: pulse 1.5s infinite; }
            @keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } }
            .card-info { flex-grow: 1; min-width: 0; }
            .card-label { color: #888; font-size: 11px; font-weight: bold; margin-bottom: 2px; text-transform: uppercase; }
            .card-value { color: #333; font-size: 15px; margin-bottom: 8px; word-break: break-all; font-family: monospace; }
            .card-name { color: #2c3e50; font-weight: 700; font-size: 16px; line-height: 1.4; border-top: 1px solid #eee; padding-top: 10px; margin-top: 5px; }
            @media screen and (max-width: 768px) { .result-card { flex-direction: column; align-items: flex-start; } .card-img-container { margin-right: 0; margin-bottom: 15px; width: 100%; height: 150px; } }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🔍 Search Barcode System")
    
    df = load_data()
    if df is None:
        st.error("❌ 找不到 Barcode.xlsx.csv")
        return

    user_input = st.text_input("Please Enter Keywords:", placeholder="SKU / Barcode / Name")

    if user_input:
        log_action("Search_Action") 
        query = user_input.strip()
        mask = (df['ProductCode'].str.contains(query, case=False, na=False) | 
                df['Barcode'].str.contains(query, case=False, na=False) |
                df['Name'].str.contains(query, case=False, na=False))
        results = df[mask]

        if not results.empty:
            st.success(f"✅ Found {len(results)} Data")
            placeholders = []
            for idx, row in results.iterrows():
                ph = st.empty()
                ph.markdown(generate_card_html(row, '<span class="loading-text">⏳ 正在載入圖片...</span>'), unsafe_allow_html=True)
                placeholders.append((ph, row))

            for ph, row in placeholders:
                img_url = get_hktvmall_image_final(str(row['Name']))
                final_img_html = f'<img src="{img_url}" />' if img_url else '<span style="color:#aaa">無圖片</span>'
                ph.markdown(generate_card_html(row, final_img_html), unsafe_allow_html=True)
        else:
            st.warning("❌ No Data Found")

# 如果需要獨立執行
if __name__ == "__main__":
    show_search_barcode_page()
