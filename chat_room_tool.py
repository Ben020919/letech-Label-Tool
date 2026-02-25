import streamlit as st
from supabase import create_client, Client
import time

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

    # 使用者設定區
    col1, col2 = st.columns([1, 3])
    with col1:
        user_name = st.text_input("👤 您的名字", value="匿名員工", key="chat_user_name")

    # 顯示聊天室歷史訊息
    st.subheader("聊天室訊息")
    chat_container = st.container(height=500) # 固定高度，讓畫面不會無限延伸
    
    with chat_container:
        try:
            response = supabase.table("messages").select("*").order("created_at", desc=False).execute()
            messages = response.data
            
            for msg in messages:
                sender = msg["user_name"]
                text = msg["message"]
                img_url = msg["image_url"]
                display_time = msg["created_at"][:19].replace("T", " ")
                
                with st.chat_message("user" if sender == user_name else "assistant"):
                    st.markdown(f"**{sender}** *( {display_time} )*")
                    if text:
                        st.write(text)
                    if img_url:
                        # 將原本的 st.image 替換成 HTML 連結，點擊即可在新分頁開啟原圖
                        st.markdown(
                            f'<a href="{img_url}" target="_blank">'
                            f'<img src="{img_url}" style="max-width: 100%; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">'
                            f'</a>', 
                            unsafe_allow_html=True
                        )
                        st.caption("🔍 點擊圖片可查看 / 放大原圖")
                        
        except Exception as e:
            st.warning("目前沒有訊息或讀取失敗。")

    # ================= 整合版輸入框 (WhatsApp 風格) =================
    # 加上 accept_file=True 即可開啟附件按鈕
    prompt = st.chat_input(
        "輸入訊息或上傳圖片...", 
        accept_file=True, 
        file_type=["jpg", "jpeg", "png"]
    )

    if prompt:
        # Streamlit 1.43+ 的 prompt 包含了文字與檔案資訊
        msg_text = prompt.text if hasattr(prompt, "text") else prompt.get("text", "")
        files = prompt.files if hasattr(prompt, "files") else prompt.get("files", [])
        
        img_url = ""

        # 如果使用者有夾帶圖片檔案
        if files:
            uploaded_file = files[0]
            with st.spinner("圖片上傳中..."):
                img_url = upload_image(supabase, uploaded_file.getvalue(), uploaded_file.name)
        
        # 只要有輸入文字或上傳圖片，就存入資料庫並重新整理
        if msg_text or img_url:
            save_message(supabase, user_name, msg_text, img_url)
            st.rerun()
