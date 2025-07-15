# app/modules/ranking_system/services/calculation_service.py
"""
Ranking Calculation Service
==========================
ランキング計算・スコア集計機能
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, desc
from app.models import db, User, Class, ClassEnrollment


class RankingCalculationService:
    """ランキング計算サービス"""
    
    @staticmethod
    def calculate_class_rankings(class_id: int, period_days: int = 30) -> List[Dict]:
        """クラス内ランキング計算"""
        try:
            # 期間設定
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # クラス内の学生を取得
            students = db.session.query(User).join(
                ClassEnrollment, User.id == ClassEnrollment.student_id
            ).filter(
                ClassEnrollment.class_id == class_id,
                ClassEnrollment.is_active == True,
                User.role == 'student'
            ).all()
            
            rankings = []
            for student in students:
                score = RankingCalculationService._calculate_student_score(
                    student.id, start_date
                )
                rankings.append({
                    'student_id': student.id,
                    'student_name': student.username,
                    'score': score,
                    'rank': 0  # 後で設定
                })
            
            # スコア順でソート
            rankings.sort(key=lambda x: x['score'], reverse=True)
            
            # ランクを設定
            for i, ranking in enumerate(rankings):
                ranking['rank'] = i + 1
            
            return rankings
            
        except Exception as e:
            print(f"[ERROR] Class ranking calculation failed: {e}")
            return []
    
    @staticmethod
    def _calculate_student_score(student_id: int, start_date: datetime) -> int:
        """学生の総合スコア計算"""
        try:
            score = 0
            
            # レッスン完了スコア
            try:
                from app.modules.lesson_system.models.lesson_models import (
                    StudentLessonProgress, StudentTaskCheck, TaskCheckStatus
                )
                
                # 完了したタスク数
                completed_tasks = StudentTaskCheck.query.filter(
                    StudentTaskCheck.student_id == student_id,
                    StudentTaskCheck.status == TaskCheckStatus.COMPLETED,
                    StudentTaskCheck.completed_at >= start_date
                ).count()
                
                score += completed_tasks * 10  # タスク完了で10ポイント
                
            except ImportError:
                pass  # レッスンシステムが利用できない場合はスキップ
            
            # BaseBuilder活動スコア
            try:
                from basebuilder.models import AnswerRecord, WordProficiency
                
                # 正解数
                correct_answers = AnswerRecord.query.filter(
                    AnswerRecord.student_id == student_id,
                    AnswerRecord.is_correct == True,
                    AnswerRecord.answered_at >= start_date
                ).count()
                
                score += correct_answers * 2  # 正解で2ポイント
                
                # 熟練度向上
                proficiency_gains = WordProficiency.query.filter(
                    WordProficiency.student_id == student_id,
                    WordProficiency.updated_at >= start_date,
                    WordProficiency.level >= 4
                ).count()
                
                score += proficiency_gains * 5  # 熟練度向上で5ポイント
                
            except ImportError:
                pass  # BaseBuilderが利用できない場合はスキップ
            
            return score
            
        except Exception as e:
            print(f"[ERROR] Student score calculation failed: {e}")
            return 0
    
    @staticmethod
    def get_school_rankings(school_id: Optional[int] = None, limit: int = 50) -> List[Dict]:
        """学校内ランキング取得"""
        try:
            query = db.session.query(User)
            
            if school_id:
                # 特定の学校のみ
                query = query.filter(User.school_id == school_id)
            
            students = query.filter(User.role == 'student').limit(limit * 2).all()
            
            # 期間設定（過去30日）
            start_date = datetime.utcnow() - timedelta(days=30)
            
            rankings = []
            for student in students:
                score = RankingCalculationService._calculate_student_score(
                    student.id, start_date
                )
                
                if score > 0:  # スコアが0の学生は除外
                    rankings.append({
                        'student_id': student.id,
                        'student_name': student.username,
                        'school_name': getattr(student, 'school_name', '不明'),
                        'score': score,
                        'rank': 0
                    })
            
            # スコア順でソート
            rankings.sort(key=lambda x: x['score'], reverse=True)
            
            # 上位のみに制限
            rankings = rankings[:limit]
            
            # ランクを設定
            for i, ranking in enumerate(rankings):
                ranking['rank'] = i + 1
            
            return rankings
            
        except Exception as e:
            print(f"[ERROR] School ranking calculation failed: {e}")
            return []
    
    @staticmethod
    def calculate_weekly_progress(student_id: int) -> Dict:
        """週間進捗計算"""
        try:
            # 過去7日間の活動を取得
            week_ago = datetime.utcnow() - timedelta(days=7)
            
            progress = {
                'lessons_completed': 0,
                'tasks_completed': 0,
                'basebuilder_answers': 0,
                'basebuilder_correct': 0,
                'total_score': 0,
                'daily_breakdown': []
            }
            
            # 日別の進捗を計算
            for i in range(7):
                day_start = week_ago + timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                
                daily_score = RankingCalculationService._calculate_daily_score(
                    student_id, day_start, day_end
                )
                
                progress['daily_breakdown'].append({
                    'date': day_start.strftime('%Y-%m-%d'),
                    'score': daily_score
                })
                
                progress['total_score'] += daily_score
            
            return progress
            
        except Exception as e:
            print(f"[ERROR] Weekly progress calculation failed: {e}")
            return {
                'lessons_completed': 0,
                'tasks_completed': 0,
                'basebuilder_answers': 0,
                'basebuilder_correct': 0,
                'total_score': 0,
                'daily_breakdown': []
            }
    
    @staticmethod
    def _calculate_daily_score(student_id: int, start_time: datetime, end_time: datetime) -> int:
        """日別スコア計算"""
        try:
            score = 0
            
            # レッスン活動
            try:
                from app.modules.lesson_system.models.lesson_models import (
                    StudentTaskCheck, TaskCheckStatus
                )
                
                daily_tasks = StudentTaskCheck.query.filter(
                    StudentTaskCheck.student_id == student_id,
                    StudentTaskCheck.status == TaskCheckStatus.COMPLETED,
                    StudentTaskCheck.completed_at >= start_time,
                    StudentTaskCheck.completed_at < end_time
                ).count()
                
                score += daily_tasks * 10
                
            except ImportError:
                pass
            
            # BaseBuilder活動
            try:
                from basebuilder.models import AnswerRecord
                
                daily_answers = AnswerRecord.query.filter(
                    AnswerRecord.student_id == student_id,
                    AnswerRecord.answered_at >= start_time,
                    AnswerRecord.answered_at < end_time
                ).count()
                
                daily_correct = AnswerRecord.query.filter(
                    AnswerRecord.student_id == student_id,
                    AnswerRecord.is_correct == True,
                    AnswerRecord.answered_at >= start_time,
                    AnswerRecord.answered_at < end_time
                ).count()
                
                score += daily_correct * 2
                
            except ImportError:
                pass
            
            return score
            
        except Exception as e:
            print(f"[ERROR] Daily score calculation failed: {e}")
            return 0
    
    @staticmethod
    def get_student_rank_in_class(student_id: int, class_id: int) -> Optional[Dict]:
        """クラス内での学生順位取得"""
        try:
            rankings = RankingCalculationService.calculate_class_rankings(class_id)
            
            for ranking in rankings:
                if ranking['student_id'] == student_id:
                    return {
                        'rank': ranking['rank'],
                        'total_students': len(rankings),
                        'score': ranking['score'],
                        'percentile': round((1 - (ranking['rank'] - 1) / len(rankings)) * 100, 1)
                    }
            
            return None
            
        except Exception as e:
            print(f"[ERROR] Student rank lookup failed: {e}")
            return None