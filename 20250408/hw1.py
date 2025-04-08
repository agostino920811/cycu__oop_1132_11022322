import requests
import csv

def fetch_bus_data(route_id, output_file):
    """
    從臺北市公開網站抓取指定公車代碼的資料，並輸出為 CSV 格式。

    :param route_id: 公車代碼 (例如 '0100000A00')
    :param output_file: 輸出的 CSV 檔案名稱
    """
    url = f"https://ebus.gov.taipei/Route/StopsOfRoute?routeid={route_id}"
    try:
        # 發送 GET 請求
        response = requests.get(url)
        response.raise_for_status()  # 檢查請求是否成功

        # 調試用：檢查伺服器返回的內容
        print("伺服器返回的內容：")
        print(response.text)

        # 嘗試解析 JSON
        try:
            data = response.json()  # 將回應轉換為 JSON 格式
        except ValueError:
            print("伺服器返回的內容不是 JSON 格式：")
            print(response.text)
            return

        # 檢查資料是否有效
        if not data or "Stops" not in data:
            print("無法取得有效的公車資料，請檢查公車代碼是否正確。")
            print("伺服器返回的資料結構：", data)
            return

        print("資料結構檢查通過，開始解析 Stops 資料...")
        stops = data.get("Stops", [])
        if not stops:
            print("伺服器返回的 Stops 資料為空。")
            return

        parsed_data = []
        for stop in stops:
            arrival_info = stop.get("ArrivalTime", "未知")
            stop_number = stop.get("StopSequence", "未知")
            stop_name = stop.get("StopName", {}).get("Zh_tw", "未知")
            stop_id = stop.get("StopID", "未知")
            latitude = stop.get("StopPosition", {}).get("PositionLat", "未知")
            longitude = stop.get("StopPosition", {}).get("PositionLon", "未知")
            parsed_data.append([arrival_info, stop_number, stop_name, stop_id, latitude, longitude])

        print("開始寫入 CSV 檔案...")
        # 將資料寫入 CSV
        with open(output_file, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["arrival_info", "stop_number", "stop_name", "stop_id", "latitude", "longitude"])
            writer.writerows(parsed_data)

        print(f"資料已成功儲存至 {output_file}")

    except requests.exceptions.RequestException as e:
        print(f"無法取得資料，請檢查網路連線或公車代碼是否正確。錯誤訊息：{e}")
    except Exception as e:
        print(f"發生錯誤：{e}")

# 測試函數
if __name__ == "__main__":
    route_id = input("請輸入公車代碼 (例如 '0100000A00')：")
    output_file = "bus_data.csv"
    fetch_bus_data(route_id, output_file)