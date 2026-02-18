import streamlit as st
import streamlit.components.v1 as components

# ================= 1. 匯入功能模組 (修復變數作用域問題) =================

# --- PDF Tool ---
try:
    from pdf_tool import show_pdf_page
except ImportError as e:
    pdf_err = str(e) # 將錯誤訊息存入持久變數
    def show_pdf_page(): 
        st.error(f"❌ 無法載入 PDF 工具: {pdf_err}")
        st.info("💡 提示: 請確認是否已安裝 pypdf (pip install pypdf)")

# --- Excel Tool ---
try:
    from excel_tool import show_excel_page
except ImportError as e:
    excel_err = str(e)
    def show_excel_page(): 
        st.error(f"❌ 無法載入 Excel 工具: {excel_err}")
        st.info("💡 提示: 請確認資料夾內是否有 Lable.py 和 Cautions.py")

# --- Anymall Tool ---
try:
    from anymall_tool import show_anymall_page
except ImportError as e:
    anymall_err = str(e)
    def show_anymall_page(): st.error(f"❌ 無法載入 Anymall 工具: {anymall_err}")

# --- Search Tool ---
try:
    from search_tool import show_search_barcode_page
except ImportError as e:
    search_err = str(e)
    def show_search_barcode_page(): st.error(f"❌ 無會載入 Search 工具: {search_err}")

# --- Homey Tool ---
try:
    from homey_tool import show_homey_page
except ImportError as e:
    homey_err = str(e)
    def show_homey_page(): st.error(f"❌ 無法載入 Homey 工具: {homey_err}")

# --- Hello Bear Tool ---
try:
    # 這裡確保匯入您的 hello_tool.py
    from hello_tool import show_hellobear_page
except ImportError as e:
    hb_err = str(e) # 修正關鍵：捕捉錯誤訊息
    def show_hellobear_page(): 
        st.error(f"❌ 無法載入 Hello Bear 工具: {hb_err}")
        st.info("💡 提示: 請確認 `hello_tool.py` 檔案存在且內容無語法錯誤。")

# ================= 2. 頁面設定 =================
st.set_page_config(
    page_title="Letech 3PL",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="auto"
)

# ================= 3. 手機版自動收合邏輯 =================
def close_sidebar_callback():
    """回調函數：選單點擊時計數器 +1"""
    if 'sidebar_trigger_count' not in st.session_state:
        st.session_state.sidebar_trigger_count = 0
    st.session_state.sidebar_trigger_count += 1

def inject_mobile_sidebar_closer():
    if 'sidebar_trigger_count' not in st.session_state:
        st.session_state.sidebar_trigger_count = 0
    
    count = st.session_state.sidebar_trigger_count
    
    js_code = f"""
    <script>
        console.log("Sidebar trigger: {count}");
        var width = window.innerWidth || document.documentElement.clientWidth || document.body.clientWidth;
        if (width <= 768) {{
            setTimeout(function() {{
                var sidebar = window.parent.document.querySelector('section[data-testid="stSidebar"]');
                if (sidebar) {{
                    var buttons = sidebar.querySelectorAll('button');
                    if (buttons.length > 0) {{
                        buttons[0].click();
                    }}
                }}
            }}, 300);
        }}
    </script>
    """
    components.html(js_code, height=0)

# ================= 4. CSS 美化 =================
st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    section[data-testid="stSidebar"] { background-color: #f7f9fc; border-right: 1px solid #e3e6f0; }
    section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
        background-color: #ffffff !important; border: 1px solid #e0e0e0 !important; 
        padding: 12px 15px !important; margin-bottom: 8px !important;
        border-radius: 8px !important; transition: all 0.2s; cursor: pointer; 
        display: flex; align-items: center; color: #333333 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }
    section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
        background-color: #eef2f7 !important; border-color: #007bff !important; color: #007bff !important;
    }
    section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-checked="true"] {
        background-color: #007bff !important; border-color: #007bff !important; 
        color: white !important; font-weight: 600 !important;
        box-shadow: 0 4px 6px rgba(0,123,255,0.25);
    }
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label > div:first-child { display: none !important; }
    .sidebar-header { font-size: 12px; font-weight: bold; color: #888; margin-top: 20px; margin-bottom: 5px; padding-left: 5px; letter-spacing: 1px; }
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

# ================= 5. 側邊欄 LOGO =================
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

# ================= 6. 首頁主視覺 =================
def render_main_header():
    col_logo, col_text = st.columns([0.08, 0.92])
    with col_logo:
        st.markdown("""<svg width="55" height="55" viewBox="0 0 24 24" fill="none" stroke="#007bff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>""", unsafe_allow_html=True)
    with col_text:
        st.markdown("""<div style="font-family: 'Helvetica Neue', sans-serif; font-size: 42px; font-weight: 800; color: #2c3e50; line-height: 1.1; margin-top: 5px;">Letech<span style="color:#007bff">.</span> 3PL</div>""", unsafe_allow_html=True)
    st.markdown("""<div style="font-size: 16px; color: #888; margin-top: -10px; margin-bottom: 20px; letter-spacing: 0.5px;"><br><br>Intelligent Logistics System & Label Solution</div>""", unsafe_allow_html=True)
    st.divider()

# ================= 7. 主程式邏輯 =================
def main():
    render_sidebar_logo()
    st.sidebar.markdown("<div class='sidebar-header'>MAIN MENU</div>", unsafe_allow_html=True)
    
    category_selection = st.sidebar.radio(
        "Main Category", 
        ["🏠 首頁總覽", "🍔 Yummy 3PL", "🛍️ Anymall 3PL", "🐻 Hello Bear 3PL", "🏠 Homey 3PL", "🔍 Search Barcode"],
        label_visibility="collapsed",
        key="main_nav",
        on_change=close_sidebar_callback
    )

    inject_mobile_sidebar_closer()

    if category_selection == "🏠 首頁總覽":
        render_main_header()
        c1, c2 = st.columns(2)
        with c1: st.markdown("""<div class="home-card"><span class="card-tag tag-yummy">Yummy 3PL</span><div class="card-icon">🍔</div><div class="card-title">Yummy System</div><div class="card-desc">PDF 處理與標籤列印</div></div>""", unsafe_allow_html=True)
        with c2: st.markdown("""<div class="home-card"><span class="card-tag tag-anymall">Anymall 3PL</span><div class="card-icon">🛍️</div><div class="card-title">Anymall System</div><div class="card-desc">自動處理空白頁與表格</div></div>""", unsafe_allow_html=True)
        st.write("") 
        c3, c4 = st.columns(2)
        with c3: st.markdown("""<div class="home-card"><span class="card-tag tag-bear">Hello Bear 3PL</span><div class="card-icon">🐻</div><div class="card-title">Hello Bear System</div><div class="card-desc">專屬物流功能</div></div>""", unsafe_allow_html=True)
        with c4: st.markdown("""<div class="home-card"><span class="card-tag tag-homey">Homey 3PL</span><div class="card-icon">🏠</div><div class="card-title">Homey System</div><div class="card-desc">資料整合與去除空白</div></div>""", unsafe_allow_html=True)
        st.write("") 
        c5, c6, c7 = st.columns([1, 2, 1])
        with c6: st.markdown("""<div class="home-card"><span class="card-tag tag-tool">Mobile Tool</span><div class="card-icon">🔍</div><div class="card-title">Search Barcode</div><div class="card-desc">快速查詢 SKU</div></div>""", unsafe_allow_html=True)

    elif category_selection == "🍔 Yummy 3PL":
        st.sidebar.markdown("---")
        yummy_ops = ["📄 PDF 處理工具", "🖨️ Excel 標籤生成"]
        yummy_function = st.sidebar.radio("Yummy Functions", yummy_ops, label_visibility="collapsed")
        if yummy_function == "📄 PDF 處理工具": show_pdf_page()
        elif yummy_function == "🖨️ Excel 標籤生成": show_excel_page()

    elif category_selection == "🛍️ Anymall 3PL":
        st.sidebar.markdown("---")
        show_anymall_page()

    elif category_selection == "🐻 Hello Bear 3PL":
        st.sidebar.markdown("---")
        show_hellobear_page()

    elif category_selection == "🏠 Homey 3PL":
        st.sidebar.markdown("---")
        show_homey_page()

    elif category_selection == "🔍 Search Barcode":
        show_search_barcode_page()

if __name__ == "__main__":
    main()