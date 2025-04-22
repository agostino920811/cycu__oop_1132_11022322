import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt


def draw_geojson_to_png(inputfile: str, outputfile: str):
    # 讀取指定的 GeoJSON 檔案
    bus_stops = gpd.read_file(inputfile)

    # 繪製所有公車站點
    fig, ax = plt.subplots(figsize=(10, 10))
    bus_stops.plot(ax=ax, color='blue', markersize=5)
    plt.title("Bus Stops")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")

    # 儲存為指定的 PNG 檔案
    plt.savefig(outputfile)
    plt.close()

if __name__ == "__main__":
    # 指定輸入的 GeoJSON 檔案和輸出的 PNG 檔案
    inputfile = "20250422/bus_stops.geojson"
    outputfile = "bus_stops.png"

    # 繪製並儲存圖形
    draw_geojson_to_png(inputfile, outputfile)