import streamlit as st
from supabase import create_client, Client
import time
from datetime import datetime, timedelta

# 1. 初始化 Supabase
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# 2. 儲存訊息功能
def save_message(supabase, user, msg, img_url=""):
    data = {
        "user_name": user,
        "message": msg,
        "image_url": img_url
    }
    supabase.table("messages").insert(data).execute()

# 3. 圖片上傳功能
def upload_image(supabase, file_bytes, file_name):
    unique_filename = f"{int(time.time())}_{file_name}"
    supabase.storage.from_("chat_images").upload(
        file=file_bytes,
        path=unique_filename,
        file_options={"content-type": "image/jpeg"}
    )
    return supabase.storage.from_("chat_images").get_public_url(unique_filename)

# ================= 自動更新的聊天區塊 =================
@st.fragment(run_every=timedelta(seconds=3))
def live_chat_feed(supabase, current_user):
    chat_container = st.container(height=500) 
    
    with chat_container:
        try:
            response = supabase.table("messages").select("*").order("created_at", desc=False).execute()
            messages = response.data
            
            if messages:
                latest_id = messages[-1]["id"]
                
                if "last_msg_id" not in st.session_state:
                    st.session_state.last_msg_id = latest_id
                elif latest_id > st.session_state.last_msg_id:
                    new_msgs = [m for m in messages if m["id"] > st.session_state.last_msg_id]
                    for nm in new_msgs:
                        if nm["user_name"] != current_user and current_user != "":
                            preview = nm["message"] if nm["message"] else "傳送了一張圖片 🖼️"
                            st.toast(f"**{nm['user_name']}**: {preview}", icon="💬")
                    
                    st.session_state.last_msg_id = latest_id

            for msg in messages:
                sender = msg["user_name"]
                text = msg["message"]
                img_url = msg["image_url"]
                
                try:
                    dt_utc = datetime.strptime(msg["created_at"][:19], "%Y-%m-%dT%H:%M:%S")
                    dt_local = dt_utc + timedelta(hours=8)
                    display_time = dt_local.strftime("%Y/%m/%d %H:%M") 
                except Exception:
                    display_time = msg["created_at"][:16].replace("T", " ")
                
                with st.chat_message("user" if sender == current_user and current_user else "assistant"):
                    st.markdown(
                        f"**{sender}** &nbsp;&nbsp;<span style='color: #888888; font-size: 0.8em;'>{display_time}</span>", 
                        unsafe_allow_html=True
                    )
                    
                    if text:
                        st.write(text)
                    if img_url:
                        st.image(img_url, width=400)
                        st.caption("👆 點擊圖片右上角的 **⛶ (全螢幕圖示)** 即可放大")
                        
        except Exception as e:
            st.warning("目前沒有訊息或讀取失敗。")

# ================= 主功能頁面 =================
def show_chat_room_page():
    st.title("💬 查詢不到訂單房間")
    
    # --- 🔒 新增：上線時間鎖定 ---
    # 取得當前伺服器時間並轉換為 UTC+8
    current_hk_time = datetime.utcnow() + timedelta(hours=8)
    launch_date = datetime(2026, 3, 1, 0, 0, 0) # 設定為 2026年3月1日 00:00:00 上線
    
    if current_hk_time < launch_date:
        st.warning(
            "🚧 **此功能尚未開放**\n\n"
            "「查詢不到訂單房間」目前正在進行最後的系統測試與優化。\n\n"
            "預計將於 **3 月 1 日** 正式上線開放使用，敬請期待！", 
            icon="⏳"
        )
        return # 提早中斷程式，不渲染下方的任何聊天室內容與輸入框
    # ------------------------------

    st.markdown("這裡是專屬的溝通頻道，遇到找不到訂單的狀況請在此回報。")
    
    st.info(
        "💡 **填寫範例**：\n\n"
        "**查詢不到訂單：H260225512645-H0956006**\n\n"
        "*(提示：您在下方只需輸入「訂單號碼」即可，發送時系統會自動幫您加上「查詢不到訂單：」的前綴)*", 
        icon="📌"
    )
    st.divider()

    try:
        supabase = init_supabase()
    except Exception as e:
        st.error(f"連線 Supabase 失敗: {e}")
        return

    col1, col2 = st.columns([1, 3])
    with col1:
        user_name = st.text_input("👤 您的名字", value="", placeholder="請輸入名字 (必填)", key="chat_user_name")

    st.subheader("聊天室訊息")
    live_chat_feed(supabase, user_name)

    prompt = st.chat_input(
        "請直接輸入訂單號碼 或 上傳圖片...", 
        accept_file=True, 
        file_type=["jpg", "jpeg", "png"]
    )

    if prompt:
        if not user_name.strip():
            st.toast("⚠️ 請先在左上方輸入您的名字！", icon="🚨")
            st.error("發送失敗：請先輸入您的「名字」後再試一次！")
        else:
            raw_text = prompt.text if hasattr(prompt, "text") else prompt.get("text", "")
            files = prompt.files if hasattr(prompt, "files") else prompt.get("files", [])
            
            msg_text = raw_text.strip()
            if msg_text and not msg_text.startswith("查詢不到訂單："):
                msg_text = f"查詢不到訂單：{msg_text}"
            elif not msg_text and files:
                msg_text = "查詢不到訂單：(僅附圖)"

            img_url = ""

            if files:
                uploaded_file = files[0]
                with st.spinner("圖片上傳中..."):
                    img_url = upload_image(supabase, uploaded_file.getvalue(), uploaded_file.name)
            
            if msg_text or img_url:
                save_message(supabase, user_name, msg_text, img_url)
                st.rerun()
