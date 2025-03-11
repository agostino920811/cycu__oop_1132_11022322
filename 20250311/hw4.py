import calendar

# 創建一個包含星期幾的列表
weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
# 創建一個包含月份的列表
months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
# 創建一個包含生肖的列表
zodiacs = ["猴", "雞", "狗", "豬", "鼠", "牛", "虎", "兔", "龍", "蛇", "馬", "羊"]

def get_zodiac(year):
    return zodiacs[year % 12]

def print_month_calendar(year, month):
    try:
        # 創建 TextCalendar 物件
        cal = calendar.TextCalendar(calendar.SUNDAY)
        # 打印指定月份的日曆
        print(cal.formatmonth(year, month))
    except calendar.IllegalMonthError:
        print("無效的月份，請輸入 1 到 12 之間的數字。")
    except ValueError:
        print("無效的年份，請輸入有效的年份。")

if __name__ == "__main__":
    while True:
        try:
            year = int(input("請輸入年份: "))
            month = int(input("請輸入月份 (1-12): "))
            if 1 <= month <= 12:
                zodiac = get_zodiac(year)
                print(f"{year} 年的生肖是: {zodiac}")
                print_month_calendar(year, month)
                break
            else:
                print("無效的月份，請輸入 1 到 12 之間的數字。")
        except ValueError:
            print("無效的輸入，請輸入數字。")


