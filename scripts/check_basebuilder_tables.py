#!/usr/bin/env python3
"""
BaseBuilder Database Table Existence Check
==========================================
BaseBuilderモジュールに必要なテーブルの存在を確認するスクリプト

使用方法:
    python scripts/check_basebuilder_tables.py

このスクリプトは機能に影響を与えません（読み取り専用）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask
from extensions import db
from config import get_config

def check_basebuilder_tables():
    """BaseBuilder必要テーブルの存在確認"""
    
    # 必要なテーブル一覧（basebuilder/models.pyより）
    required_tables = [
        'problem_categories',
        'text_deliveries', 
        'basic_knowledge_items',
        'knowledge_theme_relations',
        'answer_records',
        'proficiency_records',
        'text_proficiency_records',
        'basebuilder_learning_paths',
        'path_assignments',
        'word_proficiency_records',
        'text_sets'
    ]
    
    # 外部依存テーブル（他モジュールで定義）
    external_dependencies = [
        'users',
        'schools', 
        'subjects',
        'classes'
    ]
    
    print("🔍 BaseBuilder Database Table Check")
    print("=" * 50)
    
    try:
        # Flaskアプリケーション初期化
        app = Flask(__name__)
        config = get_config()
        app.config.from_object(config)
        db.init_app(app)
        
        with app.app_context():
            # データベース接続テスト
            try:
                inspector = db.inspect(db.engine)
                existing_tables = inspector.get_table_names()
                print(f"✅ Database connection successful")
                print(f"📊 Total tables in database: {len(existing_tables)}")
                print()
                
            except Exception as e:
                print(f"❌ Database connection failed: {e}")
                return False
            
            # BaseBuilder必要テーブルチェック
            print("🎯 BaseBuilder Required Tables:")
            missing_tables = []
            existing_basebuilder_tables = []
            
            for table in required_tables:
                if table in existing_tables:
                    print(f"   ✅ {table}")
                    existing_basebuilder_tables.append(table)
                else:
                    print(f"   ❌ {table} (MISSING)")
                    missing_tables.append(table)
            
            print()
            
            # 外部依存テーブルチェック
            print("🔗 External Dependencies:")
            missing_dependencies = []
            
            for table in external_dependencies:
                if table in existing_tables:
                    print(f"   ✅ {table}")
                else:
                    print(f"   ❌ {table} (MISSING)")
                    missing_dependencies.append(table)
            
            print()
            
            # 結果サマリー
            print("📊 Check Results:")
            print(f"   BaseBuilder tables: {len(existing_basebuilder_tables)}/{len(required_tables)} exist")
            print(f"   Dependencies: {len(external_dependencies) - len(missing_dependencies)}/{len(external_dependencies)} exist")
            
            if missing_tables:
                print(f"\n⚠️  Missing BaseBuilder tables: {', '.join(missing_tables)}")
                
            if missing_dependencies:
                print(f"\n⚠️  Missing dependencies: {', '.join(missing_dependencies)}")
            
            # 総合判定
            if not missing_tables and not missing_dependencies:
                print("\n🎉 All required tables exist! BaseBuilder should work properly.")
                return True
            elif not missing_dependencies:
                print("\n🟡 Dependencies OK, but BaseBuilder tables are missing.")
                print("   → Run 'flask db upgrade' to create missing tables")
                return False
            else:
                print("\n🔴 Critical dependencies missing. BaseBuilder cannot function.")
                return False
                
    except Exception as e:
        print(f"❌ Script execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_basebuilder_tables()
    sys.exit(0 if success else 1)