import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

def plot_normal_pdf(mu, sigma):
    # 建立 x 軸資料
    x = np.linspace(mu - 4*sigma, mu + 4*sigma, 1000)
    # 使用 norm.pdf 計算 y 軸機率密度
    y = norm.pdf(x, mu, sigma)
    
    # 畫圖
    plt.figure(figsize=(8, 5))
    plt.plot(x, y, label=f'μ={mu}, σ={sigma}')
    plt.title('Normal Distribution PDF')
    plt.xlabel('x')
    plt.ylabel('Probability Density')
    plt.grid(True)
    plt.legend()
    
    # 確保圖檔儲存於程式所在資料夾
    current_dir = os.path.dirname(os.path.abspath(__file__))
    save_path = os.path.join(current_dir, 'mid1.jpg')
    plt.savefig(save_path)
    plt.close()

# 手動輸入 μ 和 σ
try:
    mu = float(input("請輸入平均值 μ："))
    sigma = float(input("請輸入標準差 σ："))
    if sigma <= 0:
        raise ValueError("標準差 σ 必須大於 0")
except ValueError as e:
    print(f"輸入錯誤：{e}")
    exit()

# 呼叫函式繪製圖表
plot_normal_pdf(mu, sigma)
print("圖表已儲存為 'mid1.jpg'")