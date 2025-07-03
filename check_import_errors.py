#!/usr/bin/env python3
"""
Import Error Checker
===================

主要なモジュールのインポートエラーをチェックします。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_import(module_name, description):
    """モジュールインポートをテスト"""
    try:
        __import__(module_name)
        print(f"✅ {description:<40}: OK")
        return True
    except Exception as e:
        print(f"❌ {description:<40}: {str(e)}")
        return False

def main():
    """主要モジュールのインポートをテスト"""
    print("🔍 Import Error Analysis")
    print("=" * 60)
    
    success_count = 0
    total_count = 0
    
    tests = [
        ("app.auth", "Auth Module"),
        ("app.teacher", "Teacher Module"),
        ("app.student", "Student Module"),
        ("app.admin", "Admin Module"),
        ("app.teacher.modules.dashboard", "Teacher Dashboard"),
        ("app.student.modules.dashboard", "Student Dashboard"),
        ("app.services.curriculum_bridge_service", "Curriculum Bridge Service"),
        ("app.services.ranking_service", "Ranking Service"),
        ("app.models", "Database Models"),
        ("extensions", "Flask Extensions"),
        ("config", "Configuration"),
        ("basebuilder", "BaseBuilder Module"),
        ("basebuilder.models", "BaseBuilder Models"),
        ("basebuilder.routes", "BaseBuilder Routes")
    ]
    
    for module, description in tests:
        if check_import(module, description):
            success_count += 1
        total_count += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {success_count}/{total_count} modules imported successfully")
    
    if success_count < total_count:
        print(f"❌ {total_count - success_count} modules have import errors")
        print("These errors may cause 500 internal server errors.")
    else:
        print("✅ All modules imported successfully")
        print("Import errors are not the cause of the 500 error.")
    
    return success_count == total_count

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test script failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)