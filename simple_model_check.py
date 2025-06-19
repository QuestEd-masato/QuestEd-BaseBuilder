#!/usr/bin/env python3
"""
簡易モデル構文チェック

Flaskライブラリなしでモデル定義の構文チェックのみ実行
"""

import sys
import ast

def check_python_syntax(file_path):
    """Pythonファイルの構文をチェック"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # ASTによる構文解析
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, f"構文エラー: {e}"
    except Exception as e:
        return False, f"エラー: {e}"

def main():
    print("=== QuestEd モデル構文チェック ===\n")
    
    # チェックするファイルリスト
    model_files = [
        "app/models/__init__.py",
        "app/models/speech_transcription.py", 
        "app/models/ai_recommendation.py",
        "app/models/review_system.py",
        "app/models/curriculum_unit.py",
        "app/models/email_log.py",
        "app/models/subject.py",
        "basebuilder/models.py"
    ]
    
    results = []
    
    for file_path in model_files:
        print(f"チェック中: {file_path}")
        is_valid, error_msg = check_python_syntax(file_path)
        
        if is_valid:
            print(f"   ✅ 構文OK")
        else:
            print(f"   ❌ {error_msg}")
        
        results.append((file_path, is_valid, error_msg))
        print()
    
    # サマリー
    print("=== チェック結果サマリー ===")
    valid_count = sum(1 for _, is_valid, _ in results if is_valid)
    total_count = len(results)
    
    print(f"有効なファイル: {valid_count}/{total_count}")
    
    if valid_count == total_count:
        print("🎉 全ファイルの構文チェックが成功しました！")
    else:
        print("\n❌ エラーのあるファイル:")
        for file_path, is_valid, error_msg in results:
            if not is_valid:
                print(f"   - {file_path}: {error_msg}")
    
    # モデルクラス数の確認
    print("\n=== 定義されたモデルクラス ===")
    
    # 簡易的なクラス検索
    all_classes = []
    for file_path, is_valid, _ in results:
        if is_valid:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # class定義を検索（コメントアウトされていないもの）
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('class ') and '(db.Model)' in line and not line.startswith('#'):
                        class_name = line.split('class ')[1].split('(')[0].strip()
                        all_classes.append((class_name, file_path))
            except:
                pass
    
    print(f"RDS互換モデルクラス数: {len(all_classes)}")
    for class_name, file_path in sorted(all_classes):
        print(f"   - {class_name} ({file_path})")

if __name__ == "__main__":
    main()