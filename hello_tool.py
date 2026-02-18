import streamlit as st
from pypdf import PdfReader
import pandas as pd
import re
import os
import base64
import streamlit.components.v1 as components

# ================= 新增：匯入標籤格式模組 =================
try:
    import repack_label
except ImportError:
    repack_label = None

# ================= 設定固定主檔名稱 =================
MASTER_FILE = "data.xlsx"

# ================= 1. 資料讀取函數 =================

@st.cache_data
def load_master_data():
    """自動讀取固定的 Excel 主檔"""
    if not os.path.exists(MASTER_FILE):
        return None
    try:
        df = pd.read_excel(MASTER_FILE)
        df.columns = [str(c).strip() for c in df.columns]
        col_map = {c.replace('_', '').replace(' ', '').lower(): c for c in df.columns}
        p_no_col = col_map.get('productno')
        label_col = col_map.get('labeltype')
        if p_no_col and label_col:
            df[p_no_col] = df[p_no_col].astype(str).str.strip()
            df[label_col] = df[label_col].astype(str).str.strip()
            return df[[p_no_col, label_col]].rename(columns={p_no_col: 'Product_No', label_col: 'Label_Type'})
        else:
            return None
    except Exception:
        return None

# ================= 2. 主頁面顯示 (由 main.py 呼叫) =================

def show_hellobear_page():
    # 保持原本所有的 CSS 樣式、按鈕幾何形狀、寬度、高度與位移
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
        </style>
        <div class="logo-container">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#007bff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M6 9V2h12v7"></path><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><path d="M6 14h12v8H6z"></path>
            </svg>
            <div class="logo-text">Letech<span class="logo-dot">.</span></div>
            <div class="logo-sub">Intelligent Label Solution</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🐻 Hello Bear 3PL System")

    master_df = load_master_data()
    if master_df is not None:
        st.success(f"✅ Linked Database：`{MASTER_FILE}`")
    else:
        st.warning(f"⚠️ 找不到 `{MASTER_FILE}`")

    st.divider()

    uploaded_file = st.file_uploader("Please Upload Hello bear 3PL (PDF)", type=["pdf"], key="hellobear_pdf")

    if uploaded_file:
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
                if not clean_text:
                    continue 
                
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

                excel_label = ""
                if master_df is not None:
                    found = master_df[master_df['Product_No'] == p_no]
                    if not found.empty:
                        excel_label = str(found.iloc[0]['Label_Type'])

                final_label = ""
                if not barcode_val or barcode_val.strip() == "" or barcode_val == p_no:
                    final_label = "Print SKU Barcode"
                elif barcode_val and barcode_val[-1].isalpha():
                    final_label = "Print Repack Lable"
                elif excel_label and excel_label != "nan" and excel_label.strip() != "":
                    final_label = excel_label
                else:
                    final_label = "普通Lable"

                valid_rows.append({
                    "id": f"{p_no}_{i}", 
                    "Product No": p_no,
                    "Barcode": barcode_val if barcode_val else "(N/A)",
                    "商品名稱": p_name,
                    "數量": qty,
                    "Label Type": final_label
                })

            prog_bar.empty()
            status_text.empty()

            if valid_rows:
                df_result = pd.DataFrame(valid_rows)
                # 找出重複的 SKU
                duplicated_pnos = df_result[df_result.duplicated('Product No', keep=False)]['Product No'].unique().tolist()
                duplicate_count = len(duplicated_pnos)

                # --- [新增：重新加入統計指標區塊] ---
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📄 Original Pages", total_pages)
                c2.metric("✅ Valid Pages", valid_page_count)
                c3.metric("🗑️ Blank Removed", total_pages - valid_page_count)
                c4.metric("⚠️ Duplicate SKU", duplicate_count)
                
                if duplicate_count > 0:
                    st.warning(f"偵測到重複 Product No：{', '.join(duplicated_pnos)}")

                st.write("#### 📋 PDF Details")
                
                col_ratios = [0.5, 1.1, 1.1, 4.0, 0.8, 1.2, 1.2]
                headers = ["No", "Product No", "Barcode", "Product Name", "Qty", "Label Type", "Action"]
                
                cols = st.columns(col_ratios)
                for col, h in zip(cols, headers):
                    col.markdown(f"<div class='grid-header'>{h}</div>", unsafe_allow_html=True)

                for index, row in enumerate(valid_rows):
                    p_no = row['Product No']
                    barcode_clean = row['Barcode'].strip()
                    
                    pno_style = 'color: #CC5500; font-weight: bold;' if p_no in duplicated_pnos else ""
                    
                    highlight_style = ""
                    v_label = str(row['Label Type']).lower()
                    if any(k in v_label for k in ["repack", "sku", "蟲", "food"]):
                        highlight_style = "background-color: #FFFFAA; color: #B30000; font-weight: bold;"

                    with st.container():
                        c0, c1, c2, c3, c4, c5, c6 = st.columns(col_ratios)
                        
                        c0.markdown(f"<div class='grid-row'><div class='cell-text' style='text-align:center; color:#888;'>{index+1}</div></div>", unsafe_allow_html=True)
                        c1.markdown(f"<div class='grid-row'><div class='cell-text' style='{pno_style}'>{p_no}</div></div>", unsafe_allow_html=True)
                        c2.markdown(f"<div class='grid-row'><div class='cell-text'>{row['Barcode']}</div></div>", unsafe_allow_html=True)
                        c3.markdown(f"<div class='grid-row' style='{highlight_style}'><div class='cell-text'>{row['商品名稱']}</div></div>", unsafe_allow_html=True)
                        c4.markdown(f"<div class='grid-row'><span class='cell-qty'>{row['數量']}</span></div>", unsafe_allow_html=True)
                        c5.markdown(f"<div class='grid-row' style='{highlight_style}'><div class='cell-text'>{row['Label Type']}</div></div>", unsafe_allow_html=True)
                        
                        with c6:
                            needs_print = False
                            if barcode_clean and barcode_clean != "(N/A)":
                                if re.search(r'[a-zA-Z]$', barcode_clean) or barcode_clean == p_no:
                                    needs_print = True
                            
                            row_wrapper_style = "display: flex; justify-content: center; align-items: center; width: 100%; height: 100%;"
                            
                            if needs_print:
                                if st.button("打印", key=f"btn_hb_{index}"):
                                    if repack_label:
                                        final_html = repack_label.create_repack_label_html(
                                            row['商品名稱'], 
                                            row['Barcode'], 
                                            row['數量']
                                        )
                                        repack_label.js_instant_print(final_html)
                                    else:
                                        st.error("找不到 repack_label.py")
                            else:
                                st.markdown(f"<div style='{row_wrapper_style}'><div class='cell-badge-normal'>普通注意</div></div>", unsafe_allow_html=True)

                st.markdown("---")
                csv = df_result.to_csv(index=True).encode('utf-8-sig')
                st.download_button(label="📥 下載處理結果 (CSV)", data=csv, file_name="hellobear_processed_orders.csv", mime="text/csv")

        except Exception as e:
            st.error(f"處理失敗: {e}")

if __name__ == "__main__":
    show_hellobear_page()