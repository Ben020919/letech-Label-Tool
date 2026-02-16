import streamlit as st
from pypdf import PdfReader
import pandas as pd
import re
import io
import base64
import time
import os
import gc  # 引入垃圾回收機制
import streamlit.components.v1 as components

# ================= 設定預設檔案名稱 =================
DEFAULT_EXCEL_PATH = "data.xlsx"
DEFAULT_FONT_PATH = "font.ttf"

# ================= 1. 快取讀取函式 =================
@st.cache_data
def load_local_excel(file_path):
    """讀取本地 Excel 並快取結果"""
    if file_path.endswith('.csv'):
        return pd.read_csv(file_path)
    else:
        return pd.read_excel(file_path)

@st.cache_data
def load_local_font_bytes(file_path):
    """讀取本地字型檔並快取結果"""
    with open(file_path, "rb") as f:
        return f.read()

# ================= 2. 輔助函式 =================
def clean_val(val):
    if pd.isna(val) or str(val).lower() == 'nan': return ""
    return str(val).strip()

def get_nutri_val(data, key):
    val = data.get(key)
    if pd.isna(val) or str(val).lower() == 'nan': return "0"
    return str(val).strip()

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

# ================= 3. HTML 標籤生成器 (即時生成) =================
def create_label_html_on_the_fly(item, matched_data, font_css, qty):
    """
    這個函式會在按鈕被點擊時才執行，避免記憶體爆炸
    """
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

    # 生成單張標籤
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
    
    # 複製 N 份 (根據 Qty)
    import re as regex
    match = regex.search(r'<body>(.*?)</body>', single_label_html, regex.DOTALL)
    if match:
        div_content = match.group(1)
        full_body = div_content * qty
        final_html = single_label_html.replace(div_content, full_body)
    else:
        final_html = single_label_html
        
    return final_html

# ================= 4. JS 列印腳本 (Windows/Mac 兼容修復版) =================
def js_instant_print(full_html_content, item_id):
    b64_html = base64.b64encode(full_html_content.encode('utf-8')).decode('utf-8')
    js_code = f"""
    <script>
        (function() {{
            const b64 = "{b64_html}";
            const htmlContent = decodeURIComponent(escape(window.atob(b64)));
            const win = window.open('', '_blank', 'width=400,height=400');
            if (win) {{
                win.document.write(htmlContent); 
                win.document.close();
                
                win.onload = function() {{ 
                    win.focus(); 
                    
                    // --- 關鍵修復：先註冊關閉事件，再執行列印 ---
                    // 這行確保 Windows 即使阻塞也能收到關閉指令
                    win.onafterprint = function() {{ win.close(); }}; 
                    
                    // 開始列印
                    win.print(); 
                    
                    // Mac/Safari 的備用方案 (保留)
                    win.onfocus = function() {{ setTimeout(()=>{{ win.close(); }}, 500); }}; 
                }};
            }} else {{ 
                alert("請允許彈出視窗！"); 
            }}
        }})();
    </script>
    """
    components.html(js_code, height=30)

# ================= 5. 主頁面 =================
def show_excel_page():
    # 初始化
    if 'parsed_items' not in st.session_state: st.session_state['parsed_items'] = []
    if 'last_uploaded_file_id' not in st.session_state: st.session_state['last_uploaded_file_id'] = None
    if 'font_css' not in st.session_state: st.session_state['font_css'] = ""

    st.markdown("""
        <style>
            /* 與之前相同的 CSS 樣式 */
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
            st.success(f"📂 使用 PDF Tool 傳送的檔案: **{bridge_name}**")
            uploaded_pdf = io.BytesIO(bridge_pdf)
            uploaded_pdf.name = bridge_name 
            if st.button("❌ 清除 / 上傳新 PDF", key="clr_pdf"):
                del st.session_state['bridge_pdf_data']
                del st.session_state['bridge_pdf_name']
                st.rerun()
        else:
            uploaded_pdf = st.file_uploader("1. Please Upload PDF File", type=["pdf"])

    with col_up2:
        uploaded_excel_file = st.file_uploader("2. Please Upload Excel File (可選)", type=["csv", "xlsx"])
        df_master = None
        current_excel_name = ""

        if uploaded_excel_file:
            if uploaded_excel_file.name.endswith('.csv'): df_master = pd.read_csv(uploaded_excel_file)
            else: df_master = pd.read_excel(uploaded_excel_file)
            current_excel_name = uploaded_excel_file.name
        elif os.path.exists(DEFAULT_EXCEL_PATH):
            try:
                df_master = load_local_excel(DEFAULT_EXCEL_PATH)
                st.info(f"✅ 已載入預設資料庫: {DEFAULT_EXCEL_PATH}")
                current_excel_name = DEFAULT_EXCEL_PATH
            except Exception as e:
                st.error(f"預設資料庫讀取失敗: {e}")
        
        if df_master is not None:
            df_master.columns = df_master.columns.str.strip()

    uploaded_font_file = st.sidebar.file_uploader("上傳粗體字型 (.ttf/.otf)", type=["ttf", "otf", "woff"])
    font_bytes = None
    font_filename = ""
    
    if uploaded_font_file:
        font_bytes = uploaded_font_file.getvalue()
        font_filename = uploaded_font_file.name
    elif os.path.exists(DEFAULT_FONT_PATH):
        try:
            font_bytes = load_local_font_bytes(DEFAULT_FONT_PATH)
            font_filename = DEFAULT_FONT_PATH
            st.sidebar.info(f"✅ 使用預設字型: {DEFAULT_FONT_PATH}")
        except: pass

    # ================= 處理邏輯 =================
    if uploaded_pdf and df_master is not None:
        current_file_id = f"{uploaded_pdf.name}_{current_excel_name}_{font_filename}"

        if st.session_state['last_uploaded_file_id'] != current_file_id:
            st.session_state['parsed_items'] = []
            st.session_state['font_css'] = ""
            st.session_state['last_uploaded_file_id'] = current_file_id
            
            # 強制清理記憶體
            gc.collect() 
            st.cache_data.clear()

        if not st.session_state['parsed_items']:
            try:
                # 預先處理 Font CSS，這個只需要一份，不會佔太多記憶體
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
                    
                    # 匹配 Excel 資料
                    row = df_master[df_master['Product_No'].astype(str).str.strip() == p_no]
                    matched_data = {}
                    has_match = False
                    if not row.empty:
                        matched_data = row.iloc[0].to_dict()
                        has_match = True

                    # ✅ 記憶體優化重點：只儲存原始數據，不存 HTML
                    temp_items.append({
                        "id": f"{p_no}_{i}", 
                        "Product No": p_no, 
                        "商品名稱": p_name, 
                        "Barcode": barcode, 
                        "數量": qty, 
                        "日期": p_date,
                        "matched_data": matched_data,  # 存 Excel 資料
                        "has_match": has_match
                    })
                    prog.progress((i+1)/total_pages)
                
                st.session_state['parsed_items'] = temp_items
                prog.empty()
                status_text.empty()
                gc.collect() # 再次清理
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
            headers = ["No.", "Product No", "Product Name", "Barcode", "Date", "Qty", "Action"]
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
                        if item['has_match']:
                            if st.button("Print", key=f"btn_{item['id']}_{index}"):
                                # 🔥 按下按鈕瞬間生成 HTML 🔥
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