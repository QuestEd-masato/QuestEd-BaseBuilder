"""
Ranking Service Fix
==================

This file contains the corrected ranking calculation methods
that properly join user data to avoid "Unknown" entries.
"""

from typing import Dict, List, Any
from sqlalchemy import func, desc, and_
from extensions import db
from app.models import User
from basebuilder.models import AnswerRecord

class RankingServiceFix:
    """修正されたランキングサービス"""
    
    POINTS_CONFIG = {
        'correct_answer': 10,     # 正解1問あたり
        'unit_completion': 100,   # 単元完了
    }

    @classmethod
    def get_total_points_ranking_fixed(cls, limit: int = 50) -> Dict[str, Any]:
        """修正版: 総合ポイントランキング"""
        
        # シンプルな一回のクエリで実行
        ranking_query = db.session.query(
            User.id.label('student_id'),
            User.username.label('student_name'),
            func.coalesce(func.sum(AnswerRecord.is_correct * cls.POINTS_CONFIG['correct_answer']), 0).label('total_points'),
            func.count(AnswerRecord.id).label('total_answers'),
            func.sum(AnswerRecord.is_correct).label('correct_answers')
        ).select_from(User).join(
            AnswerRecord, User.id == AnswerRecord.student_id
        ).filter(
            User.role == 'student',
            User.is_active == True
        ).group_by(
            User.id, User.username
        ).order_by(
            desc('total_points')
        ).limit(limit)
        
        results = ranking_query.all()
        
        return {
            'rankings': [
                {
                    'rank': idx + 1,
                    'student_id': result.student_id,
                    'student_name': result.student_name,
                    'score': float(result.total_points),
                    'total_answers': result.total_answers,
                    'correct_answers': result.correct_answers,
                    'accuracy_rate': round((result.correct_answers / result.total_answers) * 100, 1) if result.total_answers > 0 else 0
                }
                for idx, result in enumerate(results)
            ],
            'total_participants': len(results),
            'last_updated': "2025-07-02T00:00:00Z",
            'ranking_type': 'total_points'
        }

    @classmethod
    def get_accuracy_ranking_fixed(cls, limit: int = 50, min_answers: int = 20) -> Dict[str, Any]:
        """修正版: 正答率ランキング"""
        
        ranking_query = db.session.query(
            User.id.label('student_id'),
            User.username.label('student_name'),
            (func.sum(AnswerRecord.is_correct) / func.count(AnswerRecord.id) * 100).label('accuracy_rate'),
            func.count(AnswerRecord.id).label('total_answers'),
            func.sum(AnswerRecord.is_correct).label('correct_answers')
        ).select_from(User).join(
            AnswerRecord, User.id == AnswerRecord.student_id
        ).filter(
            User.role == 'student',
            User.is_active == True
        ).group_by(
            User.id, User.username
        ).having(
            func.count(AnswerRecord.id) >= min_answers
        ).order_by(
            desc('accuracy_rate')
        ).limit(limit)
        
        results = ranking_query.all()
        
        return {
            'rankings': [
                {
                    'rank': idx + 1,
                    'student_id': result.student_id,
                    'student_name': result.student_name,
                    'score': round(float(result.accuracy_rate), 1),
                    'total_answers': result.total_answers,
                    'correct_answers': result.correct_answers
                }
                for idx, result in enumerate(results)
            ],
            'total_participants': len(results),
            'last_updated': "2025-07-02T00:00:00Z",
            'ranking_type': 'accuracy_rate'
        }

    @classmethod
    def test_fixed_rankings(cls):
        """修正されたランキングをテスト"""
        print("🧮 Testing Fixed Rankings")
        print("=" * 40)
        
        # 総合ポイントランキングテスト
        try:
            total_points = cls.get_total_points_ranking_fixed(10)
            print(f"✅ Total Points Ranking: {len(total_points['rankings'])} entries")
            
            # 上位3名表示
            for i, rank in enumerate(total_points['rankings'][:3]):
                print(f"  {i+1}. {rank['student_name']} - {rank['score']} points ({rank['total_answers']} answers)")
            
        except Exception as e:
            print(f"❌ Total Points Error: {str(e)}")
        
        print()
        
        # 正答率ランキングテスト
        try:
            accuracy = cls.get_accuracy_ranking_fixed(10)
            print(f"✅ Accuracy Ranking: {len(accuracy['rankings'])} entries")
            
            # 上位3名表示
            for i, rank in enumerate(accuracy['rankings'][:3]):
                print(f"  {i+1}. {rank['student_name']} - {rank['score']}% ({rank['total_answers']} answers)")
                
        except Exception as e:
            print(f"❌ Accuracy Error: {str(e)}")

# テスト実行用関数
def run_ranking_fix_test():
    """ランキング修正のテストを実行"""
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            RankingServiceFix.test_fixed_rankings()
            
    except Exception as e:
        print(f"❌ Test setup error: {str(e)}")

if __name__ == "__main__":
    run_ranking_fix_test()