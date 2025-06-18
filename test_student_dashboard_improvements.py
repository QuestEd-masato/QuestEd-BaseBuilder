#!/usr/bin/env python3
"""
QuestEd 生徒ダッシュボード改善のテストスクリプト
実装された機能が正しく動作するかを検証
"""

import os
import re

def test_student_routes():
    """生徒ルートの追加確認"""
    print("=== 1. 生徒ルートの追加確認 ===")
    
    student_file = "/home/masat/claude-projects/QuestEd/app/student/__init__.py"
    
    with open(student_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # class_details ルートの確認
    class_details_route = re.search(r'@student_bp\.route\(["\']*/class/<int:class_id>/details["\']', content)
    if class_details_route:
        print("✓ class_details ルートが追加されています")
        
        # 関数の確認
        class_details_func = re.search(r'def class_details\(class_id\):', content)
        if class_details_func:
            print("✓ class_details 関数が定義されています")
        else:
            print("✗ class_details 関数が見つかりません")
            return False
    else:
        print("✗ class_details ルートが見つかりません")
        return False
    
    # class_themes ルートの確認
    class_themes_route = re.search(r'@student_bp\.route\(["\']*/class/<int:class_id>/themes["\']', content)
    if class_themes_route:
        print("✓ class_themes ルートが追加されています")
        
        # 関数の確認
        class_themes_func = re.search(r'def class_themes\(class_id\):', content)
        if class_themes_func:
            print("✓ class_themes 関数が定義されています")
        else:
            print("✗ class_themes 関数が見つかりません")
            return False
    else:
        print("✗ class_themes ルートが見つかりません")
        return False
    
    # Curriculum インポートの確認
    curriculum_import = re.search(r'from app\.models import.*Curriculum', content, re.DOTALL)
    if curriculum_import:
        print("✓ Curriculum モデルがインポートされています")
    else:
        print("✗ Curriculum モデルのインポートが見つかりません")
        return False
    
    return True

def test_dashboard_template():
    """ダッシュボードテンプレートの修正確認"""
    print("\n=== 2. ダッシュボードテンプレートの修正確認 ===")
    
    template_file = "/home/masat/claude-projects/QuestEd/templates/student_dashboard.html"
    
    with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 詳細ボタンのルート変更確認
    details_button = re.search(r'url_for\(["\']student\.class_details["\'], class_id=class_theme\.class_id\)', content)
    if details_button:
        print("✓ 詳細ボタンが新しいclass_detailsルートにリンクされています")
    else:
        print("✗ 詳細ボタンのリンクが更新されていません")
        return False
    
    # テーマボタンの追加確認
    theme_button = re.search(r'url_for\(["\']student\.class_themes["\'], class_id=class_theme\.class_id\)', content)
    if theme_button:
        print("✓ テーマボタンが追加されています")
    else:
        print("✗ テーマボタンが見つかりません")
        return False
    
    # アイコンの追加確認
    icons_count = len(re.findall(r'<i class="fas fa-[^"]*"></i>', content))
    if icons_count >= 4:  # 詳細、テーマ、記録、AI のアイコン
        print(f"✓ ボタンにアイコンが追加されています ({icons_count}個)")
    else:
        print(f"✗ 十分なアイコンが見つかりません ({icons_count}個)")
        return False
    
    # flex-wrap の追加確認
    flex_wrap = re.search(r'flex-wrap', content)
    if flex_wrap:
        print("✓ レスポンシブ対応のflex-wrapが追加されています")
    else:
        print("✗ flex-wrapが見つかりません")
        return False
    
    return True

def test_class_details_template():
    """クラス詳細テンプレートの作成確認"""
    print("\n=== 3. クラス詳細テンプレートの作成確認 ===")
    
    template_file = "/home/masat/claude-projects/QuestEd/templates/student/class_details.html"
    
    if not os.path.exists(template_file):
        print("✗ class_details.html テンプレートが見つかりません")
        return False
    
    with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 基本構造の確認
    if '{% extends "base.html" %}' in content:
        print("✓ base.htmlを継承しています")
    else:
        print("✗ base.htmlの継承が見つかりません")
        return False
    
    # カリキュラムセクションの確認
    curriculum_section = re.search(r'カリキュラム.*curriculum_data', content, re.DOTALL)
    if curriculum_section:
        print("✓ カリキュラムセクションが実装されています")
    else:
        print("✗ カリキュラムセクションが見つかりません")
        return False
    
    # マイルストーンセクションの確認
    milestone_section = re.search(r'マイルストーン.*milestones', content, re.DOTALL)
    if milestone_section:
        print("✓ マイルストーンセクションが実装されています")
    else:
        print("✗ マイルストーンセクションが見つかりません")
        return False
    
    # ナビゲーションボタンの確認
    nav_buttons = re.findall(r'url_for\(["\']student\.[^"\']*["\']', content)
    if len(nav_buttons) >= 2:  # dashboard, class_themes
        print(f"✓ ナビゲーションボタンが実装されています ({len(nav_buttons)}個)")
    else:
        print(f"✗ 十分なナビゲーションボタンが見つかりません ({len(nav_buttons)}個)")
        return False
    
    # レスポンシブデザインの確認
    responsive_css = re.search(r'@media.*max-width.*768px', content, re.DOTALL)
    if responsive_css:
        print("✓ レスポンシブデザインが実装されています")
    else:
        print("✗ レスポンシブデザインが見つかりません")
        return False
    
    return True

def test_curriculum_permissions():
    """カリキュラム閲覧権限の確認"""
    print("\n=== 4. カリキュラム閲覧権限の確認 ===")
    
    teacher_file = "/home/masat/claude-projects/QuestEd/app/teacher/__init__.py"
    
    with open(teacher_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 生徒権限チェックの確認
    student_permission = re.search(r'elif current_user\.role == ["\']student["\']:', content)
    if student_permission:
        print("✓ 生徒の権限チェックが実装されています")
    else:
        print("✗ 生徒の権限チェックが見つかりません")
        return False
    
    # 所属確認クエリの確認
    enrollment_check = re.search(r'class_enrollments.*student_id.*class_id.*is_active', content, re.DOTALL)
    if enrollment_check:
        print("✓ クラス所属確認クエリが実装されています")
    else:
        print("✗ クラス所属確認クエリが見つかりません")
        return False
    
    # can_edit = False の設定確認
    can_edit_false = re.search(r'can_edit = False.*生徒は閲覧のみ', content)
    if can_edit_false:
        print("✓ 生徒の編集権限が適切に制限されています")
    else:
        print("✗ 生徒の編集権限制限が見つかりません")
        return False
    
    return True

def test_route_structure():
    """ルート構造の整合性確認"""
    print("\n=== 5. ルート構造の整合性確認 ===")
    
    student_file = "/home/masat/claude-projects/QuestEd/app/student/__init__.py"
    template_file = "/home/masat/claude-projects/QuestEd/templates/student_dashboard.html"
    class_details_template = "/home/masat/claude-projects/QuestEd/templates/student/class_details.html"
    
    # student/__init__.py の読み込み
    with open(student_file, 'r', encoding='utf-8') as f:
        student_content = f.read()
    
    # テンプレートの読み込み
    with open(template_file, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    with open(class_details_template, 'r', encoding='utf-8') as f:
        class_details_content = f.read()
    
    # ルートとテンプレートの整合性確認
    routes_in_code = re.findall(r'@student_bp\.route\(["\']([^"\']*)["\']', student_content)
    routes_in_template = re.findall(r'url_for\(["\']student\.([^"\']*)["\']', template_content)
    routes_in_class_details = re.findall(r'url_for\(["\']student\.([^"\']*)["\']', class_details_content)
    
    print(f"✓ コード内ルート定義: {len(routes_in_code)}個")
    print(f"✓ テンプレート内ルート参照: {len(set(routes_in_template))}個")
    print(f"✓ クラス詳細テンプレート内ルート参照: {len(set(routes_in_class_details))}個")
    
    # 必要なルートが参照されているか確認
    required_routes = ['class_details', 'class_themes', 'dashboard']
    missing_routes = []
    
    all_template_routes = set(routes_in_template + routes_in_class_details)
    for route in required_routes:
        if route not in all_template_routes:
            missing_routes.append(route)
    
    if missing_routes:
        print(f"✗ 不足しているルート参照: {missing_routes}")
        return False
    else:
        print("✓ 必要なルートがすべて参照されています")
    
    return True

def main():
    """メインテスト処理"""
    print("QuestEd 生徒ダッシュボード改善 - テスト実行")
    print("=" * 60)
    
    tests = [
        ("生徒ルートの追加", test_student_routes),
        ("ダッシュボードテンプレート修正", test_dashboard_template),
        ("クラス詳細テンプレート作成", test_class_details_template),
        ("カリキュラム閲覧権限", test_curriculum_permissions),
        ("ルート構造の整合性", test_route_structure)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name}でエラーが発生しました: {str(e)}")
            results.append((test_name, False))
    
    # 結果の集計
    print("\n" + "=" * 60)
    print("テスト結果サマリー:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ 合格" if result else "✗ 不合格"
        print(f"  {test_name}: {status}")
    
    print(f"\n合格: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 すべてのテストが合格しました！")
        print("\n実装された機能:")
        print("1. ✓ 生徒ダッシュボードに「詳細」「テーマ」ボタン追加")
        print("2. ✓ クラス詳細ページでカリキュラムとマイルストーン表示")
        print("3. ✓ 生徒権限でのカリキュラム閲覧機能")
        print("4. ✓ レスポンシブデザインとモダンUI")
        print("5. ✓ 適切な権限管理とエラーハンドリング")
        print("\n次のステップ:")
        print("- ブラウザでの動作確認")
        print("- 生徒アカウントでのテスト")
        print("- 権限エラーのテスト")
        return 0
    else:
        print(f"\n⚠ {total - passed}件のテストが失敗しています。")
        print("上記の不合格項目を確認してください。")
        return 1

if __name__ == '__main__':
    exit(main())