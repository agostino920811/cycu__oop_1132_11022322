import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import lognorm

def plot_lognormal_cdf(mu, sigma, x_range, output_file):
    """
    繪製對數常態累積分布函數 (Log-normal CDF) 並儲存為 JPG 檔案。
    
    :param mu: 對數常態分布的 μ 參數
    :param sigma: 對數常態分布的 σ 參數
    :param x_range: x 軸範圍 (tuple，格式為 (start, end, num_points))
    :param output_file: 輸出的 JPG 檔案名稱
    """
    # 計算對數常態分布的 s 和 scale
    s = sigma
    scale = np.exp(mu)

    # 定義 x 軸範圍
    x = np.linspace(x_range[0], x_range[1], x_range[2])

    # 計算累積分布函數 (CDF)
    cdf = lognorm.cdf(x, s, scale=scale)

    # 繪製圖形
    plt.figure(figsize=(8, 6))
    plt.plot(x, cdf, label=f'Log-normal CDF (μ={mu}, σ={sigma})', color='blue')
    plt.title('Log-normal Cumulative Distribution Function')
    plt.xlabel('x')
    plt.ylabel('CDF')
    plt.grid(True)
    plt.legend()

    # 儲存為 JPG 檔案
    plt.savefig(output_file, format='jpg')
    plt.show()

# 測試函數
if __name__ == "__main__":
    mu = 1.5  # μ
    sigma = 0.4  # σ
    x_range = (0.01, 10, 500)  # x 軸範圍 (起始, 結束, 點數)
    output_file = 'lognormal_cdf.jpg'  # 輸出檔案名稱

    plot_lognormal_cdf(mu, sigma, x_range, output_file)