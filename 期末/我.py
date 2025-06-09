import asyncio
import csv
import re
import webbrowser
import folium
from playwright.async_api import async_playwright

# --- 1. 使用 Playwright 獲取所有公車路線列表 ---
async def fetch_all_bus_routes():
    """
    使用 Playwright 從台北市公車動態資訊系統獲取所有公車路線名稱和 route_id。
    """
    print("正在獲取所有公車路線列表，請稍候...")
    all_routes = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # 可以設置為 False 觀察流程
        page = await browser.new_page()
        try:
            await page.goto("https://ebus.gov.taipei/ebus", wait_until='domcontentloaded', timeout=60000)
            
            # 等待所有摺疊面板的連結出現
            await page.wait_for_selector("a[data-toggle='collapse'][href*='#collapse']", timeout=30000)
            await asyncio.sleep(3) # 給予足夠時間讓頁面內容載入

            # 展開所有摺疊區塊
            collapse_links = await page.query_selector_all("a[data-toggle='collapse'][href*='#collapse']")
            for link in collapse_links:
                if await link.get_attribute("aria-expanded") == "false" or not await link.get_attribute("aria-expanded"):
                    await link.click()
                    await asyncio.sleep(0.5) # 每次點擊後稍作延遲

            await asyncio.sleep(3) # 再次延遲確保所有內容載入

            # 抓取所有公車路線
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
        finally:
            await browser.close()
    print(f"已獲取 {len(all_routes)} 條公車路線。")
    return all_routes

# --- 2. 使用 Playwright 獲取指定路線的站牌詳情和預估時間 ---
async def fetch_bus_stops_and_times(route_id):
    """
    使用 Playwright 從台北市公車動態資訊系統抓取指定路線的站牌名稱、經緯度、ID、序號、方向和預估到站時間。
    返回一個包含所有站牌詳細信息的列表。
    """
    url = f"https://ebus.gov.taipei/Route/StopsOfRoute?routeid={route_id}"
    all_stops_data = [] # 包含所有站點的詳細資訊

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # 等待網頁載入完成，確保去程/返程按鈕出現
            await page.wait_for_selector("p.stationlist-come-go-c", timeout=15000)
            await asyncio.sleep(2) # 額外等待確保渲染

            # --- 抓取去程站點 ---
            go_button = await page.query_selector("a.stationlist-go")
            if go_button:
                await go_button.click()
                await page.wait_for_timeout(3000)
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
                await page.wait_for_timeout(3000)
                return_elements = await page.query_selector_all("#BackDirectionRoute li .auto-list-stationlist")
                for element in return_elements:
                    stop_info = await extract_stop_details(element, "返程")
                    if stop_info:
                        all_stops_data.append(stop_info)
            else:
                print("無法找到返程按鈕。")

        except Exception as e:
            print(f"[錯誤] 獲取路線 {route_id} 站牌數據失敗：{e}")
        finally:
            await browser.close()
    
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

# --- 3. 顯示地圖函式 ---
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
    avg_lat = sum(s["lat"] for s in stops_data if s["lat"] is not None) / len(stops_data)
    avg_lon = sum(s["lon"] for s in stops_data if s["lon"] is not None) / len(stops_data)
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
        elif "分" in est_time_text:
            try:
                minutes = int(re.search(r'(\d+)', est_time_text).group(1))
                if minutes <= 5:
                    icon_color = "orange"
                elif minutes <= 15:
                    icon_color = "blue"
                else:
                    icon_color = "gray"
            except:
                icon_color = "blue"
        else:
            icon_color = "gray"
        
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
    🟠 5分鐘內<br>
    🔵 5-15分鐘<br>
    ⚫ 15分鐘以上/無資訊<br>
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

# --- 4. 將站牌數據輸出為 CSV 檔案的函式 ---
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

    # 獲取所有公車路線列表
    all_bus_routes_data = await fetch_all_bus_routes()

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
        return

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
            
            # 使用 Playwright 抓取所有站牌詳情和預估時間
            stops_data_with_times = await fetch_bus_stops_and_times(selected_route['route_id'])
            
            if stops_data_with_times:
                print(f"\n--- 路線 {selected_route['name']} 預估時間資訊 ---")
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

if __name__ == "__main__":
    asyncio.run(main())