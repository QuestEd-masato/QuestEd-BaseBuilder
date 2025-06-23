# inspect_db.py
import pymysql

# データベース接続情報
DB_USERNAME = "QuestEd"
DB_PASSWORD = "QuestEd-03012025"
DB_HOST = "localhost"
DB_NAME = "quested_db"

def check_tables():
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        
        with connection.cursor() as cursor:
            # テーブル一覧を表示
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            print("データベース内のテーブル一覧:")
            for table in tables:
                print(f"- {table[0]}")
            
            # 特定のテーブルの存在確認
            tables_to_check = [
                'word_proficiency_records',
                'answer_records',
                'curriculum_units',
                'student_unit_selections',
                'basic_knowledge_items',
                'proficiency_records',
                'text_proficiency_records'
            ]
            
            print("\n\n関連テーブルの確認:")
            for table_name in tables_to_check:
                cursor.execute(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '{DB_NAME}' AND table_name = '{table_name}'")
                exists = cursor.fetchone()[0] > 0
                
                if exists:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    print(f"✓ {table_name}: 存在します (レコード数: {count})")
                    
                    # カラム情報も取得
                    cursor.execute(f"DESCRIBE {table_name}")
                    columns = cursor.fetchall()
                    print("  カラム:")
                    for col in columns[:5]:  # 最初の5カラムのみ表示
                        print(f"    - {col[0]}: {col[1]}")
                    if len(columns) > 5:
                        print(f"    ... 他 {len(columns) - 5} カラム")
                else:
                    print(f"✗ {table_name}: 存在しません")
            
            # ランキング関連テーブルの確認
            print("\n\nランキング関連テーブルの確認:")
            ranking_tables = [
                'daily_rankings',
                'weekly_rankings',
                'monthly_rankings',
                'all_time_rankings'
            ]
            
            for table_name in ranking_tables:
                cursor.execute(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '{DB_NAME}' AND table_name = '{table_name}'")
                exists = cursor.fetchone()[0] > 0
                
                if exists:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    print(f"✓ {table_name}: 存在します (レコード数: {count})")
                else:
                    print(f"✗ {table_name}: 存在しません")
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    check_tables()