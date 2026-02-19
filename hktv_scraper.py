from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, time as dt_time
import json
import time
import os
import re
from dotenv import load_dotenv

def extract_total_count(text):
    if not text: return "0"
    numbers = re.findall(r'\d+', text)
    return numbers[-1] if numbers else "0"

def scrape_single_date(page, date_str):
    base_url = (
        f"https://merchant.shoalter.com/zh/order-management/orders/toship"
        f"?bu=HKTV&deliveryType=STANDARD_DELIVERY&productReadyMethod=STANDARD_DELIVERY_ALL"
        f"&searchType=ORDER_ID&storefrontCodes=H0956004%2CH0956006%2CH0956007%2CH0956008%2CH0956010%2CH0956012"
        f"&dateType=PICK_UP_DATE&startDate={date_str}&endDate={date_str}"
        f"&pageSize=20&pageNumber=1&sortColumn=orderDate&waybillStatuses="
    )
    statuses = [("CONFIRMED", "已建立"), ("ACKNOWLEDGED", "已確認"), ("PACKED", "已包裝"), ("PICKED", "已出貨")]
    date_data = {"date": date_str}

    page.goto(base_url + "CONFIRMED") 
    page.wait_for_timeout(2500) 
    page.locator('button:has-text("商戶8小時送貨")').click(force=True)
    page.wait_for_timeout(1000) 

    for status_val, status_name in statuses:
        page.locator('div.ant-select-selector:has-text("運單狀態")').click(force=True)
        page.wait_for_timeout(400) 
        page.locator('button[data-testid="清除全部"]').click(force=True)
        page.wait_for_timeout(300) 
        
        checkbox = page.locator(f'input[value="{status_val}"]')
        try:
            if not checkbox.is_checked(): checkbox.click(force=True)
        except Exception:
            checkbox.check(force=True)
            
        page.wait_for_timeout(200)
        page.locator('button[data-testid="套用"]').click(force=True)
        page.wait_for_timeout(1500) 
        
        try:
            result_text = page.locator('span:has-text("結果")').last.inner_text(timeout=3000)
            date_data[status_val] = extract_total_count(result_text)
        except Exception:
            date_data[status_val] = "0"
            
    return date_data

def scrape_hktvmall(username, password):
    now = datetime.now()
    current_time = now.time()
    
    today_str = now.strftime("%Y-%m-%d")
    tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    
    time_0930 = dt_time(9, 30)
    time_1301 = dt_time(13, 1)
    time_1305 = dt_time(13, 5)
    time_2201 = dt_time(22, 1)
    time_2205 = dt_time(22, 5)

    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'order_data.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            results_data = json.load(f)
    except Exception:
        results_data = {"today": {}, "tomorrow": {}}

    scrape_today = False
    scrape_tomorrow = False
    is_sleep = False

    if time_0930 <= current_time <= time_1301:
        scrape_today = True
        scrape_tomorrow = True
    elif time_1305 <= current_time <= time_2201:
        scrape_today = False
        scrape_tomorrow = True
    elif current_time >= time_2205 or current_time < time_0930:
        is_sleep = True
    else:
        if time_1301 < current_time < time_1305:
            scrape_tomorrow = True 
        elif time_2201 < current_time < time_2205:
            is_sleep = True 

    if is_sleep:
        print(f"\n[{now.strftime('%H:%M:%S')}] 🌙 目前為休息時間 (22:05 ~ 09:30)，機器人睡覺中 ZZz...")
        results_data["status_msg"] = "🌙 目前為休息時間，停止抓取資料"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, ensure_ascii=False, indent=4)
        return

    results_data["status_msg"] = "⚡ 機器人努力抓取中..."

    if scrape_today or scrape_tomorrow:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True) 
            context = browser.new_context()
            page = context.new_page()
            page.route("**/*.{png,jpg,jpeg,gif,svg}", lambda route: route.abort())

            print(f"\n🤖 [爬蟲] 登入 HKTVmall (時間: {now.strftime('%H:%M:%S')})")
            page.goto("https://merchant.shoalter.com/login") 
            page.locator('#account').fill(username)
            page.locator('#password').fill(password)
            page.locator('button[data-testid="繼續"]').click()
            page.wait_for_timeout(5000) 

            if scrape_today:
                print(f"🤖 [爬蟲] 正在抓取 【今日訂單】 ({today_str})...")
                results_data["today"] = scrape_single_date(page, today_str)
            else:
                print(f"⏭️ [爬蟲] 超過 13:01，【今日訂單】停止更新，保留最後數據不動。")

            if scrape_tomorrow:
                print(f"🤖 [爬蟲] 正在抓取 【明日訂單】 ({tomorrow_str})...")
                results_data["tomorrow"] = scrape_single_date(page, tomorrow_str)
            else:
                print(f"⏭️ [爬蟲] 超過 22:01，【明日訂單】停止更新，保留最後數據不動。")

            results_data["last_updated"] = now.strftime("%Y-%m-%d %H:%M:%S")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, ensure_ascii=False, indent=4)
                
            print(f"🎉 [爬蟲] 抓取完成！\n")
            browser.close()

def run_scraper_loop():
    load_dotenv()
    MY_USERNAME = os.getenv("HKTV_USERNAME")
    MY_PASSWORD = os.getenv("HKTV_PASSWORD")
    
    if not MY_USERNAME or not MY_PASSWORD:
        print("❌ [系統嚴重錯誤] 找不到帳號或密碼！請確認 .env 檔案是否設定正確。")
        return
    
    while True:
        try:
            scrape_hktvmall(MY_USERNAME, MY_PASSWORD)
        except Exception as e:
            print(f"❌ [爬蟲] 發生錯誤: {e}")
            
        time.sleep(240) # 每 4 分鐘抓取一次