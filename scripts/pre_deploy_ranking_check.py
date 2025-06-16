#!/usr/bin/env python3
"""
QuestEd ランキングシステム デプロイ前チェックスクリプト

ランキング機能のデプロイ前に実行するセキュリティと整合性チェック

Author: QuestEd Development Team
Created: 2025-01-15
Version: 1.0.0
"""

import sys
import os
import importlib.util
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_imports():
    """必要なモジュールのインポートチェック"""
    print("🔍 インポートチェック開始...")
    
    required_modules = [
        ('app.models', ['Ranking', 'RankingCache']),
        ('app.services.ranking_service', ['RankingService']),
        ('app.utils.exceptions', ['SecurityError']),
        ('app.utils.database_security', ['DatabaseSecurityManager']),
        ('app.config.security_config', ['validate_ranking_params', 'get_cache_duration'])
    ]
    
    for module_name, classes in required_modules:
        try:
            module = importlib.import_module(module_name)
            for class_name in classes:
                if not hasattr(module, class_name):
                    print(f"❌ {module_name}.{class_name} が見つかりません")
                    return False
            print(f"✅ {module_name} - OK")
        except ImportError as e:
            print(f"❌ {module_name} のインポートに失敗: {e}")
            return False
    
    return True

def check_file_existence():
    """必要なファイルの存在チェック"""
    print("\n📁 ファイル存在チェック開始...")
    
    required_files = [
        'app/services/ranking_service.py',
        'app/utils/exceptions.py',
        'app/utils/database_security.py',
        'app/config/security_config.py',
        'templates/student/ranking.html',
        'templates/teacher/ranking_analysis.html',
        'templates/components/ranking_widget.html',
        'static/js/ranking.js',
        'tests/test_ranking.py',
        'migrations/versions/add_ranking_system.py'
    ]
    
    for file_path in required_files:
        full_path = project_root / file_path
        if not full_path.exists():
            print(f"❌ {file_path} が見つかりません")
            return False
        print(f"✅ {file_path} - OK")
    
    return True

def check_template_syntax():
    """テンプレートの基本構文チェック"""
    print("\n🎨 テンプレート構文チェック開始...")
    
    template_files = [
        'templates/student/ranking.html',
        'templates/teacher/ranking_analysis.html',
        'templates/components/ranking_widget.html'
    ]
    
    for template_path in template_files:
        full_path = project_root / template_path
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 基本的なJinja2構文チェック
            if '{{' in content and '}}' not in content:
                print(f"❌ {template_path}: 閉じられていない{{{{があります")
                return False
            if '{%' in content and '%}' not in content:
                print(f"❌ {template_path}: 閉じられていない{{%があります")
                return False
            
            # XSS対策チェック
            if 'student_name' in content and '|e' not in content and 'escapeHtml' not in content:
                print(f"⚠️  {template_path}: XSS対策が不十分な可能性があります")
            
            print(f"✅ {template_path} - OK")
            
        except Exception as e:
            print(f"❌ {template_path}: 読み込みエラー - {e}")
            return False
    
    return True

def check_javascript_security():
    """JavaScript セキュリティチェック"""
    print("\n🔒 JavaScript セキュリティチェック開始...")
    
    js_file = project_root / 'static/js/ranking.js'
    try:
        with open(js_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # セキュリティチェック項目
        security_checks = [
            ('escapeHtml', 'HTMLエスケープ関数'),
            ('encodeURIComponent', 'URLエンコーディング'),
            ('JSON.parse', 'JSON解析')
        ]
        
        for pattern, description in security_checks:
            if pattern not in content:
                print(f"⚠️  {description} ({pattern}) が見つかりません")
            else:
                print(f"✅ {description} - OK")
        
        # 危険なパターンチェック
        dangerous_patterns = [
            ('eval(', 'eval関数の使用'),
            ('innerHTML =', '直接的なHTML挿入'),
            ('document.write', 'document.write の使用')
        ]
        
        for pattern, description in dangerous_patterns:
            if pattern in content:
                print(f"⚠️  危険なパターン検出: {description}")
        
        return True
        
    except Exception as e:
        print(f"❌ JavaScript ファイル読み込みエラー: {e}")
        return False

def check_database_migration():
    """データベースマイグレーションファイルチェック"""
    print("\n💾 データベースマイグレーションチェック開始...")
    
    migration_file = project_root / 'migrations/versions/add_ranking_system.py'
    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_elements = [
            ('def upgrade():', 'upgrade関数'),
            ('def downgrade():', 'downgrade関数'),
            ('ranking', 'rankingテーブル'),
            ('ranking_cache', 'ranking_cacheテーブル'),
            ('ForeignKeyConstraint', '外部キー制約'),
            ('create_index', 'インデックス作成')
        ]
        
        for element, description in required_elements:
            if element not in content:
                print(f"❌ {description} が見つかりません")
                return False
            print(f"✅ {description} - OK")
        
        return True
        
    except Exception as e:
        print(f"❌ マイグレーションファイル読み込みエラー: {e}")
        return False

def check_api_security():
    """API セキュリティ設定チェック"""
    print("\n🛡️  API セキュリティチェック開始...")
    
    try:
        # APIファイルの存在確認
        api_file = project_root / 'app/api/__init__.py'
        with open(api_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        security_features = [
            ('@login_required', 'ログイン必須デコレータ'),
            ('@api_limit()', 'レート制限'),
            ('jsonify({', 'JSON レスポンス'),
            ('request.args.get', 'パラメータ取得'),
            ('current_user.role', '権限チェック')
        ]
        
        for feature, description in security_features:
            if feature not in content:
                print(f"⚠️  {description} が見つかりません")
            else:
                print(f"✅ {description} - OK")
        
        return True
        
    except Exception as e:
        print(f"❌ API セキュリティチェックエラー: {e}")
        return False

def generate_deployment_report():
    """デプロイメントレポート生成"""
    print("\n📊 デプロイメントレポート生成中...")
    
    report = """
# QuestEd ランキングシステム デプロイメントレポート

## ✅ チェック完了項目
- モジュールインポート
- ファイル存在確認
- テンプレート構文
- JavaScript セキュリティ
- データベースマイグレーション
- API セキュリティ

## 🚀 デプロイ手順
1. データベースマイグレーション実行:
   ```bash
   flask db upgrade
   ```

2. 静的ファイルの配信確認:
   ```bash
   nginx -t
   systemctl reload nginx
   ```

3. アプリケーション再起動:
   ```bash
   systemctl restart quested
   ```

4. ランキングキャッシュ初期化:
   ```bash
   python -c "from app.services.ranking_service import RankingService; RankingService.clear_cache()"
   ```

## ⚠️  注意事項
- 本番環境では必ずHTTPSを使用してください
- ランキングデータは定期的にバックアップしてください
- パフォーマンスモニタリングを実施してください

## 📝 設定確認項目
- [ ] DATABASE_URL が正しく設定されている
- [ ] REDIS_URL が設定されている（キャッシュ使用時）
- [ ] セキュリティヘッダーが設定されている
- [ ] ログローテーションが設定されている
"""
    
    report_file = project_root / 'DEPLOYMENT_REPORT_RANKING.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ レポートを生成しました: {report_file}")

def main():
    """メイン実行関数"""
    print("🎯 QuestEd ランキングシステム デプロイ前チェック開始\n")
    
    checks = [
        check_imports,
        check_file_existence,
        check_template_syntax,
        check_javascript_security,
        check_database_migration,
        check_api_security
    ]
    
    all_passed = True
    for check in checks:
        if not check():
            all_passed = False
            print("❌ チェックに失敗しました")
        print()
    
    if all_passed:
        print("🎉 すべてのチェックが完了しました！")
        print("✅ ランキングシステムはデプロイ可能です")
        generate_deployment_report()
        return 0
    else:
        print("⚠️  いくつかの問題が検出されました")
        print("❌ 問題を修正してから再度実行してください")
        return 1

if __name__ == '__main__':
    sys.exit(main())