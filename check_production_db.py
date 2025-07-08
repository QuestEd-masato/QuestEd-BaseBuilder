#!/usr/bin/env python3
"""
本番環境データベース状況チェックスクリプト
"""
import sys
import mysql.connector
from datetime import datetime

# 本番環境データベース接続情報
PROD_DB_CONFIG = {
    'host': 'localhost',
    'user': 'QuestEd',
    'password': 'QuestEd-03012025MySQL',
    'database': 'quested',
    'charset': 'utf8mb4'
}

def check_db_connection():
    """データベース接続確認"""
    try:
        conn = mysql.connector.connect(**PROD_DB_CONFIG)
        cursor = conn.cursor()
        
        print("✅ データベース接続成功")
        
        # バージョン確認
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        print(f"📊 MySQL バージョン: {version}")
        
        # 文字セット確認
        cursor.execute("SHOW VARIABLES LIKE 'character_set_database'")
        charset = cursor.fetchone()[1]
        print(f"🔤 文字セット: {charset}")
        
        cursor.close()
        conn.close()
        return True
        
    except mysql.connector.Error as e:
        print(f"❌ データベース接続エラー: {e}")
        return False

def check_tables_status():
    """テーブル状況確認"""
    try:
        conn = mysql.connector.connect(**PROD_DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n📋 テーブル一覧と状況:")
        
        # 全テーブル一覧
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        print(f"📊 総テーブル数: {len(tables)}")
        
        # 主要テーブルの存在確認
        important_tables = [
            'users', 'classes', 'class_enrollments',
            'curriculum_units', 'curriculum_items', 
            'basic_knowledge_items', 'problem_categories',
            'text_sets', 'text_deliveries',
            'answer_records', 'proficiency_records'
        ]
        
        print("\n🔍 主要テーブル存在確認:")
        for table in important_tables:
            if table in tables:
                # レコード数確認
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  ✅ {table}: {count:,} レコード")
            else:
                print(f"  ❌ {table}: 存在しません")
        
        # 学年・組・学級関連の新テーブル確認
        new_tables = ['grades', 'class_groups', 'school_classes']
        print("\n🆕 学年・組・学級関連テーブル:")
        for table in new_tables:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  ✅ {table}: {count:,} レコード")
            else:
                print(f"  ➖ {table}: 未作成（マイグレーション対象）")
        
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as e:
        print(f"❌ テーブル確認エラー: {e}")

def check_migration_status():
    """マイグレーション状況確認"""
    try:
        conn = mysql.connector.connect(**PROD_DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n🔄 マイグレーション状況:")
        
        # alembic_version テーブル確認
        cursor.execute("SHOW TABLES LIKE 'alembic_version'")
        if cursor.fetchone():
            cursor.execute("SELECT version_num FROM alembic_version")
            version = cursor.fetchone()
            if version:
                print(f"  📝 現在のマイグレーションバージョン: {version[0]}")
            else:
                print("  ⚠️ マイグレーションバージョンが記録されていません")
        else:
            print("  ❌ alembic_version テーブルが存在しません")
        
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as e:
        print(f"❌ マイグレーション状況確認エラー: {e}")

def check_data_integrity():
    """データ整合性確認"""
    try:
        conn = mysql.connector.connect(**PROD_DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n🔍 データ整合性チェック:")
        
        # ユーザー数確認
        cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
        for role, count in cursor.fetchall():
            print(f"  👥 {role}: {count:,} 人")
        
        # クラス・学生関係確認
        cursor.execute("""
            SELECT c.name, COUNT(ce.student_id) as student_count
            FROM classes c
            LEFT JOIN class_enrollments ce ON c.id = ce.class_id AND ce.is_active = 1
            GROUP BY c.id, c.name
            ORDER BY c.name
        """)
        
        print("\n  📚 クラス別学生数:")
        for class_name, student_count in cursor.fetchall():
            print(f"    {class_name}: {student_count} 人")
        
        # 学習データ確認
        cursor.execute("SELECT COUNT(*) FROM answer_records")
        answer_count = cursor.fetchone()[0]
        print(f"\n  📊 総回答記録数: {answer_count:,}")
        
        cursor.execute("SELECT COUNT(*) FROM proficiency_records")
        prof_count = cursor.fetchone()[0]
        print(f"  📈 習熟度記録数: {prof_count:,}")
        
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as e:
        print(f"❌ データ整合性確認エラー: {e}")

def main():
    """メイン実行"""
    print(f"🔍 QuestEd 本番環境データベース状況チェック")
    print(f"📅 実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 接続確認
    if not check_db_connection():
        print("❌ データベース接続に失敗しました。設定を確認してください。")
        sys.exit(1)
    
    # 2. テーブル状況確認
    check_tables_status()
    
    # 3. マイグレーション状況確認
    check_migration_status()
    
    # 4. データ整合性確認
    check_data_integrity()
    
    print("\n" + "=" * 60)
    print("✅ 本番環境データベース状況チェック完了")
    print("\n💡 次のステップ:")
    print("   1. マイグレーションファイルの確認")
    print("   2. データベースバックアップの実行")
    print("   3. マイグレーションの実行")

if __name__ == "__main__":
    main()