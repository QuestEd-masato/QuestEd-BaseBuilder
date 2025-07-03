#!/usr/bin/env python3
"""
Database Connection Check
========================
データベース接続確認スクリプト
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_database_connection():
    """データベース接続をテスト"""
    
    print("🔍 Database Connection Check")
    print("=" * 50)
    
    # .envファイルの確認
    env_file = project_root / '.env'
    if not env_file.exists():
        print("❌ .env file not found")
        print("💡 Create .env file by copying .env.dev:")
        print("   cp .env.dev .env")
        return False
    
    print("✅ .env file found")
    
    try:
        # 環境変数の読み込み
        from dotenv import load_dotenv
        load_dotenv()
        
        # データベース設定の確認
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '3306')),
            'user': os.getenv('DB_USERNAME'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME')
        }
        
        print("\n📊 Database Configuration:")
        print(f"   Host: {db_config['host']}")
        print(f"   Port: {db_config['port']}")
        print(f"   User: {db_config['user']}")
        print(f"   Database: {db_config['database']}")
        
        # PyMySQLでの接続テスト
        print("\n🔄 Testing connection with PyMySQL...")
        import pymysql
        
        connection = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset='utf8mb4'
        )
        
        print("✅ PyMySQL connection successful")
        
        # テーブル数の確認
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s", (db_config['database'],))
            table_count = cursor.fetchone()[0]
            print(f"📊 Tables in database: {table_count}")
        
        connection.close()
        
        # SQLAlchemyでの接続テスト
        print("\n🔄 Testing connection with SQLAlchemy...")
        from sqlalchemy import create_engine
        
        db_url = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print("✅ SQLAlchemy connection successful")
        
        print("\n🎉 Database connection test passed!")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        print("💡 Install required packages:")
        print("   pip3 install pymysql python-dotenv sqlalchemy")
        return False
        
    except pymysql.err.OperationalError as e:
        print(f"\n❌ Database Connection Error: {e}")
        print("\n💡 Possible solutions:")
        print("   1. Check if MySQL is running:")
        print("      docker ps | grep mysql")
        print("   2. Start MySQL container:")
        print("      docker compose -f docker-compose.dev.yml up -d")
        print("   3. Check database credentials in .env file")
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_database_connection()
    sys.exit(0 if success else 1)