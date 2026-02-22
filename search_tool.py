import streamlit as st
import pandas as pd
import os
import urllib.parse
import re
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
    # 避免本機測試時如果沒有 usage_tracker 會報錯
    def log_action(action_name):
        pass

# ================= 設定固定檔案名稱 =================
DEFAULT_DB_FILE = "Barcode.xlsx.csv"

@st.cache_data
def load_data():
    if not os.path.exists(DEFAULT_DB_FILE):
        return None
    try:
        # 加上 dtype=str 避免 Pandas 報黃色警告
        df = pd.read_csv(DEFAULT_DB_FILE, dtype=str)
        cols_to_ensure = ['ProductCode', 'Name', 'Barcode']
        for col in cols_to_ensure:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str).str.strip()
                # 去除數字可能帶有的 .0 結尾
                if col in ['ProductCode', 'Barcode']:
                    df[col] = df[col].apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)
            else:
                df[col] = ""
        return df
    except Exception as e:
        return None

# ================= HKTVmall 圖片爬蟲 (具備 24 小時快取功能) =================
@st.cache_data(show_spinner=False, ttl=86400)
def get_hktvmall_image_url(original_product_name):
    # 1. 智慧去除前後括號，提取最精準的搜尋名稱
    search_name = re.sub(r'^[\(（].*?[\)）]\s*', '', original_product_name)
    search_name = re.sub(r'\s*[\(（][^()（）]*[\)）]$', '', search_name)
    
    # 2. 設定 Chrome 瀏覽器選項 (雲端伺服器必備設定)
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox") # 雲端必備
    chrome_options.add_argument("--disable-dev-shm-usage") # 雲端必備
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 自動下載/對應對的 ChromeDriver
    service = Service(ChromeDriverManager().install())
    service.log_path = os.devnull
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    def do_search(keyword):
        encoded_name = urllib.parse.quote(str(keyword))
        search_url = f"https://www.hktvmall.com/hktv/zh/search_a?keyword={encoded_name}"
        driver.get(search_url)
        try:
            # 等待 5 秒，涵蓋列表頁與詳情頁的主圖片標籤
            wait = WebDriverWait(driver, 5) 
            css_selectors = ".product-brief img, img[itemprop='image'], .productImage, .item-image img"
            img_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selectors)))
            return img_element.get_attribute("src")
        except:
            return None

    try:
        # 第一波：精準搜尋
        img_url = do_search(search_name)
        if img_url: return img_url
            
        # 第二波：簡化搜尋 (砍掉容量、國家名、連字號後面的字)
        fallback_name = re.sub(r'\s*\d+(\.\d+)?\s*(ml|g|kg|l|oz|毫升|克|件|片|樽|罐).*$', '', search_name, flags=re.IGNORECASE)
        fallback_name = re.sub(r'^(韓國|日本|美國|澳洲|英國|德國|法國|台灣|泰國|紐西蘭)\s*', '', fallback_name)
        fallback_name = re.split(r'\s*-\s*', fallback_name)[0] 
        if fallback_name != search_name and len(fallback_name) > 2:
            img_url = do_search(fallback_name)
            if img_url: return img_url
                
        # 第三波：純中文精準搜尋
        chinese_chars = "".join(re.findall(r'[\u4e00-\u9fff]+', fallback_name))
        if len(chinese_chars) >= 4:
            img_url = do_search(chinese_chars)
            if img_url: return img_url
                
        return None
    except Exception as e:
        print(f"Scraping error: {e}")
        return None
    finally:
        driver.quit()

# ================= 頁面主邏輯 =================
def show_search_barcode_page():
    # 注入 CSS：包含圖片排版的卡片樣式
    st.markdown("""
        <style>
            .result-card {
                display: flex;
                flex-direction: row;
                align-items: center;
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 15px;
                margin-bottom: 15px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                transition: transform 0.2s;
            }
            .result-card:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.08); border-color: #007bff; }
            
            .card-img-container {
                width: 110px;
                height: 110px;
                flex-shrink: 0;
                margin-right: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                background-color: #f8f9fa;
                border-radius: 8px;
                border: 1px solid #eee;
                overflow: hidden;
            }
            .card-img-container img { max-width: 100%; max-height: 100%; object-fit: contain; }
            .no-img-text { color: #aaa; font-size: 12px; font-weight: bold; }
            
            .card-info { flex-grow: 1; min-width: 0; }
            .card-label { color: #888; font-size: 11px; font-weight: bold; margin-bottom: 2px; text-transform: uppercase; letter-spacing: 0.5px;}
            .card-value { color: #333; font-size: 15px; margin-bottom: 8px; word-break: break-all; }
            .card-name { color: #2c3e50; font-weight: 700; font-size: 16px; line-height: 1.4; border-top: 1px solid #eee; padding-top: 10px; margin-top: 5px; }

            .mobile-view { display: none; }
            .desktop-view { display: block; }

            /* 手機版排版調整 */
            @media screen and (max-width: 768px) {
                .desktop-view { display: none !important; } 
                .mobile-view { display: block !important; }
                .result-card { flex-direction: column; align-items: flex-start; }
                .card-img-container { margin-right: 0; margin-bottom: 15px; width: 100%; height: 150px; }
            }
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

            # 顯示載入動畫，提示正在抓圖
            with st.spinner("正在即時獲取商品圖片... (首次搜尋約需幾秒，隨後即秒速顯示)"):
                
                # --- 渲染卡片區塊 ---
                st.markdown('<div class="mobile-view desktop-view">', unsafe_allow_html=True)
                for _, row in results.iterrows():
                    original_product_name = str(row['Name'])
                    
                    # 呼叫爬蟲獲取圖片網址 (受惠於 cache_data，搜過的會直接返回)
                    img_url = get_hktvmall_image_url(original_product_name)
                    
                    # 生成圖片的 HTML 標籤
                    if img_url:
                        img_html = f'<img src="{img_url}" alt="Product Image" />'
                    else:
                        img_html = '<span class="no-img-text">暫無圖片</span>'

                    # 插入帶有圖片的卡片 HTML
                    st.markdown(f"""
                    <div class="result-card">
                        <div class="card-img-container">
                            {img_html}
                        </div>
                        <div class="card-info">
                            <div class="card-label">SKU</div>
                            <div class="card-value">{row['ProductCode']}</div>
                            <div class="card-label">Barcode</div>
                            <div class="card-value">{row['Barcode']}</div>
                            <div class="card-name">{original_product_name}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("❌ No Data Found")
