import streamlit as st
import base64

# 匯入另外兩個檔案的功能函式
# 請確保這兩個檔案在同一目錄下，且函式名稱正確
try:
    from pdf_tool import show_pdf_page
except ImportError:
    def show_pdf_page(): st.error("找不到 pdf_tool.py 或函式錯誤")

try:
    from excel_tool import show_excel_page
except ImportError:
    def show_excel_page(): st.error("找不到 excel_tool.py 或函式錯誤")

# 1. 設定必須在最前面
st.set_page_config(
    page_title="Letech - Professional Tools",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= CSS 美化樣式 =================
st.markdown("""
    <style>
    /* 全局字體 */
    html, body, [class*="css"] {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    
    /* 側邊欄樣式優化 */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-right: 1px solid #e9ecef;
    }
    
    /* 隱藏 Radio Button 的原始圓圈，改成選單樣式 */
    section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
        background-color: transparent;
        border: 1px solid transparent;
        padding: 10px 15px;
        margin-bottom: 5px;
        border-radius: 8px;
        transition: all 0.3s;
        cursor: pointer;
    }
    
    /* 滑鼠懸停效果 */
    section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
        background-color: #e7f5ff;
        color: #007bff;
    }
    
    /* 選中狀態效果 (需要配合 Streamlit 的結構，這裡做簡單的粗體強化) */
    section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-checked="true"] {
        background-color: #e7f5ff;
        border: 1px solid #cce5ff;
        color: #0056b3;
        font-weight: bold;
    }
    
    /* 隱藏 Radio 的圓點圖標 */
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label > div:first-child {
        display: none;
    }
    
    /* 卡片樣式 (用於首頁) */
    .home-card {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 25px;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        transition: transform 0.2s;
        height: 100%;
    }
    .home-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        border-color: #007bff;
    }
    .card-icon { font-size: 40px; margin-bottom: 15px; }
    .card-title { font-size: 18px; font-weight: bold; color: #333; margin-bottom: 10px; }
    .card-desc { font-size: 14px; color: #666; line-height: 1.5; }
    
    </style>
""", unsafe_allow_html=True)

# ================= 側邊欄 LOGO 函式 =================
def render_sidebar_logo():
    logo_html = """
    <div style="display: flex; align-items: center; padding: 15px 5px 25px 5px; border-bottom: 1px solid #ddd; margin-bottom: 20px;">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#007bff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 10px;">
            <path d="M6 9V2h12v7"></path>
            <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path>
            <path d="M6 14h12v8H6z"></path>
        </svg>
        <div>
            <div style="font-size: 20px; font-weight: 800; color: #2c3e50; line-height: 1;">Letech<span style="color:#007bff">.</span></div>
            <div style="font-size: 10px; color: #888; font-weight: 400; letter-spacing: 0.5px;">MAKE PROFESSIONAL</div>
        </div>
    </div>
    """
    st.sidebar.markdown(logo_html, unsafe_allow_html=True)

# ================= 主程式邏輯 =================
def main():
    # 1. 渲染側邊欄 Logo
    render_sidebar_logo()
    
    # 2. 側邊選單 (使用 Radio 但透過 CSS 偽裝成 Menu)
    st.sidebar.markdown("<small style='color:#888; font-weight:600; padding-left:5px;'>MAIN MENU</small>", unsafe_allow_html=True)
    
    # 定義選單選項與對應的圖示
    menu_options = {
        "🏠  首頁總覽": "home",
        "📄  PDF 處理工具": "pdf",
        "🖨️  Excel 標籤生成": "excel"
    }
    
    selection = st.sidebar.radio(
        "Menu", 
        list(menu_options.keys()), 
        label_visibility="collapsed" # 隱藏標題，讓視覺更乾淨
    )

    # 3. 路由控制 (Routing)
    
    # --- 首頁 (Dashboard) ---
    if menu_options[selection] == "home":
        st.title("Welcome to Letech")
        st.markdown("### Intelligent Document & Label Solutions")
        st.markdown("Please select the tool you need from the menu on the left.")
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="home-card">
                <div class="card-icon">📄</div>
                <div class="card-title">PDF 處理工具</div>
                <div class="card-desc">
                    分割PDF空白文件，提取文字內容。<br>
                    查詢重複SKU訂單。
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div class="home-card">
                <div class="card-icon">🖨️</div>
                <div class="card-title">Excel 標籤生成</div>
                <div class="card-desc">
                    讀取 Excel 資料庫與 PDF 訂單，<br>
                    一鍵生成標準化商品標籤並支援即時列印。
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br><br>", unsafe_allow_html=True)

    # --- PDF 工具 ---
    elif menu_options[selection] == "pdf":
        show_pdf_page()

    # --- Excel 工具 ---
    elif menu_options[selection] == "excel":
        show_excel_page()
    
    # 4. 側邊欄底部版權
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        <div style="text-align: center; color: #aaa; font-size: 12px;">
            © 2024 Letech System<br>
            v1.2.0 Professional
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()