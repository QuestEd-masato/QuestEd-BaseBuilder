#!/usr/bin/env python3
"""
学年・学級フィールドの既存データ移行スクリプト
既存のクラス名から学年・学級情報を抽出して新フィールドに設定
"""

import re
import sys
from datetime import datetime
from app import create_app, db
from app.models import Class, User, ClassEnrollment

# 学年変換マッピング
GRADE_MAPPING = {
    '1': 1, '１': 1, '一': 1,
    '2': 2, '２': 2, '二': 2,
    '3': 3, '３': 3, '三': 3,
    '4': 4, '４': 4, '四': 4,
    '5': 5, '５': 5, '五': 5,
    '6': 6, '６': 6, '六': 6,
}

# 学級変換マッピング
CLASSROOM_MAPPING = {
    '1': '1組', '１': '1組',
    '2': '2組', '２': '2組',
    '3': '3組', '３': '3組',
    '4': '4組', '４': '4組',
    '5': '5組', '５': '5組',
    '6': '6組', '６': '6組',
    'A': 'A組', 'a': 'A組',
    'B': 'B組', 'b': 'B組',
    'C': 'C組', 'c': 'C組',
}

def extract_grade_classroom_from_name(class_name):
    """クラス名から学年と学級を抽出"""
    grade = None
    classroom = None
    
    # パターン1: "X年Y組" (例: "3年2組", "２年１組")
    pattern1 = r'([1-6１-６一-六])年([1-6１-６A-Ca-c])組'
    match1 = re.search(pattern1, class_name)
    if match1:
        grade_str = match1.group(1)
        classroom_str = match1.group(2)
        
        grade = GRADE_MAPPING.get(grade_str)
        classroom = CLASSROOM_MAPPING.get(classroom_str)
        
        return grade, classroom
    
    # パターン2: "第X学年" 形式
    pattern2 = r'第([1-6１-６一-六])学年'
    match2 = re.search(pattern2, class_name)
    if match2:
        grade_str = match2.group(1)
        grade = GRADE_MAPPING.get(grade_str)
        return grade, None
    
    # パターン3: 中学・高校の場合 (7-12年)
    pattern3 = r'中([1-3１-３])' # 中1, 中2, 中3
    match3 = re.search(pattern3, class_name)
    if match3:
        grade_num = GRADE_MAPPING.get(match3.group(1), 0)
        if grade_num:
            grade = grade_num + 6  # 中1=7年, 中2=8年, 中3=9年
            return grade, None
    
    pattern4 = r'高([1-3１-３])' # 高1, 高2, 高3
    match4 = re.search(pattern4, class_name)
    if match4:
        grade_num = GRADE_MAPPING.get(match4.group(1), 0)
        if grade_num:
            grade = grade_num + 9  # 高1=10年, 高2=11年, 高3=12年
            return grade, None
    
    return None, None

def populate_class_grade_classroom():
    """クラステーブルの学年・学級フィールドを設定"""
    print("[INFO] クラステーブルの学年・学級情報を更新中...")
    
    classes = Class.query.all()
    updated_count = 0
    
    for class_obj in classes:
        grade, classroom = extract_grade_classroom_from_name(class_obj.name)
        
        if grade or classroom:
            if grade:
                class_obj.grade = grade
            if classroom:
                class_obj.classroom = classroom
            
            updated_count += 1
            print(f"  - {class_obj.name}: 学年={grade}, 学級={classroom}")
    
    db.session.commit()
    print(f"[SUCCESS] {updated_count}個のクラスを更新しました")
    
    return updated_count

def populate_student_grade_classroom():
    """生徒の学年・学級フィールドを設定（所属クラスから推定）"""
    print("\n[INFO] 生徒の学年・学級情報を更新中...")
    
    students = User.query.filter_by(role='student').all()
    updated_count = 0
    
    for student in students:
        # 生徒が所属するクラスを取得
        enrollments = ClassEnrollment.query.filter_by(student_id=student.id).all()
        
        if enrollments:
            # 最も一般的な学年・学級を選択（複数クラスに所属する場合）
            grades = []
            classrooms = []
            
            for enrollment in enrollments:
                class_obj = enrollment.class_obj
                if hasattr(class_obj, 'grade') and class_obj.grade:
                    grades.append(class_obj.grade)
                if hasattr(class_obj, 'classroom') and class_obj.classroom:
                    classrooms.append(class_obj.classroom)
            
            # 最頻値を選択
            if grades:
                student.grade = max(set(grades), key=grades.count)
            if classrooms:
                student.classroom = max(set(classrooms), key=classrooms.count)
            
            if student.grade or student.classroom:
                updated_count += 1
                print(f"  - {student.username}: 学年={student.grade}, 学級={student.classroom}")
    
    db.session.commit()
    print(f"[SUCCESS] {updated_count}名の生徒を更新しました")
    
    return updated_count

def generate_student_numbers():
    """生徒番号を生成（学年・学級・連番）"""
    print("\n[INFO] 生徒番号を生成中...")
    
    students = User.query.filter_by(role='student').order_by(User.grade, User.classroom, User.username).all()
    
    # 学年・学級ごとにグループ化
    grade_classroom_groups = {}
    for student in students:
        key = (student.grade or 0, student.classroom or 'なし')
        if key not in grade_classroom_groups:
            grade_classroom_groups[key] = []
        grade_classroom_groups[key].append(student)
    
    updated_count = 0
    current_year = datetime.now().year
    
    for (grade, classroom), group_students in grade_classroom_groups.items():
        for idx, student in enumerate(group_students, 1):
            if grade and classroom != 'なし':
                # 形式: YYYY-GG-CC-NNN (年度-学年-学級-連番)
                classroom_num = classroom.replace('組', '')
                student_number = f"{current_year}-{grade:02d}-{classroom_num}-{idx:03d}"
            else:
                # 学年・学級が不明な場合
                student_number = f"{current_year}-00-00-{student.id:05d}"
            
            student.student_number = student_number
            updated_count += 1
            print(f"  - {student.username}: {student_number}")
    
    db.session.commit()
    print(f"[SUCCESS] {updated_count}名の生徒番号を生成しました")
    
    return updated_count

def validate_data():
    """データ検証"""
    print("\n[INFO] データ検証中...")
    
    # クラスの学年・学級設定状況
    total_classes = Class.query.count()
    classes_with_grade = Class.query.filter(Class.grade.isnot(None)).count()
    classes_with_classroom = Class.query.filter(Class.classroom.isnot(None)).count()
    
    print(f"  - クラス総数: {total_classes}")
    print(f"  - 学年設定済み: {classes_with_grade} ({classes_with_grade/total_classes*100:.1f}%)")
    print(f"  - 学級設定済み: {classes_with_classroom} ({classes_with_classroom/total_classes*100:.1f}%)")
    
    # 生徒の学年・学級設定状況
    total_students = User.query.filter_by(role='student').count()
    students_with_grade = User.query.filter_by(role='student').filter(User.grade.isnot(None)).count()
    students_with_classroom = User.query.filter_by(role='student').filter(User.classroom.isnot(None)).count()
    students_with_number = User.query.filter_by(role='student').filter(User.student_number.isnot(None)).count()
    
    print(f"\n  - 生徒総数: {total_students}")
    print(f"  - 学年設定済み: {students_with_grade} ({students_with_grade/total_students*100:.1f}%)")
    print(f"  - 学級設定済み: {students_with_classroom} ({students_with_classroom/total_students*100:.1f}%)")
    print(f"  - 生徒番号設定済み: {students_with_number} ({students_with_number/total_students*100:.1f}%)")
    
    # 複数クラス所属の生徒
    multi_class_students = db.session.query(ClassEnrollment.student_id)\
        .group_by(ClassEnrollment.student_id)\
        .having(db.func.count(ClassEnrollment.class_id) > 1)\
        .count()
    
    print(f"\n  - 複数クラス所属生徒: {multi_class_students}名")

def main():
    """メイン処理"""
    print("[INFO] 学年・学級データ移行スクリプト開始")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        try:
            # 1. クラスの学年・学級を設定
            populate_class_grade_classroom()
            
            # 2. 生徒の学年・学級を設定
            populate_student_grade_classroom()
            
            # 3. 生徒番号を生成
            generate_student_numbers()
            
            # 4. データ検証
            validate_data()
            
            print("\n[SUCCESS] データ移行が完了しました")
            
        except Exception as e:
            print(f"\n[ERROR] データ移行中にエラーが発生しました: {str(e)}")
            db.session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    main()