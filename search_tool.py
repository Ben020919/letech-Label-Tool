import streamlit as st
import pandas as pd
import os
import urllib.parse
import base64
import requests
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import streamlit.components.v1 as components

# ================= 1. 匯入追蹤工具 =================
try:
    from usage_tracker import log_action 
except ImportError:
    def log_action(action_name): pass

# ================= 2. 設定固定檔案名稱 =================
DEFAULT_DB_FILE = "Barcode.xlsx.csv"

# @st.cache_data
def load_data():
    if not os.path.exists(DEFAULT_DB_FILE): return None
    try:
        df = pd.read_csv(DEFAULT_DB_FILE, dtype=str)
        cols_to_ensure = ['ProductCode', 'Name', 'Barcode']
        for col in list(df.columns):
            if col in cols_to_ensure:
                df[col] = df[col].fillna('').astype(str).str.strip()
                if col in ['ProductCode', 'Barcode']:
                    df[col] = df[col].apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)
        return df
    except Exception: return None

# ================= 3. 核心爬蟲 (完全移植你的成功版本) =================
# @st.cache_data(show_spinner=False, ttl=604800)
def get_hktvmall_image_final(product_name):
    # 完全使用你 hktv_scraper.py 的設定
    encoded_name = urllib.parse.quote(str(product_name).strip())
    search_url = f"https://www.hktvmall.com/hktv/zh/search_a?keyword={encoded_name}"
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    service.log_path = os.devnull
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get(search_url)
        wait = WebDriverWait(driver, 15)
        # 完全使用你成功的精準選擇器
        img_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".product-brief img")))
        img_url = img_element.get_attribute("src")
        return img_url
    except Exception as e:
        print(f"爬蟲抓取失敗 ({product_name}): {e}")
        return None
    finally:
        driver.quit()

# ================= 4. HTML 卡片渲染器 =================
def generate_card_html(row, img_html):
    name = row.get('Name', 'Unknown')
    sku = row.get('ProductCode', 'N/A')
    barcode = row.get('Barcode', 'N/A')
    return f"""
    <div class="result-card">
        <div class="card-img-container">{img_html}</div>
        <div class="card-info">
            <div class="card-label">SKU (ProductCode)</div>
            <div class="card-value">{sku}</div>
            <div class="card-label">Barcode</div>
            <div class="card-value">{barcode}</div>
            <div class="card-name">{name}</div>
        </div>
    </div>
    """

# ================= 5. 搜尋頁面主邏輯 =================
def show_search_barcode_page():
    st.markdown("""
        <style>
            .result-card { display: flex; flex-direction: row; align-items: center; background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 15px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); transition: transform 0.2s; }
            .card-img-container { width: 110px; height: 110px; flex-shrink: 0; margin-right: 20px; display: flex; align-items: center; justify-content: center; background-color: #f8f9fa; border-radius: 8px; border: 1px solid #eee; overflow: hidden; }
            .card-img-container img { max-width: 100%; max-height: 100%; object-fit: contain; }
            .loading-text { color: #007bff; font-size: 13px; font-weight: bold; animation: pulse 1.5s infinite; }
            @keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } }
            .card-info { flex-grow: 1; min-width: 0; }
            .card-label { color: #888; font-size: 11px; font-weight: bold; margin-bottom: 2px; text-transform: uppercase; letter-spacing: 0.5px;}
            .card-value { color: #333; font-size: 15px; margin-bottom: 8px; word-break: break-all; font-family: monospace; }
            .card-name { color: #2c3e50; font-weight: 700; font-size: 16px; line-height: 1.4; border-top: 1px solid #eee; padding-top: 10px; margin-top: 5px; }
            @media screen and (max-width: 768px) { .result-card { flex-direction: column; align-items: flex-start; } .card-img-container { margin-right: 0; margin-bottom: 15px; width: 100%; height: 150px; } }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🔍 Search Barcode System")
    
    df = load_data()
    if df is None:
        st.error("❌ 找不到 Barcode.xlsx.csv 檔案")
        return

    st.caption(f"📚 Inventory Ready：Total {len(df)} Data")
    
    user_input = st.text_input("Please Enter Keywords:", placeholder="SKU / Barcode / Name")

    components.html("""<script>
        const parentDoc = window.parent.document;
        const input = parentDoc.querySelector('input[placeholder="SKU / Barcode / Name"]');
        if (input && input.type !== "search") { input.setAttribute('type', 'search'); }
        </script>""", height=0)

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
                ph.markdown(generate_card_html(row, '<span class="loading-text">⏳ 正在搜尋圖片...</span>'), unsafe_allow_html=True)
                placeholders.append((ph, row))

            for ph, row in placeholders:
                target_name = str(row['Name'])
                
                # 執行爬蟲抓網址
                img_url = get_hktvmall_image_final(target_name)
                
                if img_url:
                    try:
                        # 執行下載轉 Base64
                        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                        img_response = requests.get(img_url, headers=headers, timeout=10)
                        img_response.raise_for_status()
                        
                        b64_img = base64.b64encode(img_response.content).decode('utf-8')
                        mime_type = "image/jpeg"
                        if ".png" in img_url.lower(): mime_type = "image/png"
                        elif ".gif" in img_url.lower(): mime_type = "image/gif"
                        elif ".webp" in img_url.lower(): mime_type = "image/webp"
                        
                        final_img_html = f'<img src="data:{mime_type};base64,{b64_img}" alt="Product Image" />'
                    except Exception as e:
                        final_img_html = f'<span style="color:red; font-size:12px;">圖片下載失敗</span>'
                else:
                    final_img_html = '<span style="color:#aaa; font-size:12px;">無圖片</span>'

                ph.markdown(generate_card_html(row, final_img_html), unsafe_allow_html=True)
        else:
            st.warning("❌ No Data Found")

if __name__ == "__main__":
    show_search_barcode_page()
