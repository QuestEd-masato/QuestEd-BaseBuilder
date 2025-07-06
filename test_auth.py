#!/usr/bin/env python3
"""
認証機能のテストスクリプト
"""
import os
import sys
import requests
from urllib.parse import urljoin

# 環境変数の設定
required_env_vars = {
    'SECRET_KEY': 'dev-secret-key-123',
    'DB_USERNAME': 'QuestEd', 
    'DB_PASSWORD': 'QuestEd-03012025MySQL',
    'DB_HOST': 'localhost',
    'DB_NAME': 'quested'
}

for key, value in required_env_vars.items():
    if key not in os.environ:
        os.environ[key] = value

try:
    from app import create_app
    from app.models import db, User
    
    app = create_app()
    
    with app.app_context():
        print("=== 認証機能テスト ===")
        print()
        
        # 1. 学生アカウントを確認
        print("1. 学生アカウントの確認")
        student = User.query.filter_by(role='student').first()
        
        if student:
            print(f"✅ 学生アカウント発見: {student.username}")
            print(f"   - ID: {student.id}")
            print(f"   - is_active: {student.is_active}")
            print(f"   - is_approved: {student.is_approved}")
            print(f"   - email_confirmed: {student.email_confirmed}")
            
            # 2. 認証状態のシミュレーション
            print("\n2. 認証状態のシミュレーション")
            
            # Flask-Login のコンテキストでテスト
            from flask_login import login_user, current_user
            
            with app.test_request_context():
                print("   ログイン前:")
                print(f"     - current_user.is_authenticated: {current_user.is_authenticated}")
                
                # ログイン試行
                login_user(student)
                print("   ログイン後:")
                print(f"     - current_user.is_authenticated: {current_user.is_authenticated}")
                print(f"     - current_user.id: {current_user.id}")
                print(f"     - current_user.username: {current_user.username}")
                print(f"     - current_user.role: {current_user.role}")
                
                # セッションキーのテスト
                from flask import session
                print(f"     - session keys: {list(session.keys())}")
                
                # 学習セッションキーの追加
                session['session_type'] = 'category'
                session['category_id'] = 1
                session['start_time'] = '2025-01-01T00:00:00'
                session['problems_answered'] = 0
                session['correct_answers'] = 0
                session['current_problem_index'] = 0
                session['problem_ids'] = [1, 2, 3]
                session['total_problems'] = 3
                
                print(f"     - session keys (after adding learning data): {list(session.keys())}")
                
                # 修正後のセッションクリア処理をテスト
                print("\n3. 修正後のセッションクリア処理のテスト")
                learning_keys = ['session_type', 'category_id', 'text_id', 'start_time', 
                               'problems_answered', 'correct_answers', 'current_problem_index',
                               'problem_ids', 'total_problems']
                for key in learning_keys:
                    session.pop(key, None)
                
                print(f"     - session keys (after selective clear): {list(session.keys())}")
                print(f"     - current_user.is_authenticated (after selective clear): {current_user.is_authenticated}")
                print(f"     - current_user.username (after selective clear): {current_user.username}")
                
        else:
            print("❌ 学生アカウントが見つかりません")
            
        # 3. 教師アカウントを確認
        print("\n3. 教師アカウントの確認")
        teacher = User.query.filter_by(role='teacher').first()
        
        if teacher:
            print(f"✅ 教師アカウント発見: {teacher.username}")
            print(f"   - ID: {teacher.id}")
            print(f"   - is_active: {teacher.is_active}")
            print(f"   - is_approved: {teacher.is_approved}")
            print(f"   - email_confirmed: {teacher.email_confirmed}")
            
            if not teacher.is_active or not teacher.is_approved or not teacher.email_confirmed:
                print("   ⚠️ 教師アカウントに問題があります。修正中...")
                teacher.is_active = True
                teacher.is_approved = True
                teacher.email_confirmed = True
                db.session.commit()
                print("   ✅ 教師アカウントを修正しました")
        else:
            print("❌ 教師アカウントが見つかりません")
            
        print("\n=== テスト完了 ===")
        print("修正が完了しました。以下のコマンドでアプリケーションを起動してください：")
        print("export SECRET_KEY='dev-secret-key-123' && export DB_USERNAME='QuestEd' && export DB_PASSWORD='QuestEd-03012025MySQL' && export DB_HOST='localhost' && export DB_NAME='quested' && python3 run.py")
        
except Exception as e:
    import traceback
    print(f"❌ テスト実行エラー: {e}")
    print(f"詳細: {traceback.format_exc()}")
    sys.exit(1)