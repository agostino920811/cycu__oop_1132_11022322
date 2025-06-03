import requests
from bs4 import BeautifulSoup
import re
import csv # 導入 csv 函式庫

# 目標 URL
url = "https://ebus.gov.taipei/ebus"
output_csv_file = "20250603/taipei_bus_routes.csv" # 定義輸出 CSV 檔案的名稱

print(f"正在從 {url} 獲取網頁內容...")

try:
    # 發送 GET 請求獲取網頁內容
    response = requests.get(url)
    response.raise_for_status()  # 如果請求失敗 (例如 4xx 或 5xx 錯誤)，會拋出異常
    
    # 設定編碼，避免中文亂碼
    response.encoding = 'utf-8' 
    html_content = response.text

    print("網頁內容獲取成功，開始解析...")

    # 使用 BeautifulSoup 解析 HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # 找到所有包含 'javascript:go()' 的 <a> 標籤
    links = soup.find_all('a', href=re.compile(r"javascript:go\('(.+)'\)"))

    extracted_data = []
    if not links:
        print("未找到包含 'javascript:go()' 的連結。")
    else:
        for link in links:
            text_content = link.get_text().strip()  # 連結文字內容
            href_attr = link.get('href')           # href 屬性值
            
            # 使用正則表達式從 href 屬性中提取 go() 函式的參數
            match = re.search(r"go\('(.+)'\)", href_attr)
            
            if match:
                param = match.group(1) # 提取第一個捕獲組的內容 (即參數)
                extracted_data.append({'路線名稱': text_content, 'go_參數': param})

    # 印出提取到的資料 (保持原有的控制台輸出)
    if extracted_data:
        print("\n提取到的公車路線資訊：")
        for item in extracted_data:
            print(f"路線名稱: {item['路線名稱']}, 參數: {item['go_參數']}")
        
        # --- 將資料寫入 CSV 檔案 ---
        print(f"\n正在將資料寫入 {output_csv_file}...")
        with open(output_csv_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
            # 定義 CSV 檔案的欄位名稱 (標題)
            fieldnames = ['routename', 'routeid']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # 寫入標題列
            writer.writeheader()
            
            # 寫入所有資料列
            writer.writerows(extracted_data)
        
        print(f"資料已成功寫入 {output_csv_file} 檔案。")

    else:
        print("沒有提取到任何公車路線資訊，因此沒有生成 CSV 檔案。")

except requests.exceptions.RequestException as e:
    print(f"獲取網頁內容時發生錯誤: {e}")
except Exception as e:
    print(f"處理網頁時發生錯誤: {e}")

print("\n爬蟲程式執行完畢。")