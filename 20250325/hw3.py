import requests
from bs4 import BeautifulSoup
import re  # 用於正則表達式匹配

url = "https://pda5284.gov.taipei/MQS/route.jsp?rid=10417"
response = requests.get(url)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 鎖定「去程 (往松山車站)」下方的表格
    target_header = soup.find('td', string=re.compile(r'去程 \(往松山車站\)'))
    
    if not target_header:
        print("找不到去程標題")
    else:
        # 找到最近的父表格容器
        table = target_header.find_next('table')
        
        # 提取所有車站名稱（注意特殊符號處理）
        stations = []
        for row in table.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 1:
                # 去除末尾...和空白
                station = cells[0].text.strip().replace('...', '')
                stations.append(station)
        
        # 建立車站名稱與索引的對應 (用於演示)
        station_times = {station: f"{i+1}分鐘" for i, station in enumerate(stations)}
        
        

        # 用戶查詢
        search = input("請輸入車站名稱：").strip()
        if search in station_times:
            print(f"{search} 預估到達時間：{station_times[search]}")
        else:
            print(f"找不到 '{search}'，請檢查：")
            print("1. 是否包含『...』等省略符號")
            print("2. 是否完全符合站名（含全形括號）")
            print("3. 完整車站列表：")
            print('\n'.join(station_times.keys()))
else:
    print(f"連線失敗，狀態碼：{response.status_code}")