import streamlit as st
import base64

# ================= 匯入功能模組 =================
try:
    from pdf_tool import show_pdf_page
    from excel_tool import show_excel_page
    # 假設您剛才的新程式碼是存成 anymall_tool.py
    from anymall_tool import show_anymall_page
except ImportError:
    def show_pdf_page(): st.error("找不到 pdf_tool.py")
    def show_excel_page(): st.error("找不到 excel_tool.py")
    def show_anymall_page(): st.error("找不到 anymall_tool.py")

# ================= 預留的其他 3PL 功能 =================
def show_hellobear_page():
    st.title("🐻 Hello Bear 3PL System")
    st.info("🚧 Hello Bear 功能開發中...")

def show_homey_page():
    st.title("🏠 Homey 3PL System")
    st.info("🚧 Homey 功能開發中...")

def show_search_barcode_page():
    st.title("🔍 Search Barcode")
    st.info("💡 手機版提示：點擊下方相機可直接掃描")
    st.text_input("🔢 手動輸入條碼", placeholder="請掃描或輸入...")
    st.camera_input("點擊拍照")

# ================= 頁面設定 =================
st.set_page_config(
    page_title="Letech 3PL",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= CSS 美化 =================
st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    
    /* 側邊欄優化 */
    section[data-testid="stSidebar"] { background-color: #f7f9fc; border-right: 1px solid #e3e6f0; }
    
    /* 側邊欄按鈕美化 */
    section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
        background-color: #ffffff; border: 1px solid #e0e0e0; padding: 12px 15px; margin-bottom: 8px;
        border-radius: 8px; transition: all 0.2s; cursor: pointer; display: flex; align-items: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }
    section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
        background-color: #eef2f7; border-color: #007bff; color: #007bff; padding-left: 20px;
    }
    section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-checked="true"] {
        background-color: #007bff; border-color: #007bff; color: white; font-weight: 600;
        box-shadow: 0 4px 6px rgba(0,123,255,0.25);
    }
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label > div:first-child { display: none; }
    .sidebar-header { font-size: 12px; font-weight: bold; color: #888; margin-top: 20px; margin-bottom: 5px; padding-left: 5px; letter-spacing: 1px; }

    /* 首頁卡片 */
    .home-card {
        background-color: white; border: 1px solid #e0e0e0; border-radius: 12px; padding: 25px;
        text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05); transition: transform 0.2s; height: 100%;
    }
    .home-card:hover { transform: translateY(-5px); box-shadow: 0 8px 20px rgba(0,0,0,0.1); border-color: #007bff; }
    .card-icon { font-size: 36px; margin-bottom: 15px; }
    .card-title { font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 10px; }
    .card-desc { font-size: 13px; color: #666; line-height: 1.6; }
    .card-tag { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; margin-bottom: 15px; }
    .tag-yummy { background-color: #fff3cd; color: #856404; }
    .tag-anymall { background-color: #d4edda; color: #155724; }
    .tag-bear { background-color: #f8d7da; color: #721c24; }
    .tag-homey { background-color: #e2e3e5; color: #383d41; }
    .tag-tool { background-color: #d1ecf1; color: #0c5460; }
    </style>
""", unsafe_allow_html=True)

# ================= 側邊欄 LOGO =================
def render_sidebar_logo():
    st.sidebar.markdown("""
    <div style="display: flex; align-items: center; padding: 10px 5px 20px 5px; border-bottom: 1px solid #ddd; margin-bottom: 10px;">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#007bff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 10px;">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
            <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
            <line x1="12" y1="22.08" x2="12" y2="12"></line>
        </svg>
        <div>
            <div style="font-size: 18px; font-weight: 800; color: #2c3e50; line-height: 1;">Letech<span style="color:#007bff">.</span></div>
            <div style="font-size: 10px; color: #888; font-weight: 400; letter-spacing: 0.5px;">SYSTEM PORTAL</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ================= 首頁主視覺 =================
def render_main_header():
    col_logo, col_text = st.columns([0.08, 0.92])
    
    with col_logo:
        st.markdown("""
        <svg width="55" height="55" viewBox="0 0 24 24" fill="none" stroke="#007bff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
            <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
            <line x1="12" y1="22.08" x2="12" y2="12"></line>
        </svg>
        """, unsafe_allow_html=True)
        
    with col_text:
        st.markdown("""
        <div style="font-family: 'Helvetica Neue', sans-serif; font-size: 42px; font-weight: 800; color: #2c3e50; line-height: 1.1; margin-top: 5px;">
            Letech<span style="color:#007bff">.</span> 3PL
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="font-size: 16px; color: #888; margin-top: -10px; margin-bottom: 20px; letter-spacing: 0.5px;">
        <br><br>Intelligent Logistics System & Label Solution
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()

# ================= 主程式邏輯 =================
def main():
    render_sidebar_logo()
    
    st.sidebar.markdown("<div class='sidebar-header'>MAIN MENU</div>", unsafe_allow_html=True)
    
    category_selection = st.sidebar.radio(
        "Main Category", 
        [
            "🏠 首頁總覽",
            "🍔 Yummy 3PL",
            "🛍️ Anymall 3PL",
            "🐻 Hello Bear 3PL",
            "🏠 Homey 3PL",
            "🔍 Search Barcode"
        ],
        label_visibility="collapsed"
    )

    # 1. 首頁
    if category_selection == "🏠 首頁總覽":
        render_main_header()
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div class="home-card">
                <span class="card-tag tag-yummy">YUMMY 3PL</span>
                <div class="card-icon">🍔</div>
                <div class="card-title">Yummy 倉儲系統</div>
                <div class="card-desc">包含 PDF 訂單處理與標籤列印功能</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div class="home-card">
                <span class="card-tag tag-anymall">ANYMALL 3PL</span>
                <div class="card-icon">🛍️</div>
                <div class="card-title">Anymall 倉儲系統</div>
                <div class="card-desc">專屬物流功能模組 (已上線)</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.write("") 
        
        col3, col4 = st.columns(2)
        with col3:
            st.markdown("""
            <div class="home-card">
                <span class="card-tag tag-bear">HELLO BEAR</span>
                <div class="card-icon">🐻</div>
                <div class="card-title">Hello Bear 3PL</div>
                <div class="card-desc">Hello Bear 專屬物流功能 (Coming Soon)</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown("""
            <div class="home-card">
                <span class="card-tag tag-homey">HOMEY</span>
                <div class="card-icon">🏠</div>
                <div class="card-title">Homey 3PL</div>
                <div class="card-desc">Homey 專屬物流功能 (Coming Soon)</div>
            </div>
            """, unsafe_allow_html=True)

        st.write("") 

        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
             st.markdown("""
            <div class="home-card">
                <span class="card-tag tag-tool">Mobile Tool</span>
                <div class="card-icon">🔍</div>
                <div class="card-title">Search Barcode</div>
                <div class="card-desc">手機相機掃描與條碼查詢</div>
            </div>
            """, unsafe_allow_html=True)

    # 2. Yummy 3PL
    elif category_selection == "🍔 Yummy 3PL":
        st.sidebar.markdown("---")
        st.sidebar.markdown("<div class='sidebar-header'>YUMMY TOOLS</div>", unsafe_allow_html=True)
        yummy_function = st.sidebar.radio("Yummy Functions", ["📄 PDF 處理工具", "🖨️ Excel 標籤生成"], label_visibility="collapsed")
        
        if yummy_function == "📄 PDF 處理工具": show_pdf_page()
        elif yummy_function == "🖨️ Excel 標籤生成": show_excel_page()

    # 3. Anymall (✅ 修改處：模仿 Yummy 結構)
    elif category_selection == "🛍️ Anymall 3PL":
        st.sidebar.markdown("---")
        # 改用 sidebar-header 統一樣式
        st.sidebar.markdown("<div class='sidebar-header'>ANYMALL TOOLS</div>", unsafe_allow_html=True)
        
        # 新增子選單，預留擴充空間
        anymall_function = st.sidebar.radio(
            "Anymall Functions", 
            ["🛍️ Anymall 訂單處理工具"], 
            label_visibility="collapsed"
        )
        
        if anymall_function == "🛍️ Anymall 訂單處理工具":
            show_anymall_page()

    # 4. Hello Bear
    elif category_selection == "🐻 Hello Bear 3PL":
        st.sidebar.markdown("---")
        st.sidebar.caption("HELLO BEAR 功能選擇")
        show_hellobear_page()

    # 5. Homey
    elif category_selection == "🏠 Homey 3PL":
        st.sidebar.markdown("---")
        st.sidebar.caption("HOMEY 功能選擇")
        show_homey_page()

    # 6. Search Barcode
    elif category_selection == "🔍 Search Barcode":
        show_search_barcode_page()

    st.sidebar.markdown("---")
    st.sidebar.markdown("<div style='text-align: center; color: #aaa; font-size: 12px;'>© 2024 Letech System v3.0</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
