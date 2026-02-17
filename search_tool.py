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
    # 注入 CSS：核心邏輯在於 @media 判斷螢幕寬度
    st.markdown("""
        <style>
            /* 1. 定義手機版卡片樣式 */
            .result-card {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 12px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
            .card-label { color: #888; font-size: 11px; font-weight: bold; margin-bottom: 2px; }
            .card-value { color: #333; font-size: 15px; margin-bottom: 8px; word-break: break-all; }
            .card-name { color: #2c3e50; font-weight: 600; font-size: 16px; line-height: 1.4; border-top: 1px solid #eee; padding-top: 8px; }

            /* 2. 預設隱藏手機版卡片容器 */
            .mobile-view { display: none; }
            /* 3. 預設顯示電腦版表格容器 */
            .desktop-view { display: block; }

            /* 4. 當螢幕寬度小於等於 768px 時 (手機/平板) */
            @media screen and (max-width: 768px) {
                .desktop-view { display: none !important; } /* 隱藏表格 */
                .mobile-view { display: block !important; }  /* 顯示卡片 */
            }
        </style>
    """, unsafe_allow_html=True)
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
    st.markdown("### 🔍 Search Barcode System")
    
    df = load_data()
    if df is None:
        st.error(f"❌ 找不到資料庫 `{DEFAULT_DB_FILE}`")
        return

    st.caption(f"📚 Inventory Ready：Total {len(df)} Data")
    
    user_input = st.text_input("Please Enter Keywords. (SKU / Barcode / Name):", placeholder="Enter Search Terms...")

    if user_input:
        query = user_input.strip()
        mask = (
            df['ProductCode'].str.contains(query, case=False, na=False) | 
            df['Barcode'].str.contains(query, case=False, na=False) |
            df['Name'].str.contains(query, case=False, na=False)
        )
        results = df[mask]

        if not results.empty:
            st.success(f"✅ Found {len(results)} Data")


            # --- B. 手機版顯示區域 (被包在 mobile-view div 中) ---
            st.markdown('<div class="mobile-view">', unsafe_allow_html=True)
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
            st.warning("❌ No Data")
