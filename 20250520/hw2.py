import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load data
df = pd.read_csv('20250520/midterm_scores.csv')

# 科目列表
subjects = ['Chinese', 'English', 'Math', 'History', 'Geography', 'Physics', 'Chemistry']

# 定義分數區間: 0-9, 10-19, ..., 90-100
bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
bin_labels = [f"{bins[i]}-{bins[i+1]-1}" for i in range(len(bins)-1)]

# 定義彩虹顏色順序
# 紅、橙、黃、綠、藍、靛、紫
rainbow_colors = [
    '#FF0000',  # Red
    '#FFA500',  # Orange
    '#FFFF00',  # Yellow
    '#008000',  # Green
    '#0000FF',  # Blue
    '#4B0082',  # Indigo (近似)
    '#EE82EE'   # Violet (近似)
]

# 初始化柱狀圖數據
bar_width = 0.8 / len(subjects)  # 每科目柱狀圖的寬度
x = np.arange(len(bin_labels))  # X 軸位置

plt.figure(figsize=(12, 7)) # 調整圖形大小以獲得更好的視覺效果

# 繪製每個科目的柱狀圖
for i, subject in enumerate(subjects):
    # 計算每個分數區間的學生數量
    scores = df[subject]
    counts, _ = np.histogram(scores, bins=bins)

    # 繪製柱狀圖，使用彩虹顏色
    plt.bar(x + i * bar_width, counts, width=bar_width, label=subject, color=rainbow_colors[i], edgecolor='black')

# 設定圖表標籤與標題
plt.xlabel('分數區間', fontsize=12)
plt.ylabel('學生人數', fontsize=12)
plt.title('各科目分數分佈直條圖', fontsize=16)

# 設定 X 軸刻度與標籤
plt.xticks(x + bar_width * (len(subjects) - 1) / 2, bin_labels, rotation=45, ha='right', fontsize=10)
plt.yticks(fontsize=10) # 調整 Y 軸刻度字體大小

# 加入圖例
plt.legend(title='科目', bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.) # 將圖例移到外面

# 美化圖表
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout() # 自動調整佈局，避免重疊

# 儲存圖表為圖檔
output_path = 'C:/Users/User/Documents/GitHub/cycu__oop_1132_11022322/20250520/score_distribution_rainbow.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight') # 使用 bbox_inches='tight' 確保圖例也能完整儲存
print(f"圖表已儲存至 {output_path}")

# 顯示圖表
plt.show()