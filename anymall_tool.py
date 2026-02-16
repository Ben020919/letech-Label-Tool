import streamlit as st
from pypdf import PdfReader
import pandas as pd
import re
import io

def show_anymall_page():
    st.markdown("### 🛍️ Anymall 訂單處理工具")
    st.info("功能：去除空白頁 + 提取商品資料 (含 Barcode) + 序號索引")

    uploaded_file = st.file_uploader("請上傳 PDF 檔案", type=["pdf"], key="anymall_pdf")

    if uploaded_file:
        try:
            reader = PdfReader(uploaded_file)
            total_pages = len(reader.pages)
            
            valid_rows = []
            kept_pages = 0
            
            # 用來進度顯示
            prog_bar = st.progress(0)
            status_text = st.empty()

            for i, page in enumerate(reader.pages):
                # 更新進度
                prog_bar.progress((i + 1) / total_pages)
                status_text.text(f"正在掃描第 {i+1}/{total_pages} 頁...")

                text = page.extract_text()
                
                # 1. 去除空白頁邏輯
                if not text or not text.strip():
                    continue
                
                kept_pages += 1
                
                # 2. 資料提取邏輯
                lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
                
                # (A) Product No
                p_no = lines[0] if lines else "Unknown"
                
                # 尋找「數量」所在的行數索引
                qty_line_index = -1
                qty = 1
                
                # (B) Quantity & 定位
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

                # 3. 組合資料 (在此處加入 "序號")
                valid_rows.append({
                    "序號": len(valid_rows) + 1,  # ✅ 新增：自動從 1 開始編號
                    "原始頁碼": i + 1,
                    "Product No": p_no,
                    "Barcode": barcode,
                    "商品名稱": p_name,
                    "數量": qty
                })

            prog_bar.empty()
            status_text.empty()

            # 4. 顯示統計
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("📄 原本頁數", total_pages)
            c2.metric("✅ 有效頁數", kept_pages)
            c3.metric("🗑️ 移除空白", total_pages - kept_pages)

            if not valid_rows:
                st.warning("沒有提取到有效資料。")
                return

            # 5. 建立原始 DataFrame
            df = pd.DataFrame(valid_rows)
            
            # 計算重複
            duplicates_mask = df.duplicated(subset=['Product No'], keep=False)
            dup_count = df[duplicates_mask]['Product No'].nunique()
            
            if dup_count > 0:
                st.error(f"⚠️ 注意：發現 {dup_count} 款商品編號重複！(已用黃色標示)")
            else:
                st.success("✅ 檢查通過：沒有重複的商品編號。")

            # --- 搜尋功能 (使用內建元件以確保穩定) ---
            st.markdown("### 🔍 搜尋與檢查")
            search_query = st.text_input(
                "在此輸入關鍵字 (輸入後請按 Enter 搜尋)", 
                placeholder="Type to search..."
            )

            # 過濾邏輯
            filtered_df = df.copy()
            if search_query:
                mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
                filtered_df = filtered_df[mask]

            # 定義樣式
            def highlight_row(row):
                if row.name in duplicates_mask.index and duplicates_mask[row.name]:
                    return ['background-color: #fff3cd; color: #856404; font-weight: bold'] * len(row)
                return [''] * len(row)

            # 套用樣式
            styled_df = filtered_df.style.apply(highlight_row, axis=1)

            # 6. 顯示表格 (設定欄位)
            st.dataframe(
                styled_df,
                use_container_width=False,
                height=900,
                column_config={
                    "序號": st.column_config.NumberColumn( # ✅ 新增：序號欄位設定
                        "No.", 
                        width=50, 
                        format="%d"
                    ),
                    "原始頁碼": st.column_config.NumberColumn(
                        "頁碼", 
                        width=60, 
                        format="%d"
                    ),
                    "Product No": st.column_config.TextColumn("Product No", width=160),
                    "Barcode": st.column_config.TextColumn("Barcode", width=160),
                    "商品名稱": st.column_config.TextColumn("商品名稱", width=1000),
                    "數量": st.column_config.NumberColumn("數量", width=90, format="%d")
                },
                hide_index=True
            )

        except Exception as e:
            st.error(f"處理失敗: {e}")