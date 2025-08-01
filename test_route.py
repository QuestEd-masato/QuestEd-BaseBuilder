#!/usr/bin/env python3
"""
特定のルートをテストするためのスクリプト
500エラーの詳細を確認
"""
import sys
import traceback
from app import create_app
from flask import Flask
from flask_login import login_user
from app.models import User, Class

app = create_app()

with app.app_context():
    try:
        # データベース接続テスト
        print("=== データベース接続テスト ===")
        from extensions import db
        from sqlalchemy import text
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ データベース接続: 成功")
        
        # クラスID 8の存在確認
        print("\n=== クラスデータ確認 ===")
        class_obj = Class.query.get(8)
        if class_obj:
            print(f"✓ クラスID 8: 存在 (名前: {class_obj.name})")
        else:
            print("✗ クラスID 8: 存在しない")
            
        # テンプレートフィルターの確認
        print("\n=== テンプレートフィルター確認 ===")
        if 'fromjson' in app.jinja_env.filters:
            print("✓ fromjson フィルター: 登録済み")
        else:
            print("✗ fromjson フィルター: 未登録")
            
        if 'from_json' in app.jinja_env.filters:
            print("✓ from_json フィルター: 登録済み")
        else:
            print("✗ from_json フィルター: 未登録")
            
        # CurriculumOrchestrationServiceのテスト
        print("\n=== CurriculumOrchestrationService テスト ===")
        from app.services.curriculum.curriculum_orchestration_service import CurriculumOrchestrationService
        orchestration_service = CurriculumOrchestrationService()
        
        # モックユーザーでテスト（権限チェックをスキップ）
        with app.test_request_context():
            result = orchestration_service.get_curriculums_view(8)
            print(f"結果: {result}")
            
    except Exception as e:
        print(f"\nエラーが発生しました:")
        print(f"エラータイプ: {type(e).__name__}")
        print(f"エラーメッセージ: {str(e)}")
        print("\nスタックトレース:")
        traceback.print_exc()