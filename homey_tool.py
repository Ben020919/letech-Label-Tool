import streamlit as st
from pypdf import PdfReader
import pandas as pd
import re
import os

# ================= 設定固定主檔名稱 =================
MASTER_FILE = "data.xlsx"

@st.cache_data
def load_master_data():
    """
    自動讀取固定的 Excel 主檔
    """
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
            st.error(f"❌ 在 {MASTER_FILE} 中找不到 `Product_No` 或 `Label_Type` 欄位。")
            return None
    except Exception as e:
        st.error(f"❌ 讀取 {MASTER_FILE} 失敗: {e}")
        return None

def show_homey_page():
    st.markdown("### 🏠 Homey 3PL 訂單處理系統")
    st.caption("功能：特殊 Label 全提高亮 + 序號從 1 開始 + 自定義寬度")

    master_df = load_master_data()
    if master_df is not None:
        st.success(f"✅ 已連結主檔：`{MASTER_FILE}`")
    else:
        st.warning(f"⚠️ 找不到 `{MASTER_FILE}`")

    st.divider()

    uploaded_file = st.file_uploader("請上傳 Homey 訂單 (PDF)", type=["pdf"], key="homey_pdf")

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
                
                # --- Step 1: 去除空白頁邏輯 ---
                clean_text = re.sub(r'\[Image \d+\]', '', text).strip()
                if not clean_text:
                    continue 
                
                valid_page_count += 1
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                lines = [l for l in lines if not l.startswith("[Image")]
                if not lines: continue

                # 提取資訊
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

                # --- Step 2: 邏輯判斷 Label Type ---
                excel_label = ""
                if master_df is not None:
                    found = master_df[master_df['Product_No'] == p_no]
                    if not found.empty:
                        excel_label = str(found.iloc[0]['Label_Type'])

                final_label = ""
                if not barcode_val or barcode_val.strip() == "" or barcode_val == p_no:
                    final_label = "需要Print SKU 當作Barcode"
                elif barcode_val and barcode_val[-1].isalpha():
                    final_label = "需要Print Repack Lable"
                elif excel_label and excel_label != "nan" and excel_label.strip() != "":
                    final_label = excel_label
                else:
                    final_label = "普通Lable"

                valid_rows.append({
                    "Product No": p_no,
                    "Barcode": barcode_val if barcode_val else " (N/A) ",
                    "商品名稱": p_name,
                    "數量": qty,
                    "Label Type": final_label
                })

            prog_bar.empty()
            status_text.empty()

            st.write("#### 📊 處理統計")
            c1, c2, c3 = st.columns(3)
            c1.metric("📄 原始頁數", total_pages)
            c2.metric("✅ 有效頁數", valid_page_count)
            c3.metric("🗑️ 移除空白", total_pages - valid_page_count)

            # --- 全行高亮邏輯 ---
            def highlight_row(row):
                """
                如果 Label Type 包含特定關鍵字，則回傳該行全行的黃色樣式
                """
                v = str(row['Label Type']).lower()
                if "repack" in v or "sku" in v or "蟲" in v or "food" in v:
                    return ['background-color: #FFFFAA; color: #B30000; font-weight: bold;'] * len(row)
                return [''] * len(row)

            if valid_rows:
                df_result = pd.DataFrame(valid_rows)
                
                # 設定序號從 1 開始
                df_result.index = range(1, len(df_result) + 1)
                df_result.index.name = "No."
                
                st.write("#### 📋 訂單明細")
                
                # 使用 apply(highlight_row, axis=1) 來套用全行樣式
                st.dataframe(
                    df_result.style.apply(highlight_row, axis=1),
                    use_container_width=False,
                    height=900,
                    column_config={
                        "Product No": st.column_config.TextColumn("Product No", width=110),
                        "Barcode": st.column_config.TextColumn("Barcode", width=120),
                        "商品名稱": st.column_config.TextColumn("商品名稱", width=650),
                        "數量": st.column_config.NumberColumn("數量", width=40, format="%d"),
                        "Label Type": st.column_config.TextColumn("Label Type (自動偵測)", width=225)
                    }
                )
                
                csv = df_result.to_csv(index=True).encode('utf-8-sig')
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
