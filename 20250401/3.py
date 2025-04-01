from bs4 import BeautifulSoup

def read_bus_stop_status(file_path, station_name):
    """
    讀取指定 HTML 檔案，並根據輸入的車站名稱顯示到站狀態。

    Args:
        file_path (str): HTML 檔案路徑。
        station_name (str): 要查詢的車站名稱。

    Returns:
        None
    """
    try:
        # 讀取 HTML 檔案
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(content, "html.parser")

        # 遍歷所有車站資料
        rows = soup.find_all("tr", class_=["ttego1", "ttego2"])
        found = False
        for row in rows:
            # 提取車站名稱和到站狀態
            cols = row.find_all("td")
            if len(cols) >= 4:
                route = cols[0].text.strip()  # 路線名稱
                stop_name = cols[1].text.strip()  # 車站名稱
                direction = cols[2].text.strip()  # 去返程
                status = cols[3].text.strip()  # 到站狀態

                # 如果車站名稱匹配，顯示資訊
                if station_name in stop_name:
                    print(f"路線: {route}, 車站: {stop_name}, 去返程: {direction}, 到站狀態: {status}")
                    found = True

        if not found:
            print(f"未找到車站名稱包含「{station_name}」的資料。")

    except Exception as e:
        print(f"讀取檔案時發生錯誤: {e}")

# 測試程式
if __name__ == "__main__":
    file_path = "bus_data/bus_stop_36022.html"  # HTML 檔案路徑
    station_name = input("請輸入車站名稱: ")  # 輸入車站名稱
    read_bus_stop_status(file_path, station_name)