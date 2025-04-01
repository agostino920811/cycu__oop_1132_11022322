import requests
import html
import pandas as pd
from bs4 import BeautifulSoup

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

url = '''https://pda5284.gov.taipei/MQS/route.jsp?rid=10417'''
response = requests.get(url)

if response.status_code == 200:
    with open("bus1.html", "w", encoding="utf-8") as file:
        file.write(response.text)
    
    with open("bus1.html", "r", encoding="utf-8") as file:
        content = file.read()
        decoded_content = html.unescape(content)
    
    soup = BeautifulSoup(content, "html.parser")
    tables = soup.find_all("table")
    all_rows = []

    for table in tables:
        for tr in table.find_all("tr", class_=["ttego1", "ttego2","tteback1", "tteback2"]):
            td = tr.find("td")
            if td:
                stop_name = html.unescape(td.text.strip())
                stop_link = td.find("a")["href"] if td.find("a") else None
                
                # 修正後的判斷邏輯
                if "ttego1" in tr["class"] or "ttego2" in tr["class"]:
                    stop_type = "去程站點名稱"
                elif "tteback1" in tr["class"] or "tteback2" in tr["class"]:
                    stop_type = "回程站點名稱"
                else:
                    stop_type = "未知"
                
                all_rows.append({"類型": stop_type, "站點名稱": stop_name, "連結": stop_link})

    # 修正後的分組邏輯
    df_go = pd.DataFrame([row for row in all_rows if row["類型"] == "去程站點名稱"])
    df_return = pd.DataFrame([row for row in all_rows if row["類型"] == "回程站點名稱"])

    print("去程 DataFrame:")
    print(df_go)
    print("\n回程 DataFrame:")
    print(df_return)
else:
    print(f"無法下載網頁，HTTP 狀態碼: {response.status_code}")
