import pandas as pd
import matplotlib.pyplot as plt

# 1. 讀取 CSV 文件
route_1 = pd.read_csv('bus_route_0161000900.csv', encoding='utf-8')
route_2 = pd.read_csv('bus_route_0161001500.csv', encoding='utf-8')

# 合併兩條路線的數據
routes = pd.concat([route_1, route_2])

# 確保有「車站編號」欄位
if '車站編號' not in routes.columns:
    raise ValueError("CSV 文件中缺少 '車站編號' 欄位")

# 2. 繪製路線圖
plt.figure(figsize=(12, 8))

# 繪製每條路線
for station_id, station_data in routes.groupby('車站編號'):
    plt.plot(station_data['longitude'], station_data['latitude'], marker='o', label=f'Station {station_id}')

# 添加圖例和標籤
plt.title('Bus Route Map')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.legend()
plt.grid()

# 顯示圖形
plt.show()