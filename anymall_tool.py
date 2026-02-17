import streamlit as st
from pypdf import PdfReader
import pandas as pd
import re
import io

def show_anymall_page():
    # ================= LOGO / BRANDING AREA =================
    st.markdown("""
        <style>
            .logo-container { display: flex; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
            .logo-text { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 28px; font-weight: 800; color: #2c3e50; letter-spacing: -0.5px; margin-left: 10px; line-height: 1; }
            .logo-dot { color: #007bff; }
            .logo-sub { font-size: 14px; color: #888; font-weight: 400; margin-left: 15px; padding-left: 15px; border-left: 1px solid #ddd; height: 20px; line-height: 20px; }
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
        try:
            reader = PdfReader(uploaded_file)
            total_pages = len(reader.pages)
            
            valid_rows = []
            kept_pages = 0
            
            # 進度顯示
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
                
                # (B) Quantity & 定位
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

            # 建立 DataFrame
            df = pd.DataFrame(valid_rows)

            # --- 重複檢查邏輯 (Hello Bear Style) ---
            duplicated_mask = df.duplicated(subset=['Product No'], keep=False)
            duplicated_pnos = df[duplicated_mask]['Product No'].unique().tolist()
            duplicate_count = len(duplicated_pnos)

            # 4. 顯示統計 (改為四欄位)
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
            search_query = st.text_input(
                "Enter Keywords Here (Press Enter to Search).", 
                placeholder="Type to search..."
            )

            filtered_df = df.copy()
            if search_query:
                mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
                filtered_df = filtered_df[mask]

            # --- 樣式設定 (Hello Bear Style: 僅高亮編號儲存格) ---
            def highlight_duplicates(row):
                # 建立與行長度相同的樣式列表
                styles = [''] * len(row)
                p_no = str(row['Product No'])
                
                # 如果該 Product No 在重複名單中，將該欄位標記為橙色
                if p_no in duplicated_pnos:
                    pno_idx = row.index.get_loc('Product No')
                    styles[pno_idx] = 'background-color: #FFCC88; color: #CC5500; font-weight: bold; border: 1px solid #FFAA44;'
                return styles

            # 設定序號從 1 開始
            filtered_df.index = range(1, len(filtered_df) + 1)
            filtered_df.index.name = "No."

            # 6. 顯示表格
            st.dataframe(
                filtered_df.style.apply(highlight_duplicates, axis=1),
                use_container_width=False,
                height=800,
                column_config={
                    "Product No": st.column_config.TextColumn("Product No", width=120, help="橙色背景表示此編號在 PDF 中重複出現"),
                    "Barcode": st.column_config.TextColumn("Barcode", width=120),
                    "商品名稱": st.column_config.TextColumn("商品名稱", width=850),
                    "數量": st.column_config.NumberColumn("數量", width=50, format="%d")
                }
            )

        except Exception as e:
            st.error(f"處理失敗: {e}")

if __name__ == "__main__":
    show_anymall_page()
