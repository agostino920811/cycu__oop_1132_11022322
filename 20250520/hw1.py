import pandas as pd

# Load CSV data
df = pd.read_csv('20250520/midterm_scores.csv')

subjects = ['Chinese', 'English', 'Math', 'History', 'Geography', 'Physics', 'Chemistry']

total_subjects = len(subjects)
# 計算超過一半不及格的科目數量門檻
failing_threshold = total_subjects / 2

# 創建一個空的列表來儲存不及格學生資訊
failing_students_data = []

print(f"Students with more than {failing_threshold} failing subjects (<60):")

for idx, row in df.iterrows():
    failed_subjects_count = 0
    failed_subjects_list = []

    for subj in subjects:
        if row[subj] < 60:
            failed_subjects_count += 1
            failed_subjects_list.append(subj)

    if failed_subjects_count > failing_threshold:
        student_info = {
            'Name': row['Name'],
            'StudentID': row['StudentID'],
            'FailedSubjectsCount': failed_subjects_count,
            'FailedSubjects': ', '.join(failed_subjects_list)
        }
        failing_students_data.append(student_info)
        print(f"{row['Name']} (ID: {row['StudentID']}), Failed subjects count: {failed_subjects_count}, Subjects: {', '.join(failed_subjects_list)}")

# 將不及格學生資料轉換為 DataFrame
failing_students_df = pd.DataFrame(failing_students_data)

# 將結果輸出到 CSV 檔案
output_filename = '20250520/students_more_than_half_failing.csv'
failing_students_df.to_csv(output_filename, index=False, encoding='utf-8-sig')

print(f"\n不及格學生資料已匯出至 '{output_filename}'")