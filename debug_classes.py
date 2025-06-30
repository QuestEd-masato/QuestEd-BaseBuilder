#!/usr/bin/env python3
"""
クラス表示問題のデバッグ用スクリプト
EC2上で実行してデータベースの状況を確認
"""

import os
import sys
sys.path.append('/home/masat/claude-projects/QuestEd')

from app import create_app
from app.models import db, User, Class, ClassEnrollment, StudentEnrollment

def check_class_data():
    app = create_app()
    
    with app.app_context():
        print("=== QuestEd クラスデータ調査 ===")
        
        # 1. 基本統計
        total_users = User.query.count()
        total_classes = Class.query.count()
        total_class_enrollments = ClassEnrollment.query.count()
        total_student_enrollments = StudentEnrollment.query.count()
        
        print(f"総ユーザー数: {total_users}")
        print(f"総クラス数: {total_classes}")
        print(f"ClassEnrollment数: {total_class_enrollments}")
        print(f"StudentEnrollment数: {total_student_enrollments}")
        
        # 2. 役割別ユーザー数
        print("\n=== 役割別ユーザー数 ===")
        roles = db.session.query(User.role, db.func.count(User.id)).group_by(User.role).all()
        for role, count in roles:
            print(f"{role}: {count}人")
        
        # 3. 教師とクラス
        print("\n=== 教師とそのクラス ===")
        teachers = User.query.filter_by(role='teacher').all()
        for teacher in teachers:
            classes = Class.query.filter_by(teacher_id=teacher.id).all()
            print(f"教師 {teacher.username} (ID: {teacher.id}): {len(classes)}クラス")
            for cls in classes:
                print(f"  - {cls.name} (ID: {cls.id})")
        
        # 4. 学生とクラス登録状況
        print("\n=== 学生とクラス登録状況 ===")
        students = User.query.filter_by(role='student').limit(10).all()  # 最初の10人
        for student in students:
            # ClassEnrollment
            class_enrollments = ClassEnrollment.query.filter_by(student_id=student.id).all()
            # StudentEnrollment  
            student_enrollments = StudentEnrollment.query.filter_by(student_id=student.id).all()
            # User.class_id
            direct_class = Class.query.get(student.class_id) if student.class_id else None
            
            print(f"学生 {student.username} (ID: {student.id}):")
            print(f"  ClassEnrollment: {len(class_enrollments)}件")
            print(f"  StudentEnrollment: {len(student_enrollments)}件")
            print(f"  User.class_id: {student.class_id} ({'有効' if direct_class else '無効/NULL'})")
            
            if class_enrollments:
                for enrollment in class_enrollments:
                    print(f"    - クラス: {enrollment.class_obj.name}")
        
        # 5. データ不整合チェック
        print("\n=== データ不整合チェック ===")
        students_with_class_id = User.query.filter(User.role=='student', User.class_id.isnot(None)).count()
        students_with_enrollments = db.session.query(User.id).join(ClassEnrollment).filter(User.role=='student').distinct().count()
        
        print(f"class_idを持つ学生: {students_with_class_id}人")
        print(f"ClassEnrollmentがある学生: {students_with_enrollments}人")
        
        # 6. 問題のある学生を特定
        problem_students = []
        all_students = User.query.filter_by(role='student').all()
        for student in all_students:
            has_class_id = student.class_id is not None
            has_enrollment = ClassEnrollment.query.filter_by(student_id=student.id).first() is not None
            
            if has_class_id and not has_enrollment:
                problem_students.append((student, 'class_id有り、enrollment無し'))
            elif not has_class_id and not has_enrollment:
                problem_students.append((student, 'class_id無し、enrollment無し'))
        
        print(f"\n問題のある学生: {len(problem_students)}人")
        for student, issue in problem_students[:5]:  # 最初の5人
            print(f"  {student.username}: {issue}")

if __name__ == '__main__':
    check_class_data()