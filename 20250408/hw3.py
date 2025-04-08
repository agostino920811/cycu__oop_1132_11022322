# -*- coding: utf-8 -*-
import os
import csv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup


class BusRouteInfo:
    def __init__(self, routeid: str, direction: str = 'go'):
        self.rid = routeid
        self.content = None
        self.url = f'https://ebus.gov.taipei/Route/StopsOfRoute?routeid={routeid}'

        if direction not in ['go', 'come']:
            raise ValueError("Direction must be 'go' or 'come'")

        self.direction = direction

        self._fetch_content()
        self._parse_and_save_to_csv()

    def _fetch_content(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.url)
            
            if self.direction == 'come':
                try:
                    page.click('a.stationlist-come-go-gray.stationlist-come')
                except Exception as e:
                    print(f"無法切換方向：{e}")
            
            # 等待站點資訊載入完成
            page.wait_for_selector('.auto-list-stationlist', timeout=10000)  # 最多等待 10 秒
            self.content = page.content()
            browser.close()

        # 儲存 HTML 內容到檔案（除錯用）
        os.makedirs("data", exist_ok=True)  # 確保資料夾存在
        with open(f"data/ebus_taipei_{self.rid}.html", "w", encoding="utf-8") as file:
            file.write(self.content)

    def _parse_and_save_to_csv(self):
        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(self.content, 'html.parser')
        stops = []

        # 根據提供的 HTML 結構，選擇站點資訊
        stop_elements = soup.select('.auto-list-stationlist')  # 修改選擇器以符合實際網站結構
        if not stop_elements:
            print("無法找到站點資訊，請檢查選擇器或網站結構")
            return

        for stop in stop_elements:
            try:
                # 提取站點資訊
                arrival_info = stop.select_one('.auto-list-stationlist-position-time').text.strip()  # 到達時間
                stop_number = stop.select_one('.auto-list-stationlist-number').text.strip()  # 車站序號
                stop_name = stop.select_one('.auto-list-stationlist-place').text.strip()  # 車站名稱
                stop_id = stop.select_one('input[name="item.UniStopId"]')['value']  # 車站編號
                latitude = stop.select_one('input[name="item.Latitude"]')['value']  # 緯度
                longitude = stop.select_one('input[name="item.Longitude"]')['value']  # 經度

                stops.append([arrival_info, stop_number, stop_name, stop_id, latitude, longitude])
            except AttributeError:
                # 不顯示錯誤訊息，直接跳過
                continue

        # 確保資料夾存在
        os.makedirs("data", exist_ok=True)

        # 將資料寫入 CSV
        csv_filename = f"data/bus_route_{self.rid}.csv"
        with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["arrival_info", "stop_number", "stop_name", "stop_id", "latitude", "longitude"])
            writer.writerows(stops)

        print(f"資料已儲存至 {csv_filename}")

        # 顯示站點資訊
        for stop in stops:
            print(f"到達時間: {stop[0]}, 車站序號: {stop[1]}, 車站名稱: {stop[2]}, 車站編號: {stop[3]}, 緯度: {stop[4]}, 經度: {stop[5]}")


if __name__ == "__main__":
    # 讓使用者輸入公車代碼和方向
    routeid = input("請輸入公車代碼 (例如: 0100000A00): ").strip()
    direction = input("請輸入方向 ('go' 或 'come'): ").strip()

    try:
        route = BusRouteInfo(routeid=routeid, direction=direction)
    except ValueError as e:
        print(f"輸入錯誤: {e}")
    except Exception as e:
        print(f"發生錯誤: {e}")
