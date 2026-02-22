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
    def log_action(action_name):
        pass

# ================= 設定固定檔案名稱 =================
DEFAULT_DB_FILE = "Barcode.xlsx.csv"

@st.cache_data
def load_data():
    if not os.path.exists(DEFAULT_DB_FILE):
        return None
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

# ================= HKTVmall 圖片爬蟲 (5 段式漸進搜尋) =================
@st.cache_data(show_spinner=False, ttl=86400)
def get_hktvmall_image_url(original_product_name):
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox") 
    chrome_options.add_argument("--disable-dev-shm-usage") 
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.page_load_strategy = 'eager'
    
    if shutil.which("chromium"):
        chrome_options.binary_location = shutil.which("chromium")
    elif shutil.which("chromium-browser"):
        chrome_options.binary_location = shutil.which("chromium-browser")
        
    driver_path = shutil.which("chromedriver") or shutil.which("chromedriver-linux64")
    
    if driver_path:
        service = Service(driver_path)
    else:
        service = Service(ChromeDriverManager().install())
        
    service.log_path = os.devnull
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    def do_search(keyword):
        encoded_name = urllib.parse.quote(str(keyword).strip())
        search_url = f"https://www.hktvmall.com/hktv/zh/search_a?keyword={encoded_name}"
        driver.get(search_url)
        try:
            wait = WebDriverWait(driver, 4) 
            css_selectors = ".product-brief img, img[itemprop='image'], .productImage, .item-image img"
            img_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selectors)))
            return img_element.get_attribute("src")
        except:
            return None

    try:
        # 1. 拔除最前方的括號 (例如: "(瑕疵品)韓國洗髮水(嬰兒香)" -> "韓國洗髮水(嬰兒香)")
        name_no_prefix = re.sub(r'^[\(（].*?[\)）]\s*', '', original_product_name).strip()
        
        # 2. 拔除後方的括號 (例如: "韓國洗髮水(嬰兒香)" -> "韓國洗髮水")
        name_no_suffix = re.sub(r'\s*[\(（][^()（）]*[\)）]$', '', name_no_prefix).strip()

        # 波段 1：保留後括號，直接搜！(滿足你最新的需求)
        img_url = do_search(name_no_prefix)
        if img_url: return img_url
            
        # 波段 2：如果波段 1 找不到，且名字真的有後括號，就把後括號拔掉再搜一次
        if name_no_suffix and name_no_suffix != name_no_prefix:
            img_url = do_search(name_no_suffix)
            if img_url: return img_url

        # 波段 3：砍掉連字號 (-) 後面的所有款式字眼
        fallback_1 = re.sub(r'\s*[-－].*$', '', name_no_suffix).strip()
        if fallback_1 and fallback_1 != name_no_suffix:
            img_url = do_search(fallback_1)
            if img_url: return img_url

        # 波段 4：砍掉國家名、容量 (ml, g, 包)
        fallback_2 = re.sub(r'^(韓國|日本|美國|澳洲|英國|德國|法國|台灣|泰國|紐西蘭)\s*', '', fallback_1)
        fallback_2 = re.sub(r'\s*\d+(\.\d+)?\s*(ml|g|kg|l|oz|毫升|克|件|片|樽|罐|包).*$', '', fallback_2, flags=re.IGNORECASE).strip()
        if fallback_2 and fallback_2 != fallback_1:
            img_url = do_search(fallback_2)
            if img_url: return img_url
                
        # 波段 5：終極大絕，只取名字最前面的兩個詞彙
        words = fallback_2.split()
        if len(words) >= 2:
            fallback_3 = " ".join(words[:2])
            if fallback_3 != fallback_2:
                img_url = do_search(fallback_3)
                if img_url: return img_url
                
        return None
    except Exception as e:
        print(f"Scraping error: {e}")
        return None
    finally:
        driver.quit()

# ================= HTML 卡片產生器 =================
def generate_card_html(row, img_html):
    return f"""
    <div class="result-card">
        <div class="card-img-container">
            {img_html}
        </div>
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
    
    st.markdown("""
        <style>
            .logo-container { display: flex; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
            .logo-text { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 28px; font-weight: 800; color: #2c3e50; letter-spacing: -0.5px; margin-left: 10px; line-height: 1; }
            .logo-dot { color: #007bff; }
            .logo-sub { font-size: 14px; color: #888; font-weight: 400; margin-left: 15px; padding-left: 15px; border-left: 1px solid #ddd; height: 20px; line-height: 20px; }
        </style>
        <div class="logo-container">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#007bff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M6 9V2h12v7"></path><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><path d="M6 14h12v8H6z"></path>
            </svg>
            <div class="logo-text">Letech<span class="logo-dot">.</span></div>
            <div class="logo-sub">Intelligent Label Solution</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🔍 Search Barcode System")
    
    df = load_data()
    if df is None:
        st.error(f"❌ 找不到資料庫 `{DEFAULT_DB_FILE}`")
        return

    st.caption(f"📚 Inventory Ready：Total {len(df)} Data")
    
    user_input = st.text_input("Please Enter Keywords. (SKU / Barcode / Name):", placeholder="Enter Search Terms...")

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

            # 1. 建立空區塊，秒速顯示文字資料
            placeholders = []
            for _, row in results.iterrows():
                ph = st.empty()
                loading_html = '<span class="loading-text">⏳ 載入圖片中...</span>'
                ph.markdown(generate_card_html(row, loading_html), unsafe_allow_html=True)
                placeholders.append((ph, row))

            # 2. 背景逐一抓圖，更新畫面
            for ph, row in placeholders:
                original_product_name = str(row['Name'])
                
                img_url = get_hktvmall_image_url(original_product_name)
                
                if img_url:
                    final_img_html = f'<img src="{img_url}" alt="Product Image" />'
                else:
                    final_img_html = '<span class="no-img-text">暫無圖片</span>'

                ph.markdown(generate_card_html(row, final_img_html), unsafe_allow_html=True)

        else:
            st.warning("❌ No Data Found")
