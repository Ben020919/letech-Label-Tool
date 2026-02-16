import streamlit as st
import pandas as pd
import os

# ================= 設定固定檔案名稱 =================
# 這是您剛剛上傳的正確檔案
DEFAULT_DB_FILE = "Barcode.xlsx.csv"

@st.cache_data
def load_data():
    """
    讀取固定資料庫檔案，並處理潛在的格式問題
    """
    if not os.path.exists(DEFAULT_DB_FILE):
        return None
        
    try:
        # 讀取 CSV
        df = pd.read_csv(DEFAULT_DB_FILE)
        
        # 關鍵欄位清理
        cols_to_ensure = ['ProductCode', 'Name', 'Barcode']
        for col in cols_to_ensure:
            if col in df.columns:
                # 轉為字串、填補空值、去前後空格
                df[col] = df[col].fillna('').astype(str).str.strip()
                
                # 處理 Excel 匯出數字時常見的 .0 問題 (如 12345.0 -> 12345)
                if col in ['ProductCode', 'Barcode']:
                    df[col] = df[col].apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)
            else:
                # 若缺失欄位則補空
                df[col] = ""
                
        return df
    except Exception as e:
        st.error(f"讀取資料庫時發生錯誤: {e}")
        return None

def show_search_barcode_page():
    st.markdown("### 🔍 Search Barcode/SKU/Name")
    
    # 1. 載入固定資料
    df = load_data()
    
    if df is None:
        st.error(f"❌ 找不到資料庫檔案 `{DEFAULT_DB_FILE}`")
        st.info("請確保檔案已上傳至目錄並命名正確。")
        # 備用上傳功能
        uploaded = st.file_uploader("手動上傳備份檔案", type=['csv', 'xlsx'])
        if uploaded:
            if uploaded.name.endswith('.csv'):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
            st.success("暫時載入成功")
        else:
            return

    st.caption(f"📚 資料庫就緒：共 {len(df)} 筆商品資料")
    st.divider()

    # 2. 輸入區域
    user_input = st.text_input(
        "請輸入關鍵字 (SKU / Barcode / 商品名稱):", 
        placeholder="輸入部分內容即可搜尋..."
    )

    # 3. 執行搜尋
    if user_input:
        query = user_input.strip()
        
        # 同時在三個欄位中搜尋 (不分大小寫)
        mask = (
            df['ProductCode'].str.contains(query, case=False, na=False) | 
            df['Barcode'].str.contains(query, case=False, na=False) |
            df['Name'].str.contains(query, case=False, na=False)
        )
        
        results = df[mask]

        # 4. 顯示結果
        if not results.empty:
            st.success(f"✅ 找到 {len(results)} 筆相符結果")
            
            # 只顯示最重要的三個欄位
            st.dataframe(
                results[['ProductCode', 'Barcode', 'Name']], 
                use_container_width=True,
                column_config={
                    "ProductCode": st.column_config.TextColumn("SKU (產品編號)", width="medium"),
                    "Barcode": st.column_config.TextColumn("Barcode (條碼)", width="medium"),
                    "Name": st.column_config.TextColumn("商品名稱", width="large"),
                },
                hide_index=True
            )
        else:
            st.warning("❌ 查無資料，請確認輸入是否正確。")
