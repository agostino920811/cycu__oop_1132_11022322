from datetime import datetime, timezone, timedelta
import math

def to_julian_date(dt):
    """將 datetime 轉換為 Julian Date（以中午 12:00 為起點）"""
    dt = dt.astimezone(timezone.utc)
    year = dt.year
    month = dt.month
    day = dt.day
    hour = dt.hour
    minute = dt.minute
    second = dt.second

    if month <= 2:
        year -= 1
        month += 12

    A = year // 100
    B = 2 - A + A // 4

    # 時間轉換為當天的小數（加上 0.5 表示從中午開始）
    day_fraction = (hour + minute / 60 + second / 3600) / 24
    jd = math.floor(365.25 * (year + 4716)) \
         + math.floor(30.6001 * (month + 1)) \
         + day + day_fraction + B - 1524.5
    return jd

def calculate_time_info():
    input_time_str = input("請輸入時間（格式為 YYYY-MM-DD HH：MM：")

    try:
        # 假設輸入是台灣時間（UTC+8）
        input_time = datetime.strptime(input_time_str, "%Y-%m-%d %H:%M")
        input_time = input_time.replace(tzinfo=timezone(timedelta(hours=8)))
    except ValueError:
        print("輸入格式錯誤，請確認格式為 YYYY-MM-DD HH:MM")
        return

    # 星期中文
    weekday_map = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekday_map[input_time.weekday()]

    # 計算 Julian Date
    jd_input = to_julian_date(input_time)

    # 輸出
    print(f"\n輸入時間：{input_time_str}")
    print(f"該日為：{weekday}")
    print(f"輸入時間對應的太陽日（Julian Date）為：{round(jd_input, 6)}")

# 執行主程式
if __name__ == "__main__":
    calculate_time_info()