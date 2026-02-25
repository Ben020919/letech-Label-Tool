import streamlit as st
from supabase import create_client, Client
import time

# 初始化 Supabase 客戶端 (使用快取避免重複連線)
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def save_message(supabase, user, msg, img_url=""):
    data = {
        "user_name": user,
        "message": msg,
        "image_url": img_url
    }
    supabase.table("messages").insert(data).execute()

def upload_image(supabase, file_bytes, file_name):
    unique_filename = f"{int(time.time())}_{file_name}"
    supabase.storage.from_("chat_images").upload(
        file=file_bytes,
        path=unique_filename,
        file_options={"content-type": "image/jpeg"}
    )
    public_url = supabase.storage.from_("chat_images").get_public_url(unique_filename)
    return public_url

# ================= 主功能函數 =================
def show_chat_room_page():
    st.title("💬 查詢不到訂單房間")
    st.markdown("這裡是專屬的溝通頻道，遇到找不到訂單的狀況請在此回報。")
    st.divider()

    try:
        supabase = init_supabase()
    except Exception as e:
        st.error(f"連線 Supabase 失敗，請檢查 secrets.toml 設定: {e}")
        return

    # 1. 使用者設定區
    col1, col2 = st.columns([1, 3])
    with col1:
        user_name = st.text_input("👤 您的名字", value="匿名員工", key="chat_user_name")

    # 2. 顯示聊天歷史訊息
    st.subheader("聊天室訊息")
    
    # 建立一個固定高度的容器來放訊息 (讓版面更好看)
    chat_container = st.container(height=500)
    
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
                        st.image(img_url, width=300)
        except Exception as e:
            st.warning("目前沒有訊息或讀取失敗。")

    st.divider()

    # 3. 訊息輸入區
    st.subheader("📎 傳送訊息或圖片")
    tab1, tab2, tab3 = st.tabs(["✍️ 發送文字", "📁 上傳圖片", "📷 拍照上傳"])

    with tab1:
        text_input = st.chat_input("輸入訊息...")
        if text_input:
            save_message(supabase, user_name, text_input)
            st.rerun()

    with tab2:
        uploaded_file = st.file_uploader("選擇圖片", type=['png', 'jpg', 'jpeg'], key="chat_uploader")
        img_text = st.text_input("圖片補充說明", key="upload_text")
        if st.button("送出圖片", key="btn_upload"):
            if uploaded_file is not None:
                with st.spinner("圖片上傳中..."):
                    img_url = upload_image(supabase, uploaded_file.getvalue(), uploaded_file.name)
                    save_message(supabase, user_name, img_text, img_url)
                st.rerun()
            else:
                st.warning("請先選擇一張圖片！")

    with tab3:
        camera_photo = st.camera_input("拍攝照片", key="chat_camera")
        cam_text = st.text_input("照片補充說明", key="cam_text")
        if st.button("送出照片", key="btn_camera"):
            if camera_photo is not None:
                with st.spinner("照片上傳中..."):
                    img_url = upload_image(supabase, camera_photo.getvalue(), "camera_capture.jpg")
                    save_message(supabase, user_name, cam_text, img_url)
                st.rerun()
            else:
                st.warning("請先拍攝照片！")
