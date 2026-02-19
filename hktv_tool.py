import streamlit as st
import json
import os
import time

def show_hktvmall_page():
    st.markdown("### 📦 HKTVmall 訂單監控面板")
    st.markdown("自動追蹤 HKTVmall 商戶 8 小時送貨的訂單狀態。")
    
    # 建立一個水平排列的區域放按鈕
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🔄 手動更新畫面"):
            st.rerun()
            
    st.divider()

    # 讀取 JSON
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'order_data.json')
    if not os.path.exists(file_path):
        st.warning("⏳ 機器人尚未完成第一次抓取，請稍候片刻再試。")
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        st.error("❌ 讀取資料失敗，請確認資料檔格式。")
        return

    # 顯示狀態列
    st.markdown(f"**🕒 系統最後更新時間：** `{data.get('last_updated', '--')}`")
    status_msg = data.get("status_msg", "")
    if "休息" in status_msg:
        st.warning(status_msg)
    elif status_msg:
        st.info(status_msg)

    # 針對 Streamlit metric 元件的自訂 CSS 樣式 (統一卡片與顏色)
    st.markdown("""
        <style>
        div[data-testid="stMetricValue"] { font-size: 2.2rem !important; font-weight: 800 !important; }
        /* 今日訂單區塊顏色 */
        div[data-testid="metric-container"]:nth-child(1) div[data-testid="stMetricValue"] { color: #e67e22; }
        div[data-testid="metric-container"]:nth-child(2) div[data-testid="stMetricValue"] { color: #27ae60; }
        div[data-testid="metric-container"]:nth-child(3) div[data-testid="stMetricValue"] { color: #3498db; }
        div[data-testid="metric-container"]:nth-child(4) div[data-testid="stMetricValue"] { color: #9b59b6; }
        /* 明日訂單區塊顏色 */
        div[data-testid="metric-container"]:nth-child(5) div[data-testid="stMetricValue"] { color: #e67e22; }
        div[data-testid="metric-container"]:nth-child(6) div[data-testid="stMetricValue"] { color: #27ae60; }
        div[data-testid="metric-container"]:nth-child(7) div[data-testid="stMetricValue"] { color: #3498db; }
        div[data-testid="metric-container"]:nth-child(8) div[data-testid="stMetricValue"] { color: #9b59b6; }
        </style>
    """, unsafe_allow_html=True)

    # =================今日訂單=================
    today = data.get("today", {})
    st.markdown(f"#### 📦 今日訂單 ({today.get('date', '--')})")
    t_cols = st.columns(4)
    t_cols[0].metric("已建立 (CONFIRMED)", today.get("CONFIRMED", "--"))
    t_cols[1].metric("已確認 (ACKNOWLEDGED)", today.get("ACKNOWLEDGED", "--"))
    t_cols[2].metric("已包裝 (PACKED)", today.get("PACKED", "--"))
    t_cols[3].metric("已出貨 (PICKED)", today.get("PICKED", "--"))

    st.markdown("<br>", unsafe_allow_html=True)

    # =================明日訂單=================
    tomorrow = data.get("tomorrow", {})
    st.markdown(f"#### 🚚 明日訂單 ({tomorrow.get('date', '--')})")
    m_cols = st.columns(4)
    m_cols[0].metric("已建立 (CONFIRMED)", tomorrow.get("CONFIRMED", "--"))
    m_cols[1].metric("已確認 (ACKNOWLEDGED)", tomorrow.get("ACKNOWLEDGED", "--"))
    m_cols[2].metric("已包裝 (PACKED)", tomorrow.get("PACKED", "--"))
    m_cols[3].metric("已出貨 (PICKED)", tomorrow.get("PICKED", "--"))