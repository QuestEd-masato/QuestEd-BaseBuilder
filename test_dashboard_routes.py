#!/usr/bin/env python3
"""
Dashboard Routes Test Script
===========================

ログイン後のダッシュボードルートが正常に動作するかテストします。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from flask import url_for

def test_dashboard_routes():
    """ダッシュボードルートの存在と生成をテスト"""
    app = create_app()
    
    with app.app_context():
        print("🔍 Testing Dashboard Routes Registration")
        print("=" * 50)
        
        # 登録されているすべてのルートを取得
        rules = list(app.url_map.iter_rules())
        
        # ダッシュボード関連のルートを検索
        dashboard_routes = []
        for rule in rules:
            if 'dashboard' in rule.endpoint or 'dashboard' in str(rule.rule):
                dashboard_routes.append((rule.endpoint, rule.rule, rule.methods))
        
        print("Found Dashboard Routes:")
        for endpoint, rule, methods in dashboard_routes:
            print(f"  {endpoint:<30} {rule:<25} {methods}")
        
        print("\n🧪 Testing URL Generation:")
        print("-" * 30)
        
        # 重要なダッシュボードエンドポイントのURL生成をテスト
        test_endpoints = [
            'student_dashboard.dashboard',
            'teacher_dashboard.dashboard', 
            'admin_panel.dashboard'
        ]
        
        for endpoint in test_endpoints:
            try:
                url = url_for(endpoint)
                print(f"✅ {endpoint:<30} → {url}")
            except Exception as e:
                print(f"❌ {endpoint:<30} → ERROR: {str(e)}")
        
        print("\n🔍 Blueprint Registration Check:")
        print("-" * 40)
        
        # Blueprintの登録状況を確認
        blueprints = list(app.blueprints.keys())
        relevant_blueprints = [bp for bp in blueprints if 'dashboard' in bp or bp in ['admin_panel', 'teacher', 'student']]
        
        for bp_name in relevant_blueprints:
            bp = app.blueprints[bp_name]
            print(f"Blueprint: {bp_name:<20} | URL Prefix: {bp.url_prefix}")
        
        print("\n🔍 Auth Redirect Endpoints Check:")
        print("-" * 40)
        
        # auth/__init__.pyで使用されているエンドポイントが存在するかチェック
        auth_endpoints = [
            'student_dashboard.dashboard',
            'teacher_dashboard.dashboard',
            'admin_panel.dashboard'
        ]
        
        working_endpoints = []
        broken_endpoints = []
        
        for endpoint in auth_endpoints:
            try:
                url = url_for(endpoint)
                working_endpoints.append((endpoint, url))
            except Exception as e:
                broken_endpoints.append((endpoint, str(e)))
        
        print("✅ Working Endpoints:")
        for endpoint, url in working_endpoints:
            print(f"  {endpoint} → {url}")
        
        if broken_endpoints:
            print("\n❌ Broken Endpoints:")
            for endpoint, error in broken_endpoints:
                print(f"  {endpoint} → {error}")
        
        return len(broken_endpoints) == 0

def test_import_issues():
    """インポートエラーをテスト"""
    print("\n🔍 Testing Import Issues:")
    print("-" * 30)
    
    import_tests = [
        ("app.teacher.modules.dashboard", "Teacher Dashboard"),
        ("app.student.modules.dashboard", "Student Dashboard"), 
        ("app.admin", "Admin Panel"),
        ("app.auth", "Auth Module")
    ]
    
    for module, description in import_tests:
        try:
            __import__(module)
            print(f"✅ {description:<20} → Import OK")
        except Exception as e:
            print(f"❌ {description:<20} → Import Error: {str(e)}")

def main():
    """メイン処理"""
    print("🔧 Dashboard Routes Diagnostic")
    print("=" * 50)
    
    try:
        # インポートテスト
        test_import_issues()
        
        # ルートテスト
        routes_ok = test_dashboard_routes()
        
        print("\n🏁 Test Results:")
        print("=" * 20)
        if routes_ok:
            print("✅ All dashboard routes are working!")
            print("The login redirect issue may be caused by other factors.")
        else:
            print("❌ Some dashboard routes are broken!")
            print("This is likely the cause of the 500 error after login.")
        
        return routes_ok
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)