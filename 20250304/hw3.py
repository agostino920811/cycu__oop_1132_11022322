# 假設的 x 和 y 值
x_values = [-10, 0, 5]  # 假設 x 為 -10, 0, 5
y_values = [2, 3, 0]    # 假設 y 為 2, 3, 0

# 定義 absolute_value_wrong 函數
def absolute_value_wrong(x):
    if x < 0:
        return -x
    elif x > 0:
        return x

# 測試 absolute_value_wrong 函數
print("Testing absolute_value_wrong:")
for x in x_values:
    result = absolute_value_wrong(x)
    print(f"absolute_value_wrong({x}) = {result}")

# 定義 absolute_value_extra_return 函數
def absolute_value_extra_return(x):
    if x < 0:
        return -x
    elif x > 0:
        return x
    else:
        return 0

# 測試 absolute_value_extra_return 函數
print("\nTesting absolute_value_extra_return:")
for x in x_values:
    result = absolute_value_extra_return(x)
    print(f"absolute_value_extra_return({x}) = {result}")

# 定義 is_divisible 函數
def is_divisible(x, y):
    if y == 0:
        return False
    return x % y == 0

# 測試 is_divisible 函數
print("\nTesting is_divisible:")
for x in x_values:
    for y in y_values:
        result = is_divisible(x, y)
        print(f"is_divisible({x}, {y}) = {result}")
