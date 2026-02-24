import streamlit as st
import requests
import pandas as pd
import streamlit.components.v1 as components
from supabase import create_client, Client

# ==========================================
# 初始化 Supabase 連線
# ==========================================
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        return None

supabase = init_supabase()

def log_to_supabase(order_id, barcode, status):
    if supabase is not None:
        try:
            res = supabase.table("scan_logs").select("*").eq("order_id", order_id).execute()
            if len(res.data) > 0:
                existing_barcodes = res.data[0].get("barcode") or ""
                if status == "RESET":
                    new_barcodes = ""
                    final_status = "🔄 已重置"
                else:
                    new_barcodes = f"{existing_barcodes}, {barcode}" if existing_barcodes else barcode
                    final_status = status
                    
                supabase.table("scan_logs").update({
                    "barcode": new_barcodes,
                    "status": final_status
                }).eq("order_id", order_id).execute()
            else:
                if status != "RESET": 
                    supabase.table("scan_logs").insert({
                        "order_id": order_id,
                        "barcode": barcode,
                        "status": status
                    }).execute()
        except Exception:
            pass 

def delete_log_from_supabase(order_id):
    if supabase is not None:
        try:
            supabase.table("scan_logs").delete().eq("order_id", order_id).execute()
        except Exception:
            pass

# ==========================================
# 聲音與震動回饋 (JavaScript)
# ==========================================
def play_success_feedback():
    js = """<script>
        if (navigator.vibrate) window.navigator.vibrate(100);
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        var osc = ctx.createOscillator(); osc.connect(ctx.destination);
        osc.frequency.value = 1200; osc.start(); setTimeout(function(){ osc.stop(); }, 100);
    </script>"""
    components.html(js, height=0)

def play_error_feedback():
    js = """<script>
        if (navigator.vibrate) window.navigator.vibrate([300, 100, 300]);
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        var osc = ctx.createOscillator(); osc.type = 'square'; osc.connect(ctx.destination);
        osc.frequency.value = 200; osc.start(); setTimeout(function(){ osc.stop(); }, 500);
    </script>"""
    components.html(js, height=0)

# ==========================================
# 主功能函式
# ==========================================
def show_scanner_page():
    if 'current_order_id' not in st.session_state:
        st.session_state.current_order_id = None
    if 'order_details' not in st.session_state:
        st.session_state.order_details = None
    if 'last_completed_order' not in st.session_state:
        st.session_state.last_completed_order = None

    st.title("📦 Letech 連續出庫系統")

    st.sidebar.markdown("### ⚙️ 出庫系統設定")
    token = st.sidebar.text_input("輸入 Authorization Token：", type="password")
    
    if supabase is None:
        st.sidebar.warning("⚠️ 尚未設定 Supabase 密鑰，出庫紀錄將不會儲存。")
    else:
        st.sidebar.success("✅ Supabase 資料庫已連線")

    def get_headers():
        return {
            'Authorization': token if token.startswith('Bearer') else f'Bearer {token}',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://dashboard.letech.com.hk/'
        }

    if not token:
        st.warning("👈 請先在左側邊欄輸入 Token 才能開始出庫作業。")
        st.stop()

    # ==========================================
    # 第一階段：尚未鎖定訂單
    # ==========================================
    if st.session_state.current_order_id is None:
        st.markdown("### 步驟 1：載入訂單")
        
        if st.session_state.last_completed_order:
            st.success(f"🌟 訂單 【{st.session_state.last_completed_order}】 已全數出庫完成！請繼續掃描下一張單。")
            play_success_feedback()
            st.session_state.last_completed_order = None
        
        with st.form("order_form"):
            order_input = st.text_input("1️⃣ 請掃描或輸入【訂單號碼】(Order ID)：")
            submit_order = st.form_submit_button("🔍 查詢並鎖定訂單", use_container_width=True)
            
            if submit_order and order_input:
                with st.spinner("查詢訂單資料中..."):
                    url_order = f"https://api.letech.com.hk/api/dear/scan/order?order_id={order_input}"
                    try:
                        res_order = requests.get(url_order, headers=get_headers())
                        
                        if res_order.status_code == 200:
                            order_json = res_order.json()
                            
                            is_completed = order_json.get("status", False)
                            total_qty = 0
                            total_scanned = 0
                            
                            main_products = order_json.get("products") or []
                            for p in main_products:
                                total_qty += p.get("quantity", 0)
                                total_scanned += p.get("scanQty", 0)
                                sub_products = p.get("products") or []
                                for sub_p in sub_products:
                                    total_qty += sub_p.get("quantity", 0)
                                    total_scanned += sub_p.get("scanQty", 0)
                                    
                            if is_completed or (total_qty > 0 and total_scanned >= total_qty):
                                st.error(f"🚫 訂單 【{order_input}】 已出庫！請勿重複作業。")
                                play_error_feedback()
                            else:
                                st.session_state.current_order_id = order_input
                                st.session_state.order_details = order_json
                                play_success_feedback()
                                st.rerun()
                                
                        elif res_order.status_code == 500:
                            st.error(f"🚫 伺服器拒絕 (代碼：500)\n\n這通常代表：此單號**「不存在」**，或是**「已經出庫很久、被系統歸檔了」**！")
                            play_error_feedback()
                        elif res_order.status_code in [401, 403]:
                            st.error(f"🔒 權限失效 (代碼：{res_order.status_code})\n\n您的 Token 已經過期了，請重新輸入！")
                            play_error_feedback()
                        else:
                            st.error(f"❌ 發生未知的連線錯誤！(代碼：{res_order.status_code})")
                            play_error_feedback()
                            
                    except Exception as e:
                        st.error(f"連線錯誤：{e}")

    # ==========================================
    # 第二階段：已鎖定訂單
    # ==========================================
    else:
        order_data = st.session_state.order_details.get("order") or {}
        products_data = st.session_state.order_details.get("products") or []

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.success(f"📌 **{st.session_state.current_order_id}**\n\n🚚 目的地：{order_data.get('deliver_to_warehouse', '未指定')}")
        
        with col2:
            # 🌟 新增：強制出庫按鈕
            if st.button("⚠️ 強制出庫", use_container_width=True):
                # 寫入特殊的資料庫狀態
                log_to_supabase(st.session_state.current_order_id, "MANUAL_FORCE", "⚠️ 強制出庫")
                
                # 給予提示並跳回首頁
                st.session_state.last_completed_order = f"{st.session_state.current_order_id} (強制放行)"
                st.session_state.current_order_id = None
                st.session_state.order_details = None
                st.rerun()

        with col3:
            # 🌟 變更：原本的換單改名為「重置」
            if st.button("🔄 重置", use_container_width=True):
                t_q = 0
                t_s = 0
                for p in products_data:
                    t_q += p.get('quantity', 0)
                    t_s += p.get('scanQty', 0)
                    for sub_p in p.get('products') or []:
                        t_q += sub_p.get('quantity', 0)
                        t_s += sub_p.get('scanQty', 0)
                
                is_done = st.session_state.order_details.get("status", False) or (t_q > 0 and t_s >= t_q)
                
                # 如果尚未滿單就按下重置，一併清除資料庫與伺服器紀錄
                if not is_done:
                    delete_log_from_supabase(st.session_state.current_order_id)
                    url_cancel = f"https://api.letech.com.hk/api/dear/scan/cancel?order_id={st.session_state.current_order_id}"
                    try:
                        requests.post(url_cancel, headers=get_headers())
                    except:
                        pass
                
                st.session_state.current_order_id = None
                st.session_state.order_details = None
                st.rerun()

        table_rows = []
        total_qty = 0
        total_scanned = 0

        for p in products_data:
            qty = p.get('quantity', 0)
            sqty = p.get('scanQty', 0)
            total_qty += qty
            total_scanned += sqty
            
            diff = qty - sqty
            status = "✅ 完成" if diff <= 0 else f"🟡 尚缺 {diff}"
            
            table_rows.append({
                "商品名稱": p.get('skuNameZh', ''),
                "條碼": p.get('barcode', ''),
                "應出": qty,
                "已掃": sqty,
                "狀態": status
            })
            
            sub_products = p.get('products') or []
            if sub_products:
                for sub_p in sub_products:
                    sub_qty = sub_p.get('quantity', 0)
                    sub_sqty = sub_p.get('scanQty', 0)
                    sub_diff = sub_qty - sub_sqty
                    sub_status = "✅ 完成" if sub_diff <= 0 else f"🟡 尚缺 {sub_diff}"
                    
                    table_rows.append({
                        "商品名稱": " ↳ " + sub_p.get('skuNameZh', ''), 
                        "條碼": sub_p.get('barcode', ''),
                        "應出": sub_qty,
                        "已掃": sub_sqty,
                        "狀態": sub_status
                    })

        if total_qty > 0:
            progress = min(total_scanned / total_qty, 1.0)
            st.progress(progress, text=f"📦 出庫總進度： {total_scanned} / {total_qty}")

        st.markdown("#### 📋 應出貨品清單")
        if table_rows:
            df = pd.DataFrame(table_rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ 系統回傳：此訂單內沒有貨品資料。")

        st.divider()

        st.markdown("#### 🛒 步驟 2：連續掃描貨品")
        with st.form("barcode_form", clear_on_submit=True):
            barcode_input = st.text_input("2️⃣ 請掃描【貨品條碼】(Barcode)：")
            submit_barcode = st.form_submit_button("⚡ 出庫此貨品", use_container_width=True)
            
            if submit_barcode and barcode_input:
                url_barcode = f"https://api.letech.com.hk/api/dear/scan/barcode?order_id={st.session_state.current_order_id}&barcode={barcode_input}&is_open=0"
                try:
                    res_barcode = requests.post(url_barcode, headers=get_headers())
                    if res_barcode.status_code == 200:
                        
                        url_refresh = f"https://api.letech.com.hk/api/dear/scan/order?order_id={st.session_state.current_order_id}"
                        refreshed_data = requests.get(url_refresh, headers=get_headers()).json()
                        
                        t_q = 0
                        t_s = 0
                        for p in refreshed_data.get("products") or []:
                            t_q += p.get('quantity', 0)
                            t_s += p.get('scanQty', 0)
                            for sub_p in p.get('products') or []:
                                t_q += sub_p.get('quantity', 0)
                                t_s += sub_p.get('scanQty', 0)
                                
                        is_done = refreshed_data.get("status", False) or (t_q > 0 and t_s >= t_q)
                        
                        if is_done:
                            log_to_supabase(st.session_state.current_order_id, barcode_input, "✅ 已出庫")
                            st.session_state.last_completed_order = st.session_state.current_order_id
                            
                            st.session_state.current_order_id = None
                            st.session_state.order_details = None
                            st.rerun()
                            
                        else:
                            st.toast(f"✅ {barcode_input} 掃描成功！")
                            play_success_feedback()
                            log_to_supabase(st.session_state.current_order_id, barcode_input, "🟡 出庫中")
                            
                            st.session_state.order_details = refreshed_data
                            st.rerun()
                            
                    else:
                        st.error(f"❌ 條碼 {barcode_input} 錯誤或數量已滿！")
                        play_error_feedback()
                except Exception as e:
                    st.error(f"連線錯誤：{e}")
                    play_error_feedback()
