import streamlit as st
from pypdf import PdfReader
import pandas as pd
import re
import io
import base64
import time
import os
import gc
import streamlit.components.v1 as components

# ================= 設定預設檔案名稱 =================
DEFAULT_EXCEL_PATH = "data.xlsx"
DEFAULT_FONT_PATH = "font.ttf"

# ================= 設定特殊警告標籤清單 =================
CAUTION_PRODUCT_LIST = [
    "GAR-113166", "GAR-113167", "GAR-113168",
    "LT10006114", "LT10006115", "LT10006116",
    "POPS-106413", "POPS-107836", "SAX-103842",
    "LT10014114", "LT10011267", "NATV-113301",
    "LT10013458", "LT10013459", "PRI-111852",
    "CHE-108483"
]

# ================= 1. 快取讀取函式 =================
@st.cache_data
def load_local_excel(file_path):
    """讀取本地 Excel 並快取結果"""
    # 強制使用 dtype=str 避免自動轉換導致資料判斷錯誤
    if file_path.endswith('.csv'):
        return pd.read_csv(file_path, dtype=str, keep_default_na=False)
    else:
        return pd.read_excel(file_path, dtype=str, keep_default_na=False)

@st.cache_data
def load_local_font_bytes(file_path):
    with open(file_path, "rb") as f:
        return f.read()

# ================= 2. 輔助函式 =================
def clean_val(val):
    """清除 NaN 並轉字串"""
    if pd.isna(val) or str(val).lower() == 'nan': return ""
    return str(val).strip()

def get_nutri_val(data, key):
    val = data.get(key)
    if pd.isna(val) or str(val).lower() == 'nan': return "0"
    return str(val).strip()

# --- 智慧欄位搜尋函式 ---
def smart_get_caution_text(data_dict):
    """
    嘗試尋找 'Cautions' 欄位
    優先順序: 'Cautions' -> 'Caution' -> 'cautions' -> 包含 'caution' 的欄位
    """
    # 1. 精準匹配
    if 'Cautions' in data_dict: return clean_val(data_dict['Cautions'])
    if 'Caution' in data_dict: return clean_val(data_dict['Caution'])
    if 'cautions' in data_dict: return clean_val(data_dict['cautions'])
    
    # 2. 模糊搜尋
    lower_keys = {k.lower(): k for k in data_dict.keys()}
    for k_lower, k_original in lower_keys.items():
        if 'caution' in k_lower:
            return clean_val(data_dict[k_original])
            
    # 3. 嘗試 Warning
    for k_lower, k_original in lower_keys.items():
        if 'warning' in k_lower:
            return clean_val(data_dict[k_original])
            
    return None 

def extract_date_from_text(text):
    text = text.replace('\n', ' ')
    match_compact = re.search(r"\b(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\b", text)
    if match_compact:
        return f"{match_compact.group(1)}-{match_compact.group(2)}-{match_compact.group(3)}"
    match_dmy_slash = re.search(r"\b(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])/(20\d{2})\b", text)
    if match_dmy_slash:
        return f"{match_dmy_slash.group(3)}-{match_dmy_slash.group(2)}-{match_dmy_slash.group(1)}"
    match_standard = re.search(r"\b(20\d{2})[./-](0[1-9]|1[0-2])[./-](0[1-9]|[12]\d|3[01])\b", text)
    if match_standard:
        return f"{match_standard.group(1)}-{match_standard.group(2)}-{match_standard.group(3)}"
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
    except Exception as e: return ""

# ================= 3. HTML 標籤生成器 =================

# --- A. 標準營養標籤 ---
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

# --- B. 警告標籤 (無框、置中、粗體) ---
def create_caution_html(text, qty):
    formatted_text = str(text).replace('\n', '<br/>')
    if not formatted_text or formatted_text == "nan":
        formatted_text = ""

    single_label_html = f"""
    <html>
    <head>
    <style>
        @page {{ size: auto; margin: 0mm; }}
        body {{ margin: 0; padding: 0; font-family: Helvetica, Arial, sans-serif; }}
        .label-container {{ 
            width: 70mm; height: 50mm; box-sizing: border-box; 
            padding: 2mm; page-break-after: always; position: relative;
            display: flex; align-items: center; justify-content: center; text-align: center;
        }}
        .caution-text {{
            font-size: 15pt; font-weight: 900; line-height: 1.2; word-wrap: break-word; color: black;
        }}
    </style>
    </head>
    <body>
        <div class="label-container">
            <div class="caution-text">{formatted_text}</div>
        </div>
    </body>
    </html>
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

# ================= 4. JS 列印腳本 =================
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
                win.onload = function() {{ 
                    win.focus(); 
                    win.onafterprint = function() {{ win.close(); }}; 
                    win.print(); 
                    win.onfocus = function() {{ setTimeout(()=>{{ win.close(); }}, 500); }}; 
                }};
            }} else {{ alert("請允許彈出視窗！"); }}
        }})();
    </script>
    """
    components.html(js_code, height=30)

# ================= 5. 主頁面 =================
def show_excel_page():
    if 'parsed_items' not in st.session_state: st.session_state['parsed_items'] = []
    if 'last_uploaded_file_id' not in st.session_state: st.session_state['last_uploaded_file_id'] = None
    if 'font_css' not in st.session_state: st.session_state['font_css'] = ""

    st.markdown("""
        <style>
            .logo-container { display: flex; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
            .logo-text { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 28px; font-weight: 800; color: #2c3e50; letter-spacing: -0.5px; margin-left: 10px; line-height: 1; }
            .logo-dot { color: #007bff; }
            .logo-sub { font-size: 14px; color: #888; font-weight: 400; margin-left: 15px; padding-left: 15px; border-left: 1px solid #ddd; height: 20px; line-height: 20px; }
            .grid-header { background-color: #f8f9fa; padding: 12px 10px; border-top: 2px solid #e9ecef; border-bottom: 2px solid #e9ecef; font-weight: 600; color: #495057; font-size: 14px; }
            .grid-row { padding: 8px 0; border-bottom: 1px solid #f1f3f5; transition: background-color 0.2s; display: flex; align-items: center; height: 100%; }
            .grid-row:hover { background-color: #f8f9fa; }
            div[data-testid="column"] { display: flex; flex-direction: column; justify-content: center; align-items: center; }
            div.stButton > button { background-color: #e7f5ff; color: #004085; border: none; border-radius: 12px; padding: 4px 12px; font-size: 12px; font-weight: bold; height: auto; transition: all 0.2s; }
            div.stButton > button:hover { background-color: #d0ebff; color: #002752; }
            .cell-text { font-size: 14px; color: #333; padding: 0 5px; width: 100%; text-align: left; }
            .cell-sub { font-size: 12px; color: #888; padding: 0 5px; width: 100%; text-align: left; }
            .cell-code { font-family: monospace; font-size: 13px; background: #f1f3f5; padding: 2px 6px; border-radius: 4px; color: #333; }
            .cell-qty { font-weight: bold; font-size: 15px; color: #000; text-align: center; display: block; width: 100%; }
            .cell-badge-err { font-size: 12px; color: #dc3545; background: #ffe6e6; padding: 4px 12px; border-radius: 12px; font-weight: bold; text-align: center; white-space: nowrap; display: inline-block; }
            div[data-testid="column"]:nth-of-type(2) { align-items: flex-start; }
            div[data-testid="column"]:nth-of-type(3) { align-items: flex-start; }
            div[data-testid="column"]:nth-of-type(4) { align-items: flex-start; }
            div[data-testid="column"]:nth-of-type(5) { align-items: flex-start; }
        </style>
        
        <div class="logo-container">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#007bff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M6 9V2h12v7"></path><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><path d="M6 14h12v8H6z"></path>
            </svg>
            <div class="logo-text">Letech<span class="logo-dot">.</span></div>
            <div class="logo-sub">Intelligent Label Solution</div>
        </div>
    """, unsafe_allow_html=True)

    col_up1, col_up2 = st.columns(2)
    bridge_pdf = st.session_state.get('bridge_pdf_data')
    bridge_name = st.session_state.get('bridge_pdf_name')
    uploaded_pdf = None

    with col_up1:
        if bridge_pdf:
            st.success(f"📂 PDF Tool Transfer: **{bridge_name}**")
            uploaded_pdf = io.BytesIO(bridge_pdf)
            uploaded_pdf.name = bridge_name 
            if st.button("❌ Delete / Upload New PDF", key="clr_pdf"):
                del st.session_state['bridge_pdf_data']
                del st.session_state['bridge_pdf_name']
                st.rerun()
        else:
            uploaded_pdf = st.file_uploader("1. Please Upload PDF File", type=["pdf"])

    with col_up2:
        uploaded_excel_file = st.file_uploader("2. Please Upload Excel File", type=["csv", "xlsx"])
        
        df_master = None
        current_excel_name = ""

        if uploaded_excel_file:
            if uploaded_excel_file.name.endswith('.csv'): df_master = load_local_excel(uploaded_excel_file)
            else: df_master = load_local_excel(uploaded_excel_file)
            current_excel_name = uploaded_excel_file.name
        elif os.path.exists(DEFAULT_EXCEL_PATH):
            try:
                df_master = load_local_excel(DEFAULT_EXCEL_PATH)
                st.info(f"✅ Database: {DEFAULT_EXCEL_PATH}")
                current_excel_name = DEFAULT_EXCEL_PATH
            except Exception as e:
                st.error(f"預設資料庫讀取失敗: {e}")
        
        if df_master is not None:
            df_master.columns = df_master.columns.str.strip()

    uploaded_font_file = st.sidebar.file_uploader("Upload bold font (.ttf/.otf)", type=["ttf", "otf", "woff"])
    font_bytes = None
    font_filename = ""
    
    if uploaded_font_file:
        font_bytes = uploaded_font_file.getvalue()
        font_filename = uploaded_font_file.name
    elif os.path.exists(DEFAULT_FONT_PATH):
        try:
            font_bytes = load_local_font_bytes(DEFAULT_FONT_PATH)
            font_filename = DEFAULT_FONT_PATH
            st.sidebar.info(f"✅ Use Default font: {DEFAULT_FONT_PATH}")
        except: pass

    # ================= 處理邏輯 =================
    if uploaded_pdf and df_master is not None:
        current_file_id = f"{uploaded_pdf.name}_{current_excel_name}_{font_filename}"

        if st.session_state['last_uploaded_file_id'] != current_file_id:
            st.session_state['parsed_items'] = []
            st.session_state['font_css'] = ""
            st.session_state['last_uploaded_file_id'] = current_file_id
            gc.collect() 
            st.cache_data.clear()

        if not st.session_state['parsed_items']:
            try:
                if font_bytes and not st.session_state['font_css']:
                    st.session_state['font_css'] = font_to_base64_css(font_bytes, font_filename)
                
                reader = PdfReader(uploaded_pdf)
                temp_items = []
                prog = st.progress(0)
                status_text = st.empty()
                total_pages = len(reader.pages)
                
                for i, page in enumerate(reader.pages):
                    status_text.text(f"⏳ Processing page {i+1}/{total_pages}...")
                    text = page.extract_text()
                    if not text: continue
                    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
                    p_no = lines[0] if lines else "N/A"
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
                    
                    # 🔥 重複資料過濾邏輯 (確保找到有 Cautions 的那一行)
                    matches = df_master[df_master['Product_No'].astype(str).str.strip() == p_no]
                    matched_data = {}
                    has_match = False
                    
                    if not matches.empty:
                        has_match = True
                        if 'Cautions' in matches.columns:
                            valid_rows = matches[matches['Cautions'].notna() & (matches['Cautions'].str.strip() != "")]
                            if not valid_rows.empty:
                                matched_data = valid_rows.iloc[0].to_dict()
                            else:
                                matched_data = matches.iloc[0].to_dict()
                        else:
                            matched_data = matches.iloc[0].to_dict()

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

        # ================= 顯示列表 =================
        if st.session_state['parsed_items']:
            st.markdown("---")
            col_ratios = [0.5, 1.5, 4, 2, 1.5, 0.8, 1.2]
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
                        is_caution_item = str(item['Product No']).strip() in CAUTION_PRODUCT_LIST
                        
                        if item['has_match'] or is_caution_item:
                            if st.button("Print", key=f"btn_{item['id']}_{index}"):
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
                            st.markdown(f"<span class='cell-badge-err'>無資料</span>", unsafe_allow_html=True)

    elif not uploaded_pdf:
        st.info("👈 Please upload a PDF file or transfer from PDF Tool.")
    elif df_master is None:
        st.warning(f"⚠️ 找不到預設資料庫 `{DEFAULT_EXCEL_PATH}`，請手動上傳 Excel 檔案或將檔案放入目錄中。")
