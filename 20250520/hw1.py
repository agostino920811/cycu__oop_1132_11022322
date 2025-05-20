import pandas as pd

# Load CSV data
df = pd.read_csv('20250520/midterm_scores.csv')

subjects = ['Chinese', 'English', 'Math', 'History', 'Geography', 'Physics', 'Chemistry']

total_subjects = len(subjects)
# 計算超過一半不及格的科目數量門檻
failing_threshold = total_subjects / 2

print(f"Students with more than {failing_threshold} failing subjects (<60):")

for idx, row in df.iterrows():
    failed_subjects_count = 0
    failed_subjects_list = []

    for subj in subjects:
        if row[subj] < 60:
            failed_subjects_count += 1
            failed_subjects_list.append(subj)

    if failed_subjects_count > failing_threshold:
        print(f"{row['Name']} (ID: {row['StudentID']}), Failed subjects count: {failed_subjects_count}, Subjects: {', '.join(failed_subjects_list)}")