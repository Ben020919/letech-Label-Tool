import streamlit as st
from pypdf import PdfReader
import re
import io
import base64
from barcode import Code128
from barcode.writer import ImageWriter
import streamlit.components.v1 as components

# ================= 0. 固定樣式參數 (已鎖定) =================
STYLE_CONFIG = {
    "name_font_size": "13px",
    "name_line_height": "1.40",
    "barcode_height": "25mm",
    "barcode_num_size": "17px",
    "margin_top": "4mm"
}

# ================= 1. 核心邏輯: PDF 解析 =================

def extract_repack_items(uploaded_file):
    """
    解析 PDF，只回傳需要 Repack 的項目 (Barcode 含英文 或 與 ProductNo 相同)
    """
    reader = PdfReader(uploaded_file)
    repack_list = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text: continue

        lines = [line.strip() for line in text.split('\n') if line.strip()]
        lines = [l for l in lines if not l.startswith("[Image")]
        if not lines: continue

        p_no = lines[0]
        qty = 0
        qty_index = -1
        
        # 找數量
        for idx, line in enumerate(lines):
            if re.search(r'\d+\.0000', line):
                qty_match = re.search(r'(\d+)\.0000', line)
                if qty_match:
                    qty = int(qty_match.group(1))
                    qty_index = idx
                break
        
        # 找 Barcode
        barcode_clean = ""
        for line in lines:
            if "*" in line:
                match = re.search(r'\*\s*([A-Za-z0-9\s-]*)\s*\*|^\*([A-Za-z0-9-]*)\*$', line)
                if match:
                    barcode_clean = (match.group(1) or match.group(2) or "").replace(" ", "")
                    break
        
        # 找名稱
        p_name = ""
        if qty_index > 1:
            p_name = " ".join(lines[1:qty_index])

        # 判斷 Repack 條件
        is_repack = False
        if barcode_clean and barcode_clean != "":
            # 條件A: Barcode 含英文字母
            if re.search(r'[A-Za-z]', barcode_clean):
                is_repack = True
            # 條件B: Barcode 等於 Product No
            elif barcode_clean.lower() == p_no.lower():
                is_repack = True

        if is_repack and qty > 0:
            repack_list.append({
                "id": f"{p_no}_{i}",
                "Product No": p_no,
                "Product Name": p_name,
                "Qty": qty,
                "Barcode": barcode_clean
            })

    return repack_list

# ================= 2. 核心邏輯: 標籤生成 (固定樣式) =================

def generate_barcode_b64(code_text):
    if not code_text: return None
    rv = io.BytesIO()
    Code128(code_text, writer=ImageWriter()).write(rv, options={"write_text": False, "module_height": 10.0, "quiet_zone": 1.0})
    return f"data:image/png;base64,{base64.b64encode(rv.getvalue()).decode('utf-8')}"

def create_repack_lable_html(p_name, p_barcode_val, qty):
    """生成符合 70x50mm 規格的打印 HTML"""
    barcode_img_src = generate_barcode_b64(p_barcode_val)
    s = STYLE_CONFIG # 讀取固定參數
    
    single_lable = f"""
    <div class="lable-container">
        <img src="{barcode_img_src}" style="height: {s['barcode_height']}; width: 90%; object-fit: contain;">
        
        <div style="
            font-family: monospace; 
            font-weight: bold; 
            font-size: {s['barcode_num_size']}; 
            margin-top: -2px;
            letter-spacing: 1px;
        ">
            {p_barcode_val}
        </div>

        <div style="
            width: 90%; 
            text-align: center; 
            font-weight: bold; 
            font-family: Arial, sans-serif;
            font-size: {s['name_font_size']}; 
            line-height: {s['name_line_height']};
            margin-top: 5px;
            word-wrap: break-word;
            max-height: 20mm;
            overflow: hidden;
        ">
            {p_name}
        </div>
    </div>
    """

    full_html = f"""
    <html>
    <head>
    <style>
        @page {{ size: 70mm 50mm; margin: 0; }}
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        .lable-container {{ 
            width: 70mm; 
            height: 50mm; 
            padding-top: {s['margin_top']}; 
            box-sizing: border-box; 
            page-break-after: always; 
            display: flex; 
            flex-direction: column; 
            align-items: center; 
            justify-content: flex-start;
            overflow: hidden;
        }}
    </style>
    </head>
    <body>
        {single_lable * qty}
    </body>
    </html>
    """
    return full_html

def js_instant_print(full_html_content):
    b64_html = base64.b64encode(full_html_content.encode('utf-8')).decode('utf-8')
    js_code = f"""
    <script>
        (function() {{
            const b64 = "{b64_html}";
            const htmlContent = decodeURIComponent(escape(window.atob(b64)));
            const win = window.open('', '_blank', 'width=400,height=400');
            if (win) {{
                win.document.write(htmlContent); win.document.close();
                win.onload = function() {{ 
                    win.focus(); 
                    win.onafterprint = function() {{ win.close(); }}; 
                    win.print(); 
                    win.onfocus = function() {{ setTimeout(()=>{{ win.close(); }}, 500); }}; 
                }};
            }}
        }})();
    </script>
    """
    components.html(js_code, height=0)

# ================= 3. 主頁面 =================

def show_repack_page():
    st.set_page_config(page_title="Repack Lable Tool", layout="centered")
    st.markdown("### 🏷️ Repack Lable Generator")

    uploaded_file = st.file_uploader("Upload PDF File", type=["pdf"])

    if uploaded_file:
        # 1. 獲取資料
        items = extract_repack_items(uploaded_file)
        
        if not items:
            st.success("✅ PDF 解析完成：沒有發現需要 Repack 的項目。")
        else:
            st.warning(f"⚠️ 偵測到 {len(items)} 個項目需要製作 Repack Lable。")
            
            st.markdown("---")
            
            # 2. 建立選單 (顯示 ProductNo - 名稱)
            options = {f"{item['Product No']} | {item['Barcode']}": item for item in items}
            selected_key = st.selectbox("選擇要打印的產品:", list(options.keys()))
            
            if selected_key:
                target_item = options[selected_key]
                
                # 簡單顯示當前選中的資訊
                st.info(f"📦 **{target_item['Product Name']}**\n\n數量: {target_item['Qty']}")
                
                # 3. 打印按鈕
                if st.button("🖨️ 打印標籤 (Print Lable)", use_container_width=True, type="primary"):
                    html = create_repack_lable_html(
                        target_item['Product Name'], 
                        target_item['Barcode'], 
                        target_item['Qty']
                    )
                    js_instant_print(html)

if __name__ == "__main__":
    show_repack_page()
