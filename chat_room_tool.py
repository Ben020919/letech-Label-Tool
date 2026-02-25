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

# ================= 主功能 =================
def show_chat_room_page():
    st.title("💬 查詢不到訂單房間")
    st.markdown("這裡是專屬的溝通頻道，遇到找不到訂單的狀況請在此回報。")
    st.divider()

    try:
        supabase = init_supabase()
    except Exception as e:
        st.error(f"連線 Supabase 失敗: {e}")
        return

    # --- 防呆優化：必須填寫名字 ---
    col1, col2 = st.columns([1, 3])
    with col1:
        user_name = st.text_input("👤 您的名字", value="", placeholder="請輸入名字 (必填)", key="chat_user_name")

    # 顯示聊天室歷史訊息
    st.subheader("聊天室訊息")
    chat_container = st.container(height=500) 
    
    with chat_container:
        try:
            response = supabase.table("messages").select("*").order("created_at", desc=False).execute()
            messages = response.data
            
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
                
                with st.chat_message("user" if sender == user_name and user_name else "assistant"):
                    st.markdown(
                        f"**{sender}** &nbsp;&nbsp;<span style='color: #888888; font-size: 0.8em;'>{display_time}</span>", 
                        unsafe_allow_html=True
                    )
                    
                    if text:
                        st.write(text)
                    if img_url:
                        # 電腦版限制 400px 避免過大，右上角依然可全螢幕放大
                        st.image(img_url, width=400)
                        st.caption("👆 點擊圖片右上角的 **⛶ (全螢幕圖示)** 即可放大")
                        
        except Exception as e:
            st.warning("目前沒有訊息或讀取失敗。")

    # ================= 整合版輸入框 =================
    prompt = st.chat_input(
        "輸入訊息或上傳圖片...", 
        accept_file=True, 
        file_type=["jpg", "jpeg", "png"]
    )

    if prompt:
        # 檢查是否輸入名字
        if not user_name.strip():
            st.toast("⚠️ 請先在左上方輸入您的名字！", icon="🚨")
            st.error("發送失敗：請先輸入您的「名字」後再試一次！")
        else:
            msg_text = prompt.text if hasattr(prompt, "text") else prompt.get("text", "")
            files = prompt.files if hasattr(prompt, "files") else prompt.get("files", [])
            
            img_url = ""

            if files:
                uploaded_file = files[0]
                with st.spinner("圖片上傳中..."):
                    img_url = upload_image(supabase, uploaded_file.getvalue(), uploaded_file.name)
            
            if msg_text or img_url:
                save_message(supabase, user_name, msg_text, img_url)
                # 恢復為 st.rerun()，發送完畢後立刻刷新畫面顯示新訊息，不卡頓！
                st.rerun()
