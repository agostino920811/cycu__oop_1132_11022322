import json
import folium

def geojson_to_html(geojson_file, output_html):
    """
    Converts a GeoJSON file into an interactive HTML map using Folium.

    :param geojson_file: Path to the input GeoJSON file.
    :param output_html: Path to the output HTML file.
    """
    # Load GeoJSON data
    with open(geojson_file, 'r', encoding='utf-8') as file:
        geojson_data = json.load(file)

    # Create a Folium map
    m = folium.Map(location=[0, 0], zoom_start=2)

    # Add GeoJSON data to the map
    folium.GeoJson(geojson_data).add_to(m)

    # Save the map to an HTML file
    m.save(output_html)

# Example usage:
# geojson_to_html('bus_stops.geojson', 'bus_stops_map.html')


if __name__ == "__main__":
    # 指定輸入的 GeoJSON 檔案和輸出的 PNG 檔案
    inputfile = "20250422/bus_stops.geojson"
    outputfile = "bus_stops.html"

    # 繪製並儲存圖形
    geojson_to_html(inputfile, outputfile)