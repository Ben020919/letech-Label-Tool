# Cautions.py - 專門負責警告標籤的 PDF 繪製
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_CENTER

# 1. 尺寸設定 (70x50mm)
LABEL_WIDTH = 70 * mm
LABEL_HEIGHT = 50 * mm
MARGIN = 3 * mm

def draw_caution_label(c, caution_text, font_name="Helvetica"):
    """
    繪製 70x50mm 的警告標籤 (對應您設計的樣式)
    特色：黑色粗框、文字垂直水平居中、超粗體
    """
    
    # --- 1. 畫外框 (對應 border: 3px solid black) ---
    c.setLineWidth(1.5)             # PDF 線條寬度 (約等於螢幕的 3-4px)
    c.setStrokeColorRGB(0, 0, 0)    # 黑色
    # 畫一個矩形框 (預留邊距)
    c.rect(1.5*mm, 1.5*mm, LABEL_WIDTH - 3*mm, LABEL_HEIGHT - 3*mm) 
    
    # --- 2. 準備文字內容 ---
    if not caution_text:
        caution_text = ""
    # 將換行符號 \n 轉換為 PDF 能懂的 <br/>
    formatted_text = str(caution_text).replace('\n', '<br/>')
    
    # --- 3. 設定文字樣式 (對應 font-weight: 900, text-align: center) ---
    styles = getSampleStyleSheet()
    caution_style = ParagraphStyle(
        'CautionStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=18,          # 字體大小 (對應您預覽的 27px，PDF 中約 18-20pt)
        leading=22,           # 行距
        alignment=TA_CENTER,  # 水平居中
        textColor='black',
        wordWrap='CJK'        # 支援中文換行
    )
    
    # 建立段落物件
    p = Paragraph(formatted_text, caution_style)
    
    # --- 4. 計算位置 (Flex align-items: center 的 PDF 實作) ---
    # 計算可用空間 (總寬高 - 邊距)
    avail_width = LABEL_WIDTH - (MARGIN * 2)
    avail_height = LABEL_HEIGHT - (MARGIN * 2)
    
    # 計算文字實際佔用的寬高
    w, h = p.wrap(avail_width, avail_height)
    
    # 計算起始座標 (讓文字區塊在框內垂直居中)
    x = MARGIN
    y = (LABEL_HEIGHT - h) / 2
    
    # --- 5. 畫出文字 (含 Fake Bold 模擬超粗體) ---
    c.saveState()
    # 透過描邊來模擬 font-weight: 900
    c.setLineWidth(0.5)     # 描邊寬度 (越寬越粗)
    c.setTextRenderMode(2)  # 2 = 填色 + 描邊
    c.setStrokeColorRGB(0, 0, 0)
    c.setFillColorRGB(0, 0, 0)
    
    p.drawOn(c, x, y)
    
    c.restoreState()