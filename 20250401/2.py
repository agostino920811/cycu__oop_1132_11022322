import requests
import html
import pandas as pd
from bs4 import BeautifulSoup
import time
import os

# 設定集中儲存資料夾
DOWNLOAD_FOLDER = "taipei_bus_data"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# 2025年最新幹線公車路線ID對照表 (依據台北市政府PDF與維基百科資料)
route_ids = {
    "10417": "忠孝幹線",
    "10418": "和平幹線",
    "10419": "敦化幹線",
    "10501": "松江新生幹線",
    "10502": "民生幹線",
    "10503": "仁愛幹線",
    "10505": "內湖幹線",
    "10506": "羅斯福路幹線",
    "10507": "中山幹線",
    "10508": "重慶幹線",
    "10509": "基隆路幹線",
    "10510": "承德幹線",
    "10511": "北環幹線",
    "10512": "東環幹線",
    "10513": "南環幹線",
    "10514": "南京幹線",
    "10515": "信義幹線",
    "10516": "民權幹線"
}

all_data = []

for route_id, route_name in route_ids.items():
    url = f"https://pda5284.gov.taipei/MQS/route.jsp?rid={route_id}"
    print(f"正在爬取 {route_name}({route_id}) 資料...")
    
    try:
        # 請求主頁面
        response = requests.get(url)
        response.raise_for_status()
        
        # 儲存主HTML
        main_filename = os.path.join(DOWNLOAD_FOLDER, f"{route_name}_{route_id}.html")
        with open(main_filename, "w", encoding="utf-8") as f:
            f.write(response.text)
        
        # 解析站點資料
        soup = BeautifulSoup(response.content, "html.parser")
        tables = soup.find_all("table", {"cellpadding": "2"})
        
        # 雙向路線處理
        direction_names = ["去程", "返程"] if len(tables) >= 2 else [""]
        
        for table, direction in zip(tables, direction_names):
            stops = []
            for tr in table.find_all("tr", class_=["ttego1", "ttego2"]):
                td = tr.find("td")
                if td:
                    stop_info = {
                        "路線編號": route_id,
                        "路線名稱": route_name,
                        "方向": direction,
                        "站點名稱": html.unescape(td.text.strip()),
                        "站點ID": None,
                        "經度": None,
                        "緯度": None
                    }
                    
                    # 提取站點詳細資料
                    if td.find("a"):
                        stop_link = td.find("a")["href"]
                        stop_id = stop_link.split("sid=")[-1]
                        stop_info["站點ID"] = stop_id
                        
                        # 下載站點詳細資料
                        stop_url = f"https://pda5284.gov.taipei/MQS/{stop_link}"
                        stop_response = requests.get(stop_url)
                        if stop_response.status_code == 200:
                            stop_soup = BeautifulSoup(stop_response.content, "html.parser")
                            gmap_link = stop_soup.find("a", href=lambda x: x and "maps.google.com" in x)
                            if gmap_link:
                                coord = gmap_link["href"].split("q=")[-1].split(",")
                                stop_info["緯度"], stop_info["經度"] = coord[0], coord[1]
                            
                            # 儲存站點資料
                            stop_filename = os.path.join(DOWNLOAD_FOLDER, f"stop_{stop_id}.html")
                            with open(stop_filename, "w", encoding="utf-8") as sf:
                                sf.write(stop_response.text)
                        
                    stops.append(stop_info)
            
            all_data.extend(stops)
        
        time.sleep(1.5)  # 增加間隔時間避免被封鎖

    except Exception as e:
        print(f"處理 {route_name} 時發生錯誤: {str(e)}")

# 轉換為DataFrame
df = pd.DataFrame(all_data)

# 資料清洗
df = df.drop_duplicates(subset=["站點ID"])
df[["緯度", "經度"]] = df[["緯度", "經度"]].apply(pd.to_numeric, errors='coerce')

# 儲存結果
output_path = os.path.join(DOWNLOAD_FOLDER, "taipei_main_routes_2025.csv")
df.to_csv(output_path, index=False, encoding="utf-8-sig")
print(f"資料已儲存至 {output_path}")
