import requests
import html
import pandas as pd
from bs4 import BeautifulSoup
import os
from concurrent.futures import ThreadPoolExecutor

# 設定 User-Agent 避免被封鎖
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_stop_info(stop_link: str):
    """下載並儲存指定站點的 HTML 頁面"""
    url = f'https://pda5284.gov.taipei/MQS/{stop_link}'
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        # 讀取站點 ID
        stop_id = stop_link.split("=")[1]

        with open(f"bus_stop_{stop_id}.html", "w", encoding="utf-8") as file:
            file.write(response.text)

        print(f"✅ 下載完成：bus_stop_{stop_id}.html")

    except requests.exceptions.RequestException as e:
        print(f"❌ 下載失敗 {stop_link}: {e}")

def get_bus_route(rid: str):
    """根據公車路線 ID 取得去程與回程的站點資訊，回傳 DataFrame"""
    url = f'https://pda5284.gov.taipei/MQS/route.jsp?rid={rid}'

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        # 儲存 HTML 檔案
        with open(f"bus_route_{rid}.html", "w", encoding="utf-8") as file:
            file.write(response.text)

        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # 初始化兩個 DataFrame
        go_stops = []
        return_stops = []

        # 找出所有公車站點表格
        tables = soup.find_all("table")

        for table in tables:
            # 去程站點 (ttego1, ttego2)
            for tr in table.find_all("tr", class_=["ttego1", "ttego2"]):
                td = tr.find("td")
                if td:
                    stop_name = html.unescape(td.text.strip())
                    stop_link = td.find("a")["href"] if td.find("a") else None
                    go_stops.append({"stop_name": stop_name, "stop_link": stop_link})

            # 回程站點 (tteback1, tteback2)
            for tr in table.find_all("tr", class_=["tteback1", "tteback2"]):
                td = tr.find("td")
                if td:
                    stop_name = html.unescape(td.text.strip())
                    stop_link = td.find("a")["href"] if td.find("a") else None
                    return_stops.append({"stop_name": stop_name, "stop_link": stop_link})

        # 轉換為 DataFrame
        df_go = pd.DataFrame(go_stops)
        df_return = pd.DataFrame(return_stops)

        # 儲存 CSV 方便後續分析
        df_go.to_csv(f"去程站點_{rid}.csv", index=False, encoding="utf-8")
        df_return.to_csv(f"回程站點_{rid}.csv", index=False, encoding="utf-8")

        return df_go, df_return

    except requests.exceptions.RequestException as e:
        raise ValueError(f"❌ 無法下載網頁: {e}")

def download_all_stops(df: pd.DataFrame):
    """多線程下載所有站點的 HTML 頁面"""
    os.makedirs("stations_html", exist_ok=True)

    with ThreadPoolExecutor(max_workers=5) as executor:
        for _, row in df.iterrows():
            if row["stop_link"]:
                executor.submit(get_stop_info, row["stop_link"])

# 測試函數
if __name__ == "__main__":
    rid = "10417"  # 測試公車路線 ID

    try:
        df_go, df_return = get_bus_route(rid)

        print("\n🚏 去程站點 DataFrame:")
        print(df_go)

        print("\n🚏 回程站點 DataFrame:")
        print(df_return)

        # 下載所有站點的 HTML 頁面
        print("\n🚀 開始下載所有站點詳細資訊...")
        download_all_stops(pd.concat([df_go, df_return]))

    except ValueError as e:
        print(f"Error: {e}")