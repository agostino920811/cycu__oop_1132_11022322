import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib
from shapely.geometry import Point, LineString
import os

# 設定中文字型（支援中文）
matplotlib.rcParams['font.family'] = 'Microsoft JhengHei'
matplotlib.rcParams['axes.unicode_minus'] = False

def read_route_csv(csv_path):
    """
    讀取公車路線 CSV 檔案並轉換為 GeoDataFrame。
    """
    df = pd.read_csv(csv_path, encoding='utf-8')
    geometry = [Point(lon, lat) for lon, lat in zip(df["longitude"], df["latitude"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    return gdf

def plot_combined_map(bus_route_files: list, shp_dir: str, output_file: str):
    """
    繪製結合公車路線和北北基桃地理範圍的地圖。
    """
    fig, ax = plt.subplots(figsize=(12, 12))

    # --- 處理台灣行政區地理資料 ---
    shp_files = []
    for fname in os.listdir(shp_dir):
        if fname.endswith(".shp"):
            shp_files.append(os.path.join(shp_dir, fname))

    gdfs = []
    if not shp_files:
        print(f"警告：在 {shp_dir} 中沒有找到任何 .shp 檔案。")
    else:
        for shp_file in shp_files:
            try:
                gdf_temp = gpd.read_file(shp_file)
                gdfs.append(gdf_temp)
                print(f"成功載入：{shp_file}")
            except Exception as e:
                print(f"載入 {shp_file} 錯誤：{e}")

    if gdfs:
        # 統一所有GeoDataFrame的CRS
        crs_to_use = gdfs[0].crs
        aligned_gdfs = []
        for gdf in gdfs:
            if gdf.crs != crs_to_use:
                aligned_gdfs.append(gdf.to_crs(crs_to_use))
            else:
                aligned_gdfs.append(gdf)

        combined_gdf = pd.concat(aligned_gdfs, ignore_index=True)

        # 定義北北基桃的縣市名稱列表 (中文和英文映射)
        county_name_map = {
            '臺北市': 'Taipei City',
            '台北市': 'Taipei City',
            '新北市': 'New Taipei City',
            '基隆市': 'Keelung City',
            '桃園市': 'Taoyuan City',
            '桃园市': 'Taoyuan City'
        }

        if 'COUNTYNAME' in combined_gdf.columns:
            north_regions_gdf = combined_gdf[
                combined_gdf['COUNTYNAME'].isin(list(county_name_map.keys()))
            ].copy()

            if north_regions_gdf.empty:
                print("警告：未找到指定名稱的北北基桃區域 ('COUNTYNAME' 欄位)。")
                print("可用的 COUNTYNAMEs:", combined_gdf['COUNTYNAME'].unique())
                # 如果沒有找到北北基桃，還是繪製所有載入的 shapefile，但沒有篩選
                combined_gdf.plot(ax=ax, edgecolor='black', linewidth=0.5, cmap='viridis', alpha=0.7)
                ax.set_title("載入的所有行政區地圖 (未篩選)")
            else:
                north_regions_gdf['COUNTYNAME_EN'] = north_regions_gdf['COUNTYNAME'].map(county_name_map)
                
                # 繪製北北基桃的 GeoDataFrame
                north_regions_gdf.plot(ax=ax, edgecolor='black', linewidth=0.5, 
                                       column='COUNTYNAME_EN', cmap='Paired', legend=True, alpha=0.7)
                print("成功繪製北北基桃區域。")
        else:
            print("警告：GeoDataFrame 中沒有 'COUNTYNAME' 欄位。無法按縣市名稱篩選。")
            print("可用欄位：", combined_gdf.columns.tolist())
            # 如果沒有 COUNTYNAME，繪製所有載入的 shapefile
            combined_gdf.plot(ax=ax, edgecolor='black', linewidth=0.5, cmap='viridis', alpha=0.7)
            ax.set_title("載入的所有行政區地圖 (無 COUNTYNAME 欄位)")
    else:
        print("沒有任何 GeoDataFrame 被成功載入。")
        ax.set_title("地圖：無地理資料載入")


    # --- 處理公車路線資料 ---
    bus_colors = ['blue', 'green'] 
    for idx, file in enumerate(bus_route_files):
        try:
            gdf_bus = read_route_csv(file)
            bus_color = bus_colors[idx % len(bus_colors)]

            # 將公車路線資料轉換為與行政區相同的 CRS (如果行政區有載入)
            if gdfs and gdfs[0].crs:
                gdf_bus = gdf_bus.to_crs(gdfs[0].crs)
            
            # 繪製點 (可選，如果不需要點，可以註解掉這行)
            gdf_bus.plot(ax=ax, color=bus_color, marker='o', markersize=5, label=f"路線 {os.path.basename(file).replace('.csv', '')}")

            # 將點的 geometry 轉換為 LineString 並繪製線
            line_geometry = LineString(gdf_bus.geometry.tolist())
            line_gdf = gpd.GeoDataFrame([1], geometry=[line_geometry], crs=gdf_bus.crs)
            line_gdf.plot(ax=ax, color=bus_color, linewidth=2, linestyle='--') # 路線線條加粗虛線
            print(f"成功繪製公車路線：{file}")
        except Exception as e:
            print(f"繪製公車路線 {file} 錯誤：{e}")

    ax.set_title("北北基桃行政區與公車路線圖")
    ax.set_xlabel("經度")
    ax.set_ylabel("緯度")
    ax.set_aspect('equal')
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(loc='lower right') # 調整圖例位置以避免重疊

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    plt.savefig(output_file, dpi=300)
    plt.close()
    print(f"地圖已儲存至 {output_file}")

if __name__ == "__main__":
    bus_route_files = [
        "20250429/bus_route_0161000900.csv",
        "20250429/bus_route_0161001500.csv"
    ]
    shp_directory = "20250520/town"
    output_image_file = "20250520/bus_routes_and_regions.png"

    plot_combined_map(bus_route_files, shp_directory, output_image_file)