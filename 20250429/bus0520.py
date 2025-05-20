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
                page.click('a.stationlist-come-go-gray.stationlist-come')
            
            page.wait_for_selector('.auto-list-stationlist', timeout=10000)  # Wait up to 10 seconds
            self.content = page.content()
            browser.close()

        os.makedirs("data", exist_ok=True)
        with open(f"data/ebus_taipei_{self.rid}.html", "w", encoding="utf-8") as file:
            file.write(self.content)

    def _parse_and_save_to_csv(self):
        soup = BeautifulSoup(self.content, 'html.parser')
        stops = []

        stop_elements = soup.select('.auto-list-stationlist')
        if not stop_elements:
            print("無法找到站點資訊，請檢查選擇器或網站結構")
            return

        for stop in stop_elements:
            try:
                arrival_info = stop.select_one('.auto-list-stationlist-position-time').text.strip()
                stop_number = stop.select_one('.auto-list-stationlist-number').text.strip()
                stop_name = stop.select_one('.auto-list-stationlist-place').text.strip()
                stop_id = stop.select_one('input[name="item.UniStopId"]')['value']
                latitude = stop.select_one('input[name="item.Latitude"]')['value']
                longitude = stop.select_one('input[name="item.Longitude"]')['value']

                stops.append([arrival_info, stop_number, stop_name, stop_id, latitude, longitude])
            except AttributeError:
                continue

        os.makedirs("data", exist_ok=True)

        csv_filename = f"data/bus_route_{self.rid}_{self.direction}.csv" # Add direction to filename
        with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["公車到達時間", "車站序號", "車站名稱", "車站編號", "latitude", "longitude"])
            writer.writerows(stops)

        print(f"資料已儲存至 {csv_filename}")

        for stop in stops:
            print(f"{stop[0]}, {stop[1]}, {stop[2]}, {stop[3]}, {stop[4]}, {stop[5]}")

---

## Updated `main` Execution Block

Here's the modified `if __name__ == "__main__":` block to allow user input for both `routeid` and `direction`:

```python
if __name__ == "__main__":
    # Allow the user to input the bus ID and direction
    route_id_input = input("請輸入公車代碼 (例如: 0100000A00): ").strip()
    direction_input = input("請輸入方向 ('go' 或 'come'): ").strip().lower() # Convert to lowercase for consistency

    try:
        # Create an instance of BusRouteInfo with user-provided inputs
        bus_route_info_instance = BusRouteInfo(routeid=route_id_input, direction=direction_input)
    except ValueError as e:
        print(f"輸入錯誤: {e}")
    except Exception as e:
        print(f"發生錯誤: {e}")