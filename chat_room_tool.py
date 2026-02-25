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
    
    # --- 新增：頂部範例展示 ---
    st.info(
        "💡 **填寫範例**：\n\n"
        "**查詢不到訂單：H260225512645-H0956006**\n\n"
        "*(提示：您在下方只需輸入「訂單號碼」即可，系統發送時會自動幫您加上「查詢不到訂單：」的前綴)*", 
        icon="📌"
    )
    
    st.divider()

    try:
        supabase = init_supabase()
    except Exception as e:
        st.error(f"連線 Supabase 失敗: {e}")
        return

    # 防呆優化：必須填寫名字
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
                        st.image(img_url, width=400)
                        st.caption("👆 點擊圖片右上角的 **⛶ (全螢幕圖示)** 即可放大")
                        
        except Exception as e:
            st.warning("目前沒有訊息或讀取失敗。")

    # ================= 整合版輸入框 =================
    # 修改了輸入框的預設提示文字
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
            
            # --- 核心邏輯：自動加上 7 個字的前綴 ---
            msg_text = raw_text.strip()
            
            # 如果員工有打字，且沒有自己打上「查詢不到訂單：」，我們就幫他加
            if msg_text and not msg_text.startswith("查詢不到訂單："):
                msg_text = f"查詢不到訂單：{msg_text}"
            
            # 如果員工連字都沒打，只有上傳圖片，自動補上這句
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
