import streamlit as st
import pandas as pd
import os
import re
import base64
import time
from pathlib import Path
import streamlit.components.v1 as components

try:
    from usage_tracker import log_action
except ImportError:
    def log_action(action_name): pass

# ================= 設定預設檔案名稱 =================
DEFAULT_EXCEL_PATH = "data.xlsx"
DEFAULT_FONT_PATH = "font.ttf"
DB_NAME_FILE = "current_db_name.txt"

# ================= 1. 資料庫與字體讀取 =================
def get_current_db_name():
    if os.path.exists(DB_NAME_FILE):
        with open(DB_NAME_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return DEFAULT_EXCEL_PATH

def set_current_db_name(name):
    with open(DB_NAME_FILE, "w", encoding="utf-8") as f:
        f.write(name)

@st.cache_data
def load_database():
    if not os.path.exists(DEFAULT_EXCEL_PATH): return None
    try:
        if DEFAULT_EXCEL_PATH.endswith('.csv'):
            df = pd.read_csv(DEFAULT_EXCEL_PATH, dtype=str, keep_default_na=False)
        else:
            try:
                df = pd.read_excel(DEFAULT_EXCEL_PATH, dtype=str, keep_default_na=False)
            except:
                df = pd.read_csv(DEFAULT_EXCEL_PATH, dtype=str, keep_default_na=False)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        return None

@st.cache_data
def load_local_font_bytes(file_path):
    if not os.path.exists(file_path): return None
    with open(file_path, "rb") as f: return f.read()

# ================= 2. 標籤生成函數與智能判斷 =================
def clean_val(val):
    if pd.isna(val) or str(val).lower() == 'nan': return ""
    return str(val).strip()

def get_nutri_val(data, key):
    val = data.get(key)
    if pd.isna(val) or str(val).lower() == 'nan': return "0"
    return str(val).strip()

def font_to_base64_css(font_bytes, file_name):
    if not font_bytes: return ""
    try:
        b64_str = base64.b64encode(font_bytes).decode('utf-8')
        mime_type = "font/ttf"
        if file_name.endswith(".otf"): mime_type = "font/otf"
        elif file_name.endswith(".woff"): mime_type = "font/woff"
        return f"""
        @font-face {{ font-family: 'CustomLabelFont'; src: url(data:{mime_type};base64,{b64_str}) format('truetype'); font-weight: bold; font-style: normal; }}
        body, .label-container, div, span {{ font-family: 'CustomLabelFont', Helvetica, Arial, sans-serif !important; }}
        """
    except Exception: return ""

def smart_get_caution_text(data_dict):
    """從資料字典中聰明地尋找警告文字欄位"""
    if 'Cautions' in data_dict: return clean_val(data_dict['Cautions'])
    if 'Caution' in data_dict: return clean_val(data_dict['Caution'])
    if 'cautions' in data_dict: return clean_val(data_dict['cautions'])
    
    lower_keys = {k.lower(): k for k in data_dict.keys()}
    for k_lower, k_original in lower_keys.items():
        if 'caution' in k_lower: return clean_val(data_dict[k_original])
    for k_lower, k_original in lower_keys.items():
        if 'warning' in k_lower: return clean_val(data_dict[k_original])
    return None

def is_caution_only(data_dict):
    """如果沒有任何食品成分或營養標示數據，就判定為警告標籤"""
    food_keys = ['Ingredients', 'Energy', 'Protein', 'Total_Fat', 'Carb', 'Sodium']
    for k in food_keys:
        val = clean_val(data_dict.get(k, ''))
        if val and val != "0":
            return False
    return True

# ✨ 智能資料過濾器（過濾掉空白、無效的重複資料）
def get_best_results(results_df):
    if results_df.empty: 
        return results_df
    
    scores = []
    for _, row in results_df.iterrows():
        score = 0
        if str(row.get('Ingredients', '')).strip() not in ['', 'nan', '0', 'None']: score += 2
        if str(row.get('Energy', '')).strip() not in ['', 'nan', '0', 'None']: score += 1
        
        for k in row.keys():
            if 'caution' in str(k).lower() or 'warning' in str(k).lower():
                if str(row[k]).strip() not in ['', 'nan', '0', 'None']: 
                    score += 2
                    break
        scores.append(score)
        
    results_df = results_df.copy()
    results_df['__score'] = scores
    # 根據分數從高到低排序，然後刪除重複的 Product_No，只保留分數最高的那一筆
    results_df = results_df.sort_values(by='__score', ascending=False)
    results_df = results_df.drop_duplicates(subset=['Product_No'], keep='first')
    return results_df

# ✨ 新增：三階段智能判定器
def check_data_status(data_dict):
    """回傳: 'food', 'caution', 或 'empty'"""
    if not data_dict:
        return 'empty'
        
    # 1. 檢查是否有 Food 欄位
    food_keywords = ['ingredient', 'energy', 'protein', 'fat', 'carb', 'sodium', 'serving']
    for k, v in data_dict.items():
        k_lower = str(k).lower()
        if any(fw in k_lower for fw in food_keywords):
            val = str(v).strip().lower()
            if val and val not in ['nan', '0', 'none']:
                return 'food'
                
    # 2. 檢查是否有 Caution 欄位
    caution_keywords = ['caution', 'warning']
    for k, v in data_dict.items():
        k_lower = str(k).lower()
        if any(cw in k_lower for cw in caution_keywords):
            val = str(v).strip().lower()
            if val and val not in ['nan', 'none', '']:
                return 'caution'
                
    return 'empty'

def create_food_label_html(item, matched_data, font_css, qty):
    data = matched_data if matched_data else {}
    desc_text = clean_val(data.get('Description', item['商品名稱']))
    barcode_text = item['Barcode'] if item['Barcode'] != "未偵測到" else clean_val(data.get('Barcode', ''))
    
    nutri = {
        'Serving_Size': get_nutri_val(data, 'Serving_Size'),
        'Energy': get_nutri_val(data, 'Energy'),
        'Protein': get_nutri_val(data, 'Protein'),
        'Total_Fat': get_nutri_val(data, 'Total_Fat'),
        'Sat_Fat': get_nutri_val(data, 'Sat_Fat'),
        'Trans_Fat': get_nutri_val(data, 'Trans_Fat'),
        'Carb': get_nutri_val(data, 'Carb'),
        'Sugar': get_nutri_val(data, 'Sugar'),
        'Sodium': get_nutri_val(data, 'Sodium'),
        'Net_Content': get_nutri_val(data, 'Net_Content') or get_nutri_val(data, 'Net Content'),
        'Country_Of_Origin': get_nutri_val(data, 'Country_Of_Origin'),
    }
    ing_text = clean_val(data.get('Ingredients', ''))
    mfr_text = f"{clean_val(data.get('Madeby_Prefix', ''))} {clean_val(data.get('Madeby', ''))}".strip()
    if "Manufacturer" not in mfr_text: mfr_text = "Manufacturer: " + mfr_text

    single_label_html = f"""
    <html><head><style>
        {font_css}
        @page {{ size: auto; margin: 0mm; }}
        body {{ margin: 0; padding: 0; font-family: Helvetica, Arial, sans-serif; }}
        .label-container {{ width: 70mm; height: 50mm; position: relative; box-sizing: border-box; border: 1px solid #ddd; page-break-after: always; overflow: hidden; font-weight: bold; }}
        .barcode-text {{ position: absolute; left: 2mm; top: 2mm; font-size: 5pt; font-weight: bold; }}
        .desc-text {{ position: absolute; left: 2mm; top: 4.5mm; width: 59mm; font-size: 5pt; line-height: 1.2; font-weight: bold; }}
        .line1 {{ position: absolute; left: 0; top: 9mm; width: 70mm; border-top: 1.42pt solid black; }}
        .nutri-box {{ position: absolute; left: 2mm; top: 10mm; width: 23mm; font-size: 3.5pt; line-height: 4.5pt; font-weight: bold; }}
        .nutri-title {{ font-weight: bold; margin-bottom: 1px; }}
        .nutri-row {{ display: flex; justify-content: space-between; }}
        .indent {{ padding-left: 3px; }}
        .vline {{ position: absolute; left: 26mm; top: 9mm; height: 29mm; border-left: 1.42pt solid black; }}
        .ing-box {{ position: absolute; left: 27mm; top: 10mm; width: 41mm; height: 28mm; font-size: 3.5pt; line-height: 1.1; overflow: hidden; text-align: justify; font-weight: bold; }}
        .line2 {{ position: absolute; left: 0; top: 38mm; width: 70mm; border-top: 1.42pt solid black; }}
        .mfr-box {{ position: absolute; left: 2mm; top: 40mm; width: 35mm; font-size: 4.76pt; line-height: 1.2; font-weight: bold; }}
        .bb-box {{ position: absolute; left: 47mm; top: 40mm; width: 27mm; font-size: 4.2pt; line-height: 1.2; font-weight: bold; white-space: nowrap; }}
    </style></head><body>
        <div class="label-container">
            <div class="barcode-text">{barcode_text}</div>
            <div class="desc-text">{desc_text}</div>
            <div class="line1"></div>
            <div class="nutri-box">
                <div class="nutri-title">Nutrition Information</div>
                <div class="nutri-row"><span>Serving Size:</span><span>{nutri['Serving_Size']}</span></div>
                <div class="nutri-row"><span>Energy:</span><span>{nutri['Energy']}</span></div>
                <div class="nutri-row"><span>Protein:</span><span>{nutri['Protein']}</span></div>
                <div class="nutri-row"><span>Total fat:</span><span>{nutri['Total_Fat']}</span></div>
                <div class="nutri-row indent"><span>- Saturated fat:</span><span>{nutri['Sat_Fat']}</span></div>
                <div class="nutri-row indent"><span>- Trans fat:</span><span>{nutri['Trans_Fat']}</span></div>
                <div class="nutri-row"><span>Carbohydrates:</span><span>{nutri['Carb']}</span></div>
                <div class="nutri-row indent"><span>- Sugars:</span><span>{nutri['Sugar']}</span></div>
                <div class="nutri-row"><span>Sodium:</span><span>{nutri['Sodium']}</span></div>
                <div class="nutri-row"><span>Net Content:</span><span>{nutri['Net_Content']}</span></div>
                <div class="nutri-row"><span>Country Of Origin:</span><span>{nutri['Country_Of_Origin']}</span></div>
            </div>
            <div class="vline"></div>
            <div class="ing-box">Ingredients: {ing_text}</div>
            <div class="line2"></div>
            <div class="mfr-box">{mfr_text}</div>
            <div class="bb-box">Best before(YY-MM-DD):<br>Show on package(見包裝)<br>此日期前最佳(YY-MM-DD)</div>
        </div>
    </body></html>
    """
    import re as regex
    match = regex.search(r'<body>(.*?)</body>', single_label_html, regex.DOTALL)
    if match:
        div_content = match.group(1)
        full_body = div_content * qty
        final_html = single_label_html.replace(div_content, full_body)
    else:
        final_html = single_label_html
    return final_html

def create_caution_html(text, qty):
    formatted_text = str(text).replace('\n', '<br/>')
    if not formatted_text or formatted_text == "nan": formatted_text = ""
    single_label_html = f"""
    <html><head><style>
        @page {{ size: auto; margin: 0mm; }}
        body {{ margin: 0; padding: 0; font-family: Helvetica, Arial, sans-serif; }}
        .label-container {{ width: 70mm; height: 50mm; box-sizing: border-box; padding: 2mm; page-break-after: always; position: relative; display: flex; align-items: center; justify-content: center; text-align: center; }}
        .caution-text {{ font-size: 15pt; font-weight: 900; line-height: 1.2; word-wrap: break-word; color: black; }}
    </style></head><body>
        <div class="label-container"><div class="caution-text">{formatted_text}</div></div>
    </body></html>
    """
    import re as regex
    match = regex.search(r'<body>(.*?)</body>', single_label_html, regex.DOTALL)
    if match:
        div_content = match.group(1)
        full_body = div_content * qty
        final_html = single_label_html.replace(div_content, full_body)
    else: final_html = single_label_html
    return final_html

def js_instant_print(full_html_content):
    b64_html = base64.b64encode(full_html_content.encode('utf-8')).decode('utf-8')
    js_code = f"""
    <script>
        (function() {{
            const b64 = "{b64_html}";
            const htmlContent = decodeURIComponent(escape(window.atob(b64)));
            const win = window.open('', '_blank', 'width=400,height=400');
            if (win) {{
                win.document.write(htmlContent); win.document.close();
                win.onload = function() {{ win.focus(); win.onafterprint = function() {{ win.close(); }}; win.print(); win.onfocus = function() {{ setTimeout(()=>{{ win.close(); }}, 500); }}; }};
            }} else {{ alert("請允許彈出視窗！"); }}
        }})();
    </script>
    """
    components.html(js_code, height=0)


# ================= 3. 頁面主邏輯 =================
def show_food_label_page():
    # ================= ✨ UI 與 CSS 美化 ✨ =================
    st.markdown("""
        <style>
            .logo-container { display: flex; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
            .logo-text { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 28px; font-weight: 800; color: #2c3e50; letter-spacing: -0.5px; margin-left: 10px; line-height: 1; }
            .logo-dot { color: #007bff; }
            .logo-sub { font-size: 14px; color: #888; font-weight: 400; margin-left: 15px; padding-left: 15px; border-left: 1px solid #ddd; height: 20px; line-height: 20px; }
            
            .result-card { 
                background: linear-gradient(145deg, #ffffff, #fcfcfc);
                border: 1px solid #e2e8f0; 
                border-radius: 16px; 
                padding: 24px; 
                margin-bottom: 20px; 
                box-shadow: 0 4px 10px rgba(0,0,0,0.03); 
                transition: all 0.3s ease; 
            }
            .result-card:hover { 
                border-color: #b3d4ff; 
                box-shadow: 0 10px 20px rgba(0, 123, 255, 0.1); 
                transform: translateY(-2px);
            }
            
            .item-title { font-size: 20px; font-weight: 800; color: #1e293b; margin-bottom: 15px; line-height: 1.4; }
            
            .info-badges-container { display: flex; flex-wrap: wrap; gap: 10px; }
            .item-badge { display: flex; align-items: center; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 4px 10px; font-size: 13px; color: #64748b; font-weight: 600; }
            .item-badge-value { color: #0369a1; background-color: #f0f9ff; margin-left: 8px; padding: 2px 6px; border-radius: 4px; font-family: 'Courier New', monospace; font-weight: bold; }
            
            div[data-testid="stNumberInput"] label { font-size: 14px !important; color: #475569 !important; font-weight: 600 !important; }
            
            [data-testid="stForm"] { border: none !important; padding: 0 !important; margin: 0 !important; }
            
            div.stButton, div[data-testid="stFormSubmitButton"] { margin-top: 28px !important; } 
            div.stButton > button, div[data-testid="stFormSubmitButton"] > button { 
                width: 100% !important; height: 42px !important; 
                background: linear-gradient(135deg, #007bff, #0056b3) !important; 
                color: white !important; border: none !important; border-radius: 8px !important; 
                font-weight: bold !important; font-size: 15px !important; 
                box-shadow: 0 4px 6px rgba(0, 123, 255, 0.2) !important;
                transition: all 0.2s ease !important; 
            }
            div.stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover { 
                box-shadow: 0 6px 12px rgba(0, 123, 255, 0.3) !important; 
                transform: translateY(-1px) !important; filter: brightness(1.1);
            }
            
            div[data-testid="stPopover"] > button {
                background-color: #28a745 !important;
                color: white !important;
                border: none !important;
                font-weight: bold !important;
                border-radius: 6px !important;
                padding: 8px 16px !important;
                height: 38px !important;
                margin-top: 0px !important; 
            }
            div[data-testid="stPopover"] > button:hover {
                background-color: #218838 !important;
                box-shadow: 0 4px 8px rgba(40, 167, 69, 0.3) !important;
                transform: none !important;
                filter: none !important;
            }

            div[data-testid="stPopoverBody"] div.stButton { margin-top: 0px !important; }
            div[data-testid="stPopoverBody"] div.stButton > button { background: #007bff !important; height: 38px !important; }

            input[type="search"]::-webkit-search-cancel-button { -webkit-appearance: searchfield-cancel-button; cursor: pointer; height: 16px; width: 16px; opacity: 0.6; }
            
            .error-badge {
                background-color: #ffe6e6;
                color: #dc3545;
                font-weight: bold;
                padding: 12px 15px;
                border-radius: 8px;
                text-align: center;
                margin-top: 28px;
                border: 1px solid #f5c6cb;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- Logo 區塊 ---
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
    
    # --- 載入字體 ---
    font_bytes = load_local_font_bytes(DEFAULT_FONT_PATH)
    if 'font_css' not in st.session_state:
        st.session_state['font_css'] = font_to_base64_css(font_bytes, DEFAULT_FONT_PATH) if font_bytes else ""
    
    # ================= ✨ 綠色彈出式配置文件按鈕 ✨ =================
    col1, col2 = st.columns([0.8, 0.2])
    with col2:
        if hasattr(st, "popover"):
            with st.popover("⚙️ 配置文件"):
                st.markdown("#### 📂 上傳新資料庫")
                st.caption("支援上傳 Excel (.xlsx) 或 CSV (.csv) 檔案。上傳後會自動套用！")
                new_db_file = st.file_uploader("", type=["xlsx", "csv"], key="food_new_db_uploader", label_visibility="collapsed")
                
                if new_db_file:
                    if st.button("確認更新資料庫", type="primary", key="food_update_db_btn", use_container_width=True):
                        try:
                            if new_db_file.name.endswith('.csv'):
                                temp_df = pd.read_csv(new_db_file, dtype=str)
                                temp_df.to_excel(DEFAULT_EXCEL_PATH, index=False)
                            else:
                                with open(DEFAULT_EXCEL_PATH, "wb") as f:
                                    f.write(new_db_file.getbuffer())
                            
                            set_current_db_name(new_db_file.name)
                            st.cache_data.clear()
                            st.success(f"✅ 資料庫已成功更新為：【{new_db_file.name}】！系統將在 2 秒後重新載入...")
                            time.sleep(2)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 更新失敗: {e}")
        else:
            st.info("請更新 Streamlit。")

    # --- 載入資料庫 ---
    df = load_database()
    db_name = get_current_db_name()
    if df is not None:
        st.caption(f"📚 Linked Database: `{db_name}` (Total {len(df)} items)")
    else:
        st.warning(f"⚠️ 找不到資料庫 `{db_name}`，請點擊右上方「⚙️ 配置文件」上傳檔案。")
        return

    # --- 搜尋區塊 ---
    search_query = st.text_input("🔍 搜尋商品 (請輸入 Product No. 或 Barcode):", placeholder="例如: GAR-113166")
    
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
        
        mask = (
            df['Product_No'].astype(str).str.lower().str.contains(query, na=False) | 
            df['Barcode'].astype(str).str.lower().str.contains(query, na=False)
        )
        results = df[mask]

        if results.empty:
            st.warning(f"❌ 找不到包含「{search_query}」的商品。")
        else:
            best_results = get_best_results(results)
            st.success(f"✅ 找到 {len(best_results)} 款商品")
            
            for idx, row in best_results.iterrows():
                p_no = row.get('Product_No', 'N/A')
                barcode = row.get('Barcode', 'N/A')
                desc = row.get('Description', '未命名商品')
                
                matched_data = row.to_dict()
                # ✨ 呼叫新的三階段判定函數
                data_status = check_data_status(matched_data)
                
                with st.container():
                    st.markdown('<div class="result-card">', unsafe_allow_html=True)
                    
                    with st.form(key=f"form_print_{idx}", clear_on_submit=False):
                        c_info, c_qty, c_print = st.columns([3.5, 1, 1.2])
                        
                        with c_info:
                            st.markdown(f"<div class='item-title'>{desc}</div>", unsafe_allow_html=True)
                            
                            badge_html = f"""
                                <div class='info-badges-container'>
                                    <div class='item-badge'>SKU <span class='item-badge-value'>{p_no}</span></div>
                                    <div class='item-badge'>Barcode <span class='item-badge-value'>{barcode}</span></div>
                            """
                            if data_status == 'caution':
                                badge_html += f"<div class='item-badge' style='color:#dc3545; background-color:#ffe6e6; border-color:#f5c6cb;'>⚠️ 警告標籤模式</div>"
                                
                            badge_html += "</div>"
                            st.markdown(badge_html, unsafe_allow_html=True)
                            
                        with c_qty:
                            qty = st.number_input("列印數量 (Qty)", min_value=1, max_value=500, value=1, step=1, key=f"qty_{idx}")
                            
                        with c_print:
                            # ✨ 根據資料狀態決定顯示什麼
                            if data_status == 'empty':
                                st.markdown("<div class='error-badge'>❌ 無資料</div>", unsafe_allow_html=True)
                            else:
                                submitted = st.form_submit_button("🖨️ 打印標籤", use_container_width=True)
                                if submitted:
                                    log_action("FoodLabel_Print")
                                    item_data = {'Barcode': barcode, '商品名稱': desc}
                                    
                                    if data_status == 'caution':
                                        caution_text = smart_get_caution_text(matched_data)
                                        if not caution_text:
                                            caution_text = "Caution Column Empty"
                                        html_content = create_caution_html(caution_text, qty)
                                    else: # food
                                        html_content = create_food_label_html(item_data, matched_data, st.session_state['font_css'], qty)
                                        
                                    js_instant_print(html_content)
                                
                    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    show_food_label_page()
