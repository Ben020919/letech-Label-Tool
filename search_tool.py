import streamlit as st
import pandas as pd
import os

# ================= 設定固定檔案名稱 =================
DEFAULT_DB_FILE = "Barcode.xlsx.csv"

@st.cache_data
def load_data():
    if not os.path.exists(DEFAULT_DB_FILE):
        return None
    try:
        df = pd.read_csv(DEFAULT_DB_FILE)
        cols_to_ensure = ['ProductCode', 'Name', 'Barcode']
        for col in cols_to_ensure:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str).str.strip()
                if col in ['ProductCode', 'Barcode']:
                    df[col] = df[col].apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)
            else:
                df[col] = ""
        return df
    except Exception as e:
        return None

def show_search_barcode_page():
    # 注入 CSS：美化手機版卡片與移除預設表格邊距
    st.markdown("""
        <style>
            .result-card {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 12px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
            .card-label {
                color: #888;
                font-size: 11px;
                font-weight: bold;
                margin-bottom: 2px;
            }
            .card-value {
                color: #333;
                font-size: 15px;
                margin-bottom: 8px;
                word-break: break-all;
            }
            .card-name {
                color: #2c3e50;
                font-weight: 600;
                font-size: 16px;
                line-height: 1.4;
                border-top: 1px solid #eee;
                padding-top: 8px;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🔍 智慧條碼搜尋 (Smart Search)")
    
    df = load_data()
    if df is None:
        st.error(f"❌ 找不到資料庫 `{DEFAULT_DB_FILE}`")
        return

    st.caption(f"📚 庫存就緒：共 {len(df)} 筆")
    
    user_input = st.text_input("請輸入關鍵字 (SKU / Barcode / 名稱):", placeholder="輸入搜尋內容...")

    if user_input:
        query = user_input.strip()
        mask = (
            df['ProductCode'].str.contains(query, case=False, na=False) | 
            df['Barcode'].str.contains(query, case=False, na=False) |
            df['Name'].str.contains(query, case=False, na=False)
        )
        results = df[mask]

        if not results.empty:
            st.success(f"✅ 找到 {len(results)} 筆結果")

            # --- 關鍵修正：使用多選按鈕或寬度偵測 ---
            # 因為 Streamlit 難以百分之百準確抓取手機瀏覽器寬度
            # 我們提供一個開關，或者直接並排顯示，但為了最穩定的體驗：
            
            # 建立兩個 Tab，一個是「表格檢視 (電腦)」，一個是「卡片檢視 (手機)」
            # 這樣無論在哪種裝置，使用者都能選最適合的看，且不會出現代碼。
            tab1, tab2 = st.tabs(["💻 電腦版表格", "📱 手機版卡片"])

            with tab1:
                st.dataframe(
                    results[['ProductCode', 'Barcode', 'Name']], 
                    use_container_width=True,
                    column_config={
                        "ProductCode": "SKU",
                        "Barcode": "Barcode",
                        "Name": "商品名稱"
                    },
                    hide_index=True
                )

            with tab2:
                for _, row in results.iterrows():
                    # 使用 st.container 確保 HTML 渲染正確
                    with st.container():
                        st.markdown(f"""
                        <div class="result-card">
                            <div class="card-label">SKU</div>
                            <div class="card-value">{row['ProductCode']}</div>
                            <div class="card-label">Barcode</div>
                            <div class="card-value">{row['Barcode']}</div>
                            <div class="card-name">{row['Name']}</div>
                        </div>
                        """, unsafe_allow_html=True)
            
        else:
            st.warning("❌ 查無資料")
