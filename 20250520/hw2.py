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

# 設定顏色
colors = plt.cm.tab10(np.linspace(0, 1, len(subjects)))

# 初始化柱狀圖數據
bar_width = 0.8 / len(subjects)  # 每科目柱狀圖的寬度
x = np.arange(len(bin_labels))  # X 軸位置

# 繪製每個科目的柱狀圖
for i, subject in enumerate(subjects):
    # 計算每個分數區間的學生數量
    scores = df[subject]
    counts, _ = np.histogram(scores, bins=bins)
    
    # 繪製柱狀圖
    plt.bar(x + i * bar_width, counts, width=bar_width, label=subject, color=colors[i], edgecolor='black')

# 設定圖表標籤與標題
plt.xlabel('Score Range')
plt.ylabel('Number of Students')
plt.title('Score Distribution by Subject')

# 設定 X 軸刻度與標籤
plt.xticks(x + bar_width * (len(subjects) - 1) / 2, bin_labels, rotation=45)

# 加入圖例
plt.legend(title='Subjects')

# 美化圖表
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()

# 儲存圖表為圖檔
output_path = 'C:/Users/User/Documents/GitHub/cycu__oop_1132_11022322/20250520/score_distribution.png'
plt.savefig(output_path, dpi=300)
print(f"圖表已儲存至 {output_path}")

# 顯示圖表
plt.show()