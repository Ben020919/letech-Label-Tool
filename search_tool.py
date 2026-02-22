import streamlit as st
import pandas as pd
import os
import urllib.parse
import re
import shutil
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
    except Exception as e:
        return None

# ================= 整合版 HKTVmall 爬蟲功能 (不產生 Excel) =================
@st.cache_data(show_spinner=False, ttl=86400)
def get_hktvmall_image_combined(product_name):
    # 基礎清理邏輯
    clean_name = re.sub(r'\s*[xX*]\s*\d+\s*$', '', product_name).strip()
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 智能判斷環境 (本地或 Streamlit Cloud)
    if shutil.which("chromium"):
        chrome_options.binary_location = shutil.which("chromium")
    elif shutil.which("chromium-browser"):
        chrome_options.binary_location = shutil.which("chromium-browser")
        
    driver_path = shutil.which("chromedriver") or shutil.which("chromedriver-linux64")
    service = Service(driver_path) if driver_path else Service(ChromeDriverManager().install())
    service.log_path = os.devnull
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    def do_search(keyword):
        encoded_name = urllib.parse.quote(keyword)
        search_url = f"https://www.hktvmall.com/hktv/zh/search_a?keyword={encoded_name}"
        driver.get(search_url)
        try:
            # 使用 hktv_scraper.py 中的 15 秒等待，增加成功率
            wait = WebDriverWait(driver, 15)
            # 支援列表頁與詳情頁標籤
            css_selectors = ".product-brief img, img[itemprop='image'], .productImage, .item-image img"
            img_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selectors)))
            return img_element.get_attribute("src")
        except:
            return None

    try:
        # 第一波：原始名稱搜尋
        img_url = do_search(clean_name)
        if img_url: return img_url
        
        # 第二波：簡化名稱 (去除括號)
        simp_name = re.sub(r'[\(（].*?[\)）]', '', clean_name).strip()
        if simp_name and simp_name != clean_name:
            img_url = do_search(simp_name)
            if img_url: return img_url
            
        return None
    except Exception:
        return None
    finally:
        driver.quit()

# ================= HTML 卡片產生器 =================
def generate_card_html(row, img_html):
    return f"""
    <div class="result-card">
        <div class="card-img-container">{img_html}</div>
        <div class="card-info">
            <div class="card-label">SKU</div>
            <div class="card-value">{row['ProductCode']}</div>
            <div class="card-label">Barcode</div>
            <div class="card-value">{row['Barcode']}</div>
            <div class="card-name">{row['Name']}</div>
        </div>
    </div>
    """

# ================= 頁面主邏輯 =================
def show_search_barcode_page():
    # 注入 CSS 樣式
    st.markdown("""
        <style>
            .result-card { display: flex; flex-direction: row; align-items: center; background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 15px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); transition: transform 0.2s; }
            .result-card:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.08); border-color: #007bff; }
            .card-img-container { width: 110px; height: 110px; flex-shrink: 0; margin-right: 20px; display: flex; align-items: center; justify-content: center; background-color: #f8f9fa; border-radius: 8px; border: 1px solid #eee; overflow: hidden; }
            .card-img-container img { max-width: 100%; max-height: 100%; object-fit: contain; }
            .loading-text { color: #007bff; font-size: 13px; font-weight: bold; animation: pulse 1.5s infinite; }
            .no-img-text { color: #aaa; font-size: 12px; font-weight: bold; }
            @keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } }
            .card-info { flex-grow: 1; min-width: 0; }
            .card-label { color: #888; font-size: 11px; font-weight: bold; margin-bottom: 2px; text-transform: uppercase; letter-spacing: 0.5px;}
            .card-value { color: #333; font-size: 15px; margin-bottom: 8px; word-break: break-all; }
            .card-name { color: #2c3e50; font-weight: 700; font-size: 16px; line-height: 1.4; border-top: 1px solid #eee; padding-top: 10px; margin-top: 5px; }
            @media screen and (max-width: 768px) { .result-card { flex-direction: column; align-items: flex-start; } .card-img-container { margin-right: 0; margin-bottom: 15px; width: 100%; height: 150px; } }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🔍 Search Barcode System")
    
    df = load_data()
    if df is None:
        st.error(f"❌ 找不到資料庫 `{DEFAULT_DB_FILE}`")
        return

    st.caption(f"📚 Inventory Ready：Total {len(df)} Data")
    
    user_input = st.text_input("Please Enter Keywords. (SKU / Barcode / Name):", placeholder="Enter Search Terms...")

    # 自動轉換為搜尋框
    components.html("""<script>
        const parentDoc = window.parent.document;
        function transformToSearchBox() {
            const input = parentDoc.querySelector('input[aria-label="Please Enter Keywords. (SKU / Barcode / Name):"]');
            if (input && input.type !== "search") { input.setAttribute('type', 'search'); }
        }
        transformToSearchBox(); setTimeout(transformToSearchBox, 500);
        </script>""", height=0)

    if user_input:
        log_action("Search_Action") 

        query = user_input.strip()
        mask = (
            df['ProductCode'].str.contains(query, case=False, na=False) | 
            df['Barcode'].str.contains(query, case=False, na=False) |
            df['Name'].str.contains(query, case=False, na=False)
        )
        results = df[mask]

        if not results.empty:
            st.success(f"✅ Found {len(results)} Data")

            # 1. 秒速顯示文字資料
            placeholders = []
            for _, row in results.iterrows():
                ph = st.empty()
                loading_html = '<span class="loading-text">⏳ 載入圖片中...</span>'
                ph.markdown(generate_card_html(row, loading_html), unsafe_allow_html=True)
                placeholders.append((ph, row))

            # 2. 背景逐一爬取圖片
            for ph, row in placeholders:
                img_url = get_hktvmall_image_combined(str(row['Name']))
                
                if img_url:
                    final_img_html = f'<img src="{img_url}" alt="Product Image" />'
                else:
                    final_img_html = '<span class="no-img-text">暫無圖片</span>'

                ph.markdown(generate_card_html(row, final_img_html), unsafe_allow_html=True)

        else:
            st.warning("❌ No Data Found")

if __name__ == "__main__":
    show_search_barcode_page()
