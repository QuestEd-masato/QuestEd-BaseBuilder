#!/usr/bin/env python3
"""
Ranking System Repair Test Script
================================

This script tests and repairs the ranking system by:
1. Testing the ranking calculation with proper user joins
2. Clearing corrupted cache data
3. Regenerating correct rankings
4. Verifying the results

Usage: python test_ranking_repair.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from app.services.ranking_service import RankingService
from app.models import User, RankingCache
from basebuilder.models import AnswerRecord

def clear_corrupted_cache():
    """破損したキャッシュデータをクリア"""
    print("🧹 Clearing corrupted ranking cache...")
    
    # 破損したキャッシュを削除
    corrupted_count = RankingCache.query.filter(
        RankingCache.ranking_data.contains('"student_name": "Unknown"')
    ).count()
    
    print(f"Found {corrupted_count} corrupted cache entries")
    
    if corrupted_count > 0:
        RankingService.clear_cache()
        print("✅ Corrupted cache cleared")
    else:
        print("No corrupted cache found")

def test_user_data_integrity():
    """ユーザーデータの整合性を確認"""
    print("🔍 Testing user data integrity...")
    
    # 実際の学習データがあるユーザーを確認
    users_with_answers = db.session.query(
        User.id, User.username, User.role
    ).join(
        AnswerRecord, User.id == AnswerRecord.student_id
    ).group_by(User.id).all()
    
    print(f"Found {len(users_with_answers)} users with answer records:")
    for user in users_with_answers[:5]:  # 最初の5人を表示
        print(f"  - User ID: {user.id}, Name: {user.username}, Role: {user.role}")
    
    return len(users_with_answers) > 0

def test_ranking_calculation():
    """ランキング計算をテスト"""
    print("🧮 Testing ranking calculation...")
    
    try:
        # 総合ポイントランキングを計算
        ranking_data = RankingService.get_ranking(
            ranking_type='total_points',
            scope='school',
            scope_id=1,  # 学校ID 1を仮定
            limit=10
        )
        
        print(f"Ranking calculation result:")
        print(f"  - Total participants: {ranking_data.get('total_participants', 0)}")
        print(f"  - Rankings count: {len(ranking_data.get('rankings', []))}")
        print(f"  - Is fallback: {ranking_data.get('is_fallback', False)}")
        
        # 上位3名を表示
        if ranking_data.get('rankings'):
            print("Top 3 rankings:")
            for i, rank in enumerate(ranking_data['rankings'][:3]):
                print(f"  {i+1}. ID:{rank['student_id']} Name:{rank['student_name']} Score:{rank['score']}")
        
        # "Unknown"ユーザーが含まれているかチェック
        unknown_count = sum(1 for r in ranking_data.get('rankings', []) 
                          if r.get('student_name') == 'Unknown')
        
        if unknown_count > 0:
            print(f"⚠️  WARNING: {unknown_count} 'Unknown' users found in ranking")
            return False
        else:
            print("✅ No 'Unknown' users in ranking")
            return True
            
    except Exception as e:
        print(f"❌ Ranking calculation failed: {str(e)}")
        return False

def test_accuracy_ranking():
    """正答率ランキングをテスト"""
    print("📊 Testing accuracy ranking...")
    
    try:
        ranking_data = RankingService.get_ranking(
            ranking_type='accuracy_rate',
            scope='school',
            scope_id=1,
            limit=5
        )
        
        print(f"Accuracy ranking result:")
        print(f"  - Participants: {ranking_data.get('total_participants', 0)}")
        print(f"  - Rankings: {len(ranking_data.get('rankings', []))}")
        
        if ranking_data.get('rankings'):
            print("Top accuracy rankings:")
            for rank in ranking_data['rankings'][:3]:
                print(f"  - ID:{rank['student_id']} Name:{rank['student_name']} "
                      f"Accuracy:{rank['score']:.1f}% Answers:{rank.get('total_answers', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Accuracy ranking failed: {str(e)}")
        return False

def main():
    """メイン処理"""
    print("🔧 Starting Ranking System Repair Test")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        # Step 1: データ整合性確認
        has_users = test_user_data_integrity()
        if not has_users:
            print("❌ No users with learning data found")
            return False
        
        print()
        
        # Step 2: 破損キャッシュクリア
        clear_corrupted_cache()
        print()
        
        # Step 3: ランキング計算テスト
        ranking_success = test_ranking_calculation()
        print()
        
        # Step 4: 正答率ランキングテスト
        accuracy_success = test_accuracy_ranking()
        print()
        
        # 結果まとめ
        print("🏁 Repair Test Results:")
        print("=" * 30)
        print(f"User data integrity: {'✅' if has_users else '❌'}")
        print(f"Ranking calculation: {'✅' if ranking_success else '❌'}")
        print(f"Accuracy ranking: {'✅' if accuracy_success else '❌'}")
        
        if ranking_success and accuracy_success:
            print("\n🎉 Ranking system repair completed successfully!")
            return True
        else:
            print("\n⚠️  Some issues remain - check the detailed output above")
            return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)