import requests
import html
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import os
import time
from datetime import datetime

# 全域設定
DATA_DIR = "bus_data"
os.makedirs(DATA_DIR, exist_ok=True)

def get_stop_info(stop_link: str) -> dict:
    """
    抓取指定站點的 HTML 並儲存為本地檔案。

    Args:
        stop_link (str): 站點的相對 URL。

    Returns:
        dict: 包含站點 ID 和 HTML 檔案名稱的字典。
    """
    stop_id = stop_link.split("=")[-1]  # 修正參數解析
    url = f'https://pda5284.gov.taipei/MQS/{stop_link}'
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)
            content = page.content()
            
            # 儲存檔案到資料夾
            filename = os.path.join(DATA_DIR, f"bus_stop_{stop_id}.html")
            with open(filename, "w", encoding="utf-8") as file:
                file.write(content)
            browser.close()
            
        return {"stop_id": stop_id, "html_file": filename}
    except Exception as e:
        print(f"抓取站點失敗: {stop_id} - {str(e)}")
        return {"stop_id": stop_id, "html_file": None}

def get_bus_route(rid: str):
    """
    抓取指定路線的站點資訊，並返回去程和回程的 DataFrame。

    Args:
        rid (str): 公車路線 ID。

    Returns:
        tuple: 包含去程和回程站點資訊的兩個 DataFrame。
    """
    url = f'https://pda5284.gov.taipei/MQS/route.jsp?rid={rid}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Encoding': 'gzip, deflate'
    }

    try:
        # 發送 GET 請求
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # 儲存主檔案
        main_filename = os.path.join(DATA_DIR, f"bus_route_{rid}.html")
        with open(main_filename, "w", encoding="utf-8") as file:
            file.write(response.text)

        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(response.text, "html.parser")
        tables = soup.find_all("table")

        # 初始化 DataFrame 列表
        dataframes = []

        # 遍歷表格，提取去程和回程的站點資訊
        for table in tables:
            # 去程站點
            trs = table.find_all("tr", class_=["ttego1", "ttego2"])
            if trs:
                rows = []
                for tr in trs:
                    td = tr.find("td")
                    if td:
                        stop_name = html.unescape(td.text.strip())
                        stop_link = td.find("a")["href"] if td.find("a") else None
                        rows.append({"stop_name": stop_name, "stop_link": stop_link})
                if rows:
                    df = pd.DataFrame(rows)
                    dataframes.append(df)

            # 回程站點
            trs = table.find_all("tr", class_=["tteback1", "tteback2"])
            if trs:
                rows = []
                for tr in trs:
                    td = tr.find("td")
                    if td:
                        stop_name = html.unescape(td.text.strip())
                        stop_link = td.find("a")["href"] if td.find("a") else None
                        rows.append({"stop_name": stop_name, "stop_link": stop_link})
                if rows:
                    df = pd.DataFrame(rows)
                    dataframes.append(df)

        # 確保有足夠的表格資料
        if len(dataframes) >= 2:
            go_dataframe = dataframes[0]
            back_dataframe = dataframes[1]

            # 抓取去程站點的即時資訊
            for index, row in go_dataframe.iterrows():
                stop_link = row['stop_link']
                if stop_link:
                    stop_info = get_stop_info(stop_link)
                    print(f"去程站點: {row['stop_name']}, 資訊已儲存至 {stop_info['html_file']}")
                    time.sleep(1)  # 防止過快請求

            # 抓取回程站點的即時資訊
            for index, row in back_dataframe.iterrows():
                stop_link = row['stop_link']
                if stop_link:
                    stop_info = get_stop_info(stop_link)
                    print(f"回程站點: {row['stop_name']}, 資訊已儲存至 {stop_info['html_file']}")
                    time.sleep(1)

            return go_dataframe, back_dataframe
        else:
            raise ValueError("Insufficient table data found.")
    except Exception as e:
        raise ValueError(f"抓取路線失敗: {str(e)}")

# 測試函數
if __name__ == "__main__":
    rid = "10417"
    try:
        df1, df2 = get_bus_route(rid)
        print("\n去程站點 DataFrame:")
        print(df1.head(5))
        print("\n回程站點 DataFrame:")
        print(df2.head(5))
        
        # 儲存結果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        df1.to_csv(f"{DATA_DIR}/go_{timestamp}.csv", index=False)
        df2.to_csv(f"{DATA_DIR}/back_{timestamp}.csv", index=False)
        print(f"\n資料已儲存至 {DATA_DIR} 目錄")
    except ValueError as e:
        print(f"錯誤: {e}")