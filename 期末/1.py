# -*- coding: utf-8 -*-
import pandas as pd
import re
from playwright.sync_api import sync_playwright
import os
import time

# Define the base path for input and output files
BASE_PATH = r'C:\Users\ian50\OneDrive\文件\GitHub\cycu__oop_1132_11022322\期末'
ROUTE_LIST_CSV = 'taipei_bus_routes.csv' # 原始路線列表 CSV
OUTPUT_FILENAME = 'all_bus_routes_with_stops.csv' # 單一輸出 CSV 檔名

ROUTE_LIST_CSV_PATH = os.path.join(BASE_PATH, ROUTE_LIST_CSV)
OUTPUT_FILEPATH = os.path.join(BASE_PATH, OUTPUT_FILENAME)

class BusRouteInfo:
    def __init__(self, routeid: str, direction: str = 'go'):
        self.rid = routeid
        self.content = None
        self.url = f'https://ebus.gov.taipei/Route/StopsOfRoute?routeid={routeid}'
        self.dataframe = None # To store parsed bus stop data

        if direction not in ['go', 'come']:
            raise ValueError("Direction must be 'go' or 'come'")

        self.direction = direction

        self._fetch_content()
    
    def _fetch_content(self):
        """
        Fetches the webpage content using Playwright.
        No longer saves the rendered HTML to a local file.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                # Increased timeout for page loading
                page.goto(self.url, timeout=60000) 
                
                if self.direction == 'come':
                    # Wait for the button to be visible and enabled before clicking
                    page.wait_for_selector('a.stationlist-come-go-gray.stationlist-come', state='visible', timeout=10000)
                    page.click('a.stationlist-come-go-gray.stationlist-come')
                    # Give a short delay after clicking to ensure content updates
                    time.sleep(2) 

                # Wait for a specific part of the content to be loaded, e.g., the first station name
                # This is more robust than a fixed timeout
                page.wait_for_selector('span.auto-list-stationlist-place', timeout=10000)
                
                self.content = page.content()
            except Exception as e:
                print(f"Error fetching content for route {self.rid}, direction {self.direction}: {e}")
                self.content = None # Set content to None if fetching fails
            finally:
                browser.close()

    def parse_route_info(self) -> pd.DataFrame:
        """
        Parses the fetched HTML content to extract bus stop data.
        Returns a DataFrame containing all stop details, but we will only use 'stop_name'.
        """
        if self.content is None:
            return pd.DataFrame() # Return empty DataFrame if content is not available

        pattern = re.compile(
            r'<li>.*?<span class="auto-list-stationlist-position.*?">(.*?)</span>\s*'
            r'<span class="auto-list-stationlist-number">\s*(\d+)</span>\s*'
            r'<span class="auto-list-stationlist-place">(.*?)</span>.*?'
            r'<input[^>]+name="item\.UniStopId"[^>]+value="(\d+)"[^>]*>.*?'
            r'<input[^>]+name="item\.Latitude"[^>]+value="([\d\.]+)"[^>]*>.*?'
            r'<input[^>]+name="item\.Longitude"[^>]+value="([\d\.]+)"[^>]*>',
            re.DOTALL
        )

        matches = pattern.findall(self.content)
        if not matches:
            return pd.DataFrame() # Return empty DataFrame if no matches

        bus_stops_data = [m for m in matches]
        self.dataframe = pd.DataFrame(
            bus_stops_data,
            columns=["arrival_info", "stop_number", "stop_name", "stop_id", "latitude", "longitude"]
        )

        # Convert appropriate columns to numeric types (optional for this specific request, but good practice)
        self.dataframe["stop_number"] = pd.to_numeric(self.dataframe["stop_number"], errors='coerce')
        self.dataframe["stop_id"] = pd.to_numeric(self.dataframe["stop_id"], errors='coerce')
        self.dataframe["latitude"] = pd.to_numeric(self.dataframe["latitude"], errors='coerce')
        self.dataframe["longitude"] = pd.to_numeric(self.dataframe["longitude"], errors='coerce')

        self.dataframe["direction"] = self.direction
        self.dataframe["route_id"] = self.rid

        return self.dataframe


if __name__ == "__main__":
    # 確保輸出檔案的目錄存在 (BASE_PATH 本身)
    if not os.path.exists(BASE_PATH):
        os.makedirs(BASE_PATH)
        print(f"Created base directory: {BASE_PATH}")

    # 1. 讀取所有路線代碼和名稱，並處理進度標記
    try:
        # 使用 'utf-8-sig' 確保正確讀取中文
        df_routes_base = pd.read_csv(ROUTE_LIST_CSV_PATH, encoding='utf-8-sig')
        if 'route_id' not in df_routes_base.columns or 'route_name' not in df_routes_base.columns:
            raise ValueError(f"'{ROUTE_LIST_CSV_PATH}' must contain 'route_id' and 'route_name' columns.")
        
        # 檢查 'is_processed' 欄位是否存在，如果不存在則新增並初始化為 False
        if 'is_processed' not in df_routes_base.columns:
            df_routes_base['is_processed'] = False
            print(f"Added 'is_processed' column to {ROUTE_LIST_CSV_PATH}.")
        else:
            # 確保 'is_processed' 是布林型態
            df_routes_base['is_processed'] = df_routes_base['is_processed'].astype(bool)
            print(f"'{ROUTE_LIST_CSV_PATH}' loaded. {df_routes_base['is_processed'].sum()} routes already processed.")

        print(f"Successfully read {len(df_routes_base)} route IDs from {ROUTE_LIST_CSV_PATH}.")
    except FileNotFoundError:
        print(f"Error: '{ROUTE_LIST_CSV_PATH}' not found. Please ensure it exists.")
        exit() # Exit if the input CSV is missing
    except Exception as e:
        print(f"Error reading CSV file '{ROUTE_LIST_CSV_PATH}': {e}")
        exit()

    # 判斷輸出 CSV 檔案是否已存在，以決定是否寫入 header
    # 注意：如果每次執行都想從頭開始一個全新的 OUTPUT_FILEPATH，請在運行前手動刪除舊的檔案。
    # 如果希望在檔案中追加，並根據檔案是否存在來決定是否寫入 header，則保持此邏輯。
    output_file_exists = os.path.exists(OUTPUT_FILEPATH)
    
    # 2. 遍歷每個路線代碼，抓取站點名稱並合併
    processed_count = 0
    total_routes = len(df_routes_base)

    for index, row in df_routes_base.iterrows():
        route_id = row['route_id']
        route_name = row['route_name']
        is_processed = row['is_processed']
        
        # 為最終數據集準備的當前路線數據 (單獨一個字典用於單行數據)
        current_route_output_data = {'route_id': route_id, 'route_name': route_name} 

        if is_processed:
            print(f"\n--- Skipping Route: {route_name} ({route_id}) - Already processed. ---")
            # 如果是跳過，則理論上這條數據已經在 OUTPUT_FILEPATH 中了，無需再次處理和寫入
            # 如果你想要在每次運行時，即使是跳過的數據也確保會出現在最終的 OUTPUT_FILEPATH 中
            # 則需要在一開始就讀取 OUTPUT_FILEPATH 的內容並存入一個列表，再在此處加入已處理的數據
            # 為了避免複雜化，這裡就直接跳過了，假設 OUTPUT_FILEPATH 會在第一次運行時完整生成。
            continue # 跳過已處理的路線

        print(f"\n--- Processing Route: {route_name} ({route_id}) --- ({processed_count + 1}/{total_routes})")
        
        # --- 處理 'go' (去程) 方向 ---
        go_stop_names = []
        go_latitudes = []
        go_longitudes = []
        go_fetch_success = False
        try:
            route_info_go = BusRouteInfo(route_id, direction="go")
            df_stops_go = route_info_go.parse_route_info()
            
            if not df_stops_go.empty:
                go_stop_names = df_stops_go['stop_name'].tolist()
                go_latitudes = df_stops_go['latitude'].tolist()
                go_longitudes = df_stops_go['longitude'].tolist()
                print(f"  Found {len(go_stop_names)} stops for 'go' direction.")
                go_fetch_success = True
            else:
                print(f"  No stop data found for 'go' direction.")
            
            time.sleep(1) # Add a small delay between requests

        except Exception as e:
            print(f"  Error processing 'go' direction for route {route_id}: {e}")
            
        for i, stop_name in enumerate(go_stop_names):
            current_route_output_data[f'stop_name_go_{i+1}'] = stop_name
            current_route_output_data[f'latitude_go_{i+1}'] = go_latitudes[i]
            current_route_output_data[f'longitude_go_{i+1}'] = go_longitudes[i]
            
        # --- 處理 'come' (返程) 方向 ---
        come_stop_names = []
        come_latitudes = []
        come_longitudes = []
        come_fetch_success = False
        try:
            route_info_come = BusRouteInfo(route_id, direction="come")
            df_stops_come = route_info_come.parse_route_info()

            if not df_stops_come.empty:
                come_stop_names = df_stops_come['stop_name'].tolist()
                come_latitudes = df_stops_come['latitude'].tolist()
                come_longitudes = df_stops_come['longitude'].tolist()
                print(f"  Found {len(come_stop_names)} stops for 'come' direction.")
                come_fetch_success = True
            else:
                print(f"  No stop data found for 'come' direction.")

            time.sleep(1) # Add a small delay between requests

        except Exception as e:
            print(f"  Error processing 'come' direction for route {route_id}: {e}")
        
        for i, stop_name in enumerate(come_stop_names):
            current_route_output_data[f'stop_name_come_{i+1}'] = stop_name
            current_route_output_data[f'latitude_come_{i+1}'] = come_latitudes[i]
            current_route_output_data[f'longitude_come_{i+1}'] = come_longitudes[i]
        
        # 將單一路線的數據轉換為 DataFrame，並追加寫入 CSV
        single_route_df = pd.DataFrame([current_route_output_data])
        
        # 確保輸出目錄存在 (BASE_PATH)
        os.makedirs(os.path.dirname(OUTPUT_FILEPATH), exist_ok=True)

        # 寫入 CSV
        # 如果檔案不存在，則寫入 header；否則，追加且不寫入 header
        single_route_df.to_csv(
            OUTPUT_FILEPATH, 
            mode='a', # 追加模式
            index=False, 
            encoding='utf-8-sig', 
            header=not output_file_exists # 只有在檔案不存在時才寫入 header
        )
        
        # 寫入後，將 output_file_exists 設為 True，確保後續追加不再寫入 header
        output_file_exists = True 
        
        print(f"--- Route {route_id} data appended to {OUTPUT_FILEPATH}. ---")

        # 僅當去程或返程至少有一個有數據時，才將該路線標記為已處理
        if go_fetch_success or come_fetch_success: # 如果有成功抓取到任何一個方向的數據
            df_routes_base.loc[index, 'is_processed'] = True # 在 df_routes_base 中更新標記
        else:
            print(f"  Warning: No data successfully fetched for route {route_id}. Not marked as processed.")


        processed_count += 1
        print(f"--- Finished processing route {route_id}. Status updated. ---")
        
        # 定期保存進度到原始的路線列表 CSV，以防程式崩潰
        if processed_count % 10 == 0: # 每處理10條路線，保存一次
            print(f"Saving processing progress to {ROUTE_LIST_CSV_PATH}...")
            df_routes_base.to_csv(ROUTE_LIST_CSV_PATH, index=False, encoding='utf-8-sig')
            print("Progress saved.")
        
        # 延遲策略
        if processed_count % 10 == 0: # 每處理10條路線，休息更久
            print("Taking a longer break...")
            time.sleep(10)
        else:
            time.sleep(3) # 一般延遲

    # 3. 程式結束時，最終保存一次更新後的路線列表狀態
    print(f"\nFinal save of processing status to {ROUTE_LIST_CSV_PATH}...")
    df_routes_base.to_csv(ROUTE_LIST_CSV_PATH, index=False, encoding='utf-8-sig')
    print("Final status saved. Script finished.")

    print(f"\nAll processed routes' stop data (including newly processed and skipped) are available in: {OUTPUT_FILEPATH}")