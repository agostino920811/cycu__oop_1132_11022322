from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import csv
import time

options = Options()
options.add_argument("--headless=new")  # 使用新 Headless 模式
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-extensions")
options.add_argument("--blink-settings=imagesEnabled=false")  # 不加載圖片
options.page_load_strategy = 'eager'  # 不等全部資源下載完就繼續跑

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get("https://ebus.gov.taipei/ebus")

wait = WebDriverWait(driver, 1)
wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='javascript:go']")))

# 抓取所有公車路線連結
link_data = []
for link in driver.find_elements(By.CSS_SELECTOR, "a[href*='javascript:go']"):
    href = link.get_attribute("href")
    name = link.text.strip()
    if href and name:
        link_data.append((href, name))

results = []

for href, bus_name in link_data:
    try:
        route_id = href.split("('")[1].split("')")[0]
        detail_url = f"https://ebus.gov.taipei/EBus/VsSimpleMap?routeid={route_id}&gb=1"
        driver.get(detail_url)

        # 等待站牌區出現
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#plMapStops .snz > span")))

        time.sleep(0.5)  # 小延遲，避免動態渲染不完整

        stop_spans = driver.find_elements(By.CSS_SELECTOR, "#plMapStops .snz > span")
        for span in stop_spans:
            stop_name = span.text.strip()
            if stop_name:
                results.append([bus_name, stop_name])
        print(f"[完成] {bus_name}：{len(stop_spans)} 站")

    except Exception as e:
        print(f"[警告] {bus_name} 抓取失敗：{e}")

# 寫入 CSV 檔
with open("bus_data.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["公車名稱", "站牌名稱"])
    writer.writerows(results)

driver.quit()
print("✅ 完成！已寫入 bus_data.csv")