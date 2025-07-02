#!/usr/bin/env python3
"""
Database Migration Script
========================
Flask-Migrateコマンドの代替スクリプト
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 環境変数設定
os.environ['FLASK_APP'] = 'app.py'
os.environ['FLASK_ENV'] = 'development'

try:
    # .envファイルから環境変数を読み込み
    from dotenv import load_dotenv
    load_dotenv()
    
    # Flaskアプリケーションのインポート
    from app import app
    from extensions import db, migrate
    
    print("🔍 Database Migration Script")
    print("=" * 50)
    
    # アプリケーションコンテキストで実行
    with app.app_context():
        # データベース接続情報の表示
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')
        print(f"📊 Database URI: {db_uri[:50]}...")
        
        # マイグレーションディレクトリの確認
        migrations_dir = os.path.join(project_root, 'migrations')
        
        if not os.path.exists(migrations_dir):
            print("\n⚠️  Migrations directory not found. Initializing...")
            os.system('python3 -m flask db init')
            print("✅ Migrations initialized")
        
        # マイグレーションの生成
        print("\n🔄 Generating migration...")
        result = os.system('python3 -m flask db migrate -m "Create BaseBuilder and other tables"')
        
        if result == 0:
            print("✅ Migration generated successfully")
            
            # マイグレーションの適用
            print("\n📝 Applying migration...")
            result = os.system('python3 -m flask db upgrade')
            
            if result == 0:
                print("✅ Migration applied successfully")
                
                # テーブル確認
                print("\n🔍 Checking created tables...")
                from sqlalchemy import inspect
                
                inspector = inspect(db.engine)
                tables = inspector.get_table_names()
                
                print(f"📊 Total tables created: {len(tables)}")
                
                # BaseBuilder関連テーブルの確認
                basebuilder_tables = [t for t in tables if 'basebuilder' in t or 'problem' in t or 'proficiency' in t]
                
                print(f"\n📦 BaseBuilder related tables:")
                for table in basebuilder_tables:
                    print(f"   ✅ {table}")
                
                print("\n🎉 Database migration completed successfully!")
                
            else:
                print("❌ Failed to apply migration")
                sys.exit(1)
        else:
            print("❌ Failed to generate migration")
            sys.exit(1)
            
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("\n📋 Required packages:")
    print("   - flask")
    print("   - flask-sqlalchemy")
    print("   - flask-migrate")
    print("   - pymysql")
    print("   - python-dotenv")
    print("\n💡 Install with: pip3 install -r requirements.txt")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)