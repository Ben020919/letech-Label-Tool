import streamlit as st
from pypdf import PdfReader, PdfWriter
import pandas as pd
import re
import os
import sys
import time
from pathlib import Path
import base64
import io
from usage_tracker import log_action
import streamlit.components.v1 as components

current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

try:
    import repack_lable
except ImportError as e:
    st.error(f"❌ 模組匯入失敗 (repack_lable): {e}")
    repack_lable = None

# ================= 設定預設檔案名稱 =================
MASTER_FILE = "data.xlsx"
DEFAULT_FONT_PATH = "font.ttf"
DB_NAME_FILE = "homey_current_db_name.txt"

def get_current_db_name():
    if os.path.exists(DB_NAME_FILE):
        with open(DB_NAME_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return MASTER_FILE

def set_current_db_name(name):
    with open(DB_NAME_FILE, "w", encoding="utf-8") as f:
        f.write(name)

# ================= 1. 資料庫與字體讀取函數 =================
@st.cache_data
def load_master_data():
    if not os.path.exists(MASTER_FILE): return None
    try:
        if MASTER_FILE.endswith('.csv'):
            df = pd.read_csv(MASTER_FILE)
        else:
            try:
                df = pd.read_excel(MASTER_FILE)
            except:
                df = pd.read_csv(MASTER_FILE)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"❌ 讀取 {MASTER_FILE} 失敗: {e}")
        return None

def get_master_row(master_df, p_no):
    if master_df is None: return None
    if 'Product_No' in master_df.columns:
        return master_df[master_df['Product_No'].astype(str).str.strip() == p_no]
    elif 'Product No' in master_df.columns:
        return master_df[master_df['Product No'].astype(str).str.strip() == p_no]
    return None

@st.cache_data
def load_local_font_bytes(file_path):
    if not os.path.exists(file_path): return None
    with open(file_path, "rb") as f:
        return f.read()

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

# ================= 2. 標籤 HTML 生成核心 =================
def clean_val(val):
    if pd.isna(val) or str(val).lower() == 'nan': return ""
    return str(val).strip()

def get_nutri_val(data, key):
    val = data.get(key)
    if pd.isna(val) or str(val).lower() == 'nan': return "0"
    return str(val).strip()

def create_food_label_html(item_name, barcode_text, matched_data, font_css, qty):
    data = matched_data if matched_data is not None and not matched_data.empty else {}
    if isinstance(data, pd.DataFrame):
        data = data.iloc[0].to_dict()
    elif not isinstance(data, dict):
        data = {}

    desc_text = clean_val(data.get('Description', item_name))
    b_text = barcode_text if barcode_text and barcode_text != "(N/A)" else clean_val(data.get('Barcode', ''))

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
            <div class="barcode-text">{b_text}</div>
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

# ✨ 蟲蟲標籤：恢復字體 8.5pt，並將 Barcode 與 Name 合併同一段 ✨
def create_insects_label_html(matched_data, qty):
    data = matched_data if matched_data is not None and not matched_data.empty else {}
    if isinstance(data, pd.DataFrame):
        data = data.iloc[0].to_dict()
    elif not isinstance(data, dict):
        data = {}
        
    barcode = clean_val(data.get('Barcode', ''))         
    desc = clean_val(data.get('Description', ''))        
    features = clean_val(data.get('FEATURES', ''))       
    cautions = clean_val(data.get('Cautions', ''))       
    
    net_content = clean_val(data.get('Net Content', '')) 
    if not net_content: net_content = clean_val(data.get('Net_Content', ''))
        
    ingredients = clean_val(data.get('Ingredients', '')) 
    warnings = clean_val(data.get('警告字眼', ''))         
    
    css = """
    <style>
        @page { size: 70mm 50mm; margin: 0; }
        body { margin: 0; padding: 0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: white;}
        .label-box {
            width: 70mm;
            height: 50mm;
            box-sizing: border-box;
            padding: 3mm 4mm;
            overflow: hidden;
            background-color: white;
            color: black;
            font-size: 8.5pt;
            line-height: 1.1;
            page-break-after: always;
        }
        .line-section {
            margin-bottom: 6pt; 
            word-wrap: break-word;
            font-weight: bold;
            min-height: 6pt; 
        }
        .line-section:last-child {
            margin-bottom: 0;
        }
    </style>
    """
    
    label_content = f"""
        <div class="line-section">
            <div>{barcode}</div>
            <div>{desc}</div>
        </div>
        <div class="line-section">{features}</div>
        <div class="line-section">{cautions}</div>
        <div class="line-section">{net_content}</div>
        <div class="line-section">{ingredients}</div>
        <div class="line-section">{warnings}</div>
    """
    
    single_label = f'<div class="label-box">{label_content}</div>'
    html = f"<html><head>{css}</head><body>{single_label * qty}</body></html>"
    return html

def create_simple_text_html(text, qty):
    single_label_html = f"""
    <div style="width: 70mm; height: 50mm; box-sizing: border-box; padding: 2mm; page-break-after: always; display: flex; align-items: center; justify-content: center; text-align: center;">
        <div style="font-size: 15pt; font-weight: 900; line-height: 1.2; font-family: sans-serif;">{text}</div>
    </div>
    """
    full_html = f"""
    <html><head><style>@page {{ size: 70mm 50mm; margin: 0; }} body {{ margin: 0; padding: 0; }}</style></head>
    <body>{single_label_html * qty}</body></html>
    """
    return full_html

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
                win.onload = function() {{ 
                    win.focus(); 
                    win.onafterprint = function() {{ win.close(); }}; 
                    win.print(); 
                    win.onfocus = function() {{ setTimeout(()=>{{ win.close(); }}, 500); }}; 
                }};
            }} else {{ alert("請允許彈出視窗！(Please allow popups)"); }}
        }})();
    </script>
    """
    components.html(js_code, height=0)

def show_homey_page():
    st.markdown("""
        <style>
            .logo-container { display: flex; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
            .logo-text { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 28px; font-weight: 800; color: #2c3e50; letter-spacing: -0.5px; margin-left: 10px; line-height: 1; }
            .logo-dot { color: #007bff; }
            .logo-sub { font-size: 14px; color: #888; font-weight: 400; margin-left: 15px; padding-left: 15px; border-left: 1px solid #ddd; height: 20px; line-height: 20px; }
            
            .grid-header { background-color: #f8f9fa; padding: 12px 10px; border-top: 2px solid #e9ecef; border-bottom: 2px solid #e9ecef; font-weight: 600; color: #495057; font-size: 14px; }
            .grid-row { padding: 8px 0; border-bottom: 1px solid #f1f3f5; transition: background-color 0.2s; display: flex; align-items: center; height: 100%; min-height: 45px; }
            .grid-row:hover { background-color: #f8f9fa; }
            
            /* ✨ 打印按鈕：完全還原您最原始的 CSS，完美對齊 */
            div.stButton > button { 
                width: 100px !important; height: 38px !important; min-height: 32px !important;
                border-radius: 6px !important; padding: 0px !important;      
                background-color: #e7f5ff !important; color: #004085 !important; border: none !important; 
                display: flex !important; justify-content: center !important; align-items: center !important;
                margin: 0 auto !important; transform: translateX(19px) !important;
            }
            div.stButton > button:hover { background-color: #d0ebff !important; color: #002752 !important; }
            div.stButton > button p { font-size: 13px !important; font-weight: bold !important; line-height: 1 !important; margin: 0 !important; padding: 0 !important; }
            div.stButton { width: 100% !important; display: flex !important; justify-content: center !important; margin: 0 !important; }

            .cell-badge-normal { 
                width: 100px !important; height: 37px !important; min-height: 32px !important;
                border-radius: 6px !important; padding: 0px !important;
                background-color: #eee !important; color: #666 !important; 
                display: flex !important; justify-content: center !important; align-items: center !important;
                margin: 0 auto !important; font-size: 13px !important; font-weight: bold !important;
                line-height: 1 !important; transform: translateX(1px) !important;
            }

            .cell-text { font-size: 15px; color: #333; padding: 0 5px; width: 100%; text-align: left; }
            .cell-qty { font-weight: bold; font-size: 15px; color: #000; text-align: center; display: block; width: 100%; }
            div[data-testid="column"] { display: flex; flex-direction: column; justify-content: center; }
            div[data-testid="column"]:nth-of-type(7) > div { display: flex !important; flex-direction: row !important; justify-content: center !important; align-items: center !important; width: 100% !important; height: 100% !important; }

            /* ✨ 保護下載按鈕與綠色配置按鈕，不受打印按鈕的樣式影響 */
            div[data-testid="stDownloadButton"] > button {
                width: 100% !important; 
                height: 38px !important; 
                min-height: 38px !important; 
                padding: 0 15px !important; 
                transform: translateX(0) !important;
                background-color: #f1f3f5 !important;
                color: #495057 !important;
                border: 1px solid #ced4da !important;
                border-radius: 6px !important;
            }
            div[data-testid="stDownloadButton"] > button:hover { background-color: #e9ecef !important; color: #212529 !important; }
            
            div[data-testid="stPopover"] > button {
                width: 100% !important;
                height: 38px !important;
                min-height: 38px !important;
                background-color: #28a745 !important;
                color: white !important;
                border: none !important;
                font-weight: bold !important;
                border-radius: 6px !important;
                padding: 0 15px !important;
                transform: translateX(0) !important; 
            }
            div[data-testid="stPopover"] > button:hover {
                background-color: #218838 !important;
                box-shadow: 0 4px 8px rgba(40, 167, 69, 0.3) !important;
            }
        </style>
        <div class="logo-container">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#007bff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M6 9V2h12v7"></path><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2-2v5a2 2 0 0 1-2 2h-2"></path><path d="M6 14h12v8H6z"></path>
            </svg>
            <div class="logo-text">Letech<span class="logo-dot">.</span></div>
            <div class="logo-sub">Intelligent Label Solution</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("### 🏠 Homey 3PL System")

    # ================= ✨ 綠色彈出式配置文件按鈕 ✨ =================
    col1, col2 = st.columns([0.85, 0.15])
    with col2:
        if hasattr(st, "popover"):
            with st.popover("⚙️ 配置文件"):
                st.markdown("#### 📂 上傳新資料庫")
                st.caption("支援上傳 Excel (.xlsx) 或 CSV (.csv) 檔案。上傳後會自動套用！")
                new_db_file = st.file_uploader("", type=["xlsx", "csv"], key="homey_new_db_uploader", label_visibility="collapsed")
                
                if new_db_file:
                    if st.button("確認更新", type="primary", key="homey_update_btn", use_container_width=True):
                        try:
                            if new_db_file.name.endswith('.csv'):
                                temp_df = pd.read_csv(new_db_file, dtype=str)
                                temp_df.to_excel(MASTER_FILE, index=False)
                            else:
                                with open(MASTER_FILE, "wb") as f:
                                    f.write(new_db_file.getbuffer())
                            
                            set_current_db_name(new_db_file.name)
                            st.cache_data.clear()
                            st.success(f"✅ 更新為：【{new_db_file.name}】！即將重新載入...")
                            time.sleep(2)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 更新失敗: {e}")
        else:
            st.info("請更新 Streamlit。")

    font_bytes = load_local_font_bytes(DEFAULT_FONT_PATH)
    font_css = font_to_base64_css(font_bytes, DEFAULT_FONT_PATH) if font_bytes else ""

    master_df = load_master_data()
    current_db_name = get_current_db_name()
    
    if master_df is not None:
        st.success(f"✅ Linked Database：`{current_db_name}`")
    else:
        st.warning(f"⚠️ 找不到 `{current_db_name}`，請點擊右上方「⚙️ 配置文件」上傳檔案。")

    st.divider()

    uploaded_file = st.file_uploader("Please Upload Homey 3PL (PDF)", type=["pdf"], key="homey_pdf")

    if uploaded_file:
        if 'last_homey_file' not in st.session_state or st.session_state.last_homey_file != uploaded_file.name:
            st.session_state.last_homey_file = uploaded_file.name
            log_action("Homey_Upload")

        try:
            reader = PdfReader(uploaded_file)
            writer = PdfWriter()
            total_pages = len(reader.pages)
            valid_rows = []
            valid_page_count = 0
            
            prog_bar = st.progress(0)
            status_text = st.empty()

            for i, page in enumerate(reader.pages):
                prog_bar.progress((i + 1) / total_pages)
                status_text.text(f"正在分析第 {i+1}/{total_pages} 頁...")
                
                text = page.extract_text()
                clean_text = re.sub(r'\[Image \d+\]', '', text).strip()
                
                # 1. 去空白頁
                if not clean_text: continue 
                
                # 儲存非空白頁
                writer.add_page(page)
                valid_page_count += 1
                
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                lines = [l for l in lines if not l.startswith("[Image")]
                if not lines: continue

                p_no = lines[0].strip()
                qty = 0
                qty_line_index = -1
                for idx, line in enumerate(lines):
                    if re.search(r'\d+\.0000', line):
                        match = re.search(r'(\d+)\.0000', line)
                        if match:
                            qty = int(match.group(1))
                            qty_line_index = idx
                        break
                
                barcode_val = ""
                for line in lines:
                    if "*" in line:
                        match = re.search(r'\*\s*([A-Za-z0-9\s-]*)\s*\*|^\*([A-Za-z0-9-]*)\*$', line)
                        if match:
                            raw = (match.group(1) or match.group(2) or "").replace(" ", "")
                            barcode_val = raw
                            break
                
                p_name = ""
                if qty_line_index > 1:
                    p_name = " ".join(lines[1:qty_line_index])

                master_row = get_master_row(master_df, p_no)
                excel_label = ""
                if master_row is not None and not master_row.empty:
                    if 'Label_Type' in master_row.columns:
                        excel_label = str(master_row.iloc[0]['Label_Type'])
                    elif 'Label Type' in master_row.columns:
                        excel_label = str(master_row.iloc[0]['Label Type'])

                final_label = ""
                
                if "food" in excel_label.lower():
                    final_label = excel_label
                elif "蟲" in excel_label or "insect" in excel_label.lower(): 
                    final_label = "蟲蟲label"
                elif not barcode_val or barcode_val.strip() == "" or barcode_val == p_no:
                    final_label = "Print SKU Barcode"
                elif barcode_val and barcode_val[-1].isalpha():
                    final_label = "Print Repack Lable"
                elif excel_label and excel_label != "nan" and excel_label.strip() != "":
                    final_label = excel_label
                else:
                    final_label = "普通Label"

                valid_rows.append({
                    "id": f"{p_no}_{i}", 
                    "Product No": p_no,
                    "Barcode": barcode_val if barcode_val else "(N/A)",
                    "商品名稱": p_name,
                    "數量": qty,
                    "Label Type": final_label,
                    "master_row": master_row 
                })

            prog_bar.empty()
            status_text.empty()

            if valid_rows:
                df_result = pd.DataFrame(valid_rows)
                
                # 產生清洗後的 PDF
                pdf_out_buffer = io.BytesIO()
                writer.write(pdf_out_buffer)
                cleaned_pdf_bytes = pdf_out_buffer.getvalue()

                duplicated_pnos = df_result[df_result.duplicated('Product No', keep=False)]['Product No'].unique().tolist()
                duplicate_count = len(duplicated_pnos)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📄 Original Page Number", total_pages)
                c2.metric("✅ Valid Pages", valid_page_count)
                c3.metric("🗑️ Remove Blanks", total_pages - valid_page_count)
                c4.metric("⚠️ Duplicate SKU", duplicate_count, delta=None, delta_color="inverse")
                
                # ✨ 加入下載乾淨 PDF 按鈕
                st.download_button(
                    label="📥 下載去除空白頁的 PDF",
                    data=cleaned_pdf_bytes,
                    file_name=f"Cleaned_{uploaded_file.name}",
                    mime="application/pdf"
                )

                if duplicate_count > 0:
                    st.warning(f"⚠️ 偵測到以下 Product No 有重複出現：{', '.join(duplicated_pnos)}")

                st.write("#### 📋 PDF Details")
                
                col_ratios = [0.5, 1.1, 1.1, 4.0, 0.8, 1.2, 1.2]
                headers = ["No", "Product No", "Barcode", "Product Name", "Qty", "Label Type", "Action"]
                
                cols = st.columns(col_ratios)
                for col, h in zip(cols, headers):
                    col.markdown(f"<div class='grid-header'>{h}</div>", unsafe_allow_html=True)

                for index, row in enumerate(valid_rows):
                    p_no = row['Product No']
                    barcode_clean = row['Barcode'].strip()
                    label_type = row['Label Type']
                    
                    pno_style = 'color: #CC5500; font-weight: bold;' if p_no in duplicated_pnos else ""
                    
                    highlight_style = ""
                    if any(k in str(label_type).lower() for k in ["repack", "sku", "蟲", "food"]):
                        highlight_style = "background-color: #FFFFAA; color: #B30000; font-weight: bold;"

                    with st.container():
                        c0, c1, c2, c3, c4, c5, c6 = st.columns(col_ratios)
                        
                        c0.markdown(f"<div class='grid-row'><div class='cell-text' style='text-align:center; color:#888;'>{index+1}</div></div>", unsafe_allow_html=True)
                        c1.markdown(f"<div class='grid-row'><div class='cell-text' style='{pno_style}'>{p_no}</div></div>", unsafe_allow_html=True)
                        c2.markdown(f"<div class='grid-row'><div class='cell-text'>{row['Barcode']}</div></div>", unsafe_allow_html=True)
                        c3.markdown(f"<div class='grid-row' style='{highlight_style}'><div class='cell-text'>{row['商品名稱']}</div></div>", unsafe_allow_html=True)
                        c4.markdown(f"<div class='grid-row'><span class='cell-qty'>{row['數量']}</span></div>", unsafe_allow_html=True)
                        c5.markdown(f"<div class='grid-row' style='{highlight_style}'><div class='cell-text'>{label_type}</div></div>", unsafe_allow_html=True)
                        
                        with c6:
                            needs_print = False
                            v_label_lower = str(label_type).lower()
                            
                            if "food" in v_label_lower:
                                needs_print = True
                            elif "蟲" in v_label_lower or "insect" in v_label_lower: 
                                needs_print = True
                            elif not barcode_clean or barcode_clean == "(N/A)":
                                needs_print = True
                            elif re.search(r'[a-zA-Z]$', barcode_clean) or barcode_clean == p_no:
                                needs_print = True
                                
                            row_wrapper_style = "display: flex; justify-content: center; align-items: center; width: 100%; height: 100%;"
                            
                            if needs_print:
                                if st.button("打印", key=f"btn_hm_{index}"):
                                    log_action("Homey_Print")

                                    if "food" in v_label_lower:
                                        html = create_food_label_html(row['商品名稱'], barcode_clean, row['master_row'], font_css, row['數量'])
                                        js_instant_print(html)
                                        
                                    elif "蟲" in v_label_lower or "insect" in v_label_lower: 
                                        log_action("InsectsLabel_Print")
                                        html = create_insects_label_html(row['master_row'], row['數量'])
                                        js_instant_print(html)
                                        
                                    elif "repack" in v_label_lower or "sku" in v_label_lower:
                                        if repack_lable:
                                            print_barcode = p_no if not barcode_clean or barcode_clean == "(N/A)" else barcode_clean
                                            html = repack_lable.create_repack_label_html(row['商品名稱'], print_barcode, row['數量'])
                                            js_instant_print(html)
                                        else:
                                            st.error("找不到 repack_lable.py")
                                    else:
                                        html = create_simple_text_html(label_type, row['數量'])
                                        js_instant_print(html)
                            else:
                                st.markdown(f"<div style='{row_wrapper_style}'><div class='cell-badge-normal'>{label_type}</div></div>", unsafe_allow_html=True)

                st.markdown("---")
                df_export = df_result.drop(columns=['master_row'])
                csv = df_export.to_csv(index=True).encode('utf-8-sig')
                st.download_button(
                    label="📥 下載處理結果 (CSV)",
                    data=csv,
                    file_name="homey_processed_orders.csv",
                    mime="text/csv",
                )
            else:
                st.warning("沒有提取到有效資料。")

        except Exception as e:
            st.error(f"處理失敗: {e}")

if __name__ == "__main__":
    show_homey_page()
