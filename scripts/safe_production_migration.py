#!/usr/bin/env python3
"""
本番環境向け安全なマイグレーション実行スクリプト
学年・組・学級管理に必要な最小限の変更のみを適用
"""
import mysql.connector
import sys
from datetime import datetime

# 本番環境データベース接続情報
DB_CONFIG = {
    'host': 'localhost',
    'user': 'QuestEd',
    'password': 'QuestEd-03012025MySQL',
    'database': 'quested',
    'charset': 'utf8mb4'
}

def execute_safe_sql(cursor, sql, description):
    """安全にSQL文を実行"""
    try:
        print(f"🔄 実行中: {description}")
        cursor.execute(sql)
        print(f"✅ 完了: {description}")
        return True
    except mysql.connector.Error as e:
        if "already exists" in str(e) or "Duplicate" in str(e):
            print(f"ℹ️ スキップ: {description} (既に存在)")
            return True
        else:
            print(f"❌ エラー: {description} - {e}")
            return False

def check_table_exists(cursor, table_name):
    """テーブルの存在確認"""
    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
    return cursor.fetchone() is not None

def check_column_exists(cursor, table_name, column_name):
    """カラムの存在確認"""
    cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE '{column_name}'")
    return cursor.fetchone() is not None

def create_grades_table(cursor):
    """grades テーブルの作成（必要な場合）"""
    if check_table_exists(cursor, 'grades'):
        print("ℹ️ grades テーブルは既に存在します")
        return True
    
    sql = """
    CREATE TABLE grades (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(20) NOT NULL COMMENT '学年名(1年、2年など)',
        display_order INT NOT NULL DEFAULT 0 COMMENT '表示順序',
        is_active BOOLEAN DEFAULT TRUE COMMENT '有効フラグ',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uk_grade_name (name),
        INDEX idx_display_order (display_order),
        INDEX idx_is_active (is_active)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    COMMENT='学年マスタ'
    """
    
    return execute_safe_sql(cursor, sql, "grades テーブル作成")

def create_school_classes_table(cursor):
    """school_classes テーブルの作成（必要な場合）"""
    if check_table_exists(cursor, 'school_classes'):
        print("ℹ️ school_classes テーブルは既に存在します")
        return True
    
    sql = """
    CREATE TABLE school_classes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        school_id INT NOT NULL,
        grade_id INT,
        name VARCHAR(100) NOT NULL COMMENT 'クラス名(1組、A組など)',
        display_name VARCHAR(150) COMMENT '表示用クラス名',
        teacher_id INT,
        room_number VARCHAR(20) COMMENT '教室番号',
        capacity INT DEFAULT 30 COMMENT '定員',
        is_active BOOLEAN DEFAULT TRUE COMMENT '有効フラグ',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE,
        FOREIGN KEY (grade_id) REFERENCES grades(id) ON DELETE SET NULL,
        FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE SET NULL,
        INDEX idx_school_id (school_id),
        INDEX idx_grade_id (grade_id),
        INDEX idx_teacher_id (teacher_id),
        INDEX idx_is_active (is_active),
        UNIQUE KEY uk_school_grade_name (school_id, grade_id, name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    COMMENT='学校クラス管理'
    """
    
    return execute_safe_sql(cursor, sql, "school_classes テーブル作成")

def add_grade_classroom_fields(cursor):
    """既存テーブルに学年・学級フィールドを追加（必要な場合）"""
    success = True
    
    # users テーブルに grade, classroom フィールドを追加
    if not check_column_exists(cursor, 'users', 'grade'):
        sql = "ALTER TABLE users ADD COLUMN grade INT COMMENT '学年(1-12)'"
        success &= execute_safe_sql(cursor, sql, "users テーブルに grade カラム追加")
    
    if not check_column_exists(cursor, 'users', 'classroom'):
        sql = "ALTER TABLE users ADD COLUMN classroom VARCHAR(10) COMMENT '学級(1組、A組等)'"
        success &= execute_safe_sql(cursor, sql, "users テーブルに classroom カラム追加")
    
    if not check_column_exists(cursor, 'users', 'student_number'):
        sql = "ALTER TABLE users ADD COLUMN student_number VARCHAR(20) COMMENT '生徒番号'"
        success &= execute_safe_sql(cursor, sql, "users テーブルに student_number カラム追加")
    
    # classes テーブルに grade, classroom フィールドを追加
    if not check_column_exists(cursor, 'classes', 'grade'):
        sql = "ALTER TABLE classes ADD COLUMN grade INT COMMENT '対象学年'"
        success &= execute_safe_sql(cursor, sql, "classes テーブルに grade カラム追加")
    
    if not check_column_exists(cursor, 'classes', 'classroom'):
        sql = "ALTER TABLE classes ADD COLUMN classroom VARCHAR(10) COMMENT '学級名'"
        success &= execute_safe_sql(cursor, sql, "classes テーブルに classroom カラム追加")
    
    return success

def insert_basic_grades(cursor):
    """基本的な学年データの挿入"""
    try:
        # 既存データ確認
        cursor.execute("SELECT COUNT(*) FROM grades")
        count = cursor.fetchone()[0]
        
        if count > 0:
            print("ℹ️ grades テーブルに既にデータが存在します")
            return True
        
        print("🔄 基本学年データを挿入中...")
        
        grades_data = [
            (1, '1年', 1),
            (2, '2年', 2),
            (3, '3年', 3),
            (4, '4年', 4),
            (5, '5年', 5),
            (6, '6年', 6)
        ]
        
        sql = "INSERT INTO grades (id, name, display_order) VALUES (%s, %s, %s)"
        cursor.executemany(sql, grades_data)
        
        print("✅ 基本学年データの挿入完了")
        return True
        
    except mysql.connector.Error as e:
        print(f"❌ 学年データ挿入エラー: {e}")
        return False

def update_alembic_version(cursor):
    """Alembicバージョンテーブルの更新"""
    try:
        # 新しいマイグレーションバージョンを作成
        new_version = f"safe_prod_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        sql = "UPDATE alembic_version SET version_num = %s"
        cursor.execute(sql, (new_version,))
        
        print(f"✅ Alembicバージョンを更新: {new_version}")
        return True
        
    except mysql.connector.Error as e:
        print(f"❌ Alembicバージョン更新エラー: {e}")
        return False

def main():
    """メイン実行"""
    print(f"🚀 QuestEd 本番環境安全マイグレーション")
    print(f"📅 実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # データベース接続
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("✅ データベース接続成功")
        
        # 1. grades テーブル作成
        if not create_grades_table(cursor):
            print("❌ grades テーブル作成に失敗")
            return False
        
        # 2. school_classes テーブル作成
        if not create_school_classes_table(cursor):
            print("❌ school_classes テーブル作成に失敗")
            return False
        
        # 3. 既存テーブルへのフィールド追加
        if not add_grade_classroom_fields(cursor):
            print("❌ フィールド追加に失敗")
            return False
        
        # 4. 基本学年データ挿入
        if not insert_basic_grades(cursor):
            print("❌ 基本学年データ挿入に失敗")
            return False
        
        # 5. Alembicバージョン更新
        if not update_alembic_version(cursor):
            print("❌ Alembicバージョン更新に失敗")
            return False
        
        # コミット
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ 本番環境マイグレーション完了")
        print("\n💡 実行された変更:")
        print("   - grades テーブル作成 (学年マスタ)")
        print("   - school_classes テーブル作成 (学校クラス管理)")
        print("   - users テーブルに学年・学級フィールド追加")
        print("   - classes テーブルに学年・学級フィールド追加")
        print("   - 基本学年データ挿入 (1年〜6年)")
        print("\n🔍 次のステップ:")
        print("   1. 動作確認テスト実行")
        print("   2. アプリケーション機能テスト")
        
        return True
        
    except mysql.connector.Error as e:
        print(f"❌ データベースエラー: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)