import asyncio
import csv
import re
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
        await page.goto("https://ebus.gov.taipei/ebus", wait_until='domcontentloaded', timeout=60000)

        await page.wait_for_selector("a[data-toggle='collapse'][href*='#collapse']", state='attached', timeout=30000)

        collapse_links = await page.query_selector_all("a[data-toggle='collapse'][href*='#collapse']")

        click_tasks = []
        for link in collapse_links:
            if await link.get_attribute("aria-expanded") == "false" or not await link.get_attribute("aria-expanded"):
                click_tasks.append(link.click())

        if click_tasks:
            await asyncio.gather(*click_tasks)
            await asyncio.sleep(1)

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

# --- 2. 使用 Playwright 獲取指定路線的站牌詳情 (無預估時間，因為是靜態爬取) ---
async def fetch_bus_stops_details(page: Page, route_id: str):
    """
    使用 Playwright 從台北市公車動態資訊系統抓取指定路線的站牌名稱、經緯度、ID、序號、方向。
    此函數用於靜態爬取所有站點信息，不包含實時預估時間。
    返回一個包含所有站牌詳細信息的列表。
    """
    url = f"https://ebus.gov.taipei/Route/StopsOfRoute?routeid={route_id}"
    all_stops_data = []

    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_selector("p.stationlist-come-go-c", timeout=15000)

        # --- 抓取去程站點 ---
        go_button = await page.query_selector("a.stationlist-go")
        if go_button:
            await go_button.click()
            await page.wait_for_selector("#GoDirectionRoute li .auto-list-stationlist", timeout=10000)
            go_elements = await page.query_selector_all("#GoDirectionRoute li .auto-list-stationlist")
            for element in go_elements:
                stop_info = await extract_stop_details_static(element, "去程")
                if stop_info:
                    all_stops_data.append(stop_info)

        # --- 抓取返程站點 ---
        return_button = await page.query_selector("a.stationlist-come")
        if return_button:
            await return_button.click()
            await page.wait_for_selector("#BackDirectionRoute li .auto-list-stationlist", timeout=10000)
            return_elements = await page.query_selector_all("#BackDirectionRoute li .auto-list-stationlist")
            for element in return_elements:
                stop_info = await extract_stop_details_static(element, "返程")
                if stop_info:
                    all_stops_data.append(stop_info)

    except Exception as e:
        print(f"[錯誤] 獲取路線 {route_id} 站牌數據失敗：{e}")

    # No need for unique_stops_map here as deduplication will happen in main_crawler
    # Just sort for consistency
    sorted_stops_data = sorted(all_stops_data, key=lambda x: (x.get('direction', ''), x.get('sequence', 0)))

    return sorted_stops_data

async def extract_stop_details_static(element, direction):
    """
    從 Playwright 的元素中提取站牌的詳細資訊（用於靜態爬取）。
    """
    name_elem = await element.query_selector(".auto-list-stationlist-place")
    number_elem = await element.query_selector(".auto-list-stationlist-number")
    stop_id_elem = await element.query_selector("input[name='item.UniStopId']")
    latitude_elem = await element.query_selector("input[name='item.Latitude']")
    longitude_elem = await element.query_selector("input[name='item.Longitude']")

    name_text = await name_elem.inner_text() if name_elem else "未知站名"
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
        return None

    return {
        "direction": direction,
        "sequence": int(number_text.strip()) if number_text.strip().isdigit() else None,
        "name": name_text.strip(),
        "stop_id": stop_id_value.strip(),
        "lat": lat,
        "lon": lon,
        "estimated_time": "N/A" # 在靜態爬取中，預估時間是無效的
    }

# --- 3. 將所有站牌數據輸出為 CSV 檔案 ---
def export_all_stops_to_csv(all_data):
    """
    將所有公車路線的所有站牌數據輸出為單一 CSV 檔案。
    """
    csv_filename = "all_taipei_bus_stops.csv"
    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['路線名稱', '路線ID', '方向', '站序', '站牌名稱', '站牌ID', '緯度', '經度', '預估時間']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for row in all_data:
                writer.writerow(row)
        print(f"\n✅ 所有公車路線站牌數據已成功輸出到 '{csv_filename}'。")
    except Exception as e:
        print(f"錯誤：輸出 '{csv_filename}' 時發生問題：{e}")

# --- 主爬蟲程式 ---
async def main_crawler():
    print("🚀 正在啟動台北市公車全路線站牌數據爬取程序...")
    all_collected_stops = []
    # Use a set to store unique keys of already added stops to prevent duplicates
    # Key format: (route_id, direction, stop_id, sequence)
    processed_stop_keys = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        all_bus_routes = await fetch_all_bus_routes(page)

        total_routes = len(all_bus_routes)
        for i, route in enumerate(all_bus_routes):
            route_name = route['name']
            route_id = route['route_id']
            print(f"[{i+1}/{total_routes}] 正在爬取路線: {route_name} (ID: {route_id})...")
            stops_details = await fetch_bus_stops_details(page, route_id)

            for stop in stops_details:
                # Create a unique key for the stop based on route, direction, stop_id, and sequence
                # This ensures we don't add the same physical stop on the same route/direction twice
                unique_key = (route_id, stop.get('direction'), stop.get('stop_id'), stop.get('sequence'))

                if unique_key not in processed_stop_keys:
                    row = {
                        '路線名稱': route_name,
                        '路線ID': route_id,
                        '方向': stop.get('direction', ''),
                        '站序': stop.get('sequence', ''),
                        '站牌名稱': stop.get('name', ''),
                        '站牌ID': stop.get('stop_id', ''),
                        '緯度': stop.get('lat', ''),
                        '經度': stop.get('lon', ''),
                        '預估時間': stop.get('estimated_time', '')
                    }
                    all_collected_stops.append(row)
                    processed_stop_keys.add(unique_key) # Add the key to the set
            await asyncio.sleep(0.1) # Short delay to be polite to the server

        await browser.close()

    # Final check for duplicates based on the CSV row's core identifying columns
    # This is a safeguard, but the set-based deduplication above should handle most cases.
    # If pandas is available, this would be more robust:
    # import pandas as pd
    # df = pd.DataFrame(all_collected_stops)
    # df.drop_duplicates(subset=['路線名稱', '路線ID', '方向', '站序', '站牌ID'], inplace=True)
    # all_collected_stops = df.to_dict('records')

    export_all_stops_to_csv(all_collected_stops)
    print("\n🎉 爬取任務完成！")

if __name__ == "__main__":
    asyncio.run(main_crawler())