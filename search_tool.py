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
    # 注入手機版專屬 CSS
    st.markdown("""
        <style>
            /* 手機版樣式 (螢幕寬度小於 768px) */
            @media (max-width: 768px) {
                /* 隱藏原生表格 */
                .mobile-hide { display: none !important; }
                
                /* 卡片容器 */
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
                    text-transform: uppercase;
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
            }
            
            /* 電腦版樣式 */
            @media (min-width: 769px) {
                .desktop-hide { display: none !important; }
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

            # --- 1. 電腦版顯示 (表格) ---
            st.markdown('<div class="mobile-hide">', unsafe_allow_html=True)
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
            st.markdown('</div>', unsafe_allow_html=True)

            # --- 2. 手機版顯示 (三行卡片式) ---
            st.markdown('<div class="desktop-hide">', unsafe_allow_html=True)
            for _, row in results.iterrows():
                st.markdown(f"""
                <div class="result-card">
                    <div class="card-label">SKU</div>
                    <div class="card-value">{row['ProductCode']}</div>
                    
                    <div class="card-label">Barcode</div>
                    <div class="card-value">{row['Barcode']}</div>
                    
                    <div class="card-name">{row['Name']}</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        else:
            st.warning("❌ 查無資料")
