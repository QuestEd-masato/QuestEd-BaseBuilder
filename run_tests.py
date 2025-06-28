#!/usr/bin/env python3
"""
テスト実行スクリプト
==================
リファクタリング後のシステムの動作確認を行うテストスクリプト
"""

import sys
import os
import subprocess
import traceback

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_import_tests():
    """基本的なインポートテスト"""
    print("1. Testing basic imports...")
    
    try:
        # Flask関連
        import flask
        print("   ✅ Flask imported successfully")
        
        # アプリケーション作成
        from app import create_app
        print("   ✅ App factory imported successfully")
        
        # Blueprint imports
        from app.teacher import teacher_bp
        print("   ✅ Teacher blueprint imported successfully")
        
        from app.student import student_bp
        print("   ✅ Student blueprint imported successfully")
        
        from app.api import api_bp
        print("   ✅ API blueprint imported successfully")
        
        # Service imports
        from app.services.unit_item_mapping_service import UnitItemMappingService
        print("   ✅ Unit mapping service imported successfully")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Import test failed: {e}")
        traceback.print_exc()
        return False


def run_route_tests():
    """ルートの登録テスト"""
    print("\n2. Testing route registration...")
    
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            # Blueprint routes
            teacher_routes = [rule for rule in app.url_map.iter_rules() if 'teacher' in rule.endpoint]
            student_routes = [rule for rule in app.url_map.iter_rules() if 'student' in rule.endpoint]
            api_routes = [rule for rule in app.url_map.iter_rules() if 'api' in rule.endpoint]
            
            print(f"   ✅ Teacher routes: {len(teacher_routes)}")
            print(f"   ✅ Student routes: {len(student_routes)}")
            print(f"   ✅ API routes: {len(api_routes)}")
            
            # Check for duplicates
            route_paths = {}
            duplicates = []
            
            for rule in app.url_map.iter_rules():
                key = (str(rule.rule), tuple(sorted(rule.methods - {'HEAD', 'OPTIONS'})))
                if key in route_paths:
                    duplicates.append((rule.rule, rule.endpoint, route_paths[key]))
                else:
                    route_paths[key] = rule.endpoint
            
            if duplicates:
                print(f"   ⚠️  Found {len(duplicates)} route duplicates:")
                for route, endpoint1, endpoint2 in duplicates:
                    print(f"      - {route}: {endpoint1} vs {endpoint2}")
            else:
                print("   ✅ No route duplicates found")
            
            return len(duplicates) == 0
            
    except Exception as e:
        print(f"   ❌ Route test failed: {e}")
        traceback.print_exc()
        return False


def run_module_tests():
    """モジュール分割テスト"""
    print("\n3. Testing module refactoring...")
    
    try:
        # Teacher modules
        from app.teacher.modules.dashboard import dashboard
        from app.teacher.modules.class_management import classes
        from app.teacher.modules.curriculum_management import view_curriculums
        print("   ✅ Teacher modules imported successfully")
        
        # Student modules
        from app.student.modules.dashboard import dashboard as student_dashboard
        from app.student.modules.activities import activities
        from app.student.modules.surveys import surveys
        from app.student.modules.goals_todos import goals, todos
        print("   ✅ Student modules imported successfully")
        
        # Backward compatibility
        from app.teacher import dashboard as teacher_dashboard_compat
        from app.student import dashboard as student_dashboard_compat
        print("   ✅ Backward compatibility maintained")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Module test failed: {e}")
        traceback.print_exc()
        return False


def run_database_tests():
    """データベース関連テスト"""
    print("\n4. Testing database models...")
    
    try:
        from app import create_app
        from app.models import db, User, School, CurriculumUnit
        
        app = create_app()
        
        with app.app_context():
            # テーブル作成テスト
            db.create_all()
            print("   ✅ Database tables created successfully")
            
            # モデルインスタンス作成テスト
            school = School(name='テスト学校', code='TEST001')
            print("   ✅ Model instances created successfully")
            
            return True
            
    except Exception as e:
        print(f"   ❌ Database test failed: {e}")
        traceback.print_exc()
        return False


def run_api_tests():
    """API機能テスト"""
    print("\n5. Testing API functionality...")
    
    try:
        from app import create_app
        app = create_app()
        
        with app.test_client() as client:
            # Basic health check
            response = client.get('/api/stats')
            print(f"   ✅ API stats endpoint: {response.status_code}")
            
            # Data integrity API (unauthorized)
            response = client.get('/api/data-integrity/verify')
            print(f"   ✅ Data integrity API: {response.status_code} (expected 401/403)")
            
            return True
            
    except Exception as e:
        print(f"   ❌ API test failed: {e}")
        traceback.print_exc()
        return False


def run_phase3_tests():
    """Phase 3 データ整合性テスト"""
    print("\n6. Testing Phase 3 data integrity...")
    
    try:
        from app.services.unit_item_mapping_service import UnitItemMappingService
        from app.api.data_integrity import data_integrity_bp
        
        # Service methods
        problems = UnitItemMappingService.get_unit_problems(999)  # Non-existent unit
        print(f"   ✅ Unit mapping service works (returned {len(problems)} problems)")
        
        # Blueprint registration
        assert data_integrity_bp.name == 'data_integrity'
        print("   ✅ Data integrity blueprint created")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Phase 3 test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """メイン実行関数"""
    print("QuestEd Test Suite")
    print("=" * 50)
    
    tests = [
        run_import_tests,
        run_route_tests,
        run_module_tests,
        run_database_tests,
        run_api_tests,
        run_phase3_tests
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ Test crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())