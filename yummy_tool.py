import streamlit as st
from pypdf import PdfReader, PdfWriter
import pandas as pd
import re
import io
import base64
import time
import os
import gc
import streamlit.components.v1 as components
from usage_tracker import log_action

# ================= 設定預設檔案名稱 =================
DEFAULT_EXCEL_PATH = "data.xlsx"
DEFAULT_FONT_PATH = "font.ttf"
DB_NAME_FILE = "yummy_current_db_name.txt"

# ================= 1. 快取讀取與檔名記憶函式 =================
def get_current_db_name():
    if os.path.exists(DB_NAME_FILE):
        with open(DB_NAME_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "data.xlsx"

def set_current_db_name(name):
    with open(DB_NAME_FILE, "w", encoding="utf-8") as f:
        f.write(name)

@st.cache_data
def load_local_excel(file_path):
    if not os.path.exists(file_path):
        return None
    if file_path.endswith('.csv'):
        return pd.read_csv(file_path, dtype=str, keep_default_na=False)
    else:
        return pd.read_excel(file_path, dtype=str, keep_default_na=False)

@st.cache_data
def load_local_font_bytes(file_path):
    if not os.path.exists(file_path):
        return None
    with open(file_path, "rb") as f:
        return f.read()

# ================= 2. 輔助函式與智能判斷 =================
def clean_val(val):
    if pd.isna(val) or str(val).lower() == 'nan': return ""
    return str(val).strip()

def get_nutri_val(data, key):
    val = data.get(key)
    if pd.isna(val) or str(val).lower() == 'nan': return "0"
    return str(val).strip()

def smart_get_caution_text(data_dict):
    if 'Cautions' in data_dict: return clean_val(data_dict['Cautions'])
    if 'Caution' in data_dict: return clean_val(data_dict['Caution'])
    if 'cautions' in data_dict: return clean_val(data_dict['cautions'])
    
    lower_keys = {k.lower(): k for k in data_dict.keys()}
    for k_lower, k_original in lower_keys.items():
        if 'caution' in k_lower: return clean_val(data_dict[k_original])
    for k_lower, k_original in lower_keys.items():
        if 'warning' in k_lower: return clean_val(data_dict[k_original])
    return None 

def extract_date_from_text(text):
    text = text.replace('\n', ' ')
    match_compact = re.search(r"\b(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\b", text)
    if match_compact: return f"{match_compact.group(1)}-{match_compact.group(2)}-{match_compact.group(3)}"
    match_dmy_slash = re.search(r"\b(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])/(20\d{2})\b", text)
    if match_dmy_slash: return f"{match_dmy_slash.group(3)}-{match_dmy_slash.group(2)}-{match_dmy_slash.group(1)}"
    match_standard = re.search(r"\b(20\d{2})[./-](0[1-9]|1[0-2])[./-](0[1-9]|[12]\d|3[01])\b", text)
    if match_standard: return f"{match_standard.group(1)}-{match_standard.group(2)}-{match_standard.group(3)}"
    return "未偵測到"

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

# ✨ 智能判定是否為純警告標籤 ✨
def is_caution_only(data_dict):
    """如果沒有任何食品成分或營養標示數據，就判定為警告標籤"""
    food_keys = ['Ingredients', 'Energy', 'Protein', 'Total_Fat', 'Carb', 'Sodium']
    for k in food_keys:
        val = clean_val(data_dict.get(k, ''))
        # 只要有一個欄位有資料且不為 "0"，就代表它是食品標籤
        if val and val != "0":
            return False
    # 全部為空或 0，判定為 Caution Label
    return True

# ✨ 智能資料過濾器（解決多個重複結果）✨
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

# ================= 3. HTML 標籤生成器 =================
def create_label_html_on_the_fly(item, matched_data, font_css, qty):
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
        body {{ margin: 0; padding: 0; }}
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
            <div class="bb-box">Best before(Date Format):<br>Show on package(見包裝)<br>此日期前最佳(Format CHI)</div>
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
    # ✨ 這裡已將 border: 4px solid black 移除 ✨
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

def js_instant_print(full_html_content, item_id):
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
    components.html(js_code, height=30)

# ================= 4. 合併後的主頁面 =================
def show_yummy_page():
    if 'parsed_items' not in st.session_state: st.session_state['parsed_items'] = []
    if 'last_uploaded_file_id' not in st.session_state: st.session_state['last_uploaded_file_id'] = None
    if 'font_css' not in st.session_state: st.session_state['font_css'] = ""
    if 'cleaned_pdf_bytes' not in st.session_state: st.session_state['cleaned_pdf_bytes'] = None
    if 'cleaned_pdf_name' not in st.session_state: st.session_state['cleaned_pdf_name'] = ""
    if 'product_no_tracker' not in st.session_state: st.session_state['product_no_tracker'] = {} 

    st.markdown("""
        <style>
            .logo-container { display: flex; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
            .logo-text { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 28px; font-weight: 800; color: #2c3e50; letter-spacing: -0.5px; margin-left: 10px; line-height: 1; }
            .logo-dot { color: #007bff; }
            .logo-sub { font-size: 14px; color: #888; font-weight: 400; margin-left: 15px; padding-left: 15px; border-left: 1px solid #ddd; height: 20px; line-height: 20px; }
            .grid-header { background-color: #f8f9fa; padding: 12px 10px; border-top: 2px solid #e9ecef; border-bottom: 2px solid #e9ecef; font-weight: 600; color: #495057; font-size: 14px; }
            .grid-row { padding: 8px 0; border-bottom: 1px solid #f1f3f5; transition: background-color 0.2s; display: flex; align-items: center; height: 100%; min-height: 45px;}
            .grid-row:hover { background-color: #f8f9fa; }
            div[data-testid="column"] { display: flex; flex-direction: column; justify-content: center; }
            
            /* ✨ 原始霸道寫法：強制所有 stButton (包含打印) 變成您要的樣子 */
            div.stButton > button { 
                width: 100px !important; 
                height: 38px !important; 
                min-height: 38px !important; 
                border-radius: 6px !important; 
                padding: 0px !important; 
                background-color: #e7f5ff !important; 
                color: #004085 !important; 
                border: none !important; 
                display: flex !important; 
                justify-content: center !important; 
                align-items: center !important; 
                margin: 0 auto !important; 
                transform: translateX(20px) !important; 
            }
            div.stButton > button:hover { background-color: #d0ebff !important; color: #002752 !important; }
            div.stButton > button p { font-size: 13px !important; font-weight: bold !important; line-height: 1 !important; margin: 0 !important; padding: 0 !important; }
            div.stButton { width: 100% !important; display: flex !important; justify-content: center !important; align-items: center !important; height: 100% !important; min-height: 45px !important; margin: 0 !important; }
            
            /* ✨ 保護 1：下載按鈕 (強制覆蓋上面的設定) */
            div[data-testid="stDownloadButton"] > button {
                width: auto !important; 
                height: 32px !important; 
                min-height: 32px !important; 
                padding: 0 15px !important; 
                transform: none !important;
                background-color: #f1f3f5 !important;
                color: #495057 !important;
                border: 1px solid #ced4da !important;
                border-radius: 4px !important;
            }
            div[data-testid="stDownloadButton"] > button:hover { background-color: #e9ecef !important; color: #212529 !important; }

            /* ✨ 保護 2：綠色 Popover 按鈕 (強制覆蓋上面的設定) */
            div[data-testid="stPopover"] > button {
                width: 100% !important;
                background-color: #28a745 !important;
                color: white !important;
                border: none !important;
                font-weight: bold !important;
                border-radius: 6px !important;
                padding: 8px 16px !important;
                transform: none !important;
                height: 38px !important;
                min-height: 38px !important;
            }
            div[data-testid="stPopover"] > button:hover {
                background-color: #218838 !important;
                box-shadow: 0 4px 8px rgba(40, 167, 69, 0.3) !important;
                color: white !important;
            }
            
            /* ✨ 保護 3：Popover 內部的「確認更新」按鈕 (強制覆蓋) */
            div[data-testid="stPopoverBody"] div.stButton > button {
                width: 100% !important;
                transform: none !important;
                background-color: #007bff !important;
                color: white !important;
            }
            div[data-testid="stPopoverBody"] div.stButton > button:hover {
                background-color: #0056b3 !important;
            }

            .cell-badge-err { width: 100px !important; height: 38px !important; min-height: 38px !important; border-radius: 6px !important; padding: 0px !important; background-color: #ffe6e6 !important; color: #dc3545 !important; display: flex !important; justify-content: center !important; align-items: center !important; margin: 0 auto !important; font-size: 13px !important; font-weight: bold !important; line-height: 1 !important; transform: translateX(-1px) !important; }
            
            .cell-text { font-size: 15px; color: #333; padding: 0 5px; width: 100%; text-align: left; }
            .cell-sub { font-size: 12px; color: #888; padding: 0 5px; width: 100%; text-align: left; }
            .cell-code { font-family: monospace; font-size: 13px; background: #f1f3f5; padding: 2px 6px; border-radius: 4px; color: #333; }
            .cell-qty { font-weight: bold; font-size: 15px; color: #000; text-align: center; display: block; width: 100%; }
            div[data-testid="column"]:nth-of-type(7) > div { display: flex !important; flex-direction: row !important; justify-content: center !important; align-items: center !important; width: 100% !important; height: 100% !important; }
        </style>
        
        <div class="logo-container">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#007bff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M6 9V2h12v7"></path><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><path d="M6 14h12v8H6z"></path>
            </svg>
            <div class="logo-text">Letech<span class="logo-dot">.</span></div>
            <div class="logo-sub">Intelligent Label Solution</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🍔 Yummy 3PL System")

    # ================= ✨ Yummy 專用：配置新文件區塊 (按鈕版) ✨ =================
    col1, col2 = st.columns([0.8, 0.2])
    with col2:
        if hasattr(st, "popover"):
            with st.popover("⚙️ 配置文件"):
                st.markdown("#### 📂 Upload New Database")
                st.caption("Support Excel (.xlsx) 或 CSV (.csv) File。It will be automatically applied after uploading.！")
                new_db_file = st.file_uploader("", type=["xlsx", "csv"], key="yummy_new_db_uploader", label_visibility="collapsed")
                
                if new_db_file:
                    if st.button("Confirm Database Update", type="primary", key="yummy_update_btn", use_container_width=True):
                        try:
                            if new_db_file.name.endswith('.csv'):
                                temp_df = pd.read_csv(new_db_file, dtype=str)
                                temp_df.to_excel(DEFAULT_EXCEL_PATH, index=False)
                            else:
                                with open(DEFAULT_EXCEL_PATH, "wb") as f:
                                    f.write(new_db_file.getbuffer())
                            
                            set_current_db_name(new_db_file.name)
                            st.cache_data.clear()
                            st.success(f"✅ Database Update to：【{new_db_file.name}】！System will Reload in 2 Seconds...")
                            time.sleep(2)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 更新失敗: {e}")
        else:
            st.info("請更新 Streamlit。")

    # ================= 預先載入資料庫 =================
    df_master = load_local_excel(DEFAULT_EXCEL_PATH)
    font_bytes = load_local_font_bytes(DEFAULT_FONT_PATH)
    current_db_name = get_current_db_name() 
    
    if df_master is not None:
        df_master.columns = df_master.columns.str.strip()
        st.success(f"✅ Linked Database：`{current_db_name}` (最新版本)")
    else:
        st.warning(f"⚠️ 找不到 `{current_db_name}`，請點擊上方「⚙️ 配置文件」上傳檔案。")

    st.divider()

    uploaded_pdf = st.file_uploader("Please Upload Yummy 3PL PDF File", type=["pdf"])

    if uploaded_pdf and df_master is not None:
        current_file_id = f"{uploaded_pdf.name}_{DEFAULT_EXCEL_PATH}_{DEFAULT_FONT_PATH}"

        if st.session_state['last_uploaded_file_id'] != current_file_id:
            log_action("Yummy_Process")
            st.session_state['parsed_items'] = []
            st.session_state['font_css'] = ""
            st.session_state['cleaned_pdf_bytes'] = None
            st.session_state['cleaned_pdf_name'] = ""
            st.session_state['product_no_tracker'] = {}
            st.session_state['last_uploaded_file_id'] = current_file_id
            gc.collect() 
            st.cache_data.clear()

        # 如果還沒解析過，則進行合併處理 (清洗PDF + 提取資料)
        if not st.session_state['parsed_items']:
            try:
                if font_bytes and not st.session_state['font_css']:
                    st.session_state['font_css'] = font_to_base64_css(font_bytes, DEFAULT_FONT_PATH)
                
                reader = PdfReader(uploaded_pdf)
                writer = PdfWriter()
                temp_items = []
                
                total_pages = len(reader.pages)
                kept_pages_count = 0
                product_no_tracker = {}
                
                prog = st.progress(0)
                status_text = st.empty()
                
                for i, page in enumerate(reader.pages):
                    status_text.text(f"⏳ Processing page {i+1}/{total_pages}...")
                    text = page.extract_text()
                    images = page.images
                    
                    # 1. 判斷空白頁
                    has_content = (text and text.strip()) or len(images) > 0
                    
                    if has_content:
                        # 加入新 PDF
                        writer.add_page(page)
                        kept_pages_count += 1
                        current_page_num = i + 1
                        
                        # 2. 提取文字資料
                        lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
                        p_no = lines[0] if lines else "N/A"
                        
                        # ⭐ 紀錄重複頁面
                        if p_no not in product_no_tracker:
                            product_no_tracker[p_no] = []
                        product_no_tracker[p_no].append(current_page_num)
                        
                        qty = 1
                        qty_match = re.search(r"(\d+)\.0000", text)
                        if qty_match: qty = int(qty_match.group(1))
                        
                        barcode = "未偵測到"
                        b_match = re.search(r"\b\d{12,14}\b", text)
                        if b_match: barcode = b_match.group(0)
                        
                        p_date = extract_date_from_text(text)
                        
                        name_parts = []
                        if len(lines) > 1:
                            for line in lines[1:]:
                                if re.search(r"\d+\.0000|\b\d{12,14}\b", line): break
                                name_parts.append(line)
                        p_name = " ".join(name_parts)
                        
                        # 3. 匹配 Excel 資料庫 (✨ 使用智能過濾器過濾空資料)
                        matches = df_master[df_master['Product_No'].astype(str).str.strip() == p_no]
                        matched_data = {}
                        has_match = False
                        
                        if not matches.empty:
                            has_match = True
                            # 取出分數最高、資料最完整的那一筆
                            best_match_df = get_best_results(matches)
                            matched_data = best_match_df.iloc[0].to_dict()

                        temp_items.append({
                            "id": f"{p_no}_{i}", 
                            "Product No": p_no, 
                            "商品名稱": p_name, 
                            "Barcode": barcode, 
                            "數量": qty, 
                            "日期": p_date,
                            "matched_data": matched_data,
                            "has_match": has_match
                        })
                        
                    prog.progress((i+1)/total_pages)
                
                # 儲存清洗後的 PDF 與追蹤器
                output_buffer = io.BytesIO()
                writer.write(output_buffer)
                st.session_state['cleaned_pdf_bytes'] = output_buffer.getvalue()
                st.session_state['cleaned_pdf_name'] = f"cleaned_{uploaded_pdf.name}"
                st.session_state['kept_pages_count'] = kept_pages_count
                st.session_state['total_pages'] = total_pages
                st.session_state['product_no_tracker'] = product_no_tracker
                
                st.session_state['parsed_items'] = temp_items
                prog.empty()
                status_text.empty()
                gc.collect()
                st.success("✅ Processing Complete!")
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")
                return

        # ================= 顯示結果與列表 =================
        if st.session_state['parsed_items']:
            
            # --- 顯示 PDF 處理結果與重複檢測表格 ---
            st.subheader("📄 PDF Processing & Duplicate Check")
            res_col1, res_col2 = st.columns([1, 1.5])
            
            with res_col1:
                st.write("**📊 Summary**")
                c1, c2 = st.columns(2)
                c1.metric("Original Pages", st.session_state.get('total_pages', 0))
                c2.metric("Valid Pages", st.session_state.get('kept_pages_count', 0))
                
                st.write("") 
                st.download_button(
                    label="📥 Download Cleaned PDF",
                    data=st.session_state['cleaned_pdf_bytes'],
                    file_name=st.session_state['cleaned_pdf_name'],
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
                
            with res_col2:
                st.write("**⚠️ Duplicate Detection**")
                tracker = st.session_state.get('product_no_tracker', {})
                # 篩選出出現大於 1 次的編號
                duplicates = {k: v for k, v in tracker.items() if len(v) > 1}
                
                if duplicates:
                    st.error(f"Found {len(duplicates)} Duplicates!")
                    dup_data = []
                    for p_no, pages in duplicates.items():
                        dup_data.append({
                            "Product No": p_no,
                            "Repeat Times": len(pages),
                            "Pages Number": ", ".join(map(str, pages)) # 清楚列出哪幾頁
                        })
                    # 顯示清晰的表格
                    st.dataframe(pd.DataFrame(dup_data), use_container_width=True, hide_index=True)
                else:
                    st.success("✅ No duplicates found.")
            
            st.markdown("---")
            st.subheader("📋 Label Generation List")

            col_ratios = [0.5, 1.5, 4, 2, 1.5, 0.8, 1.5]
            headers = ["No", "Product No", "Product Name", "Barcode", "Date", "Qty", "Action"]
            cols = st.columns(col_ratios)
            for col, h in zip(cols, headers):
                col.markdown(f"<div class='grid-header'>{h}</div>", unsafe_allow_html=True)

            skus = [x['Product No'] for x in st.session_state['parsed_items']]
            dups = [x for x in skus if skus.count(x) > 1]

            for index, item in enumerate(st.session_state['parsed_items']):
                p_no = item['Product No']
                is_dup = p_no in dups
                name_bg_style = "background-color: #fff3cd;" if is_dup else ""
                
                with st.container():
                    c0, c1, c2, c3, c4, c5, c6 = st.columns(col_ratios)
                    c0.markdown(f"<div class='grid-row'><div class='cell-text' style='text-align:center; color:#888;'>{index+1}</div></div>", unsafe_allow_html=True)
                    c1.markdown(f"<div class='grid-row'><div class='cell-text'><b>{p_no}</b></div></div>", unsafe_allow_html=True)
                    name_html = f"<div class='cell-text'>{item['商品名稱']}</div>"
                    c2.markdown(f"<div class='grid-row' style='{name_bg_style}'>{name_html}</div>", unsafe_allow_html=True)
                    code_html = f"<span class='cell-code'>{item['Barcode']}</span>"
                    c3.markdown(f"<div class='grid-row'>{code_html}</div>", unsafe_allow_html=True)
                    c4.markdown(f"<div class='grid-row'><div class='cell-sub'>{item['日期']}</div></div>", unsafe_allow_html=True)
                    c5.markdown(f"<div class='grid-row'><span class='cell-qty'>{item['數量']}</span></div>", unsafe_allow_html=True)
                    
                    with c6:
                        # ✨ 智能判斷：是否為警告標籤
                        is_caution_item = is_caution_only(item['matched_data'])
                        
                        row_wrapper_style = "display: flex; justify-content: center; align-items: center; width: 100%; height: 100%; min-height: 45px;"
                        
                        if item['has_match'] or is_caution_item:
                            if st.button("打印", key=f"btn_{item['id']}_{index}"):
                                log_action("Yummy_Print")
                                
                                if is_caution_item:
                                    caution_text = smart_get_caution_text(item['matched_data'])
                                    if caution_text is None:
                                        available_cols = ", ".join(item['matched_data'].keys())
                                        caution_text = f"Cautions Column Missing!<br>Available: {available_cols}"
                                    elif caution_text == "":
                                        caution_text = "Caution Column Empty"
                                        
                                    final_html = create_caution_html(caution_text, item['數量'])
                                else:
                                    final_html = create_label_html_on_the_fly(
                                        item, 
                                        item['matched_data'], 
                                        st.session_state['font_css'],
                                        item['數量']
                                    )
                                js_instant_print(final_html, item['id'])
                        else:
                            st.markdown(f"<div style='{row_wrapper_style}'><div class='cell-badge-err'>無資料</div></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    show_yummy_page()
