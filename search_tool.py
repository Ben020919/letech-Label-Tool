import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def get_hktvmall_product_image(product_name):
    # 1. 將商品名稱轉換為 URL 編碼
    encoded_name = urllib.parse.quote(product_name)
    # HKTVmall 的搜尋網址結構
    search_url = f"https://www.hktvmall.com/hktv/zh/search_a?keyword={encoded_name}"
    
    print(f"正在前往 HKTVmall 搜尋: {product_name}...")
    print(f"搜尋網址: {search_url}")

    # 2. 設定無頭瀏覽器 (Headless Browser) 以背景執行，不彈出視窗
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    # 加入 User-Agent 偽裝成真人，避免被網站阻擋
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 自動下載並設定 ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get(search_url)
        
        # 3. 等待網頁加載，最長等待 15 秒
        wait = WebDriverWait(driver, 15)
        
        # 尋找商品卡片中的圖片標籤 (根據 HKTVmall 目前的網頁結構)
        # CSS Selector '.product-brief img' 通常能抓到第一件商品的圖片
        print("等待圖片加載中...")
        img_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".product-brief img")))
        
        # 4. 獲取圖片連結
        img_url = img_element.get_attribute("src")
        
        if img_url:
            print("\n✅ 成功找到圖片！")
            print(f"圖片連結: {img_url}")
            return img_url
        else:
            print("\n❌ 找到元素，但沒有圖片連結。")
            return None
            
    except Exception as e:
        print(f"\n❌ 發生錯誤：可能找不到該商品，或 HKTVmall 更改了網頁設計。")
        print(f"錯誤詳情: {e}")
        return None
        
    finally:
        # 確保關閉瀏覽器釋放記憶體
        driver.quit()

# 測試代碼
if __name__ == "__main__":
    target_product = "日本 Asahi 一本滿足蛋白棒 - 士多啤梨味 39g"
    get_hktvmall_product_image(target_product)
