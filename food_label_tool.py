import streamlit as st
import pandas as pd
import os
import sys
import time
from pathlib import Path
import streamlit.components.v1 as components

# ================= 確保能載入 Lable.py =================
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

try:
    import Lable
except ImportError as e:
    st.error(f"❌ 模組匯入失敗 (Lable): {e}")
    Lable = None

try:
    from usage_tracker import log_action
except ImportError:
    def log_action(action_name): pass

# ================= 設定預設檔案名稱 =================
DEFAULT_EXCEL_PATH = "data.xlsx"
DB_NAME_FILE = "current_db_name.txt"

# ================= 1. 資料庫讀取與檔名記憶函式 =================
def get_current_db_name():
    """讀取當前使用的真實資料庫名稱"""
    if os.path.exists(DB_NAME_FILE):
        with open(DB_NAME_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return DEFAULT_EXCEL_PATH

def set_current_db_name(name):
    """儲存您上傳的真實資料庫名稱"""
    with open(DB_NAME_FILE, "w", encoding="utf-8") as f:
        f.write(name)

@st.cache_data
def load_database():
    if not os.path.exists(DEFAULT_EXCEL_PATH):
        return None
    try:
        # 為了相容性，先嘗試讀取 csv，若失敗則讀取 excel
        if DEFAULT_EXCEL_PATH.endswith('.csv'):
            df = pd.read_csv(DEFAULT_EXCEL_PATH, dtype=str, keep_default_na=False)
        else:
            try:
                df = pd.read_excel(DEFAULT_EXCEL_PATH, dtype=str, keep_default_na=False)
            except:
                # 容錯處理：如果實際是 csv 但副檔名是 xlsx 
                df = pd.read_csv(DEFAULT_EXCEL_PATH, dtype=str, keep_default_na=False)
                
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"資料庫讀取失敗: {e}")
        return None

# ================= 2. 頁面主邏輯 =================
def show_food_label_page():
    # --- CSS 與 UI 樣式 ---
    st.markdown("""
        <style>
            .logo-container { display: flex; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
            .logo-text { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 28px; font-weight: 800; color: #2c3e50; letter-spacing: -0.5px; margin-left: 10px; line-height: 1; }
            .logo-dot { color: #007bff; }
            .logo-sub { font-size: 14px; color: #888; font-weight: 400; margin-left: 15px; padding-left: 15px; border-left: 1px solid #ddd; height: 20px; line-height: 20px; }
            
            .result-card { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 20px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); transition: all 0.2s; }
            .result-card:hover { border-color: #007bff; box-shadow: 0 6px 12px rgba(0,123,255,0.1); }
            
            .item-title { font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 5px; }
            .item-code { font-family: monospace; background: #f1f3f5; padding: 2px 8px; border-radius: 4px; color: #d63384; font-size: 14px; margin-right: 10px; }
            .item-label { font-size: 13px; color: #666; font-weight: bold; }
            
            /* 調整數字輸入框外觀 */
            div[data-testid="stNumberInput"] label { display: none; }
            
            /* 打印按鈕美化 */
            .print-btn-container button { width: 100% !important; height: 45px !important; background-color: #e7f5ff !important; color: #004085 !important; border: 1px solid #b8daff !important; border-radius: 8px !important; font-weight: bold !important; font-size: 16px !important; transition: all 0.2s !important; }
            .print-btn-container button:hover { background-color: #007bff !important; color: white !important; }
            
            /* Search Input X 按鈕 */
            input[type="search"]::-webkit-search-cancel-button { -webkit-appearance: searchfield-cancel-button; cursor: pointer; height: 16px; width: 16px; opacity: 0.6; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="logo-container">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#007bff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M6 9V2h12v7"></path><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><path d="M6 14h12v8H6z"></path>
            </svg>
            <div class="logo-text">Letech<span class="logo-dot">.</span></div>
            <div class="logo-sub">Intelligent Label Solution</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🍎 Food Label 打印系統")
    
    # ================= 🌟 配置新文件區塊 =================
    with st.expander("⚙️ 配置新資料庫文件 (Database Management)", expanded=False):
        st.info("支援上傳任何檔名的 Excel (.xlsx) 或 CSV (.csv) 檔案。上傳後系統會自動套用！")
        new_db_file = st.file_uploader("上傳新的資料庫檔案", type=["xlsx", "csv"], key="food_new_db_uploader")
        
        if new_db_file:
            if st.button("確認更新資料庫", type="primary", key="food_update_db_btn"):
                try:
                    # 檔案轉換邏輯：不管是啥名字，統一轉成 data.xlsx 給系統吃
                    if new_db_file.name.endswith('.csv'):
                        temp_df = pd.read_csv(new_db_file, dtype=str)
                        temp_df.to_excel(DEFAULT_EXCEL_PATH, index=False)
                    else:
                        with open(DEFAULT_EXCEL_PATH, "wb") as f:
                            f.write(new_db_file.getbuffer())
                    
                    # ⭐ 記錄真實檔名，讓 UI 可以顯示
                    set_current_db_name(new_db_file.name)
                    
                    st.cache_data.clear()
                    st.success(f"✅ 資料庫已成功更新為：【{new_db_file.name}】！系統將在 2 秒後重新載入...")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 更新失敗: {e}")

    # ================= 預先載入資料庫 =================
    df = load_database()
    db_name = get_current_db_name()
    if df is not None:
        st.caption(f"📚 Linked Database: `{db_name}` (Total {len(df)} items)")
    else:
        st.warning(f"⚠️ 找不到資料庫 `{db_name}`，請在上方「配置新資料庫文件」上傳檔案。")
        return

    # --- 搜尋區塊 ---
    search_query = st.text_input("🔍 搜尋商品 (請輸入 Product No. 或 Barcode):", placeholder="例如: GAR-113166")
    
    # 轉換成 search type 顯示打叉按鈕
    components.html("""
        <script>
        const parentDoc = window.parent.document;
        function setupSearchBox() {
            const inputs = parentDoc.querySelectorAll('input[placeholder="例如: GAR-113166"]');
            inputs.forEach(input => { if (input.type !== "search") { input.setAttribute('type', 'search'); } });
        }
        setupSearchBox(); setTimeout(setupSearchBox, 300); setTimeout(setupSearchBox, 1000);
        </script>
    """, height=0)

    st.divider()

    # --- 搜尋與顯示邏輯 ---
    if search_query:
        query = search_query.strip().lower()
        
        # 精準/模糊搜尋 (針對 Product_No 和 Barcode)
        mask = (
            df['Product_No'].astype(str).str.lower().str.contains(query, na=False) | 
            df['Barcode'].astype(str).str.lower().str.contains(query, na=False)
        )
        results = df[mask]

        if results.empty:
            st.warning(f"❌ 找不到包含「{search_query}」的商品。")
        else:
            st.success(f"✅ 找到 {len(results)} 款商品")
            
            for idx, row in results.iterrows():
                p_no = row.get('Product_No', 'N/A')
                barcode = row.get('Barcode', 'N/A')
                desc = row.get('Description', '未命名商品')
                
                with st.container():
                    st.markdown('<div class="result-card">', unsafe_allow_html=True)
                    
                    # 使用 Columns 排版: 左邊是資訊，右邊是數量與列印
                    c_info, c_qty, c_print = st.columns([3, 1, 1.5])
                    
                    with c_info:
                        st.markdown(f"<div class='item-title'>{desc}</div>", unsafe_allow_html=True)
                        st.markdown(f"""
                            <div style='margin-top: 10px;'>
                                <span class='item-label'>SKU:</span> <span class='item-code'>{p_no}</span>
                                <span class='item-label'>Barcode:</span> <span class='item-code'>{barcode}</span>
                            </div>
                        """, unsafe_allow_html=True)
                        
                    with c_qty:
                        st.markdown("<div style='font-size: 13px; font-weight: bold; color: #666; margin-bottom: 5px; text-align: center;'>列印數量</div>", unsafe_allow_html=True)
                        qty = st.number_input("Qty", min_value=1, max_value=500, value=1, step=1, key=f"qty_{idx}")
                        
                    with c_print:
                        st.markdown("<div style='margin-bottom: 23px;'></div>", unsafe_allow_html=True) # 為了對齊
                        st.markdown('<div class="print-btn-container">', unsafe_allow_html=True)
                        if st.button("🖨️ 打印 Food Label", key=f"print_{idx}", use_container_width=True):
                            log_action("FoodLabel_Print")
                            
                            if Lable:
                                # 組合 Lable.py 需要的資料格式
                                item_data = {
                                    'Barcode': barcode,
                                    '商品名稱': desc
                                }
                                # 將 pandas row 轉回單行的 DataFrame 交給 Lable.py
                                master_df_row = pd.DataFrame([row])
                                
                                # 呼叫您既有的 Lable.py 產出 HTML
                                html_content = Lable.generate_food_label_html(item_data, master_df_row, qty)
                                
                                # 觸發隱藏的 Iframe 列印
                                components.html(html_content, height=30)
                            else:
                                st.error("找不到 Lable.py 模組，無法列印。")
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    show_food_label_page()
