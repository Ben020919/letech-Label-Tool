# Lable.py (模組化版本 - 更新整合版)
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from io import BytesIO
import pandas as pd
import base64

# ================= 1. 精確設定 (固定參數) =================
LABEL_WIDTH = 70 * mm
LABEL_HEIGHT = 50 * mm
FIXED_BC_X = 2
FIXED_BC_Y = 47
FIXED_BC_FONT = 5
FIXED_DESC_X = 2
FIXED_DESC_Y = 46
FIXED_DESC_FONT = 5
FIXED_DESC_WIDTH = 59
FIXED_LINE1_X = 0
FIXED_LINE1_Y = 41
FIXED_LINE1_LEN = 70
FIXED_LINE1_THICK = 1.42
FIXED_NUTRI_X = 2
FIXED_NUTRI_Y = 40
FIXED_NUTRI_FS = 3.5
FIXED_COL1_W = 16
FIXED_COL2_W = 7
FIXED_NUTRI_GAP = 0.2
FIXED_VLINE_X = 26
FIXED_VLINE_Y_TOP = 41
FIXED_VLINE_Y_BOTTOM = 12
FIXED_VLINE_THICK = 1.42
FIXED_ING_X = 27
FIXED_ING_Y = 40
FIXED_ING_W = 41
FIXED_ING_H = 28
FIXED_ING_MAX_FS = 3.5
FIXED_ING_MIN_FS = 3.0
FIXED_LINE2_X = 0
FIXED_LINE2_Y = 12
FIXED_LINE2_LEN = 70
FIXED_LINE2_THICK = 1.42
FIXED_MFR_X = 2
FIXED_MFR_Y = 10
FIXED_MFR_W = 35
FIXED_MFR_FS = 4.76
FIXED_BB_X = 49
FIXED_BB_Y = 10
FIXED_BB_W = 26
FIXED_BB_FS = 4.50

# ================= 2. 畫布生成函數 (單頁) =================
def create_single_label_canvas(c, barcode_text, desc_text, nutri_dict, ing_text, mfr_text, date_format, font_name="Helvetica"):
    # --- 1. Barcode ---
    if barcode_text:
        bc_font = "Helvetica-Bold" if font_name == "Helvetica" else font_name
        c.setFont(bc_font, FIXED_BC_FONT)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(FIXED_BC_X * mm, FIXED_BC_Y * mm, barcode_text)
    
    # --- 2. Description ---
    if desc_text:
        styles = getSampleStyleSheet()
        my_style = ParagraphStyle('MyDesc', parent=styles['Normal'], fontSize=FIXED_DESC_FONT, leading=FIXED_DESC_FONT*1.2, fontName=font_name)
        p = Paragraph(f"{desc_text}", my_style) 
        p.wrapOn(c, FIXED_DESC_WIDTH * mm, LABEL_HEIGHT) 
        w, h = p.wrap(FIXED_DESC_WIDTH * mm, LABEL_HEIGHT)
        p.drawOn(c, FIXED_DESC_X * mm, FIXED_DESC_Y * mm - h)

    # --- 3. Line 1 ---
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(FIXED_LINE1_THICK)
    c.setLineCap(0) 
    c.line(FIXED_LINE1_X * mm, FIXED_LINE1_Y * mm, (FIXED_LINE1_X + FIXED_LINE1_LEN) * mm, FIXED_LINE1_Y * mm)

    # --- 4. Nutrition ---
    if nutri_dict:
        styles = getSampleStyleSheet()
        style_all = ParagraphStyle('NutriAll', parent=styles['Normal'], fontSize=FIXED_NUTRI_FS, leading=FIXED_NUTRI_FS+1, fontName=font_name)
        
        def v(key):
            val = nutri_dict.get(key)
            if pd.isna(val) or str(val).lower() == 'nan': return "0"
            return str(val).strip()

        data = [
            [Paragraph("Nutrition Information", style_all), ""],
            [Paragraph("Serving Size:", style_all),    Paragraph(v('Serving_Size'), style_all)],
            [Paragraph("Energy:", style_all),          Paragraph(v('Energy'), style_all)],
            [Paragraph("Protein:", style_all),         Paragraph(v('Protein'), style_all)],
            [Paragraph("Total fat:", style_all),       Paragraph(v('Total_Fat'), style_all)],
            [Paragraph("- Saturated fat:", style_all), Paragraph(v('Sat_Fat'), style_all)],
            [Paragraph("- Trans fat:", style_all),     Paragraph(v('Trans_Fat'), style_all)],
            [Paragraph("Carbohydrates:", style_all),   Paragraph(v('Carb'), style_all)],
            [Paragraph("- Sugars:", style_all),        Paragraph(v('Sugar'), style_all)],
            [Paragraph("Sodium:", style_all),          Paragraph(v('Sodium'), style_all)],
            [Paragraph("Net Content:", style_all),     Paragraph(v('Net_Content'), style_all)],
            [Paragraph("Country Of Origin:", style_all), Paragraph(v('Country_Of_Origin'), style_all)],
        ]
        t = Table(data, colWidths=[FIXED_COL1_W * mm, FIXED_COL2_W * mm])
        t.setStyle(TableStyle([
            ('SPAN', (0,0), (1,0)), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), FIXED_NUTRI_GAP), 
            ('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('INDENT', (0,5), (0,6), 3), ('INDENT', (0,8), (0,8), 3),
        ]))
        w_table, h_table = t.wrap((FIXED_COL1_W + FIXED_COL2_W) * mm, LABEL_HEIGHT)
        t.drawOn(c, FIXED_NUTRI_X * mm, FIXED_NUTRI_Y * mm - h_table)

    # --- 5. Vertical Line ---
    c.setLineWidth(FIXED_VLINE_THICK)
    c.line(FIXED_VLINE_X * mm, FIXED_VLINE_Y_TOP * mm, FIXED_VLINE_X * mm, FIXED_VLINE_Y_BOTTOM * mm)

    # --- 6. Line 2 ---
    c.setLineWidth(FIXED_LINE2_THICK)
    c.line(FIXED_LINE2_X * mm, FIXED_LINE2_Y * mm, (FIXED_LINE2_X + FIXED_LINE2_LEN) * mm, FIXED_LINE2_Y * mm)

    # --- 7. Ingredients ---
    if ing_text:
        styles = getSampleStyleSheet()
        final_fs = FIXED_ING_MAX_FS
        while final_fs >= FIXED_ING_MIN_FS:
            current_style = ParagraphStyle('Ing', parent=styles['Normal'], fontSize=final_fs, leading=final_fs*1.1, fontName=font_name)
            p_ing = Paragraph(f" {ing_text}", current_style)
            avail_w = FIXED_ING_W * mm
            avail_h = FIXED_ING_H * mm
            actual_w, actual_h = p_ing.wrap(avail_w, avail_h)
            if actual_h <= avail_h:
                p_ing.drawOn(c, FIXED_ING_X * mm, FIXED_ING_Y * mm - actual_h)
                break
            final_fs -= 0.2
        if final_fs < FIXED_ING_MIN_FS:
             current_style = ParagraphStyle('Ing', parent=styles['Normal'], fontSize=FIXED_ING_MIN_FS, leading=FIXED_ING_MIN_FS*1.1, fontName=font_name)
             p_ing = Paragraph(f"Ingredients: {ing_text}", current_style)
             p_ing.wrap(FIXED_ING_W * mm, FIXED_ING_H * mm)
             w, h = p_ing.wrap(FIXED_ING_W * mm, FIXED_ING_H * mm)
             p_ing.drawOn(c, FIXED_ING_X * mm, FIXED_ING_Y * mm - h)

    # --- 8. Manufacturer ---
    if mfr_text:
        styles = getSampleStyleSheet()
        mfr_style = ParagraphStyle('Mfr', parent=styles['Normal'], fontSize=FIXED_MFR_FS, leading=FIXED_MFR_FS*1.2, fontName=font_name)
        prefix = "Manufacturer: "
        if "Manufacturer" not in str(mfr_text): final_text = prefix + str(mfr_text)
        else: final_text = str(mfr_text)
        p_mfr = Paragraph(final_text, mfr_style)
        p_mfr.wrapOn(c, FIXED_MFR_W * mm, LABEL_HEIGHT) 
        w, h = p_mfr.wrap(FIXED_MFR_W * mm, LABEL_HEIGHT)
        p_mfr.drawOn(c, FIXED_MFR_X * mm, FIXED_MFR_Y * mm - h)

    # --- 9. Best Before ---
    styles = getSampleStyleSheet()
    bb_style = ParagraphStyle('BB', parent=styles['Normal'], fontSize=FIXED_BB_FS, leading=FIXED_BB_FS*1.2, fontName=font_name)
    df_str = str(date_format) if date_format else "YY-MM-DD"
    bb_content = f"Best before({df_str}):<br/>Show on package(見包裝)<br/>此日期前最佳({df_str})"
    p_bb = Paragraph(bb_content, bb_style)
    p_bb.wrapOn(c, FIXED_BB_W * mm, LABEL_HEIGHT)
    w, h = p_bb.wrap(FIXED_BB_W * mm, LABEL_HEIGHT)
    p_bb.drawOn(c, FIXED_BB_X * mm, FIXED_BB_Y * mm - h)

# ================= 3. 新增：匯出 HTML 用於列印 =================
def generate_food_label_html(item_data, master_df_row, qty):
    """
    產生包含 PDF Base64 內容的 HTML，透過 iframe 直接調用瀏覽器列印
    """
    buffer = BytesIO()
    
    # 建立 ReportLab Canvas
    c = canvas.Canvas(buffer, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))
    
    # 準備資料
    barcode_text = item_data.get('Barcode', '')
    desc_text = item_data.get('商品名稱', '')
    date_format = "YY-MM-DD" # 若有特定欄位可替換

    # 從 master_df 讀取營養標籤資料
    nutri_dict = {}
    ing_text = ""
    mfr_text = ""

    if master_df_row is not None and not master_df_row.empty:
        row = master_df_row.iloc[0]
        nutri_dict = {
            'Serving_Size': row.get('Serving_Size', ''),
            'Energy': row.get('Energy', ''),
            'Protein': row.get('Protein', ''),
            'Total_Fat': row.get('Total_Fat', ''),
            'Sat_Fat': row.get('Sat_Fat', ''),
            'Trans_Fat': row.get('Trans_Fat', ''),
            'Carb': row.get('Carb', ''),
            'Sugar': row.get('Sugar', ''),
            'Sodium': row.get('Sodium', ''),
            'Net_Content': row.get('Net_Content', ''),
            'Country_Of_Origin': row.get('Country_Of_Origin', '')
        }
        ing_text = row.get('Ingredients', '')
        mfr_text = f"{row.get('Madeby_Prefix', '')} {row.get('Madeby', '')}".strip()

    # 根據數量生成多頁
    for _ in range(qty):
        create_single_label_canvas(
            c=c, 
            barcode_text=barcode_text, 
            desc_text=desc_text, 
            nutri_dict=nutri_dict, 
            ing_text=ing_text, 
            mfr_text=mfr_text, 
            date_format=date_format
        )
        c.showPage()
    
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()

    # 轉成 Base64 HTML 供列印使用
    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    
    html = f"""
    <html>
        <head>
            <style>
                body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; }}
            </style>
        </head>
        <body>
            <iframe id="pdfFrame" src="data:application/pdf;base64,{b64_pdf}" style="width:100%; height:100%; border:none;"></iframe>
            <script>
                window.onload = function() {{
                    var iframe = document.getElementById('pdfFrame');
                    iframe.contentWindow.focus();
                    iframe.contentWindow.print();
                    // 延遲關閉視窗，確保列印對話框彈出
                    setTimeout(function() {{ window.close(); }}, 1000);
                }};
            </script>
        </body>
    </html>
    """
    return html
