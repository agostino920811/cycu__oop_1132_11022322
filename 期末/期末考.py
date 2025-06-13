import asyncio
import csv
import re
import webbrowser
import folium
from playwright.async_api import async_playwright, Browser, Page

# --- 1. 使用 Playwright 獲取所有公車路線列表 (只在程式啟動時執行一次) ---
async def fetch_all_bus_routes(page: Page):
    """
    使用 Playwright 從台北市公車動態資訊系統獲取所有公車路線名稱和 route_id。
    這個函數應該只在程式啟動時執行一次。
    """
    print("正在獲取所有公車路線列表，請稍候...")
    all_routes = []
    try:
        # 將 'domcontentcontentloaded' 更正為 'domcontentloaded'
        await page.goto("https://ebus.gov.taipei/ebus", wait_until='domcontentloaded', timeout=60000)

        # 等待所有摺疊面板的連結出現
        await page.wait_for_selector("a[data-toggle='collapse'][href*='#collapse']", state='attached', timeout=30000)

        # 展開所有摺疊區塊 - 嘗試並行點擊或減少每次點擊的延遲
        collapse_links = await page.query_selector_all("a[data-toggle='collapse'][href*='#collapse']")

        # 收集所有需要點擊的Promise
        click_tasks = []
        for link in collapse_links:
            if await link.get_attribute("aria-expanded") == "false" or not await link.get_attribute("aria-expanded"):
                click_tasks.append(link.click())

        # 並行執行所有點擊操作，然後再等待一小段時間確保內容載入
        if click_tasks:
            await asyncio.gather(*click_tasks)
            await asyncio.sleep(1) # 給予頁面渲染時間，比之前總和的等待時間短很多

        # 抓取所有公車路線
        # 等待公車路線連結出現，而不是固定時間
        await page.wait_for_selector("a[href*='javascript:go']", timeout=15000)
        bus_links = await page.query_selector_all("a[href*='javascript:go']")
        for link in bus_links:
            href = await link.get_attribute("href")
            name = await link.inner_text()
            if href and name:
                route_id_match = re.search(r"go\('([^']+)'\)", href)
                if route_id_match:
                    route_id = route_id_match.group(1)
                    all_routes.append({"name": name.strip(), "route_id": route_id})
    except Exception as e:
        print(f"錯誤：無法獲取公車路線列表。原因：{e}")
    print(f"已獲取 {len(all_routes)} 條公車路線。")
    return all_routes

# --- 2. 使用 Playwright 獲取指定路線的站牌詳情和預估時間 ---
async def fetch_bus_stops_and_times(page: Page, route_id: str):
    """
    使用 Playwright 從台北市公車動態資訊系統抓取指定路線的站牌名稱、經緯度、ID、序號、方向和預估到站時間。
    返回一個包含所有站牌詳細信息的列表。
    """
    url = f"https://ebus.gov.taipei/Route/StopsOfRoute?routeid={route_id}"
    all_stops_data = [] # 包含所有站點的詳細資訊

    try:
        # 將 'domcontentcontentloaded' 更正為 'domcontentloaded'
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)

        # 等待網頁載入完成，確保去程/返程按鈕出現
        await page.wait_for_selector("p.stationlist-come-go-c", timeout=15000)

        # --- 抓取去程站點 ---
        go_button = await page.query_selector("a.stationlist-go")
        if go_button:
            await go_button.click()
            # 等待去程站點列表的元素出現
            await page.wait_for_selector("#GoDirectionRoute li .auto-list-stationlist", timeout=10000)
            go_elements = await page.query_selector_all("#GoDirectionRoute li .auto-list-stationlist")
            for element in go_elements:
                stop_info = await extract_stop_details(element, "去程")
                if stop_info:
                    all_stops_data.append(stop_info)
        else:
            print("無法找到去程按鈕。")

        # --- 抓取返程站點 ---
        return_button = await page.query_selector("a.stationlist-come")
        if return_button:
            await return_button.click()
            # 等待返程站點列表的元素出現
            await page.wait_for_selector("#BackDirectionRoute li .auto-list-stationlist", timeout=10000)
            return_elements = await page.query_selector_all("#BackDirectionRoute li .auto-list-stationlist")
            for element in return_elements:
                stop_info = await extract_stop_details(element, "返程")
                if stop_info:
                    all_stops_data.append(stop_info)
        else:
            print("無法找到返程按鈕。")

    except Exception as e:
        print(f"[錯誤] 獲取路線 {route_id} 站牌數據失敗：{e}")

    # 確保站點是唯一的（以防萬一），並根據方向和序號排序
    unique_stops_map = {}
    for stop in all_stops_data:
        key = (stop.get('stop_id'), stop.get('direction'))
        unique_stops_map[key] = stop

    sorted_stops_data = sorted(list(unique_stops_map.values()), key=lambda x: (x.get('direction', ''), x.get('sequence', 0)))

    print(f"路線 {route_id} 的站牌數據和預估時間獲取完成。共 {len(sorted_stops_data)} 站。")
    return sorted_stops_data

async def extract_stop_details(element, direction):
    """
    從 Playwright 的元素中提取站牌的詳細資訊。
    """
    name_elem = await element.query_selector(".auto-list-stationlist-place")
    status_elem = await element.query_selector(".auto-list-stationlist-position")
    number_elem = await element.query_selector(".auto-list-stationlist-number")
    stop_id_elem = await element.query_selector("input[name='item.UniStopId']")
    latitude_elem = await element.query_selector("input[name='item.Latitude']")
    longitude_elem = await element.query_selector("input[name='item.Longitude']")

    name_text = await name_elem.inner_text() if name_elem else "未知站名"
    status_text = await status_elem.inner_text() if status_elem else "無資料"
    number_text = await number_elem.inner_text() if number_elem else "未知序號"
    stop_id_value = await stop_id_elem.get_attribute("value") if stop_id_elem else "未知編號"
    latitude_value = await latitude_elem.get_attribute("value") if latitude_elem else "未知緯度"
    longitude_value = await longitude_elem.get_attribute("value") if longitude_elem else "未知經度"

    try:
        lat = float(latitude_value)
        lon = float(longitude_value)
    except ValueError:
        lat = None
        lon = None
        print(f"警告：站點 '{name_text}' 經緯度無效，已跳過。")
        return None

    return {
        "direction": direction,
        "estimated_time": status_text.strip(),
        "sequence": int(number_text.strip()) if number_text.strip().isdigit() else None,
        "name": name_text.strip(),
        "stop_id": stop_id_value.strip(),
        "lat": lat,
        "lon": lon
    }

# --- 新增功能：根據起訖站查詢路線 ---
async def find_routes_between_stops(page: Page, all_bus_routes: list, origin_stop: str, destination_stop: str):
    """
    根據起點站和終點站查找包含這兩個站點且方向正確的公車路線。
    返回一個列表，每個元素包含路線名稱、route_id 和符合方向的站牌數據。
    """
    found_routes = []
    print(f"\n正在查詢從 '{origin_stop}' 到 '{destination_stop}' 的公車路線，請稍候...")

    # For large number of routes, fetching all stops for every route can be slow.
    # Consider caching stop data if this becomes a performance bottleneck for frequent queries.
    for route in all_bus_routes:
        route_name = route['name']
        route_id = route['route_id']
        print(f"檢查路線: {route_name}...")
        
        stops_data = await fetch_bus_stops_and_times(page, route_id)

        # Separate stops by direction
        go_direction_stops = [s for s in stops_data if s['direction'] == '去程']
        return_direction_stops = [s for s in stops_data if s['direction'] == '返程']

        # Check '去程' (Go Direction)
        origin_go_idx = -1
        destination_go_idx = -1
        for i, stop in enumerate(go_direction_stops):
            if origin_stop.lower() in stop['name'].lower():
                origin_go_idx = i
            if destination_stop.lower() in stop['name'].lower():
                destination_go_idx = i

        if origin_go_idx != -1 and destination_go_idx != -1 and origin_go_idx < destination_go_idx:
            found_routes.append({
                "route_name": route_name,
                "route_id": route_id,
                "direction": "去程",
                "stops_data": go_direction_stops # Only store relevant direction stops
            })
            print(f"找到符合路線 (去程): {route_name}")


        # Check '返程' (Return Direction)
        origin_return_idx = -1
        destination_return_idx = -1
        for i, stop in enumerate(return_direction_stops):
            if origin_stop.lower() in stop['name'].lower():
                origin_return_idx = i
            if destination_stop.lower() in stop['name'].lower():
                destination_return_idx = i

        if origin_return_idx != -1 and destination_return_idx != -1 and origin_return_idx < destination_return_idx:
            found_routes.append({
                "route_name": route_name,
                "route_id": route_id,
                "direction": "返程",
                "stops_data": return_direction_stops # Only store relevant direction stops
            })
            print(f"找到符合路線 (返程): {route_name}")

    return found_routes

# --- 3. 顯示地圖函式 (不變) ---
def display_bus_route_on_map(route_name, stops_data):
    """
    將公車路線、站牌和預估時間顯示在地圖上。
    stops_data: 列表，每個元素是一個字典，包含 'name', 'lat', 'lon', 'estimated_time', 'direction', 'sequence'
    """
    if not stops_data:
        print(f"沒有路線 '{route_name}' 的站牌數據可顯示。")
        return

    print(f"\n正在為路線 '{route_name}' 生成地圖...")

    # 以所有站牌的中心點為地圖中心
    valid_stops = [s for s in stops_data if s["lat"] is not None and s["lon"] is not None]
    if not valid_stops:
        print("沒有有效的站點座標來生成地圖。")
        return

    avg_lat = sum(s["lat"] for s in valid_stops) / len(valid_stops)
    avg_lon = sum(s["lon"] for s in valid_stops) / len(valid_stops)
    map_center = [avg_lat, avg_lon]
    m = folium.Map(location=map_center, zoom_start=13)

    # 添加站牌標記和彈出視窗
    for stop in stops_data:
        stop_name = stop.get("name", "未知站名")
        coords = [stop.get("lat"), stop.get("lon")]
        est_time_text = stop.get("estimated_time", "未知")
        direction_text = stop.get("direction", "未知")
        sequence_text = stop.get("sequence", "N/A")

        if coords[0] is None or coords[1] is None:
            continue # 跳過無效座標的站點

        # 根據預估時間設置不同的顏色
        if est_time_text in ["進站中", "即將到站"]:
            icon_color = "red"
        else:
            icon_color = "blue"

        popup_html = f"""
        <div style='font-family: Arial; width: 200px;'>
            <b style='font-size: 14px;'>{stop_name}</b><br>
            <hr style='margin: 5px 0;'>
            <span style='color: #2E8B57;'><b>預估時間:</b></span> {est_time_text}<br>
            <span style='color: #4682B4;'><b>方向:</b></span> {direction_text}<br>
            <span style='color: #4682B4;'><b>站序:</b></span> {sequence_text}<br>
            <span style='color: #666;'><b>座標:</b></span> {coords[0]:.6f}, {coords[1]:.6f}
        </div>
        """

        folium.Marker(
            location=coords,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{stop_name} - {est_time_text}",
            icon=folium.Icon(color=icon_color, icon="info-sign")
        ).add_to(m)

    # 繪製路線路徑 (分開去程和返程繪製)
    go_direction_stops = sorted([s for s in stops_data if s.get('direction') == '去程' and s.get('lat') is not None and s.get('lon') is not None], key=lambda x: x.get('sequence', 0))
    return_direction_stops = sorted([s for s in stops_data if s.get('direction') == '返程' and s.get('lat') is not None and s.get('lon') is not None], key=lambda x: x.get('sequence', 0))

    if len(go_direction_stops) > 1:
        go_route_coords_list = [[stop["lat"], stop["lon"]] for stop in go_direction_stops]
        folium.PolyLine(
            locations=go_route_coords_list,
            color='green',
            weight=4,
            opacity=0.8,
            tooltip=f"路線: {route_name} (去程)"
        ).add_to(m)
        print(f"已繪製 {route_name} 去程路線 ({len(go_route_coords_list)} 點)。")

    if len(return_direction_stops) > 1:
        return_route_coords_list = [[stop["lat"], stop["lon"]] for stop in return_direction_stops]
        folium.PolyLine(
            locations=return_route_coords_list,
            color='purple',
            weight=4,
            opacity=0.8,
            tooltip=f"路線: {route_name} (返程)"
        ).add_to(m)
        print(f"已繪製 {route_name} 返程路線 ({len(return_route_coords_list)} 點)。")

    # 添加圖例
    legend_html = '''
    <div style="position: fixed;
                top: 10px; right: 10px; width: 200px; height: 160px;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:14px; padding: 10px">
    <b>圖例說明</b><br>
    🔴 進站中/即將到站<br>
    🔵 其他站點<br>
    🟢 去程路線<br>
    🟣 返程路線
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

# --- 4. 將站牌數據輸出為 CSV 檔案的函式 (不變) ---
def export_stops_to_csv(route_name, stops_data):
    """
    將公車路線的站牌數據輸出為 CSV 檔案。
    stops_data: 列表，每個元素是一個字典，包含 'name', 'lat', 'lon', 'stop_id', 'sequence', 'direction', 'estimated_time'
    """
    if not stops_data:
        print(f"沒有路線 '{route_name}' 的站牌數據可輸出到 CSV。")
        return

    csv_filename = f"bus_route_{route_name}_stops.csv"
    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            # 定義 CSV 檔頭
            fieldnames = ['方向', '站序', '站牌名稱', '站牌ID', '緯度', '經度', '預估時間']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader() # 寫入標題行
            for stop in stops_data:
                writer.writerow({
                    '方向': stop.get('direction', ''),
                    '站序': stop.get('sequence', ''),
                    '站牌名稱': stop.get('name', ''),
                    '站牌ID': stop.get('stop_id', ''),
                    '緯度': stop.get('lat', ''),
                    '經度': stop.get('lon', ''),
                    '預估時間': stop.get('estimated_time', '')
                })
        print(f"站牌數據已成功輸出到 '{csv_filename}'。")
    except Exception as e:
        print(f"錯誤：輸出 '{csv_filename}' 時發生問題：{e}")

# --- 主程式 ---
async def main():
    print("歡迎使用台北市公車路線查詢與地圖顯示工具！")
    print("本工具可顯示路線圖、站牌位置和預估到站時間")
    print("=============================================")

    # 啟動 Playwright 瀏覽器實例，並在整個會話中重複使用
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # 可以設置為 False 觀察流程
        page = await browser.new_page()

        # 只在程式啟動時獲取一次所有公車路線列表
        all_bus_routes_data = await fetch_all_bus_routes(page)

        while True:
            print("\n請選擇查詢模式:")
            print("1. 依公車路線號碼查詢 (例如: 299, 0東)")
            print("2. 依起訖站點查詢 (例如: 台北車站, 國父紀念館)")
            print("輸入 'exit' 退出程式")

            choice = input("請輸入您的選擇 (1 或 2): ").strip()

            if choice.lower() == 'exit':
                print("感謝使用，再見！")
                break

            if choice == '1':
                route_name_input = input("\n請輸入您想查詢的公車路線號碼: ").strip()

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

                    # 使用 Playwright 抓取所有站牌詳情和預估時間 (重複使用已開啟的 page)
                    stops_data_with_times = await fetch_bus_stops_and_times(page, selected_route['route_id'])

                    if stops_data_with_times:
                        print(f"\n--- 路線 {selected_route['name']} 預估時間資訊 ---")
                        # 只顯示前5個站點，避免輸出過多
                        for i, stop in enumerate(stops_data_with_times):
                            if i >= 5:
                                break
                            print(f"{stop['name']} ({stop['direction']} 站序 {stop['sequence']}): {stop['estimated_time']}")
                        if len(stops_data_with_times) > 5:
                            print("... (更多站點資訊請查看地圖和 CSV 檔案)")
                        print("--------------------------------")

                        # 顯示地圖
                        display_bus_route_on_map(selected_route['name'], stops_data_with_times)

                        # 將資料輸出到 CSV
                        export_stops_to_csv(selected_route['name'], stops_data_with_times)

                    else:
                        print("無法取得該路線的站牌資料。")
                else:
                    print("找不到該路線，請確認輸入是否正確。")
                    suggestions = [route['name'] for route in all_bus_routes_data if route_name_input.lower() in route['name'].lower()]
                    if suggestions:
                        print(f"您是否想找這些路線？{suggestions[:5]}")

            elif choice == '2':
                origin_stop_input = input("請輸入您的起點站名稱: ").strip()
                if not origin_stop_input:
                    print("起點站名稱不能為空，請重試。")
                    continue

                destination_stop_input = input("請輸入您的目的站名稱: ").strip()
                if not destination_stop_input:
                    print("目的站名稱不能為空，請重試。")
                    continue

                # 查找符合條件的路線
                matching_routes = await find_routes_between_stops(page, all_bus_routes_data, origin_stop_input, destination_stop_input)

                if matching_routes:
                    print(f"\n找到以下從 '{origin_stop_input}' 到 '{destination_stop_input}' 的公車路線:")
                    for i, route_info in enumerate(matching_routes):
                        print(f"{i+1}. 路線: {route_info['route_name']} (方向: {route_info['direction']})")

                    while True:
                        try:
                            selection = input("請輸入您想查看的路線編號，或輸入 '0' 返回主選單: ").strip()
                            if selection == '0':
                                break
                            selected_index = int(selection) - 1
                            if 0 <= selected_index < len(matching_routes):
                                selected_route_info = matching_routes[selected_index]
                                print(f"\n您選擇了路線: {selected_route_info['route_name']} ({selected_route_info['direction']})")

                                # 直接使用已經獲取並篩選過的站牌數據
                                stops_data_to_display = selected_route_info['stops_data']

                                if stops_data_to_display:
                                    print(f"\n--- 路線 {selected_route_info['route_name']} ({selected_route_info['direction']}) 預估時間資訊 ---")
                                    for i, stop in enumerate(stops_data_to_display):
                                        if i >= 5: # Limit output to console
                                            break
                                        print(f"{stop['name']} ({stop['direction']} 站序 {stop['sequence']}): {stop['estimated_time']}")
                                    if len(stops_data_to_display) > 5:
                                        print("... (更多站點資訊請查看地圖和 CSV 檔案)")
                                    print("--------------------------------")

                                    # 顯示地圖
                                    display_bus_route_on_map(f"{selected_route_info['route_name']} ({selected_route_info['direction']})", stops_data_to_display)

                                    # 將資料輸出到 CSV
                                    export_stops_to_csv(f"{selected_route_info['route_name']}_{selected_route_info['direction']}", stops_data_to_display)
                                else:
                                    print("該路線方向沒有可用的站牌數據。")
                                break # Exit inner loop after displaying
                            else:
                                print("無效的路線編號，請重新輸入。")
                        except ValueError:
                            print("無效的輸入，請輸入數字。")

                else:
                    print(f"沒有找到從 '{origin_stop_input}' 到 '{destination_stop_input}' 的公車路線。")

            else:
                print("無效的選擇，請輸入 '1', '2' 或 'exit'。")

        await browser.close() # 在主程式結束時關閉瀏覽器

if __name__ == "__main__":
    asyncio.run(main())