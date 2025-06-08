import asyncio
import csv
from playwright.async_api import async_playwright

async def fetch_bus_stops(route_id):
    url = f"https://ebus.gov.taipei/Route/StopsOfRoute?routeid={route_id}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 啟動瀏覽器（非無頭模式，方便除錯）
        page = await browser.new_page()
        await page.goto(url)

        # 等待網頁載入完成
        try:
            await page.wait_for_selector("p.stationlist-come-go-c", timeout=15000)  # 等待切換按鈕出現
        except Exception as e:
            print("無法找到切換按鈕，請檢查網頁結構。")
            await browser.close()
            return []

        all_results = []

        # 點擊去程按鈕並抓取去程站點資訊
        go_button = await page.query_selector("a.stationlist-go")
        if go_button:
            await go_button.click()
            await page.wait_for_timeout(5000)  # 等待 5 秒，確保資料完全載入
            go_direction = await page.query_selector("#GoDirectionRoute")
            go_stops = await fetch_with_retry(page, "#GoDirectionRoute li .auto-list-stationlist")
            go_results = await extract_stops(go_stops, "去程")
            all_results.extend(go_results)
        else:
            print("無法找到去程按鈕。")

        # 點擊返程按鈕並抓取返程站點資訊
        return_button = await page.query_selector("a.stationlist-come")
        if return_button:
            await return_button.click()
            await page.wait_for_timeout(5000)  # 等待 5 秒，確保資料完全載入
            return_direction = await page.query_selector("#BackDirectionRoute")
            return_stops = await fetch_with_retry(page, "#BackDirectionRoute li .auto-list-stationlist")
            return_results = await extract_stops(return_stops, "返程")
            all_results.extend(return_results)
        else:
            print("無法找到返程按鈕。")

        await browser.close()

        # 將所有結果輸出為單一 CSV 檔案
        save_to_csv(all_results, f"bus_stops_{route_id}.csv")

        print(f"資料已成功輸出至 bus_stops_{route_id}.csv")
        return all_results


async def fetch_with_retry(page, selector, retries=3):
    for i in range(retries):
        try:
            await page.wait_for_selector(selector, timeout=15000)
            return await page.query_selector_all(selector)
        except Exception as e:
            print(f"嘗試第 {i+1} 次失敗，重試中...")
            await page.wait_for_timeout(2000)  # 等待 2 秒後重試
    print("多次嘗試後仍無法獲取資料。")
    return []


async def extract_stops(stops, direction):
    results = []
    for stop in stops:
        # 抓取站點名稱
        name = await stop.query_selector(".auto-list-stationlist-place")
        name_text = await name.inner_text() if name else "未知站名"

        # 抓取到站狀態（進站時間或進站中）
        status = await stop.query_selector(".auto-list-stationlist-position")
        status_text = await status.inner_text() if status else "無資料"

        # 抓取站點編號
        stop_id = await stop.query_selector("input#item_UniStopId")
        stop_id_value = await stop_id.get_attribute("value") if stop_id else "未知編號"

        # 抓取緯度
        latitude = await stop.query_selector("input#item_Latitude")
        latitude_value = await latitude.get_attribute("value") if latitude else "未知緯度"

        # 抓取經度
        longitude = await stop.query_selector("input#item_Longitude")
        longitude_value = await longitude.get_attribute("value") if longitude else "未知經度"

        # 抓取站點序號
        number = await stop.query_selector(".auto-list-stationlist-number")
        number_text = await number.inner_text() if number else "未知序號"

        results.append({
            "方向": direction,
            "公車到達時間": status_text.strip() if status_text.strip() else "無資料",
            "車站序號": number_text.strip(),
            "車站名稱": name_text.strip(),
            "車站編號": stop_id_value.strip(),
            "經緯度座標": f"{latitude_value.strip()},{longitude_value.strip()}"
        })
    return results


def save_to_csv(results, filename):
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["方向", "公車到達時間", "車站序號", "車站名稱", "車站編號", "經緯度座標 latitude", "longitude"])  # 寫入標題
        for result in results:
            writer.writerow([
                result["方向"],
                result["公車到達時間"],
                result["車站序號"],
                result["車站名稱"],
                result["車站編號"],
                result["經緯度座標"].split(",")[0],  # 緯度
                result["經緯度座標"].split(",")[1]   # 經度
            ])


# 主程式執行
if __name__ == "__main__":
    route_id = input("請輸入公車代碼: ")
    asyncio.run(fetch_bus_stops(route_id))