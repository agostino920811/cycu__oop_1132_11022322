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
    df = pd.read_csv(csv_path, encoding='utf-8')
    geometry = [Point(lon, lat) for lon, lat in zip(df["longitude"], df["latitude"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    return gdf

def draw_multiple_routes(input_files: list, outputfile: str):
    colors = ['blue', 'green', 'red', 'purple', 'orange']  # 預備多條線用不同顏色
    fig, ax = plt.subplots(figsize=(12, 12))

    for idx, file in enumerate(input_files):
        gdf = read_route_csv(file)
        color = colors[idx % len(colors)]

        # 繪製點
        gdf.plot(ax=ax, color=color, marker='o', markersize=5, label=f"路線 {os.path.basename(file)}")

        # 將點的 geometry 轉換為 LineString 並繪製線
        line_geometry = LineString(gdf.geometry.tolist())
        line_gdf = gpd.GeoDataFrame([1], geometry=[line_geometry], crs=gdf.crs)
        line_gdf.plot(ax=ax, color=color, linewidth=1)

        # 顯示每個站名
        for x, y, name in zip(gdf.geometry.x, gdf.geometry.y, gdf["車站名稱"]):
            ax.text(x, y, name, fontsize=6, ha='left', va='center')

    ax.set_title("多條公車路線圖")
    ax.set_xlabel("經度")
    ax.set_ylabel("緯度")
    ax.set_aspect('equal')
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend()

    os.makedirs(os.path.dirname(outputfile), exist_ok=True)
    plt.savefig(outputfile, dpi=300)
    plt.close()

if __name__ == "__main__":
    input_files = [
        "20250422/bus_route_0161000900.csv",
        "20250422/bus_route_0161001500.csv"
    ]
    outputfile = "20250422/bus_routes_with_lines.png"
    draw_multiple_routes(input_files, outputfile)