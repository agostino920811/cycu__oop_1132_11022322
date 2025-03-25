import pandas as pd
import matplotlib.pyplot as plt

# 讀取 CSV 檔案
file_path = r'c:\Users\User\Documents\GitHub\cycu__oop_1132_11022322\20250325\gold.csv'
df = pd.read_csv(file_path)

# 將資料日期轉換為 datetime 格式
df['資料日期'] = pd.to_datetime(df['資料日期'], format='%Y%m%d')

# 選取需要的資料
dates = df['資料日期']
cash_1 = df['現金.BUY']
cash_2 = df['現金.SELL']

# 繪製折線圖
plt.figure(figsize=(10, 5))
plt.plot(dates, cash_1, label='現金.BUY', marker='o')
plt.plot(dates, cash_2, label='現金.SELL', marker='o')

# 設定圖表標題和標籤
plt.title('現金匯率折線圖')
plt.xlabel('資料日期')
plt.ylabel('現金匯率')
plt.xticks(rotation=45)
plt.legend()

# 顯示圖表
plt.tight_layout()
plt.show()