import streamlit as st
import requests
import pandas as pd
import streamlit.components.v1 as components
from supabase import create_client, Client
from PIL import Image

# 嘗試載入條碼解析引擎
try:
    from pyzbar.pyzbar import decode
    HAS_PYZBAR = True
except ImportError:
    HAS_PYZBAR = False

def decode_barcode(image_file):
    if not HAS_PYZBAR:
        return None
    try:
        img = Image.open(image_file)
        decoded = decode(img)
        if decoded:
            return decoded[0].data.decode('utf-8')
    except Exception:
        pass
    return None

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
# 聲音與震動回饋
# ==========================================
def play_success_feedback():
    js = """<script>if (navigator.vibrate) window.navigator.vibrate(100);</script>"""
    components.html(js, height=0)

def play_error_feedback():
    js = """<script>if (navigator.vibrate) window.navigator.vibrate([300, 100, 300]);</script>"""
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
    if 'processed_cam_hashes' not in st.session_state:
        st.session_state.processed_cam_hashes = set()

    st.title("📦 Letech 連續出庫系統")

    st.sidebar.markdown("### ⚙️ 出庫系統設定")
    token = st.sidebar.text_input("輸入 Authorization Token：", type="password")
    
    if supabase is None:
        st.sidebar.warning("⚠️ 尚未設定 Supabase 密鑰，出庫紀錄將不會儲存。")

    def get_headers():
        return {
            'Authorization': token if token.startswith('Bearer') else f'Bearer {token}',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
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
            st.success(f"🌟 訂單 【{st.session_state.last_completed_order}】 已全數出庫完成！請繼續作業。")
            play_success_feedback()
            st.session_state.last_completed_order = None
            
        input_mode = st.radio("掃描模式：", ["⌨️ 鍵盤 / 藍牙槍", "📷 手機相機拍照"], horizontal=True, key="mode_1")
        
        order_input = None
        
        if input_mode == "⌨️ 鍵盤 / 藍牙槍":
            with st.form("order_form"):
                text_in = st.text_input("1️⃣ 請輸入或掃描【訂單號碼】：")
                submit_order = st.form_submit_button("🔍 查詢並鎖定", use_container_width=True)
                if submit_order and text_in:
                    order_input = text_in
        else:
            cam_image = st.camera_input("📸 請對準訂單條碼並拍照", key="cam_order")
            if cam_image:
                cam_hash = hash(cam_image.getvalue())
                if cam_hash not in st.session_state.processed_cam_hashes:
                    with st.spinner("解析條碼中..."):
                        decoded_text = decode_barcode(cam_image)
                        if decoded_text:
                            order_input = decoded_text
                            st.session_state.processed_cam_hashes.add(cam_hash)
                        else:
                            st.error("❌ 無法辨識條碼，請確認畫面清晰！")

        if order_input:
            with st.spinner("查詢訂單資料中..."):
                url_order = f"https://api.letech.com.hk/api/dear/scan/order?order_id={order_input}"
                try:
                    res_order = requests.get(url_order, headers=get_headers())
                    if res_order.status_code == 200:
                        order_json = res_order.json()
                        is_completed = order_json.get("status", False)
                        total_qty = 0
                        total_scanned = 0
                        
                        for p in (order_json.get("products") or []):
                            total_qty += p.get("quantity", 0)
                            total_scanned += p.get("scanQty", 0)
                            for sub_p in (p.get("products") or []):
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
                    else:
                        st.error(f"❌ 找不到此訂單或伺服器異常 (代碼：{res_order.status_code})")
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
            st.success(f"📌 **{st.session_state.current_order_id}**\n🚚 目的地：{order_data.get('deliver_to_warehouse', '未指定')}")
        with col2:
            if st.button("⚠️ 強制出庫", use_container_width=True):
                st.warning("🚧 此功能開發中！")
                play_error_feedback()
        with col3:
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
                if not is_done:
                    delete_log_from_supabase(st.session_state.current_order_id)
                    try:
                        requests.post(f"https://api.letech.com.hk/api/dear/scan/cancel?order_id={st.session_state.current_order_id}", headers=get_headers())
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
            status = "✅ 完成" if qty - sqty <= 0 else f"🟡 尚缺 {qty - sqty}"
            table_rows.append({"商品名稱": p.get('skuNameZh', ''), "條碼": p.get('barcode', ''), "應出": qty, "已掃": sqty, "狀態": status})
            
            for sub_p in (p.get('products') or []):
                sub_qty = sub_p.get('quantity', 0)
                sub_sqty = sub_p.get('scanQty', 0)
                sub_status = "✅ 完成" if sub_qty - sub_sqty <= 0 else f"🟡 尚缺 {sub_qty - sub_sqty}"
                table_rows.append({"商品名稱": " ↳ " + sub_p.get('skuNameZh', ''), "條碼": sub_p.get('barcode', ''), "應出": sub_qty, "已掃": sub_sqty, "狀態": sub_status})

        if total_qty > 0:
            st.progress(min(total_scanned / total_qty, 1.0), text=f"📦 出庫總進度： {total_scanned} / {total_qty}")

        st.markdown("#### 📋 應出貨品清單")
        if table_rows:
            st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

        st.divider()

        st.markdown("#### 🛒 步驟 2：連續掃描貨品")
        
        input_mode_2 = st.radio("掃描模式：", ["⌨️ 鍵盤 / 藍牙槍", "📷 手機相機拍照"], horizontal=True, key="mode_2")
        
        barcode_input = None
        
        if input_mode_2 == "⌨️ 鍵盤 / 藍牙槍":
            with st.form("barcode_form", clear_on_submit=True):
                text_in_b = st.text_input("2️⃣ 請輸入或掃描【貨品條碼】：")
                submit_barcode = st.form_submit_button("⚡ 出庫此貨品", use_container_width=True)
                if submit_barcode and text_in_b:
                    barcode_input = text_in_b
        else:
            cam_image_b = st.camera_input("📸 請對準貨品條碼並拍照", key="cam_barcode")
            if cam_image_b:
                cam_hash_b = hash(cam_image_b.getvalue())
                if cam_hash_b not in st.session_state.processed_cam_hashes:
                    with st.spinner("解析條碼中..."):
                        decoded_text_b = decode_barcode(cam_image_b)
                        if decoded_text_b:
                            barcode_input = decoded_text_b
                            st.session_state.processed_cam_hashes.add(cam_hash_b)
                        else:
                            st.error("❌ 無法辨識條碼，請確認畫面清晰！")

        if barcode_input:
            url_barcode = f"https://api.letech.com.hk/api/dear/scan/barcode?order_id={st.session_state.current_order_id}&barcode={barcode_input}&is_open=0"
            try:
                res_barcode = requests.post(url_barcode, headers=get_headers())
                if res_barcode.status_code == 200:
                    url_refresh = f"https://api.letech.com.hk/api/dear/scan/order?order_id={st.session_state.current_order_id}"
                    refreshed_data = requests.get(url_refresh, headers=get_headers()).json()
                    
                    t_q = sum(p.get('quantity', 0) for p in (refreshed_data.get("products") or [])) + sum(sub_p.get('quantity', 0) for p in (refreshed_data.get("products") or []) for sub_p in (p.get('products') or []))
                    t_s = sum(p.get('scanQty', 0) for p in (refreshed_data.get("products") or [])) + sum(sub_p.get('scanQty', 0) for p in (refreshed_data.get("products") or []) for sub_p in (p.get('products') or []))
                            
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
