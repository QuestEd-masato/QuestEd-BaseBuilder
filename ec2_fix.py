#!/usr/bin/env python3
"""
EC2環境での問題修正スクリプト
"""

import os
import sys

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
    from basebuilder.models import ProblemCategory, BasicKnowledgeItem
    
    app = create_app()
    
    with app.app_context():
        print("=== QuestEd EC2 修正スクリプト ===")
        print()
        
        # 1. データベース接続確認
        try:
            user_count = User.query.count()
            print(f"✅ データベース接続成功 - ユーザー数: {user_count}")
        except Exception as e:
            print(f"❌ データベース接続失敗: {e}")
            sys.exit(1)
        
        # 2. DB3300カテゴリの問題を確認・修正
        print("\n2. DB3300カテゴリの確認と修正")
        db3300_category = ProblemCategory.query.filter(
            ProblemCategory.name.like('%DB3300%')
        ).first()
        
        if db3300_category:
            print(f"✅ DB3300カテゴリ発見: {db3300_category.name} (ID: {db3300_category.id})")
            
            total_problems = BasicKnowledgeItem.query.filter_by(
                category_id=db3300_category.id
            ).count()
            
            active_problems = BasicKnowledgeItem.query.filter_by(
                category_id=db3300_category.id, 
                is_active=True
            ).count()
            
            print(f"   総問題数: {total_problems}")
            print(f"   アクティブ問題数: {active_problems}")
            
            if total_problems > 0 and active_problems == 0:
                print("   ⚠️ 問題をアクティブ化中...")
                BasicKnowledgeItem.query.filter_by(
                    category_id=db3300_category.id
                ).update({'is_active': True})
                db.session.commit()
                print("   ✅ すべての問題をアクティブ化しました")
            elif active_problems > 0:
                print("   ✅ 問題は既にアクティブです")
        else:
            print("❌ DB3300カテゴリが見つかりません")
        
        # 3. 教師アカウントの確認と修正
        print("\n3. 教師アカウントの確認と修正")
        teachers = User.query.filter_by(role='teacher').all()
        print(f"教師アカウント数: {len(teachers)}")
        
        problematic_teachers = []
        for teacher in teachers:
            issues = []
            if not teacher.is_active:
                issues.append("inactive")
            if not teacher.is_approved:
                issues.append("not_approved")
            if not teacher.email_confirmed:
                issues.append("email_not_confirmed")
            
            if issues:
                problematic_teachers.append((teacher, issues))
            else:
                print(f"   ✅ {teacher.username}: 正常")
        
        # 教師アカウントの問題を修正
        if problematic_teachers:
            print("   ⚠️ 問題のある教師アカウントを修正中...")
            for teacher, issues in problematic_teachers:
                print(f"   修正: {teacher.username} - {', '.join(issues)}")
                teacher.is_active = True
                teacher.is_approved = True
                teacher.email_confirmed = True
                db.session.add(teacher)
            
            db.session.commit()
            print("   ✅ 教師アカウントの修正完了")
        else:
            print("   ✅ すべての教師アカウントが正常です")
        
        # 4. カテゴリの問題数統計更新
        print("\n4. カテゴリ統計の更新")
        categories = ProblemCategory.query.all()
        for category in categories:
            problem_count = BasicKnowledgeItem.query.filter_by(
                category_id=category.id
            ).count()
            active_count = BasicKnowledgeItem.query.filter_by(
                category_id=category.id, 
                is_active=True
            ).count()
            
            if problem_count > 0:
                print(f"   {category.name}: {active_count}/{problem_count} アクティブ")
        
        print("\n=== 修正完了 ===")
        print("以下を実行してアプリケーションを再起動してください：")
        print("sudo systemctl restart questEd")
        print("または適切な再起動コマンド")
        
except Exception as e:
    import traceback
    print(f"❌ スクリプト実行エラー: {e}")
    print(f"詳細: {traceback.format_exc()}")
    sys.exit(1)