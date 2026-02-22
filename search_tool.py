import streamlit as st
import pandas as pd
import os
import urllib.parse
import re
import requests
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

# ================= 🌟 革命性升級：極速雙引擎圖片搜尋 =================
@st.cache_data(show_spinner=False, ttl=86400)
def get_product_image_url(original_name):
    # 1. 基礎清理：砍掉結尾的 "x 2", "x10" 等干擾
    clean_name = re.sub(r'\s*[xX*]\s*\d+\s*$', '', original_name).strip()
    
    # 偽裝成真人瀏覽器的標頭檔
    headers_modern = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    # 偽裝成舊版瀏覽器 (用來觸發 Google 吐出最簡單的圖片源碼)
    headers_old = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1"}

    # 🚀 引擎 A：HKTVmall 直連 (極速 0.5 秒)
    try:
        url_hktv = f"https://www.hktvmall.com/hktv/zh/search_a?keyword={urllib.parse.quote(clean_name)}"
        res = requests.get(url_hktv, headers=headers_modern, timeout=3)
        # 直接從 HTML 原始碼挖出圖片網址
        imgs = re.findall(r'src="(//images\.hktvmall\.com/[^"]+)"', res.text)
        if imgs: return "https:" + imgs[0]
    except: pass

    # 🚀 引擎 A-2：HKTVmall 直連 (拔除前方括號再試一次)
    simp_name = re.sub(r'^[\(（].*?[\)）]\s*', '', clean_name).strip()
    if simp_name != clean_name:
        try:
            url_hktv2 = f"https://www.hktvmall.com/hktv/zh/search_a?keyword={urllib.parse.quote(simp_name)}"
            res2 = requests.get(url_hktv2, headers=headers_modern, timeout=3)
            imgs2 = re.findall(r'src="(//images\.hktvmall\.com/[^"]+)"', res2.text)
            if imgs2: return "https:" + imgs2[0]
        except: pass

    # 🚀 引擎 B：Yahoo 圖片搜尋 (最強語意理解，無視錯字與特殊括號)
    try:
        url_yahoo = f"https://images.search.yahoo.com/search/images?p={urllib.parse.quote(clean_name)}"
        res_yahoo = requests.get(url_yahoo, headers=headers_modern, timeout=3)
        imgs_yahoo = re.findall(r"src=['\"](https://tse\d+\.mm\.bing\.net/th\?id=[^'\"]+)['\"]", res_yahoo.text)
        if imgs_yahoo: return imgs_yahoo[0]
    except: pass

    # 🚀 引擎 C：Google 圖片搜尋 (終極保底)
    try:
        url_google = f"https://www.google.com/search?q={urllib.parse.quote(clean_name)}&tbm=isch"
        res_google = requests.get(url_google, headers=headers_old, timeout=3)
        imgs_google = re.findall(r'<img[^>]+src="(https://encrypted-tbn0\.gstatic\.com/images[^"]+)"', res_google.text)
        if imgs_google: return imgs_google[0]
    except: pass

    return None

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
            input[type="search"]::-webkit-search-cancel-button { -webkit-appearance: searchfield-cancel-button; cursor: pointer; height: 14px; width: 14px; }
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

    components.html("""<script>
        const parentDoc = window.parent.document;
        function transformToSearchBox() {
            const input = parentDoc.querySelector('input[aria-label="Please Enter Keywords. (SKU / Barcode / Name):"]');
            if (input && input.type !== "search") { input.setAttribute('type', 'search'); }
        }
        transformToSearchBox(); setTimeout(transformToSearchBox, 500); setTimeout(transformToSearchBox, 1500);
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

            # 1. 建立空區塊，秒速顯示文字資料
            placeholders = []
            for _, row in results.iterrows():
                ph = st.empty()
                loading_html = '<span class="loading-text">⏳ 載入圖片中...</span>'
                ph.markdown(generate_card_html(row, loading_html), unsafe_allow_html=True)
                placeholders.append((ph, row))

            # 2. 背景極速抓圖，更新畫面
            for ph, row in placeholders:
                original_product_name = str(row['Name'])
                
                img_url = get_product_image_url(original_product_name)
                
                if img_url:
                    final_img_html = f'<img src="{img_url}" alt="Product Image" />'
                else:
                    final_img_html = '<span class="no-img-text">暫無圖片</span>'

                ph.markdown(generate_card_html(row, final_img_html), unsafe_allow_html=True)

        else:
            st.warning("❌ No Data Found")

if __name__ == "__main__":
    show_search_barcode_page()
