import streamlit as st
import pandas as pd
import os
import urllib.parse
import time
import streamlit.components.v1 as components

# ================= 1. 匯入追蹤工具 =================
try:
    from usage_tracker import log_action 
except ImportError:
    def log_action(action_name): pass

# ================= 2. 設定固定檔案名稱 =================
DEFAULT_DB_FILE = "Barcode.xlsx.csv"
DB_NAME_FILE = "search_current_db_name.txt"

def get_current_db_name():
    if os.path.exists(DB_NAME_FILE):
        with open(DB_NAME_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return DEFAULT_DB_FILE

def set_current_db_name(name):
    with open(DB_NAME_FILE, "w", encoding="utf-8") as f:
        f.write(name)

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

# ================= 3. HTML 卡片渲染器 =================
def generate_card_html(row):
    name = row.get('Name', 'Unknown')
    sku = row.get('ProductCode', 'N/A')
    barcode = row.get('Barcode', 'N/A')
    
    encoded_name = urllib.parse.quote(str(name).strip())
    search_url = f"https://www.hktvmall.com/hktv/zh/search_a?keyword={encoded_name}"
    
    return f"""
    <div class="result-card">
        <div class="card-action-container">
            <a href="{search_url}" target="_blank" class="hktv-btn">
                <span style="font-size: 18px; display: block; margin-bottom: 4px;">🔍</span>
                前往查看
            </a>
        </div>
        <div class="card-info">
            <div class="card-label">SKU (ProductCode)</div>
            <div class="card-value">{sku}</div>
            <div class="card-label">Barcode</div>
            <div class="card-value">{barcode}</div>
            <div class="card-name">{name}</div>
        </div>
    </div>
    """

# ================= 4. 搜尋頁面主邏輯 =================
def show_search_barcode_page():
    st.markdown("""
        <style>
            .result-card { display: flex; flex-direction: row; align-items: center; background-color: #ffffff; border: 1px solid #eef0f2; border-radius: 12px; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); transition: transform 0.2s, box-shadow 0.2s; }
            .result-card:hover { transform: translateY(-2px); box-shadow: 0 8px 16px rgba(0,0,0,0.08); }
            .card-action-container { width: 110px; height: 110px; flex-shrink: 0; margin-right: 20px; display: flex; align-items: center; justify-content: center; background-color: #f4f7f6; border-radius: 10px; }
            .hktv-btn { background-color: #10b981; color: white !important; padding: 10px 14px; border-radius: 8px; text-decoration: none; font-size: 13px; font-weight: 600; letter-spacing: 0.5px; text-align: center; display: inline-block; width: 85%; transition: all 0.2s ease-in-out; box-shadow: 0 2px 6px rgba(16, 185, 129, 0.25); }
            .hktv-btn:hover { background-color: #059669; box-shadow: 0 4px 10px rgba(16, 185, 129, 0.4); transform: translateY(-1px); }
            .card-info { flex-grow: 1; min-width: 0; }
            .card-label { color: #888; font-size: 11px; font-weight: bold; margin-bottom: 2px; text-transform: uppercase; letter-spacing: 0.5px;}
            .card-value { color: #333; font-size: 15px; margin-bottom: 8px; word-break: break-all; font-family: monospace; }
            .card-name { color: #2c3e50; font-weight: 700; font-size: 16px; line-height: 1.4; border-top: 1px solid #f0f0f0; padding-top: 10px; margin-top: 5px; }
            
            input[type="search"] { -webkit-appearance: textfield; }
            input[type="search"]::-webkit-search-cancel-button { -webkit-appearance: searchfield-cancel-button !important; display: block !important; cursor: pointer; height: 16px; width: 16px; opacity: 0.6; margin-left: 5px; }
            input[type="search"]::-webkit-search-cancel-button:hover { opacity: 1; }
            @media screen and (max-width: 768px) { .result-card { flex-direction: column; align-items: flex-start; } .card-action-container { margin-right: 0; margin-bottom: 15px; width: 100%; height: auto; padding: 12px 0; background: transparent; justify-content: flex-start; } .hktv-btn { width: auto; padding: 8px 20px; display: flex; align-items: center; gap: 8px; } .hktv-btn span { margin-bottom: 0 !important; } }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🔍 Search Barcode System")
    
    # ================= ✨ 搜尋專用：配置新文件區塊 ✨ =================
    with st.expander("⚙️ 配置新資料庫文件 (Database Management)", expanded=False):
        st.info("支援上傳任何檔名的 Excel (.xlsx) 或 CSV (.csv) 檔案。上傳後系統會自動套用！")
        new_db_file = st.file_uploader("上傳新的資料庫檔案", type=["xlsx", "csv"], key="search_new_db_uploader")
        
        if new_db_file:
            if st.button("確認更新資料庫", type="primary", key="search_update_btn"):
                try:
                    if new_db_file.name.endswith('.xlsx') or new_db_file.name.endswith('.xls'):
                        temp_df = pd.read_excel(new_db_file, dtype=str)
                        temp_df.to_csv(DEFAULT_DB_FILE, index=False)
                    else:
                        with open(DEFAULT_DB_FILE, "wb") as f:
                            f.write(new_db_file.getbuffer())
                    
                    set_current_db_name(new_db_file.name)
                    st.cache_data.clear()
                    st.success(f"✅ 資料庫已成功更新為：【{new_db_file.name}】！系統將在 2 秒後重新載入...")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 更新失敗: {e}")

    df = load_data()
    current_db_name = get_current_db_name()
    
    if df is None:
        st.error(f"❌ 找不到資料庫 `{current_db_name}`，請在上方上傳檔案。")
        return

    st.caption(f"📚 Linked Database: `{current_db_name}` (Total {len(df)} Data)")
    
    user_input = st.text_input("Please Enter Keywords:", placeholder="SKU / Barcode / Name")

    components.html("""
        <script>
        const parentDoc = window.parent.document;
        function setupSearchBox() {
            const inputs = parentDoc.querySelectorAll('input[placeholder="SKU / Barcode / Name"]');
            inputs.forEach(input => { if (input.type !== "search") { input.setAttribute('type', 'search'); } });
        }
        setupSearchBox(); setTimeout(setupSearchBox, 200); setTimeout(setupSearchBox, 800);
        </script>
        """, height=0)

    if user_input:
        log_action("Search_Action") 
        query = user_input.strip()
        mask = (df['ProductCode'].str.contains(query, case=False, na=False) | 
                df['Barcode'].str.contains(query, case=False, na=False) |
                df['Name'].str.contains(query, case=False, na=False))
        results = df[mask]

        if not results.empty:
            st.success(f"✅ Found {len(results)} Data")
            for idx, row in results.iterrows():
                st.markdown(generate_card_html(row), unsafe_allow_html=True)
        else:
            st.warning("❌ No Data Found")

if __name__ == "__main__":
    show_search_barcode_page()
