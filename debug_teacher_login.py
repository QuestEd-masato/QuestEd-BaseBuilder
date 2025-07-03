#!/usr/bin/env python3
"""
教師ログイン問題デバッグスクリプト
===============================

教師アカウントのログイン関連情報を調査します。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models import User, School, db
from extensions import db
from werkzeug.security import check_password_hash

def check_teacher_accounts():
    """教師アカウントの状態をチェック"""
    print("🔍 教師アカウント調査")
    print("=" * 60)
    
    # 教師アカウント一覧取得
    teachers = User.query.filter_by(role='teacher').all()
    
    print(f"登録教師数: {len(teachers)}")
    print()
    
    for i, teacher in enumerate(teachers, 1):
        print(f"教師 {i}:")
        print(f"  - ID: {teacher.id}")
        print(f"  - ユーザー名: {teacher.username}")
        print(f"  - 表示名: {teacher.full_name}")
        print(f"  - メール: {teacher.email}")
        print(f"  - メール確認: {'✅' if teacher.email_confirmed else '❌'}")
        print(f"  - 承認状態: {'✅' if teacher.is_approved else '❌'}")
        print(f"  - アクティブ: {'✅' if teacher.is_active else '❌'}")
        print(f"  - 学校ID: {teacher.school_id}")
        
        # 学校情報
        if teacher.school_id:
            school = School.query.get(teacher.school_id)
            if school:
                print(f"  - 学校名: {school.name}")
                print(f"  - 学校コード: {school.code}")
            else:
                print(f"  - 学校: ❌ 見つからない (ID: {teacher.school_id})")
        else:
            print(f"  - 学校: ❌ 未設定")
        
        print()

def test_login_conditions():
    """ログイン条件をテスト"""
    print("🧪 ログイン条件テスト")
    print("=" * 60)
    
    teachers = User.query.filter_by(role='teacher').all()
    
    for teacher in teachers:
        print(f"教師: {teacher.username}")
        
        # 基本条件チェック
        conditions = {
            "メール確認済み": teacher.email_confirmed,
            "アクティブ": teacher.is_active,
            "学校設定済み": teacher.school_id is not None,
            "パスワード設定済み": teacher.password is not None
        }
        
        all_ok = all(conditions.values())
        
        for condition, status in conditions.items():
            print(f"  - {condition}: {'✅' if status else '❌'}")
        
        print(f"  - 総合判定: {'✅ ログイン可能' if all_ok else '❌ ログイン不可'}")
        print()

def test_sample_passwords():
    """サンプルパスワードでテスト"""
    print("🔐 パスワードテスト")
    print("=" * 60)
    
    teachers = User.query.filter_by(role='teacher').limit(3).all()
    common_passwords = ['password', 'teacher123', 'admin', '123456', 'test']
    
    for teacher in teachers:
        print(f"教師: {teacher.username}")
        
        if not teacher.password:
            print("  - パスワード未設定")
            continue
        
        # 一般的なパスワードをテスト
        found = False
        for pwd in common_passwords:
            if check_password_hash(teacher.password, pwd):
                print(f"  - パスワード: {pwd} ✅")
                found = True
                break
        
        if not found:
            print("  - パスワード: 不明（一般的なパスワードではない）")
        
        print()

def main():
    """メイン処理"""
    try:
        # データベース接続テスト
        total_users = User.query.count()
        print(f"📊 総ユーザー数: {total_users}")
        print()
        
        # 各チェック実行
        check_teacher_accounts()
        test_login_conditions()
        test_sample_passwords()
        
        # 推奨事項
        print("💡 推奨事項")
        print("=" * 60)
        print("1. 教師アカウントのメール確認状態を確認")
        print("2. 学校コードが正しく設定されているか確認")
        print("3. パスワードリセット機能を使用")
        print("4. 新規教師アカウントを作成してテスト")
        
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()