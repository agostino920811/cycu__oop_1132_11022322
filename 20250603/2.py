import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- 1. 載入地震地表加速度數據 ---
# 修改檔案路徑為您提供的具體路徑
file_path = r'C:\Users\User\Documents\GitHub\cycu_oop_1132_11022143\地震期末\Kobe.txt'
try:
    # 讀取數據，跳過第一行（標題行），並指定列名
    df_ground_accel = pd.read_csv(file_path, sep='\s+', header=None, skiprows=1, names=['Time (s)', 'Acceleration (g)'])
    # 將加速度從 'g' 轉換為 m/s^2 (假設 1g = 9.81 m/s^2)
    g = 9.81  # 重力加速度，單位為 m/s^2
    df_ground_accel['Acceleration (m/s²)'] = df_ground_accel['Acceleration (g)'] * g
    time_series = df_ground_accel['Time (s)'].values # 時間序列
    ground_accel = df_ground_accel['Acceleration (m/s²)'].values # 地震地表加速度
    dt = time_series[1] - time_series[0] # 時間步長
except FileNotFoundError:
    print(f"錯誤：找不到檔案 '{file_path}'。請確保檔案在正確的目錄中。")
    exit()

# --- 2. 定義系統參數 ---
# 主結構（單層樓）參數
ms = 84600000  # KG (主結構質量)
# 自然頻率通常是 omega_n 或 f_n，這裡假設 "自然頻率比0.9174rad/s" 是主結構的自然頻率 omega_ns
omega_ns = 0.9174  # rad/s (主結構自然頻率)
zeta_s = 0.01  # (主結構阻尼比)

# 調諧質量阻尼器 (TMD) 參數
mu = 0.03  # md/ms (阻尼器質量比)
alpha = 0.9592  # omega_nd/omega_ns (調諧頻率比)
zeta_d = 0.0857  # (阻尼器阻尼比)

# --- 3. 推導物理參數 ---
# 主結構參數
ks = ms * (omega_ns**2)  # 主結構剛度
cs = 2 * zeta_s * ms * omega_ns  # 主結構阻尼係數

# TMD 參數
md = mu * ms  # 阻尼器質量
omega_nd = alpha * omega_ns  # 阻尼器自然頻率
kd = md * (omega_nd**2)  # 阻尼器剛度
cd = 2 * zeta_d * md * omega_nd  # 阻尼器阻尼係數

print(f"推導出的主結構參數：")
print(f"  剛度 (ks): {ks:.2f} N/m")
print(f"  阻尼係數 (cs): {cs:.2f} Ns/m")
print(f"\n推導出的 TMD 參數：")
print(f"  阻尼器質量 (md): {md:.2f} KG")
print(f"  阻尼器自然頻率 (omega_nd): {omega_nd:.4f} rad/s")
print(f"  阻尼器剛度 (kd): {kd:.2f} N/m")
print(f"  阻尼器阻尼係數 (cd): {cd:.2f} Ns/m")

# --- 4. 建立雙自由度系統矩陣 ---
# 自由度定義：
# x[0] = us (主結構相對於地面的位移)
# x[1] = ud (阻尼器相對於主結構的位移)

M = np.array([[ms, 0],
              [0, md]])

C = np.array([[cs + cd, -cd],
              [-cd, cd]])

K = np.array([[ks + kd, -kd],
              [-kd, kd]])

# 地面加速度的載荷向量
# P(t) = -M * 1 * u_double_dot_g(t)
# 其中 1 = {1, 0} 用於 us_relative_to_ground 和 ud_relative_to_structure
load_matrix = np.array([[1], [0]])

# --- 5. 數值積分 (Newmark-Beta 方法) ---
# Newmark-beta 參數（平均常加速度法）
gamma = 0.5
beta = 0.25

num_steps = len(time_series)
# 初始化位移、速度和加速度向量
# 響應數據儲存為列：us, ud_rel, us_dot, ud_rel_dot, us_double_dot, ud_rel_double_dot
response = np.zeros((num_steps, 6))

# 初始條件（全部為零）
us_0 = 0.0
ud_rel_0 = 0.0
us_dot_0 = 0.0
ud_rel_dot_0 = 0.0

# 計算初始加速度
# 初始加速度向量應該是 (2,1) 形狀
initial_accel_vec = np.linalg.solve(M, -M @ load_matrix * ground_accel[0])

response[0, 4] = initial_accel_vec[0, 0] # 初始 us_double_dot (相對)
response[0, 5] = initial_accel_vec[1, 0] # 初始 ud_rel_double_dot

# Newmark-beta 的有效剛度矩陣
K_eff = K + (gamma / (beta * dt)) * C + (1 / (beta * dt**2)) * M

# 迴圈遍歷時間步長
for i in range(num_steps - 1):
    # 當前值，確保是 (2,1) 的列向量
    u_i = response[i, 0:2].reshape(-1, 1) # us, ud_rel
    v_i = response[i, 2:4].reshape(-1, 1) # us_dot, ud_rel_dot
    a_i = response[i, 4:6].reshape(-1, 1) # us_double_dot, ud_rel_double_dot

    # t+dt 時刻的有效載荷向量
    P_t_plus_dt = -M @ load_matrix * ground_accel[i+1] # Force due to ground acceleration at t+dt, shape (2,1)

    # 計算 RHS_force_terms
    # 確保所有加法項都是 (2,1) 形狀，使用 @ 進行矩陣乘法
    RHS_force_terms = P_t_plus_dt + \
                      M @ ((1/(beta*dt**2))*u_i + (1/(beta*dt))*v_i + (1/(2*beta) - 1)*a_i) + \
                      C @ ((gamma/(beta*dt))*u_i + (gamma/beta - 1)*v_i + (gamma/2 - beta)*dt*a_i)

    # 求解 t+dt 時刻的位移，結果為 (2,1)
    u_t_plus_dt = np.linalg.solve(K_eff, RHS_force_terms)

    # 更新 t+dt 時刻的加速度和速度，結果為 (2,1)
    a_t_plus_dt = (1/(beta*dt**2)) * (u_t_plus_dt - u_i) - (1/(beta*dt)) * v_i - (1/(2*beta) - 1) * a_i
    v_t_plus_dt = v_i + (1 - gamma) * dt * a_i + gamma * dt * a_t_plus_dt

    # 儲存結果到 response 陣列的 (2,) 切片中，需要將 (2,1) 的結果攤平為 (2,)
    response[i+1, 0:2] = u_t_plus_dt.flatten() # us, ud_rel
    response[i+1, 2:4] = v_t_plus_dt.flatten() # us_dot, ud_rel_dot
    response[i+1, 4:6] = a_t_plus_dt.flatten() # us_double_dot, ud_rel_double_dot

# --- 6. 計算絕對響應和性能指標 ---
# us: 主結構相對於地面的位移
# ud_rel: 阻尼器相對於主結構的位移

# 阻尼器的絕對位移
u_d_abs = response[:, 0] + response[:, 1]

# 主結構的絕對加速度（相對於地面）
# response[:, 4] 已經是 u_double_dot_s (相對於地面，這對於主結構來說就是絕對加速度)
u_double_dot_s_abs = response[:, 4]

# 阻尼器的絕對加速度（相對於地面）
u_double_dot_d_abs = response[:, 4] + response[:, 5]

# 將響應結果轉換為 DataFrame 以便於處理
results_df = pd.DataFrame({
    '時間 (s)': time_series,
    '地表加速度 (m/s²)': ground_accel,
    '樓層位移 (m)': response[:, 0],
    '樓層速度 (m/s)': response[:, 2],
    '樓層加速度 (m/s²)': u_double_dot_s_abs, # 這是樓層的絕對加速度
    '阻尼器相對位移 (m)': response[:, 1], # 阻尼器相對於樓層的位移
    '阻尼器相對速度 (m/s)': response[:, 3], # 阻尼器相對於樓層的速度
    '阻尼器相對加速度 (m/s²)': response[:, 5], # 阻尼器相對於樓層的加速度
    '阻尼器絕對位移 (m)': u_d_abs, # 阻尼器絕對位移
    '阻尼器絕對加速度 (m/s²)': u_double_dot_d_abs # 阻尼器絕對加速度
})

print("\n--- 計算出的響應前 5 行 ---")
print(results_df.head())

# --- 將結果儲存為 CSV 檔案 ---
output_csv_path = r'C:\Users\User\Documents\GitHub\cycu_oop_1132_11022143\地震期末\simulation_results.csv'
try:
    results_df.to_csv(output_csv_path, index=False, encoding='utf-8')
    print(f"\n計算結果已成功儲存至：{output_csv_path}")
except Exception as e:
    print(f"\n儲存檔案時發生錯誤：{e}")


# --- 7. 繪製結果 ---
plt.figure(figsize=(15, 10))

# 繪製樓層絕對加速度
plt.subplot(3, 1, 1)
plt.plot(results_df['時間 (s)'], results_df['樓層加速度 (m/s²)'], label='樓層絕對加速度')
plt.plot(results_df['時間 (s)'], results_df['地表加速度 (m/s²)'], linestyle='--', alpha=0.7, label='地表加速度輸入')
plt.title('樓層絕對加速度響應')
plt.xlabel('時間 (s)')
plt.ylabel('加速度 (m/s²)')
plt.grid(True)
plt.legend()

# 繪製樓層位移
plt.subplot(3, 1, 2)
plt.plot(results_df['時間 (s)'], results_df['樓層位移 (m)'], label='樓層位移 (相對於地面)')
plt.title('樓層位移響應')
plt.xlabel('時間 (s)')
plt.ylabel('位移 (m)')
plt.grid(True)
plt.legend()

# 繪製阻尼器絕對加速度
plt.subplot(3, 1, 3)
plt.plot(results_df['時間 (s)'], results_df['阻尼器絕對加速度 (m/s²)'], label='阻尼器絕對加速度')
plt.plot(results_df['時間 (s)'], results_df['阻尼器相對加速度 (m/s²)'], linestyle=':', alpha=0.7, label='阻尼器相對加速度 (相對於樓層)')
plt.title('阻尼器加速度響應')
plt.xlabel('時間 (s)')
plt.ylabel('加速度 (m/s²)')
plt.grid(True)
plt.legend()

plt.tight_layout()
plt.show()

# --- 8. 基本性能指標 (可選) ---
max_ground_accel = np.max(np.abs(ground_accel))
max_floor_accel = np.max(np.abs(results_df['樓層加速度 (m/s²)']))
max_floor_disp = np.max(np.abs(results_df['樓層位移 (m)']))
max_damper_abs_accel = np.max(np.abs(results_df['阻尼器絕對加速度 (m/s²)']))
max_damper_rel_disp = np.max(np.abs(results_df['阻尼器相對位移 (m)']))

print(f"\n--- 響應摘要 ---")
print(f"最大地表加速度: {max_ground_accel:.4f} m/s²")
print(f"最大樓層絕對加速度: {max_floor_accel:.4f} m/s²")
print(f"最大樓層位移 (相對於地面): {max_floor_disp:.4f} m")
print(f"最大阻尼器絕對加速度: {max_damper_abs_accel:.4f} m/s²")
print(f"最大阻尼器相對位移 (相對於樓層): {max_damper_rel_disp:.4f} m")

# 若要計算沒有 TMD 的情況，您需要另外運行一個單自由度 (SDOF) 分析。
# 此程式碼目前僅計算有 TMD 的情況。