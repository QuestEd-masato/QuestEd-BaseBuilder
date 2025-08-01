#!/usr/bin/env python3
import mysql.connector

try:
    # Database connection
    conn = mysql.connector.connect(
        host='localhost',
        port=3306,
        user='QuestEd',
        password='QuestEd-03012025MySQL',
        database='quested'
    )
    
    cursor = conn.cursor()
    
    # Check for lesson-related tables
    cursor.execute("SHOW TABLES LIKE '%lesson%'")
    lesson_tables = cursor.fetchall()
    
    cursor.execute("SHOW TABLES LIKE '%task%'")
    task_tables = cursor.fetchall()
    
    print("=== レッスンシステムテーブル確認 ===")
    print("Lesson関連テーブル:")
    for table in lesson_tables:
        print(f"  ✅ {table[0]}")
    
    print("\nTask関連テーブル:")
    for table in task_tables:
        print(f"  ✅ {table[0]}")
    
    # Check table structure for key tables
    if lesson_tables or task_tables:
        print("\n=== テーブル構造確認 ===")
        
        try:
            cursor.execute("DESC curriculum_lessons")
            print("✅ curriculum_lessons テーブル構造正常")
        except:
            print("❌ curriculum_lessons テーブル未作成")
            
        try:
            cursor.execute("DESC lesson_tasks") 
            print("✅ lesson_tasks テーブル構造正常")
        except:
            print("❌ lesson_tasks テーブル未作成")
            
        try:
            cursor.execute("DESC student_lesson_progress")
            print("✅ student_lesson_progress テーブル構造正常")
        except:
            print("❌ student_lesson_progress テーブル未作成")
            
        try:
            cursor.execute("DESC student_task_checks")
            print("✅ student_task_checks テーブル構造正常")
        except:
            print("❌ student_task_checks テーブル未作成")
    
    cursor.close()
    conn.close()
    
    if lesson_tables and task_tables:
        print("\n🎉 データベーステーブル復旧成功!")
    else:
        print("\n❌ テーブル復旧が必要です")
        
except Exception as e:
    print(f"❌ データベース接続エラー: {e}")