import streamlit as st
from pypdf import PdfReader
import pandas as pd
import re
import os
import sys
from pathlib import Path
import base64
from usage_tracker import log_action
import streamlit.components.v1 as components

# ================= 新增：強制路徑並匯入標籤格式模組 =================
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

try:
    import repack_lable
except ImportError as e:
    st.error(f"❌ 模組匯入失敗 (repack_lable): {e}")
    repack_lable = None

try:
    import Lable
except ImportError as e:
    st.error(f"❌ 模組匯入失敗 (Lable): {e}")
    Lable = None

# ================= 設定固定主檔名稱 =================
MASTER_FILE = "data.xlsx"

@st.cache_data
def load_master_data():
    """自動讀取固定的 Excel 主檔"""
    if not os.path.exists(MASTER_FILE):
        return None
    try:
        df = pd.read_excel(MASTER_FILE)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"❌ 讀取 {MASTER_FILE} 失敗: {e}")
        return None

def get_master_row(master_df, p_no):
    """根據 Product No 找出對應的 Excel 資料列"""
    if master_df is None: return None
    if 'Product_No' in master_df.columns:
        return master_df[master_df['Product_No'].astype(str).str.strip() == p_no]
    elif 'Product No' in master_df.columns:
        return master_df[master_df['Product No'].astype(str).str.strip() == p_no]
    return None

def create_simple_text_html(text, qty):
    """生成簡單的純文字標籤 (用於普通注意等)"""
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
    """通用的 JS 列印觸發器"""
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
            }}
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
            .grid-row { 
                padding: 8px 0; border-bottom: 1px solid #f1f3f5; 
                transition: background-color 0.2s; 
                display: flex; align-items: center; height: 100%; 
                min-height: 45px; 
            }
            .grid-row:hover { background-color: #f8f9fa; }
            
            div.stButton > button { 
                width: 100px !important;       
                height: 38px !important;      
                min-height: 32px !important;
                border-radius: 6px !important; 
                padding: 0px !important;      
                background-color: #e7f5ff !important; 
                color: #004085 !important; 
                border: none !important; 
                display: flex !important; 
                justify-content: center !important; 
                align-items: center !important;
                margin: 0 auto !important;    
                transform: translateX(19px) !important;
            }
            div.stButton > button:hover { background-color: #d0ebff !important; color: #002752 !important; }
            
            div.stButton > button p {
                font-size: 13px !important;
                font-weight: bold !important;
                line-height: 1 !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            
            div.stButton { width: 100% !important; display: flex !important; justify-content: center !important; margin: 0 !important; }

            .cell-text { font-size: 15px; color: #333; padding: 0 5px; width: 100%; text-align: left; }
            .cell-qty { font-weight: bold; font-size: 15px; color: #000; text-align: center; display: block; width: 100%; }
            div[data-testid="column"] { display: flex; flex-direction: column; justify-content: center; }
            div[data-testid="column"]:nth-of-type(7) > div {
                display: flex !important;
                flex-direction: row !important;
                justify-content: center !important; 
                align-items: center !important;     
                width: 100% !important;
                height: 100% !important;
            }
            
            .cell-badge-normal { 
                width: 100px !important;       
                height: 37px !important;      
                min-height: 32px !important;
                border-radius: 6px !important; 
                padding: 0px !important;
                background-color: #eee !important; 
                color: #666 !important; 
                display: flex !important; 
                justify-content: center !important; 
                align-items: center !important;
                margin: 0 auto !important;
                font-size: 13px !important;    
                font-weight: bold !important;
                line-height: 1 !important;
                transform: translateX(1px) !important;
            }
        </style>
        <div class="logo-container">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#007bff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M6 9V2h12v7"></path><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><path d="M6 14h12v8H6z"></path>
            </svg>
            <div class="logo-text">Letech<span class="logo-dot">.</span></div>
            <div class="logo-sub">Intelligent Label Solution</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("### 🏠 Homey 3PL System")

    master_df = load_master_data()
    if master_df is not None:
        st.success(f"✅ Linked Database：`{MASTER_FILE}`")
    else:
        st.warning(f"⚠️ 找不到 `{MASTER_FILE}`")

    st.divider()

    uploaded_file = st.file_uploader("Please Upload Homey 3PL (PDF)", type=["pdf"], key="homey_pdf")

    if uploaded_file:
        if 'last_homey_file' not in st.session_state or st.session_state.last_homey_file != uploaded_file.name:
            st.session_state.last_homey_file = uploaded_file.name
            log_action("Homey_Upload")

        try:
            reader = PdfReader(uploaded_file)
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
                if not clean_text: continue 
                
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

                # 提取 Excel Label
                master_row = get_master_row(master_df, p_no)
                excel_label = ""
                if master_row is not None and not master_row.empty:
                    if 'Label_Type' in master_row.columns:
                        excel_label = str(master_row.iloc[0]['Label_Type'])
                    elif 'Label Type' in master_row.columns:
                        excel_label = str(master_row.iloc[0]['Label Type'])
                    elif 'Lable_Type' in master_row.columns:
                        excel_label = str(master_row.iloc[0]['Lable_Type'])
                    elif 'Lable Type' in master_row.columns:
                        excel_label = str(master_row.iloc[0]['Lable Type'])

                final_label = ""
                
                # 判斷邏輯
                if "food" in excel_label.lower():
                    final_label = excel_label
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
                duplicated_pnos = df_result[df_result.duplicated('Product No', keep=False)]['Product No'].unique().tolist()
                duplicate_count = len(duplicated_pnos)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📄 Original Page Number", total_pages)
                c2.metric("✅ Valid Pages", valid_page_count)
                c3.metric("🗑️ Remove Blanks", total_pages - valid_page_count)
                c4.metric("⚠️ Duplicate SKU", duplicate_count, delta=None, delta_color="inverse")

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
                            # 判斷是否顯示列印按鈕
                            needs_print = False
                            v_label_lower = str(label_type).lower()
                            
                            if "food" in v_label_lower:
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
                                        if Lable:
                                            # 注意這裡的拼寫：修正為 label_html
                                            html = Lable.generate_food_label_html(row, row['master_row'], row['數量'])
                                            components.html(html, height=0)
                                        else:
                                            st.error("找不到 Lable.py")
                                    else:
                                        if repack_lable:
                                            print_barcode = p_no if not barcode_clean or barcode_clean == "(N/A)" else barcode_clean
                                            # 注意這裡的拼寫：修正為 label_html
                                            html = repack_lable.create_repack_label_html(row['商品名稱'], print_barcode, row['數量'])
                                            js_instant_print(html)
                                        else:
                                            st.error("找不到 repack_lable.py")
                            else:
                                # 這裡改為顯示實際的 Label Type 文字！
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
