#!/usr/bin/env python3
"""
QuestEd カリキュラム機能修正の検証スクリプト
すべての修正が正しく適用されているかをチェック
"""

import os
import re

def check_curriculum_model():
    """Curriculumモデルのformat列チェック"""
    print("=== 1. Curriculumモデルのformat列チェック ===")
    
    model_file = "/home/masat/claude-projects/QuestEd/app/models/__init__.py"
    
    with open(model_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Curriculum クラス内でのformat列の定義を探す
    curriculum_class = re.search(r'class Curriculum\(.*?\):(.*?)(?=^class|\Z)', content, re.DOTALL | re.MULTILINE)
    
    if curriculum_class:
        class_content = curriculum_class.group(1)
        if 'format = db.Column' in class_content:
            print("✓ Curriculum.format 列が定義されています")
            
            # 詳細の確認
            format_line = re.search(r'format = db\.Column\([^)]*\)', class_content)
            if format_line:
                print(f"  定義: {format_line.group(0).strip()}")
            return True
        else:
            print("✗ Curriculum.format 列が見つかりません")
            print("  クラス内容の一部:")
            lines = class_content.split('\n')[:10]  # 最初の10行を表示
            for line in lines:
                if line.strip():
                    print(f"    {line.strip()}")
            return False
    else:
        print("✗ Curriculumクラスが見つかりません")
        return False

def check_import_paths():
    """インポートパスの修正チェック"""
    print("\n=== 2. インポートパスの修正チェック ===")
    
    teacher_file = "/home/masat/claude-projects/QuestEd/app/teacher/__init__.py"
    
    with open(teacher_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # view_curriculum関数内のインポートを確認
    view_curriculum = re.search(r'def view_curriculum\(.*?\):(.*?)(?=@teacher_bp\.route|def|\Z)', content, re.DOTALL)
    
    if view_curriculum:
        func_content = view_curriculum.group(1)
        
        # 正しいインポート
        if 'from app.models import ProblemCategory, TextSet' in func_content:
            print("✓ 正しいインポートパス: from app.models import ProblemCategory, TextSet")
            good_import = True
        else:
            print("✗ 正しいインポートが見つかりません")
            good_import = False
        
        # 古いインポートがないことを確認
        if 'from basebuilder.models import ProblemCategory, TextSet' not in func_content:
            print("✓ 古いインポートパスは削除されています")
            no_old_import = True
        else:
            print("✗ 古いインポートパスがまだ残っています")
            no_old_import = False
        
        return good_import and no_old_import
    else:
        print("✗ view_curriculum関数が見つかりません")
        return False

def check_csrf_token():
    """CSRFトークンの追加チェック"""
    print("\n=== 3. CSRFトークンの追加チェック ===")
    
    template_file = "/home/masat/claude-projects/QuestEd/templates/curriculum_unified.html"
    
    with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # フォーム内のCSRFトークンを確認
    csrf_pattern = r'<input[^>]*name=["\']csrf_token["\'][^>]*>'
    csrf_matches = re.findall(csrf_pattern, content)
    
    if csrf_matches:
        print(f"✓ CSRFトークンが{len(csrf_matches)}個見つかりました")
        for i, match in enumerate(csrf_matches, 1):
            print(f"  {i}. {match}")
        return True
    else:
        print("✗ CSRFトークンが見つかりません")
        return False

def check_delete_button():
    """削除ボタンのPOSTメソッド対応チェック"""
    print("\n=== 4. 削除ボタンのPOSTメソッド対応チェック ===")
    
    curriculums_file = "/home/masat/claude-projects/QuestEd/templates/curriculums.html"
    
    with open(curriculums_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 削除ボタンがフォームで実装されているかチェック
    delete_form = re.search(r'<form[^>]*action="[^"]*delete_curriculum[^"]*"[^>]*>', content)
    
    if delete_form:
        form_tag = delete_form.group(0)
        if 'method="POST"' in form_tag or "method='POST'" in form_tag:
            print("✓ 削除ボタンがPOSTメソッドのフォームで実装されています")
            print(f"  フォームタグ: {form_tag}")
            
            # CSRFトークンもチェック
            if 'csrf_token' in content:
                print("✓ 削除フォームにCSRFトークンも含まれています")
                return True
            else:
                print("⚠ 削除フォームにCSRFトークンがありません")
                return False
        else:
            print("✗ 削除フォームがPOSTメソッドを使用していません")
            return False
    else:
        print("✗ 削除ボタンがフォームで実装されていません")
        return False

def check_route_methods():
    """ルートのメソッド設定チェック"""
    print("\n=== 5. ルートのメソッド設定チェック ===")
    
    teacher_file = "/home/masat/claude-projects/QuestEd/app/teacher/__init__.py"
    
    with open(teacher_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # view_curriculumルートのメソッド確認
    view_route = re.search(r'@teacher_bp\.route\(["\'][^"\']*curriculum/<int:curriculum_id>["\'][^)]*\)', content)
    if view_route:
        route_def = view_route.group(0)
        if 'methods=' in route_def and 'POST' in route_def:
            print("✓ view_curriculumルートがGETとPOSTに対応しています")
            print(f"  定義: {route_def}")
            view_ok = True
        else:
            print("✗ view_curriculumルートがPOSTに対応していません")
            view_ok = False
    else:
        print("✗ view_curriculumルートが見つかりません")
        view_ok = False
    
    # delete_curriculumルートのメソッド確認
    delete_route = re.search(r'@teacher_bp\.route\([^)]*curriculum[^)]*delete[^)]*\)', content)
    if delete_route:
        route_def = delete_route.group(0)
        if "methods=['POST']" in route_def or 'methods=["POST"]' in route_def:
            print("✓ delete_curriculumルートがPOSTのみに対応しています")
            print(f"  定義: {route_def}")
            delete_ok = True
        else:
            print("✗ delete_curriculumルートがPOSTのみに対応していません")
            print(f"  見つかった定義: {route_def}")
            delete_ok = False
    else:
        print("✗ delete_curriculumルートが見つかりません")
        delete_ok = False
    
    return view_ok and delete_ok

def main():
    """メイン検証処理"""
    print("QuestEd カリキュラム機能修正の検証")
    print("=" * 50)
    
    results = []
    
    # 各チェックを実行
    results.append(("Curriculumモデルformat列", check_curriculum_model()))
    results.append(("インポートパス修正", check_import_paths()))
    results.append(("CSRFトークン追加", check_csrf_token()))
    results.append(("削除ボタンPOST対応", check_delete_button()))
    results.append(("ルートメソッド設定", check_route_methods()))
    
    # 結果の集計
    print("\n" + "=" * 50)
    print("検証結果サマリー:")
    
    total_checks = len(results)
    passed_checks = sum(1 for _, result in results if result)
    
    for name, result in results:
        status = "✓ 合格" if result else "✗ 不合格"
        print(f"  {name}: {status}")
    
    print(f"\n合格: {passed_checks}/{total_checks}")
    
    if passed_checks == total_checks:
        print("\n🎉 すべての修正が正しく適用されました！")
        print("\nカリキュラム機能は以下のエラーが解決されました:")
        print("1. ✓ CSRFトークンエラー")
        print("2. ✓ Curriculumモデルのformatフィールドエラー")
        print("3. ✓ 削除エンドポイントのHTTPメソッドエラー")
        print("\n次のステップ:")
        print("- データベースマイグレーションの実行")
        print("- ブラウザでの動作確認")
        return 0
    else:
        print(f"\n⚠ {total_checks - passed_checks}件の問題が残っています。")
        print("上記の不合格項目を確認してください。")
        return 1

if __name__ == '__main__':
    exit(main())