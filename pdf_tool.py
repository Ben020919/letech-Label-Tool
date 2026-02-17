import streamlit as st
from pypdf import PdfReader, PdfWriter
import io
import pandas as pd

def show_pdf_page():
    # ================= LOGO / BRANDING AREA =================
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

    st.markdown("### 🛍️ Anymall 3PL System")

    uploaded_file = st.file_uploader("Please Upload PDF File", type=["pdf"])

    if uploaded_file is not None:
        try:
            reader = PdfReader(uploaded_file)
            writer = PdfWriter()
            
            total_pages = len(reader.pages)
            kept_pages_count = 0
            removed_pages_indices = []
            product_no_tracker = {}
            
            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, page in enumerate(reader.pages):
                current_page_num = i + 1
                text = page.extract_text()
                images = page.images
                
                # 判斷空白頁
                has_content = (text and text.strip()) or len(images) > 0
                
                if has_content:
                    writer.add_page(page)
                    kept_pages_count += 1
                    
                    # 抓取頁首 Product No
                    if text:
                        lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
                        if lines:
                            p_no = lines[0]
                            if p_no not in product_no_tracker:
                                product_no_tracker[p_no] = []
                            product_no_tracker[p_no].append(current_page_num)
                else:
                    removed_pages_indices.append(current_page_num)
                
                progress_bar.progress(current_page_num / total_pages)
                status_text.text(f"Scanning page {current_page_num} / {total_pages}...")

            status_text.empty()
            progress_bar.empty()

            st.divider()
            
            col1, col2 = st.columns(2)
            
            # 生成處理後的 PDF bytes
            output_buffer = io.BytesIO()
            writer.write(output_buffer)
            pdf_bytes = output_buffer.getvalue()
            cleaned_filename = f"cleaned_{uploaded_file.name}"

            with col1:
                st.subheader("Results")
                st.write(f"Original: **{total_pages}** Pages , Reserve: **{kept_pages_count}** Pages")
                
                # 下載按鈕
                st.download_button(
                    label="Download PDF",
                    data=pdf_bytes,
                    file_name=cleaned_filename,
                    mime="application/pdf",
                    type="primary"
                )
                
                st.write("") # Spacer

                # === 新增功能：傳送按鈕 ===
                if st.button("Transfer to Excel Tool", type="secondary"):
                    # 將檔案存入 Session State 作為「橋接」
                    st.session_state['bridge_pdf_data'] = pdf_bytes
                    st.session_state['bridge_pdf_name'] = cleaned_filename
                    st.success("✅ File Transferred! Please switch to 'Excel Tool' from the menu.")

            with col2:
                st.subheader("Duplicate Detection")
                duplicates = {k: v for k, v in product_no_tracker.items() if len(v) > 1}
                
                if duplicates:
                    st.error(f"Found {len(duplicates)} Duplicates!")
                    data_items = []
                    for p_no, pages in duplicates.items():
                        data_items.append({
                            "SKU No.": p_no,
                            "Repeat Times": len(pages),
                            "Pages Number": str(pages)
                        })
                    st.dataframe(pd.DataFrame(data_items), use_container_width=True)
                else:
                    st.success("No duplicates found.")

        except Exception as e:
            st.error(f"Error processing PDF: {e}")
