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
        for col in ['ProductCode', 'Name', 'Barcode']:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str).str.strip()
                if col in ['ProductCode', 'Barcode']:
                    df[col] = df[col].apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)
            else:
                df[col] = ""
        return df
    except Exception: return None

# ================= 100% 純 HKTVmall 爬蟲 (V3 深度抓取版) =================
@st.cache_data(show_spinner=False, ttl=604800) # 快取延長至一週，減少重複抓取
def get_hktvmall_image_v3(original_name):
    # 1. 基礎清理：切掉結尾的數量干擾
    clean_name = re.sub(r'\s*[xX*]\s*\d+\s*$', '', original_name).strip()
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox") 
    chrome_options.add_argument("--disable-dev-shm-usage") 
    chrome_options.add_argument("--disable-gpu")
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
            # 🌟 技巧：模擬捲動以觸發延遲加載
            driver.execute_script("window.scrollTo(0, 200);")
            time.sleep(1) 
            
            wait = WebDriverWait(driver, 6) 
            css_selectors = ".product-brief img, img[itemprop='image'], .productImage, .item-image img"
            img_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selectors)))
            
            # 🌟 技巧：多重屬性抓取 (解決 Lazy Loading 問題)
            # 優先嘗試 data-src (通常是真實圖片網址)
            real_url = img_element.get_attribute("data-src")
            if not real_url:
                # 其次嘗試 srcset 的第一項
                srcset = img_element.get_attribute("srcset")
                if srcset:
                    real_url = srcset.split(',')[0].split(' ')[0]
            if not real_url:
                # 最後才用 src (且要排除 base64 佔位圖)
                src = img_element.get_attribute("src")
                if src and "base64" not in src:
                    real_url = src
            
            if real_url and real_url.startswith("//"):
                real_url = "https:" + real_url
                
            return real_url
        except:
            return None

    try:
        # 循序漸進搜尋
        search_name = clean_name
        img_url = do_search(search_name)
        if img_url: return img_url
            
        step2 = re.sub(r'^[\(（].*?[\)）]\s*', '', search_name).strip()
        if step2 != search_name:
            img_url = do_search(step2)
            if img_url: return img_url

        # 如果連中文打擊都失效，最後再回傳 None
        chinese_chars = "".join(re.findall(r'[\u4e00-\u9fff]+', search_name))
        if len(chinese_chars) >= 3: 
            img_url = do_search(chinese_chars)
            if img_url: return img_url

        return None
    except Exception as e:
        return None
    finally:
        driver.quit()

# ================= HTML 卡片產生器 =================
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
            .loading-text { color: #007bff; font-size: 13px; font-weight: bold; animation: pulse 1.5s infinite; }
            @keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } }
            .card-info { flex-grow: 1; min-width: 0; }
            .card-label { color: #888; font-size: 11px; font-weight: bold; margin-bottom: 2px; text-transform: uppercase; }
            .card-value { color: #333; font-size: 15px; margin-bottom: 8px; word-break: break-all; }
            .card-name { color: #2c3e50; font-weight: 700; font-size: 16px; line-height: 1.4; border-top: 1px solid #eee; padding-top: 10px; margin-top: 5px; }
            @media screen and (max-width: 768px) { .result-card { flex-direction: column; align-items: flex-start; } .card-img-container { margin-right: 0; margin-bottom: 15px; width: 100%; height: 150px; } }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🔍 Search Barcode System")
    df = load_data()
    if df is None: return

    user_input = st.text_input("Please Enter Keywords:", placeholder="SKU / Barcode / Name")

    components.html("""<script>
        const parentDoc = window.parent.document;
        function transformToSearchBox() {
            const input = parentDoc.querySelector('input[placeholder="SKU / Barcode / Name"]');
            if (input && input.type !== "search") { input.setAttribute('type', 'search'); }
        }
        transformToSearchBox(); setTimeout(transformToSearchBox, 500);
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
            for _, row in results.iterrows():
                ph = st.empty()
                ph.markdown(generate_card_html(row, '<span class="loading-text">⏳ 載入圖片中...</span>'), unsafe_allow_html=True)
                placeholders.append((ph, row))

            for ph, row in placeholders:
                # 🌟 改用 V3 版本，強制更新記憶
                img_url = get_hktvmall_image_v3(str(row['Name']))
                final_img_html = f'<img src="{img_url}" />' if img_url else '<span style="color:#aaa">暫無圖片</span>'
                ph.markdown(generate_card_html(row, final_img_html), unsafe_allow_html=True)
        else:
            st.warning("❌ No Data Found")

if __name__ == "__main__":
    show_search_barcode_page()
