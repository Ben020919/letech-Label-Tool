import streamlit as st
import pandas as pd
import os
import urllib.parse
import base64
import requests
import shutil
import json
import time
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import streamlit.components.v1 as components
from selenium_stealth import stealth

# ================= 1. 匯入追蹤工具 =================
try:
    from usage_tracker import log_action 
except ImportError:
    def log_action(action_name): pass

# ================= 2. 設定固定檔案名稱與快取 =================
DEFAULT_DB_FILE = "Barcode.xlsx.csv"
IMAGE_CACHE_FILE = "image_cache.json"

@st.cache_data
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

def load_image_cache():
    if os.path.exists(IMAGE_CACHE_FILE):
        try:
            with open(IMAGE_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

def save_image_cache(cache_dict):
    try:
        with open(IMAGE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_dict, f, ensure_ascii=False)
    except Exception as e: print(f"記憶庫儲存失敗: {e}")

# ================= 3. 核心爬蟲 (記憶體極致優化版) =================

# 🌟 新增：統一的瀏覽器啟動器 (只啟動一次)
def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-features=NetworkService")
    chrome_options.add_argument("--window-size=1920x1080")
    # 極致省記憶體設定
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    
    chrome_binary = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_binary: chrome_options.binary_location = chrome_binary
        
    driver_path = shutil.which("chromedriver") or shutil.which("chromedriver-linux64")
    service = Service(executable_path=driver_path) if driver_path else Service(ChromeDriverManager().install())
    service.log_path = os.devnull
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    stealth(driver,
        languages=["zh-TW", "zh-HK", "en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    return driver

# 🌟 修改：不再自己開關瀏覽器，而是接收上面那台「包車」來用
def get_hktvmall_image_final(product_name, driver):
    time.sleep(1.5) # 模擬人類停頓
    encoded_name = urllib.parse.quote(str(product_name).strip())
    search_url = f"https://www.hktvmall.com/hktv/zh/search_a?keyword={encoded_name}"
    
    try:
        driver.get(search_url)
        wait = WebDriverWait(driver, 15)
        img_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".product-brief img")))
        return img_element.get_attribute("src")
    except Exception as e:
        return f"ERROR:{str(e).splitlines()[0]}"

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
            
            image_cache = load_image_cache()
            cache_updated = False
            placeholders = []
            
            # 第一階段：先建立所有的卡片空殼
            for idx, row in results.iterrows():
                ph = st.empty()
                placeholders.append((ph, row))

            # 🌟 第二階段：判斷是不是有需要真正去爬網頁的商品
            items_to_scrape = [row for ph, row in placeholders if str(row['Name']) not in image_cache]
            driver = None
            
            if items_to_scrape:
                try:
                    # 只有在真的需要抓新圖的時候，才叫一台「包車 (瀏覽器)」過來
                    driver = init_driver()
                except Exception as e:
                    st.error("伺服器記憶體過載，請稍後再試或清除記憶。")

            # 第三階段：依序填入圖片 (讀取記憶 or 使用包車去抓)
            for ph, row in placeholders:
                target_name = str(row['Name'])
                
                # 1. 記憶庫裡有，直接秒出！
                if target_name in image_cache:
                    ph.markdown(generate_card_html(row, image_cache[target_name]), unsafe_allow_html=True)
                
                # 2. 記憶庫沒有，開始抓
                else:
                    if driver is None:
                        # 瀏覽器啟動失敗的防呆機制
                        final_img_html = '<span style="color:red; font-size:11px; text-align:center;">瀏覽器啟動失敗</span>'
                        ph.markdown(generate_card_html(row, final_img_html), unsafe_allow_html=True)
                        continue
                        
                    ph.markdown(generate_card_html(row, '<span class="loading-text">⏳ 正在抓取圖片...</span>'), unsafe_allow_html=True)
                    
                    img_url = get_hktvmall_image_final(target_name, driver)
                    
                    if img_url and img_url.startswith("ERROR:"):
                         error_msg = img_url.replace("ERROR:", "")
                         if "TimeoutException" in error_msg:
                             final_img_html = '<span style="color:red; font-size:11px; text-align:center;">15秒超時<br>(被防護阻擋)</span>'
                         else:
                             final_img_html = '<span style="color:red; font-size:11px; text-align:center;">尋找圖片失敗</span>'
                    elif img_url:
                        try:
                            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                            img_response = requests.get(img_url, headers=headers, timeout=10)
                            img_response.raise_for_status()
                            
                            b64_img = base64.b64encode(img_response.content).decode('utf-8')
                            mime_type = "image/jpeg"
                            if ".png" in img_url.lower(): mime_type = "image/png"
                            elif ".gif" in img_url.lower(): mime_type = "image/gif"
                            elif ".webp" in img_url.lower(): mime_type = "image/webp"
                            
                            final_img_html = f'<img src="data:{mime_type};base64,{b64_img}" alt="Product Image" />'
                            
                            # 寫進記憶庫
                            image_cache[target_name] = final_img_html
                            cache_updated = True
                        except Exception as e:
                            final_img_html = f'<span style="color:red; font-size:12px;">防盜鏈阻擋下載</span>'
                    else:
                        final_img_html = '<span style="color:#aaa; font-size:12px;">無圖片</span>'

                    ph.markdown(generate_card_html(row, final_img_html), unsafe_allow_html=True)
            
            # 🌟 任務全部結束，把這台唯一的「包車」徹底關閉銷毀，釋放珍貴的記憶體！
            if driver:
                try: driver.quit()
                except: pass

            if cache_updated: save_image_cache(image_cache)
                
        else:
            st.warning("❌ No Data Found")

if __name__ == "__main__":
    show_search_barcode_page()
