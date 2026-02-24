import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from usage_tracker import load_stats 

# ================= 1. 匯入功能模組 =================

# --- 合併後的 Yummy Tool ---
try:
    from yummy_tool import show_yummy_page
except ImportError as e:
    yummy_err = str(e)
    def show_yummy_page(): 
        st.error(f"❌ 無法載入 Yummy 工具: {yummy_err}")

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
    def show_search_barcode_page(): st.error(f"❌ 無法載入 Search 工具: {search_err}")

# --- Homey Tool ---
try:
    from homey_tool import show_homey_page
except ImportError as e:
    homey_err = str(e)
    def show_homey_page(): st.error(f"❌ 無法載入 Homey 工具: {homey_err}")

# --- Hello Bear Tool ---
try:
    from hello_tool import show_hellobear_page
except ImportError as e:
    hb_err = str(e)
    def show_hellobear_page(): 
        st.error(f"❌ 無法載入 Hello Bear 工具: {hb_err}")

# --- Food Label Tool ---
try:
    from food_label_tool import show_food_label_page
except ImportError as e:
    food_err = str(e)
    def show_food_label_page(): st.error(f"❌ 無法載入 Food Label 工具: {food_err}")

# --- ✅ 新增：掃碼出庫 Tool ---
try:
    from scanner_tool import show_scanner_page
except ImportError as e:
    scanner_err = str(e)
    def show_scanner_page(): st.error(f"❌ 無法載入 掃碼出庫 工具: {scanner_err}")

# ================= 2. 頁面設定 =================
st.set_page_config(page_title="Letech 3PL", page_icon="📦", layout="wide", initial_sidebar_state="auto")

# ================= 3. 手機版自動收合邏輯 =================
def close_sidebar_callback():
    if 'sidebar_trigger_count' not in st.session_state: st.session_state.sidebar_trigger_count = 0
    st.session_state.sidebar_trigger_count += 1

def inject_mobile_sidebar_closer():
    if 'sidebar_trigger_count' not in st.session_state: st.session_state.sidebar_trigger_count = 0
    count = st.session_state.sidebar_trigger_count
    js_code = f"""
    <script>
        console.log("Sidebar trigger: {count}");
        var width = window.innerWidth || document.documentElement.clientWidth || document.body.clientWidth;
        if (width <= 768) {{
            setTimeout(function() {{
                var sidebar = window.parent.document.querySelector('section[data-testid="stSidebar"]');
                if (sidebar) {{ var buttons = sidebar.querySelectorAll('button'); if (buttons.length > 0) {{ buttons[0].click(); }} }}
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
        padding: 12px 15px !important; margin-bottom: 8px !important; border-radius: 8px !important; 
        transition: all 0.2s; cursor: pointer; display: flex; align-items: center; color: #333333 !important; box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }
    section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover { background-color: #eef2f7 !important; border-color: #007bff !important; color: #007bff !important; }
    section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-checked="true"] { background-color: #007bff !important; border-color: #007bff !important; color: white !important; font-weight: 600 !important; box-shadow: 0 4px 6px rgba(0,123,255,0.25); }
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label > div:first-child { display: none !important; }
    .sidebar-header { font-size: 12px; font-weight: bold; color: #888; margin-top: 20px; margin-bottom: 5px; padding-left: 5px; letter-spacing: 1px; }
    
    .home-card { background-color: white; border: 1px solid #e0e0e0; border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05); transition: transform 0.2s; height: 100%; display: flex; flex-direction: column; justify-content: flex-start; align-items: center; }
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
    .tag-food { background-color: #f5c6cb; color: #721c24; }
    .tag-scan { background-color: #cce5ff; color: #004085; } /* 新增掃碼標籤顏色 */
    
    .stat-card-num { font-size: 2.1em; font-weight: 800; color: #007bff; margin: 15px 0; line-height: 1; }
    .stat-card-label { font-size: 1.2em; font-weight: bold; color: #2c3e50; }
    .stat-card-icon { font-size: 40px; color: #007bff; margin-bottom: 5px; }
    
    .dual-stat-box { display: flex; justify-content: space-between; align-items: center; width: 100%; margin-top: 15px; padding-top: 15px; border-top: 1px solid #eee; }
    .stat-item { width: 48%; text-align: center; }
    .mini-stat-num { font-size: 26px; font-weight: 800; color: #007bff; line-height: 1.2; }
    .mini-stat-label { font-size: 12px; color: #666; font-weight: 600; margin-bottom: 2px; }
    .stat-divider { width: 1px; height: 40px; background-color: #eee; }
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

# ================= 7. 控制台頁面 =================
def render_dashboard_page():
    col_title, col_btn = st.columns([0.85, 0.15])
    with col_title:
        st.markdown("### 📊 System Dashboard")
        st.markdown("Overview of system usage statistics.")
            
    st.divider()
    
    stats = load_stats()
    
    dashboard_cards = [
        {
            "type": "dual", "icon": "🍔", "title": "Yummy System",
            "val1": stats.get("Yummy_Process", 0), "label1": "📄 Uploads",
            "val2": stats.get("Yummy_Print", 0), "label2": "🖨️ Prints"
        },
        {
            "type": "dual", "icon": "🐻", "title": "HelloBear System",
            "val1": stats.get("HelloBear_Upload", 0), "label1": "📄 Uploads",
            "val2": stats.get("HelloBear_Print", 0), "label2": "🖨️ Prints"
        },
        {
            "type": "dual", "icon": "🛍️", "title": "Anymall System", 
            "val1": stats.get("Anymall_Upload", 0), "label1": "📄 Uploads",
            "val2": stats.get("Anymall_Print", 0), "label2": "🖨️ Prints" 
        },
        {
            "type": "dual", "icon": "🏠", "title": "Homey System", 
            "val1": stats.get("Homey_Upload", 0), "label1": "📄 Uploads",
            "val2": stats.get("Homey_Print", 0), "label2": "🖨️ Prints" 
        },
        {
            "type": "single", "icon": "🍎", "title": "Label System", 
            "count": stats.get("FoodLabel_Print", 0), "desc": "Total Printed Labels"
        },
        {
            "type": "single", "icon": "🔍", "title": "Search Action", 
            "count": stats.get("Search_Action", 0), "desc": "Database Queries"
        },
    ]
    
    cols = st.columns(3)
    for i, card in enumerate(dashboard_cards):
        col_idx = i % 3
        if card["type"] == "dual":
            card_html = f"""
            <div class="home-card">
                <div class="stat-card-icon">{card['icon']}</div>
                <div class="stat-card-label">{card['title']}</div>
                <div class="dual-stat-box">
                    <div class="stat-item"><div class="mini-stat-label">{card['label1']}</div><div class="mini-stat-num">{card['val1']}</div></div>
                    <div class="stat-divider"></div>
                    <div class="stat-item"><div class="mini-stat-label">{card['label2']}</div><div class="mini-stat-num">{card['val2']}</div></div>
                </div>
            </div>
            """
        else:
            card_html = f"""
            <div class="home-card">
                <div class="stat-card-icon">{card['icon']}</div>
                <div class="stat-card-label">{card['title']}</div>
                <div class="stat-card-num">{card['count']}</div>
                <div class="card-desc">{card['desc']}</div>
            </div>
            """
        cols[col_idx].markdown(card_html, unsafe_allow_html=True)
        if col_idx == 2: st.write(""); st.write(""); st.write("") 

# ================= 8. 首頁頁面 =================
def render_home_page():
    render_main_header()
    home_cards = [
        {"tag": "WMS Tool", "tag_class": "tag-scan", "icon": "📦", "title": "掃碼出庫系統", "desc": "Mobile Barcode Scanning & Outbound System."}, # ✅ 新增了這裡的區塊
        {"tag": "Yummy 3PL", "tag_class": "tag-yummy", "icon": "🍔", "title": "Yummy System", "desc": "PDF Processing and Food Label Printing."},
        {"tag": "Anymall 3PL", "tag_class": "tag-anymall", "icon": "🛍️", "title": "Anymall System", "desc": "PDF Processing and Label Printing."},
        {"tag": "Hello Bear 3PL", "tag_class": "tag-bear", "icon": "🐻", "title": "Hello Bear System", "desc": "PDF Processing and Repack Label Printing."},
        {"tag": "Homey 3PL", "tag_class": "tag-homey", "icon": "🏠", "title": "Homey System", "desc": "PDF Processing and Insects/Repack Label Printing."},
        {"tag": "Nutrition Label", "tag_class": "tag-food", "icon": "🍎 🐛", "title": "Label Printing", "desc": "For Yummy/Homey 3PL, Search and Print Label"},
        {"tag": "Mobile Tool", "tag_class": "tag-tool", "icon": "🔍", "title": "Search Barcode", "desc": "Search for Product Images, SKU Number, and Barcode."}
    ]
    
    cols = st.columns(3)
    for i, card in enumerate(home_cards):
        col_idx = i % 3
        card_html = f"""
        <div class="home-card">
            <span class="card-tag {card['tag_class']}">{card['tag']}</span>
            <div class="card-icon">{card['icon']}</div>
            <div class="card-title">{card['title']}</div>
            <div class="card-desc">{card['desc']}</div>
        </div>
        """
        cols[col_idx].markdown(card_html, unsafe_allow_html=True)
        if col_idx == 2: st.write(""); st.write(""); st.write("") 

# ================= 9. 主程式邏輯 =================
def main():
    render_sidebar_logo()
    st.sidebar.markdown("<div class='sidebar-header'>MAIN MENU</div>", unsafe_allow_html=True)
    
    # ✅ 在這裡將 "📦 掃碼出庫" 加入到左側選單列表中
    category_selection = st.sidebar.radio(
        "Main Category", 
        ["📊 Dashboard", "🏠 Homepage", "開發中 📦 掃碼出庫", "🍔 Yummy 3PL", "🛍️ Anymall 3PL", "🐻 Hello Bear 3PL", "🏠 Homey 3PL", "🏷️ Label Printing", "🔍 Search Barcode"],
        label_visibility="collapsed",
        key="main_nav",
        on_change=close_sidebar_callback
    )

    inject_mobile_sidebar_closer()

    if category_selection == "📊 Dashboard":
        render_dashboard_page() 

    elif category_selection == "🏠 Homepage":
        render_home_page() 
        
    # ✅ 新增的選項路由
    elif category_selection == "開發中 📦 掃碼出庫":
        st.sidebar.markdown("---")
        show_scanner_page()

    elif category_selection == "🍔 Yummy 3PL":
        st.sidebar.markdown("---")
        show_yummy_page()

    elif category_selection == "🛍️ Anymall 3PL":
        st.sidebar.markdown("---")
        show_anymall_page()

    elif category_selection == "🐻 Hello Bear 3PL":
        st.sidebar.markdown("---")
        show_hellobear_page()

    elif category_selection == "🏠 Homey 3PL":
        st.sidebar.markdown("---")
        show_homey_page()

    elif category_selection == "🏷️ Label Printing":
        st.sidebar.markdown("---")
        show_food_label_page()

    elif category_selection == "🔍 Search Barcode":
        st.sidebar.markdown("---")
        show_search_barcode_page()

if __name__ == "__main__":
    main()
