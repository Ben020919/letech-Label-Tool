import streamlit as st
import requests
import pandas as pd
import streamlit.components.v1 as components
from supabase import create_client, Client
from PIL import Image

# 🌟 新增：匯入使用量追蹤器
try:
    from usage_tracker import log_action
except ImportError:
    def log_action(action_name):
        pass

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
        except Exception as e:
            print(f"Supabase Insert Error: {e}") 

def delete_log_from_supabase(order_id):
    if supabase is not None:
        try:
            supabase.table("scan_logs").delete().eq("order_id", order_id).execute()
        except Exception as e:
            print(f"Supabase Delete Error: {e}")

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
    # --- 💅 注入自訂 CSS 美化介面 ---
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; }
        
        div[data-baseweb="input"] { border-radius: 12px !important; border: 2px solid #007bff !important; }
        div[data-baseweb="input"] input { font-size: 1.2rem !important; padding: 12px !important; text-align: center; font-weight: bold;}
        
        div.stButton > button {
            width: 100%;
            border-radius: 12px;
            font-weight: bold;
            font-size: 16px;
            padding: 10px 0;
            transition: all 0.2s;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border: none;
        }
        div.stButton > button:first-child { background-color: #007bff; color: white; }
        div.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.15); }
        
        .info-card {
            background: #ffffff;
            border-radius: 15px;
            padding: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            border: 1px solid #e0e0e0;
            margin-bottom: 15px;
        }
        .info-title { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px;}
        .info-value { font-size: 20px; font-weight: 900; color: #2c3e50; }
        .info-dest { font-size: 14px; color: #e67e22; font-weight: bold; margin-top: 5px; }
        
        div[role="radiogroup"] { background: #f8f9fa; padding: 10px; border-radius: 10px; }
        
        /* 🌟 新增：自訂 HTML 表格自動換行 CSS */
        table.custom-table { width: 100%; border-collapse: collapse; font-size: 14px; background-color: white; margin-bottom: 15px;}
        table.custom-table th, table.custom-table td { 
            border-bottom: 1px solid #e0e0e0; 
            padding: 10px 8px; 
            text-align: left; 
            word-break: break-word; 
            white-space: normal !important; /* 強制文字遇到邊界自動換行 */
            vertical-align: middle;
        }
        table.custom-table th { background-color: #f8f9fa; color: #555; font-weight: bold; font-size: 13px;}
        </style>
    """, unsafe_allow_html=True)

    if 'current_order_id' not in st.session_state:
        st.session_state.current_order_id = None
    if 'order_details' not in st.session_state:
        st.session_state.order_details = None
    if 'last_completed_order' not in st.session_state:
        st.session_state.last_completed_order = None
    if 'processed_cam_hashes' not in st.session_state:
        st.session_state.processed_cam_hashes = set()

    st.markdown("<h2 style='text-align: center; color: #2c3e50;'>📦 出庫作業台</h2>", unsafe_allow_html=True)

    # ==========================================
    # 🌟 智慧獲取 Token 邏輯
    # ==========================================
    st.sidebar.markdown("### ⚙️ 系統核心設定")
    
    try:
        secret_token = st.secrets["LETECH_TOKEN"]
    except Exception:
        secret_token = ""
        
    token = st.sidebar.text_input("輸入 Authorization Token：", value=secret_token, type="password")
    
    if token and token == secret_token:
        st.sidebar.success("✅ API Token 已從雲端自動載入")
    elif token and token != secret_token:
        st.sidebar.info("💡 目前使用手動輸入的 Token")
        
    if supabase is None:
        st.sidebar.warning("⚠️ 尚未設定 Supabase 密鑰，出庫紀錄將不會儲存。")
    else:
        st.sidebar.success("✅ Supabase 資料庫已連線")

    def get_headers():
        return {
            'Authorization': token if token.startswith('Bearer') else f'Bearer {token}',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            'Referer': 'https://dashboard.letech.com.hk/'
        }

    if not token:
        st.info("👋 歡迎使用！請先設定或輸入您的 Token 以啟用系統。")
        st.stop()

    # ==========================================
    # 第一階段：尚未鎖定訂單
    # ==========================================
    if st.session_state.current_order_id is None:
        
        if st.session_state.last_completed_order:
            st.success(f"🎉 完美！訂單 **{st.session_state.last_completed_order}** 已全數出庫完成。")
            play_success_feedback()
            st.session_state.last_completed_order = None
            
        input_mode = st.radio("選擇掃描工具：", ["⌨️ 掃描槍 / 鍵盤", "📷 手機相機 (需手動拍照)"], horizontal=True, key="mode_1")
        
        order_input = None
        
        if input_mode == "⌨️ 掃描槍 / 鍵盤":
            with st.form("order_form", clear_on_submit=True):
                text_in = st.text_input("📝 請掃描訂單條碼：", placeholder="等待掃描...")
                submit_order = st.form_submit_button("🔍 鎖定訂單", use_container_width=True)
                if submit_order and text_in:
                    order_input = text_in
        else:
            cam_image = st.camera_input("📸 請對準訂單條碼並點擊拍照", key="cam_order")
            if cam_image:
                cam_hash = hash(cam_image.getvalue())
                if cam_hash not in st.session_state.processed_cam_hashes:
                    with st.spinner("🔄 解析條碼中..."):
                        decoded_text = decode_barcode(cam_image)
                        if decoded_text:
                            order_input = decoded_text
                            st.session_state.processed_cam_hashes.add(cam_hash)
                        else:
                            st.error("❌ 條碼解析失敗，請靠近一點或確保光線充足！")

        if order_input:
            with st.spinner("🔄 正在連線 Letech 伺服器..."):
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
                            st.error(f"🚫 訂單 **{order_input}** 已出庫！請勿重複作業。")
                            play_error_feedback()
                        else:
                            st.session_state.current_order_id = order_input
                            st.session_state.order_details = order_json
                            play_success_feedback()
                            st.rerun()
                    elif res_order.status_code == 500:
                        st.error("🚫 查無此單，或該單號已歸檔 (代碼：500)")
                        play_error_feedback()
                    elif res_order.status_code in [401, 403]:
                        st.error("🔒 Token 權限已失效！請重新從系統獲取並更新至 Secrets。")
                        play_error_feedback()
                    else:
                        st.error(f"❌ 發生連線錯誤！(代碼：{res_order.status_code})")
                        play_error_feedback()
                except Exception as e:
                    st.error(f"連線異常：{e}")

    # ==========================================
    # 第二階段：已鎖定訂單
    # ==========================================
    else:
        order_data = st.session_state.order_details.get("order") or {}
        products_data = st.session_state.order_details.get("products") or []

        dest = order_data.get('deliver_to_warehouse', '未指定')
        st.markdown(f"""
            <div class="info-card">
                <div class="info-title">目前處理訂單</div>
                <div class="info-value">{st.session_state.current_order_id}</div>
                <div class="info-dest">🚚 目的地：{dest}</div>
            </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚠️ 強制出庫", use_container_width=True):
                st.warning("🚧 強制過帳功能開發中！")
                play_error_feedback()
        with col2:
            if st.button("🔄 換單 / 重置", use_container_width=True):
                t_q = sum(p.get('quantity', 0) for p in products_data) + sum(sub_p.get('quantity', 0) for p in products_data for sub_p in (p.get('products') or []))
                t_s = sum(p.get('scanQty', 0) for p in products_data) + sum(sub_p.get('scanQty', 0) for p in products_data for sub_p in (p.get('products') or []))
                
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
            status = "✅ 完成" if qty - sqty <= 0 else f"🟡 缺 {qty - sqty}"
            
            # 確保主商品名稱完整抓取
            table_rows.append({"商品名稱": p.get('skuNameZh', ''), "條碼": p.get('barcode', ''), "應出": qty, "已掃": sqty, "狀態": status})
            
            for sub_p in (p.get('products') or []):
                sub_qty = sub_p.get('quantity', 0)
                sub_sqty = sub_p.get('scanQty', 0)
                sub_status = "✅ 完成" if sub_qty - sub_sqty <= 0 else f"🟡 缺 {sub_qty - sub_sqty}"
                # 確保子商品名稱完整抓取 (移除文字截斷)
                table_rows.append({"商品名稱": " ↳ " + sub_p.get('skuNameZh', ''), "條碼": sub_p.get('barcode', ''), "應出": sub_qty, "已掃": sub_sqty, "狀態": sub_status})

        if total_qty > 0:
            st.progress(min(total_scanned / total_qty, 1.0), text=f"📦 出庫總進度： {total_scanned} / {total_qty}")

        # ==========================================
        # 🌟 自適應 HTML 表格渲染 (解決換行與滑動問題)
        # ==========================================
        st.caption("📋 應出貨品清單")
        if table_rows:
            df = pd.DataFrame(table_rows)
            # 使用 Pandas 轉換成 HTML 並賦予 CSS class，搭配頂部的樣式自動排版
            html_table = df.to_html(index=False, escape=False, classes="custom-table")
            st.markdown(html_table, unsafe_allow_html=True)

        st.divider()

        st.markdown("<h4 style='text-align: center;'>🛒 連續掃描貨品</h4>", unsafe_allow_html=True)
        input_mode_2 = st.radio("掃描工具：", ["⌨️ 掃描槍 / 鍵盤", "📷 手機相機 (需手動拍照)"], horizontal=True, key="mode_2")
        
        barcode_input = None
        
        if input_mode_2 == "⌨️ 掃描槍 / 鍵盤":
            with st.form("barcode_form", clear_on_submit=True):
                text_in_b = st.text_input("📝 請掃描貨品條碼：", placeholder="等待掃描...")
                submit_barcode = st.form_submit_button("⚡ 出庫此貨品", use_container_width=True)
                if submit_barcode and text_in_b:
                    barcode_input = text_in_b
        else:
            cam_image_b = st.camera_input("📸 請對準貨品條碼並點擊拍照", key="cam_barcode")
            if cam_image_b:
                cam_hash_b = hash(cam_image_b.getvalue())
                if cam_hash_b not in st.session_state.processed_cam_hashes:
                    with st.spinner("🔄 解析條碼中..."):
                        decoded_text_b = decode_barcode(cam_image_b)
                        if decoded_text_b:
                            barcode_input = decoded_text_b
                            st.session_state.processed_cam_hashes.add(cam_hash_b)
                        else:
                            st.error("❌ 條碼解析失敗，請重新拍攝！")

        if barcode_input:
            with st.spinner("⚡ 過帳中..."):
                url_barcode = f"https://api.letech.com.hk/api/dear/scan/barcode?order_id={st.session_state.current_order_id}&barcode={barcode_input}&is_open=0"
                try:
                    res_order_post = requests.post(url_barcode, headers=get_headers())
                    if res_order_post.status_code == 200:
                        url_refresh = f"https://api.letech.com.hk/api/dear/scan/order?order_id={st.session_state.current_order_id}"
                        refreshed_data = requests.get(url_refresh, headers=get_headers()).json()
                        
                        t_q = sum(p.get('quantity', 0) for p in (refreshed_data.get("products") or [])) + sum(sub_p.get('quantity', 0) for p in (refreshed_data.get("products") or []) for sub_p in (p.get('products') or []))
                        t_s = sum(p.get('scanQty', 0) for p in (refreshed_data.get("products") or [])) + sum(sub_p.get('scanQty', 0) for p in (refreshed_data.get("products") or []) for sub_p in (p.get('products') or []))
                                
                        is_done = refreshed_data.get("status", False) or (t_q > 0 and t_s >= t_q)
                        
                        if is_done:
                            log_to_supabase(st.session_state.current_order_id, barcode_input, "✅ 已出庫")
                            
                            # 🌟 寫入總儀表板統計數字 (+1)
                            log_action("Order_Outbound_Success")
                            
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
                    st.error(f"連線異常：{e}")
                    play_error_feedback()
