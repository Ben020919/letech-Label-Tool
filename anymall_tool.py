import streamlit as st
from pypdf import PdfReader
import pandas as pd
import re
import os
import sys
from pathlib import Path
import base64
import streamlit.components.v1 as components
from usage_tracker import log_action

# ================= 新增：強制路徑並匯入 repack_lable 模組 =================
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

try:
    import repack_lable
except ImportError as e:
    st.error(f"❌ 模組匯入失敗 (repack_lable): {e}")
    repack_lable = None

# ================= 專屬標籤與列印功能 =================

def create_anymall_repack_label(barcode_val, qty):
    """
    專屬 Anymall 的 Repack Label:
    只顯示 Barcode 圖片與數字，不顯示商品名稱，並且在 70x50mm 完美置中。
    """
    if repack_lable:
        barcode_img_src = repack_lable.generate_barcode_b64(barcode_val)
    else:
        barcode_img_src = ""

    single_label = f"""
    <div style="
        width: 70mm; 
        height: 50mm; 
        box-sizing: border-box; 
        page-break-after: always; 
        display: flex; 
        flex-direction: column; 
        justify-content: center; 
        align-items: center;
        padding-top: 3mm;
    ">
        <img src="{barcode_img_src}" style="height: 25mm; width: 90%; object-fit: contain;">
        
        <div style="
            font-family: monospace; 
            font-weight: bold; 
            font-size: 17px; 
            margin-top: 3px;
            letter-spacing: 1px;
        ">
            {barcode_val}
        </div>
    </div>
    """

    full_html = f"""
    <html>
    <head>
    <style>
        @page {{ size: 70mm 50mm; margin: 0; }}
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: white; }}
    </style>
    </head>
    <body>
        {single_label * qty}
    </body>
    </html>
    """
    return full_html

def js_instant_print(full_html_content):
    """觸發瀏覽器列印"""
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


# ================= 主頁面 =================

def show_anymall_page():
    # ================= LOGO / BRANDING / CSS AREA =================
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
            
            /* ====== 【對齊修正區】 ====== */
            
            /* 1. 打印按鈕 (藍色) */
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
                transform: translateX(20px) !important; /* 統一往右平移 20px */
            }
            div.stButton > button:hover { background-color: #d0ebff !important; color: #002752 !important; }
            
            div.stButton > button p {
                font-size: 13px !important;
                font-weight: bold !important;
                line-height: 1 !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            
            /* 按鈕的外層容器：確保高度與 .grid-row 一致且置中 */
            div.stButton { 
                width: 100% !important; 
                display: flex !important; 
                justify-content: center !important; 
                align-items: center !important;
                height: 100% !important;
                min-height: 45px !important;
                margin: 0 !important; 
            }

            /* 2. 普通注意標籤 (灰色) */
            .cell-badge-normal { 
                width: 100px !important;       
                height: 38px !important; /* 修正：統一為 38px */
                min-height: 38px !important;
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
                transform: translateX(20px) !important; /* 修正：統一往右平移 20px */
            }

            .cell-text { font-size: 15px; color: #333; padding: 0 5px; width: 100%; text-align: left; }
            .cell-qty { font-weight: bold; font-size: 15px; color: #000; text-align: center; display: block; width: 100%; }
            div[data-testid="column"] { display: flex; flex-direction: column; justify-content: center; }
            
            div[data-testid="column"]:nth-of-type(6) > div {
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
    
    st.markdown("### 🛍️ Anymall 3PL System")

    uploaded_file = st.file_uploader("Please Upload Anymall 3PL PDF File", type=["pdf"], key="anymall_pdf")

    if uploaded_file:
        if 'last_anymall_file' not in st.session_state or st.session_state.last_anymall_file != uploaded_file.name:
            st.session_state.last_anymall_file = uploaded_file.name
            log_action("Anymall_Upload")

        try:
            reader = PdfReader(uploaded_file)
            total_pages = len(reader.pages)
            
            valid_rows = []
            kept_pages = 0
            
            prog_bar = st.progress(0)
            status_text = st.empty()

            for i, page in enumerate(reader.pages):
                prog_bar.progress((i + 1) / total_pages)
                status_text.text(f"正在分析第 {i+1}/{total_pages} 頁...")

                text = page.extract_text()
                
                # 1. 去除空白頁邏輯
                if not text or not text.strip():
                    continue
                
                kept_pages += 1
                
                # 2. 資料提取邏輯
                lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
                
                # (A) Product No
                p_no = lines[0] if lines else "Unknown"
                
                # (B) Quantity
                qty_line_index = -1
                qty = 1
                for idx, line in enumerate(lines):
                    if ".0000" in line:
                        qty_line_index = idx
                        qty_match = re.search(r"(\d+)\.0000", line)
                        if qty_match:
                            qty = int(qty_match.group(1))
                        break
                
                # (C) Product Name
                p_name = ""
                if qty_line_index > 1:
                    name_parts = lines[1:qty_line_index]
                    p_name = " ".join(name_parts)
                elif len(lines) > 1 and qty_line_index == -1:
                    p_name = lines[1]

                # (D) Barcode Logic
                barcode = ""
                if qty_line_index != -1 and qty_line_index < len(lines) - 1:
                    raw_barcode_lines = lines[qty_line_index+1:]
                    cleaned_bc_lines = [
                        line for line in raw_barcode_lines 
                        if "N/A" not in line and "PAGE" not in line
                    ]
                    raw_bc_text = "".join(cleaned_bc_lines)
                    barcode = re.sub(r'[\s\*]', '', raw_bc_text)

                valid_rows.append({
                    "id": f"{p_no}_{i}",
                    "Product No": p_no,
                    "Barcode": barcode,
                    "商品名稱": p_name,
                    "數量": qty
                })

            prog_bar.empty()
            status_text.empty()

            if not valid_rows:
                st.warning("沒有提取到有效資料。")
                return

            df = pd.DataFrame(valid_rows)

            # --- 重複檢查邏輯 ---
            duplicated_mask = df.duplicated(subset=['Product No'], keep=False)
            duplicated_pnos = df[duplicated_mask]['Product No'].unique().tolist()
            duplicate_count = len(duplicated_pnos)

            # 顯示統計
            st.divider()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📄 Original Pages", total_pages)
            c2.metric("✅ Valid Pages", kept_pages)
            c3.metric("🗑️ Blank Removed", total_pages - kept_pages)
            c4.metric("⚠️ Duplicate SKU", duplicate_count, delta=None, delta_color="inverse")

            if duplicate_count > 0:
                st.warning(f"⚠️ 發現 {duplicate_count} 款商品編號重複：{', '.join(duplicated_pnos)}")
            

            # --- 搜尋功能 ---
            st.markdown("### 🔍 Search and Inspection")
            search_query = st.text_input("Enter Keywords Here (Press Enter to Search).", placeholder="Type to search...")

            filtered_df = df.copy()
            if search_query:
                mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
                filtered_df = filtered_df[mask]

            # --- 表格渲染 (加入 Action 欄位) ---
            col_ratios = [0.5, 1.5, 1.5, 4.0, 0.8, 1.5]
            headers = ["No", "Product No", "Barcode", "Product Name", "Qty", "Action"]
            
            cols = st.columns(col_ratios)
            for col, h in zip(cols, headers):
                col.markdown(f"<div class='grid-header'>{h}</div>", unsafe_allow_html=True)

            # 將 DataFrame 轉為字典列表方便迭代
            display_rows = filtered_df.to_dict('records')

            for index, row in enumerate(display_rows):
                p_no = row['Product No']
                barcode_clean = row['Barcode'].strip()
                
                # 橙色高亮重複項目
                pno_style = 'color: #CC5500; font-weight: bold;' if p_no in duplicated_pnos else ""
                
                with st.container():
                    c0, c1, c2, c3, c4, c5 = st.columns(col_ratios)
                    
                    c0.markdown(f"<div class='grid-row'><div class='cell-text' style='text-align:center; color:#888;'>{index+1}</div></div>", unsafe_allow_html=True)
                    c1.markdown(f"<div class='grid-row'><div class='cell-text' style='{pno_style}'>{p_no}</div></div>", unsafe_allow_html=True)
                    c2.markdown(f"<div class='grid-row'><div class='cell-text'>{row['Barcode']}</div></div>", unsafe_allow_html=True)
                    c3.markdown(f"<div class='grid-row'><div class='cell-text'>{row['商品名稱']}</div></div>", unsafe_allow_html=True)
                    c4.markdown(f"<div class='grid-row'><span class='cell-qty'>{row['數量']}</span></div>", unsafe_allow_html=True)
                    
                    with c5:
                        # 邏輯判斷：如果 Barcode 數字與 Product No 一樣
                        needs_print = False
                        if barcode_clean and barcode_clean != "(N/A)" and barcode_clean == p_no:
                            needs_print = True
                        
                        # 確保標籤的 wrapper 高度與 .grid-row 一致
                        row_wrapper_style = "display: flex; justify-content: center; align-items: center; width: 100%; height: 100%; min-height: 45px;"
                        
                        if needs_print:
                            if st.button("打印", key=f"btn_am_{row['id']}_{index}"):
                                log_action("Anymall_Print")
                                if repack_lable:
                                    # 產生沒有商品名稱的專屬標籤
                                    html = create_anymall_repack_label(barcode_clean, row['數量'])
                                    js_instant_print(html)
                                else:
                                    st.error("找不到 repack_lable.py")
                        else:
                            st.markdown(f"<div style='{row_wrapper_style}'><div class='cell-badge-normal'>普通注意</div></div>", unsafe_allow_html=True)

            st.markdown("---")
            # 匯出結果
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 下載處理結果 (CSV)",
                data=csv,
                file_name="anymall_processed_orders.csv",
                mime="text/csv",
            )

        except Exception as e:
            st.error(f"處理失敗: {e}")

if __name__ == "__main__":
    show_anymall_page()
