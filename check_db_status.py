#!/usr/bin/env python3
"""
データベースの状態を包括的にチェックするスクリプト
"""
import os
import sys
from datetime import datetime

# プロジェクトのパスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from sqlalchemy import text

def check_database_status():
    """データベースの状態を確認"""
    app = create_app()
    
    with app.app_context():
        print("=== QuestEd データベース診断レポート ===")
        print(f"実行日時: {datetime.now()}")
        print()
        
        # 1. テーブルの存在確認
        print("【1. テーブル存在確認】")
        tables_to_check = [
            'word_proficiency_records',
            'answer_records', 
            'curriculum_units',
            'student_unit_selections',
            'activity_logs',
            'users',
            'words',
            'text_deliveries'
        ]
        
        existing_tables = []
        missing_tables = []
        
        for table in tables_to_check:
            try:
                result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                existing_tables.append(f"{table}: {result}件")
            except Exception as e:
                missing_tables.append(f"{table}: 存在しない or エラー")
        
        print("✓ 存在するテーブル:")
        for t in existing_tables:
            print(f"  - {t}")
        
        if missing_tables:
            print("\n✗ 存在しないテーブル:")
            for t in missing_tables:
                print(f"  - {t}")
        
        # 2. ユーザーデータの確認
        print("\n【2. ユーザーデータ確認】")
        try:
            user_stats = db.session.execute(text("""
                SELECT role, COUNT(*) as count 
                FROM users 
                GROUP BY role
            """)).fetchall()
            
            for row in user_stats:
                print(f"  - {row.role}: {row.count}人")
        except Exception as e:
            print(f"  エラー: {str(e)}")
        
        # 3. BaseBuilderデータの確認
        print("\n【3. BaseBuilderデータ確認】")
        
        # answer_records
        try:
            answer_stats = db.session.execute(text("""
                SELECT 
                    COUNT(DISTINCT student_id) as students,
                    COUNT(*) as total_answers,
                    SUM(is_correct) as correct_answers
                FROM answer_records
            """)).first()
            
            print(f"  answer_records:")
            print(f"    - 学習者数: {answer_stats.students}人")
            print(f"    - 総回答数: {answer_stats.total_answers}件")
            print(f"    - 正解数: {answer_stats.correct_answers}件")
        except Exception as e:
            print(f"  answer_records: エラー - {str(e)}")
        
        # word_proficiency_records
        try:
            proficiency_stats = db.session.execute(text("""
                SELECT 
                    COUNT(DISTINCT student_id) as students,
                    COUNT(DISTINCT problem_id) as problems,
                    COUNT(CASE WHEN level = 5 THEN 1 END) as mastered
                FROM word_proficiency_records
            """)).first()
            
            print(f"\n  word_proficiency_records:")
            print(f"    - 学習者数: {proficiency_stats.students}人")
            print(f"    - 問題数: {proficiency_stats.problems}問")
            print(f"    - レベル5達成: {proficiency_stats.mastered}件")
        except Exception as e:
            print(f"\n  word_proficiency_records: エラー - {str(e)}")
        
        # 4. カリキュラムデータの確認
        print("\n【4. カリキュラムデータ確認】")
        
        try:
            unit_count = db.session.execute(text("""
                SELECT COUNT(*) FROM curriculum_units
            """)).scalar()
            
            selection_stats = db.session.execute(text("""
                SELECT 
                    status, 
                    COUNT(*) as count
                FROM student_unit_selections
                GROUP BY status
            """)).fetchall()
            
            print(f"  - 総単元数: {unit_count}件")
            print(f"  - 学生選択状況:")
            for row in selection_stats:
                print(f"    - {row.status}: {row.count}件")
        except Exception as e:
            print(f"  エラー: {str(e)}")
        
        # 5. カラム名の確認
        print("\n【5. 重要カラムの確認】")
        
        # activity_logs
        try:
            cols = db.session.execute(text("""
                SHOW COLUMNS FROM activity_logs
            """)).fetchall()
            
            print("  activity_logs カラム:")
            important_cols = ['timestamp', 'created_at', 'study_duration']
            for col in cols:
                if col[0] in important_cols:
                    print(f"    - {col[0]}: {col[1]}")
        except Exception as e:
            print(f"  activity_logs: エラー - {str(e)}")
        
        # answer_records
        try:
            cols = db.session.execute(text("""
                SHOW COLUMNS FROM answer_records
            """)).fetchall()
            
            print("\n  answer_records カラム:")
            important_cols = ['timestamp', 'created_at', 'student_id', 'is_correct']
            for col in cols:
                if col[0] in important_cols:
                    print(f"    - {col[0]}: {col[1]}")
        except Exception as e:
            print(f"  answer_records: エラー - {str(e)}")
        
        print("\n=== 診断完了 ===")

if __name__ == "__main__":
    check_database_status()