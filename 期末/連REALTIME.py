import asyncio
import csv
import re
import webbrowser
import folium
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# --- 輔助函數：獲取站點詳細信息 (包括去程和返程) ---
async def fetch_stops_detail(page, direction_selector, direction_name):
    """
    通用函數，用於獲取指定方向（去程或返程）的站點詳細信息。
    """
    stops_data = []
    
    try:
        # 等待該方向的列表出現並可見
        await page.wait_for_selector(f'{direction_selector} li .auto-list-stationlist-place', state='visible', timeout=10000)
        
        # 獲取所有站點元素
        stop_elements = await page.query_selector_all(f'{direction_selector} li')

        for i, stop_elem in enumerate(stop_elements):
            try:
                name_elem = await stop_elem.query_selector(".auto-list-stationlist-place")
                number_elem = await stop_elem.query_selector(".auto-list-stationlist-number")
                stop_id_input = await stop_elem.query_selector("input[name='item.UniStopId']")
                latitude_input = await stop_elem.query_selector("input[name='item.Latitude']")
                longitude_input = await stop_elem.query_selector("input[name='item.Longitude']")

                name = await name_elem.inner_text() if name_elem else "未知站名"
                number_text = await number_elem.inner_text() if number_elem else str(i + 1) # 如果沒有序號，用索引作為序號
                stop_id = await stop_id_input.get_attribute("value") if stop_id_input else "未知編號"
                lat = float(await latitude_input.get_attribute("value")) if latitude_input and await latitude_input.get_attribute("value") else None
                lon = float(await longitude_input.get_attribute("value")) if longitude_input and await longitude_input.get_attribute("value") else None
                
                if lat is not None and lon is not None:
                    stops_data.append({
                        "direction": direction_name,
                        "sequence": int(number_text.strip()),
                        "name": name.strip(),
                        "stop_id": stop_id.strip(),
                        "lat": lat,
                        "lon": lon
                    })
                else:
                    print(f"警告: 站點 '{name}' 缺少經緯度，已跳過。")

            except Exception as e:
                print(f"處理 {direction_name} 站點時發生錯誤: {e}")
                continue
    except PlaywrightTimeoutError:
        print(f"警告: 等待 {direction_name} 站點列表超時，可能沒有該方向數據或網頁載入問題。")
    except Exception as e:
        print(f"獲取 {direction_name} 站點時發生未預期錯誤: {e}")

    return stops_data

# --- 獲取公車路線的站牌名稱、真實經緯度和預估到站時間 ---
async def get_bus_route_info(page, route_id, bus_name):
    """
    從大台北公車動態資訊系統抓取指定路線的站牌名稱、真實經緯度、預估到站時間和公車位置。
    返回一個字典，包含 'stops_data', 'estimated_times', 'bus_locations'。
    """
    print(f"\n正在從 ebus.gov.taipei 獲取路線 '{bus_name}' ({route_id}) 的站牌數據和即時資訊...")

    url = f'https://ebus.gov.taipei/Route/StopsOfRoute?routeid={route_id}'
    all_stops_data = []
    estimated_times = {}
    bus_locations = []

    try:
        await page.goto(url, timeout=60000)
        # 等待主要的站點列表容器出現，確保頁面基本載入
        await page.wait_for_selector('div.panel-body.xidstyle', state='visible', timeout=20000)
        
        # 點擊去程按鈕並抓取去程站點資訊
        go_button = await page.query_selector("a.stationlist-go")
        if go_button:
            await go_button.click()
            # 等待去程內容完全載入，確保新的站點資訊已更新
            await page.wait_for_selector('#GoDirectionRoute li', state='visible', timeout=10000)
            go_stops_data = await fetch_stops_detail(page, '#GoDirectionRoute', '去程')
            all_stops_data.extend(go_stops_data)
        else:
            print("警告: 無法找到去程按鈕。")

        # 點擊返程按鈕並抓取返程站點資訊
        return_button = await page.query_selector("a.stationlist-come")
        if return_button:
            await return_button.click()
            # 等待返程內容完全載入
            await page.wait_for_selector('#BackDirectionRoute li', state='visible', timeout=10000)
            return_stops_data = await fetch_stops_detail(page, '#BackDirectionRoute', '返程')
            all_stops_data.extend(return_stops_data)
        else:
            print("警告: 無法找到返程按鈕。")
        
        # --- 獲取預估到站時間和公車位置 ---
        # 由於去返程的站點已載入，我們可以重新遍歷它們來獲取預估時間
        # 注意：這個頁面 (StopsOfRoute) 通常會顯示預估時間和公車位置。
        # 如果需要更精確的即時公車位置 (在地圖上移動的車輛)，可能需要訪問 /Route/BusInfo 頁面，
        # 但這通常會導致重複載入數據或需要額外邏輯來關聯。
        # 目前先從 StopsOfRoute 頁面嘗試獲取。

        # 遍歷所有已找到的站點，嘗試獲取其預估時間
        # 由於去返程的 li 可能有重複的站名，我們需要確保estimated_times字典更新正確
        for stop_item in await page.query_selector_all('.auto-list-stationlist li'):
            name_elem = await stop_item.query_selector(".auto-list-stationlist-place")
            eta_elem = await stop_item.query_selector(".auto-list-stationlist-position-time") # 從你之前的截圖來看，這個選擇器更精確
            
            name = await name_elem.inner_text() if name_elem else None
            eta = await eta_elem.inner_text() if eta_elem else "無資料"
            
            if name:
                estimated_times[name.strip()] = eta.strip()

        # 嘗試獲取公車位置 (如果網頁提供數據標記在 DOM 中)
        # 檢查是否有標記公車位置的元素，通常會有 data-lat 和 data-lng 屬性
        # 在 `StopsOfRoute` 頁面，公車位置通常是地圖上的圖標，可能無法直接通過 DOM 獲取
        # 如果網站通過 API 返回，我們就無法直接從此頁面獲取
        # 假設如果有，可能會在 `.bus-marker` 類別或類似元素上
        
        # 注意：ebus.gov.taipei 的 StopsOfRoute 頁面通常不直接在 DOM 中提供公車的精確實時經緯度
        # 它們是透過 JavaScript 在地圖上繪製的。如果需要實時公車位置，需要額外的請求或更複雜的爬蟲
        # 這裡的 bus_locations 可能會是空列表，因為它很難從靜態 DOM 中獲取。
        # 如果需要，可能需要分析網站的 XHR 請求來找出獲取即時公車位置的 API。
        bus_position_elements = await page.query_selector_all('[data-lat][data-lng], .bus-location-marker') # 嘗試常見選擇器
        for pos_elem in bus_position_elements:
            try:
                lat = float(await pos_elem.get_attribute('data-lat')) if await pos_elem.get_attribute('data-lat') else None
                lon = float(await pos_elem.get_attribute('data-lng')) if await pos_elem.get_attribute('data-lng') else None
                if lat and lon:
                    bus_locations.append({'lat': lat, 'lon': lon})
            except Exception as e:
                # print(f"解析公車位置元素時發生錯誤: {e}") # 避免過多輸出
                continue

    except PlaywrightTimeoutError as e:
        print(f"[錯誤] 獲取路線 {bus_name} 數據超時：{e}")
        all_stops_data = []
        estimated_times = {}
        bus_locations = []
    except Exception as e:
        print(f"[錯誤] 獲取路線 {bus_name} 數據失敗：{e}")
        all_stops_data = []
        estimated_times = {}
        bus_locations = []

    print(f"路線 '{bus_name}' 的站牌數據獲取完成。共 {len(all_stops_data)} 站。")
    print(f"已獲取 {len(estimated_times)} 個站點的預估時間資訊。")
    if bus_locations:
        print(f"已獲取 {len(bus_locations)} 個公車位置。")

    return {
        "stops_data": all_stops_data,
        "estimated_times": estimated_times,
        "bus_locations": bus_locations
    }

# --- 顯示地圖函式 ---
def display_bus_route_on_map(route_name, stops_data, bus_locations=None, estimated_times=None):
    """
    將公車路線、站牌、預估時間和公車位置顯示在地圖上。
    stops_data: 列表，每個元素是一個字典，包含 'name', 'lat', 'lon', 'direction', 'sequence'
    bus_locations: 列表，包含公車位置的字典 [{'lat': xx, 'lon': xx}, ...]
    estimated_times: 字典，鍵為站牌名稱，值為預估時間，可選
    """
    if not stops_data:
        print(f"沒有路線 '{route_name}' 的站牌數據可顯示。")
        return

    print(f"\n正在為路線 '{route_name}' 生成地圖...")

    # 以所有站牌的中心點為地圖中心
    avg_lat = sum(s["lat"] for s in stops_data if s["lat"] is not None) / len(stops_data)
    avg_lon = sum(s["lon"] for s in stops_data if s["lon"] is not None) / len(stops_data)
    map_center = [avg_lat, avg_lon]
    m = folium.Map(location=map_center, zoom_start=13)

    # 繪製路線路徑 (分開去程和返程)
    # 按照 sequence 排序，並分組
    directions = {}
    for stop in stops_data:
        direction = stop['direction']
        if direction not in directions:
            directions[direction] = []
        directions[direction].append(stop)

    colors = {'去程': 'green', '返程': 'blue'} # 可以為不同方向設置不同顏色
    for direction_name, stops_in_direction in directions.items():
        # 根據站序排序
        sorted_stops = sorted(stops_in_direction, key=lambda x: x['sequence'])
        route_coords_list = [[stop["lat"], stop["lon"]] for stop in sorted_stops if stop["lat"] is not None and stop["lon"] is not None]
        
        if len(route_coords_list) > 1:
            folium.PolyLine(
                locations=route_coords_list,
                color=colors.get(direction_name, 'purple'), # 使用方向對應的顏色
                weight=4,
                opacity=0.7,
                tooltip=f"路線: {route_name} ({direction_name})"
            ).add_to(m)

    # 添加站牌標記和彈出視窗
    for stop in stops_data:
        stop_name = stop["name"]
        coords = [stop["lat"], stop["lon"]]
        direction = stop["direction"] # 顯示方向

        est_time_text = estimated_times.get(stop_name, "未知") if estimated_times else "未知"
        
        # 根據預估時間設置不同的顏色
        icon_color = "gray" # 預設顏色
        if est_time_text:
            if "進站中" in est_time_text or "即將進站" in est_time_text:
                icon_color = "red"
            elif "分" in est_time_text:
                try:
                    minutes_match = re.search(r'(\d+)\s*分', est_time_text)
                    if minutes_match:
                        minutes = int(minutes_match.group(1))
                        if minutes <= 5:
                            icon_color = "orange"
                        elif minutes <= 15:
                            icon_color = "blue"
                        else:
                            icon_color = "darkgreen" # 超過15分鐘的顏色
                except:
                    pass # 如果解析失敗，保持灰色
        
        popup_html = f"""
        <div style='font-family: Arial; width: 200px;'>
            <b style='font-size: 14px;'>{stop_name}</b><br>
            <hr style='margin: 5px 0;'>
            <span style='color: #8B4513;'><b>方向:</b></span> {direction}<br>
            <span style='color: #2E8B57;'><b>預估時間:</b></span> {est_time_text}<br>
            <span style='color: #4682B4;'><b>站序:</b></span> {stop['sequence']}<br>
            <span style='color: #666;'><b>座標:</b></span> {coords[0]:.6f}, {coords[1]:.6f}
        </div>
        """

        folium.Marker(
            location=coords,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{stop_name} ({direction}) - {est_time_text}",
            icon=folium.Icon(color=icon_color, icon="info-sign")
        ).add_to(m)

    # 添加公車當前位置標記 (如果提供)
    if bus_locations:
        for i, bus_loc in enumerate(bus_locations):
            if bus_loc.get('lat') is not None and bus_loc.get('lon') is not None:
                folium.Marker(
                    location=[bus_loc["lat"], bus_loc["lon"]],
                    popup=folium.Popup(f"<b>公車位置 #{i+1}</b><br>路線: {route_name}", max_width=200),
                    tooltip=f"公車 #{i+1}",
                    icon=folium.Icon(color="purple", icon="bus", prefix="fa") # 將公車顏色改為紫色區別
                ).add_to(m)

    # 添加圖例
    legend_html = '''
    <div style="position: fixed; 
                top: 10px; right: 10px; width: 200px; height: 160px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <b>圖例說明</b><br>
    🔴 進站中/即將到站<br>
    🟠 5分鐘內<br>
    🔵 5-15分鐘<br>
    ⚫ 15分鐘以上<br>
    🟪 公車位置<br>
    🟢 去程路線<br>
    🟦 返程路線
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    # 將地圖保存為HTML文件並自動打開
    map_filename = f"bus_route_{route_name}_map.html"
    m.save(map_filename)
    print(f"地圖已保存到 '{map_filename}'。")
    print("正在嘗試在瀏覽器中打開地圖...")
    webbrowser.open(map_filename)
    print("✅ 完成！")

# --- 將站牌數據輸出為 CSV 檔案的函式 ---
def export_stops_to_csv(route_name, stops_data, estimated_times=None):
    """
    將公車路線的站牌數據輸出為 CSV 檔案。
    stops_data: 列表，每個元素是一個字典，包含 'name', 'lat', 'lon', 'stop_id', 'direction', 'sequence'
    estimated_times: 字典，鍵為站牌名稱，值為預估時間
    """
    if not stops_data:
        print(f"沒有路線 '{route_name}' 的站牌數據可輸出到 CSV。")
        return

    csv_filename = f"bus_route_{route_name}_stops.csv"
    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            # 定義 CSV 檔頭
            fieldnames = ['方向', '站序', '站牌名稱', '緯度', '經度', '站牌ID', '預估時間']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader() # 寫入標題行
            for stop in stops_data:
                est_time = estimated_times.get(stop['name'], '未知') if estimated_times else '未知'
                writer.writerow({
                    '方向': stop.get('direction', '未知'),
                    '站序': stop.get('sequence', ''),
                    '站牌名稱': stop.get('name', ''),
                    '緯度': stop.get('lat', ''),
                    '經度': stop.get('lon', ''),
                    '站牌ID': stop.get('stop_id', ''),
                    '預估時間': est_time
                })
        print(f"站牌數據已成功輸出到 '{csv_filename}'。")
    except Exception as e:
        print(f"錯誤：輸出 '{csv_filename}' 時發生問題：{e}")

# --- 主程式 ---
async def main():
    print("歡迎使用台北市公車路線查詢與地圖顯示工具！")
    print("本工具可顯示路線圖、站牌位置和預估到站時間")
    print("=============================================")

    all_bus_routes_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # 生產環境建議 True，調試時可以改為 False
        page = await browser.new_page()

        try:
            # 預先抓取所有公車路線的名稱和其對應的 route_id
            print("正在獲取所有公車路線列表，請稍候...")
            await page.goto("https://ebus.gov.taipei/ebus", timeout=60000)

            # 等待所有摺疊區塊的連結出現
            await page.wait_for_selector("a[data-toggle='collapse'][href*='#collapse']", timeout=30000)
            
            # 展開所有摺疊區塊
            for i in range(1, 23): # 根據觀察，大概有22-23個摺疊區塊
                try:
                    collapse_link_selector = f"a[href='#collapse{i}']"
                    # 使用 locator 確保元素存在且可點擊
                    collapse_link = page.locator(collapse_link_selector)

                    if await collapse_link.is_visible() and await collapse_link.get_attribute("aria-expanded") == "false":
                        await collapse_link.click()
                        # 無需額外 sleep，Playwright 會自動處理點擊後的穩定
                        # print(f"已點擊展開 #collapse{i}...") 
                    # 考慮到網頁可能預設已展開或點擊後無效，這裡不再強制延遲
                except PlaywrightTimeoutError:
                    # print(f"警告: 展開 #collapse{i} 超時，可能沒有該元素或已展開。")
                    pass # 不每個都打印，避免刷屏
                except Exception as e:
                    print(f"點擊 #collapse{i} 失敗或該元素不存在: {e}")

            # 等待所有路線列表元素載入完成 (例如等待最後一個collapse區塊中的a標籤)
            # 或者等待一個標誌性元素，確保所有路線都已渲染
            await page.wait_for_selector('div.panel-body.xidstyle ul#list li a', state='visible', timeout=100000)

            # 抓取所有公車路線
            bus_links = await page.query_selector_all("a[href*='javascript:go']")
            for link in bus_links:
                href = await link.get_attribute("href")
                name = await link.inner_text()
                if href and name:
                    try:
                        route_id_match = re.search(r"go\('([^']+)'\)", href)
                        if route_id_match:
                            route_id = route_id_match.group(1)
                            all_bus_routes_data.append({"name": name.strip(), "route_id": route_id})
                    except Exception as e:
                        print(f"處理連結 {href} 時發生錯誤：{e}，跳過此連結。")
            
            print(f"已獲取 {len(all_bus_routes_data)} 條公車路線。")

        except Exception as e:
            print(f"錯誤：無法獲取公車路線列表。原因：{e}")
            print("請檢查您的網路連接或稍後再試。程式將退出。")
            await browser.close()
            return # 退出主程式

        # --- 顯示所有可讀取的路線 ---
        if all_bus_routes_data:
            print("\n--- 可查詢的公車路線列表 ---")
            display_count = 20
            if len(all_bus_routes_data) > 2 * display_count:
                print(f"部分路線列表 (共 {len(all_bus_routes_data)} 條):")
                for i in range(display_count):
                    print(f"- {all_bus_routes_data[i]['name']}")
                print("...")
                for i in range(len(all_bus_routes_data) - display_count, len(all_bus_routes_data)):
                    print(f"- {all_bus_routes_data[i]['name']}")
            else:
                for route in all_bus_routes_data:
                    print(f"- {route['name']}")
            print("----------------------------")
        else:
            print("\n警告：未獲取到任何公車路線資訊。")

        while True:
            route_name_input = input("\n請輸入您想查詢的公車路線號碼 (例如: 299, 0東)，或輸入 'exit' 退出: ").strip()

            if route_name_input.lower() == 'exit':
                print("感謝使用，再見！")
                break

            if not route_name_input:
                print("輸入不能為空，請重試。")
                continue

            selected_route = None
            for route in all_bus_routes_data:
                if route['name'] == route_name_input:
                    selected_route = route
                    break

            if selected_route:
                print(f"您選擇的路線為: {selected_route['name']} (route_id: {selected_route['route_id']})")
                
                # 獲取路線所有資訊（站牌、時間、位置）
                # 注意：Playwright 的 page 實例在每次循環中都會重新導航，
                # 這比每次都創建新瀏覽器更高效。
                route_info = await get_bus_route_info(page, selected_route['route_id'], selected_route['name'])
                stops_data = route_info['stops_data']
                estimated_times = route_info['estimated_times']
                bus_locations = route_info['bus_locations']

                if stops_data:
                    print(f"\n--- 路線 {selected_route['name']} 預估時間資訊 (前5個站點) ---")
                    # 為確保輸出順序，對 stops_data 進行排序 (按方向和站序)
                    sorted_display_stops = sorted(stops_data, key=lambda x: (x['direction'], x['sequence']))
                    for stop in sorted_display_stops[:5]:
                        time_info = estimated_times.get(stop['name'], '未知')
                        print(f"[{stop['direction']}] {stop['name']}: {time_info}")
                    if len(stops_data) > 5:
                        print("... (更多站點資訊請查看地圖和CSV)")
                    print("--------------------------------")
                    
                    # 顯示地圖
                    display_bus_route_on_map(selected_route['name'], stops_data, bus_locations, estimated_times)
                    
                    # 導出 CSV
                    export_stops_to_csv(selected_route['name'], stops_data, estimated_times)

                else:
                    print("無法取得該路線的站牌資料。")
            else:
                print("找不到該路線，請確認輸入是否正確。")
                # 提供模糊搜尋建議
                suggestions = [route['name'] for route in all_bus_routes_data if route_name_input.lower() in route['name'].lower()]
                if suggestions:
                    print(f"您是否想找這些路線？{suggestions[:5]}")
                else:
                    print("沒有找到相關建議路線。")

        # 關閉瀏覽器
        print("正在關閉瀏覽器...")
        await browser.close()
        print("程式結束。")

# 執行主程式
if __name__ == "__main__":
    asyncio.run(main())