"""
ランキングサービス

学習ランキングの計算と管理を担当
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import text, func
from sqlalchemy.exc import SQLAlchemyError

from app.models import db, User


class RankingService:
    """ランキング管理サービス"""
    
    @staticmethod
    def get_ranking_statistics() -> Dict[str, Any]:
        """ランキング統計を取得"""
        try:
            # 基本的な統計情報
            total_students = User.query.filter_by(role='student').count()
            
            return {
                'total_students': total_students,
                'active_rankings': 0,  # 実装予定
                'last_updated': datetime.utcnow().isoformat()
            }
        except Exception as e:
            current_app.logger.error(f"Failed to get ranking statistics: {e}")
            return {
                'total_students': 0,
                'active_rankings': 0,
                'last_updated': datetime.utcnow().isoformat()
            }
    
    @staticmethod
    def get_lesson_progress_ranking(class_id: int = None, limit: int = 10) -> List[Dict[str, Any]]:
        """レッスン進捗ランキングを取得"""
        try:
            query = """
            SELECT 
                u.id as user_id,
                u.username,
                u.full_name,
                COUNT(slp.id) as total_lessons,
                COUNT(CASE WHEN slp.is_completed = 1 THEN 1 END) as completed_lessons,
                ROUND(AVG(slp.completion_percentage), 1) as avg_completion,
                SUM(slp.time_spent_minutes) as total_time_spent
            FROM users u
            LEFT JOIN student_lesson_progress slp ON u.id = slp.student_id
            WHERE u.role = 'student'
            """
            
            params = {}
            if class_id:
                query += " AND u.class_id = :class_id"
                params['class_id'] = class_id
            
            query += """
            GROUP BY u.id, u.username, u.full_name
            HAVING total_lessons > 0
            ORDER BY completed_lessons DESC, avg_completion DESC
            LIMIT :limit
            """
            params['limit'] = limit
            
            result = db.session.execute(text(query), params)
            
            rankings = []
            rank = 1
            for row in result:
                completion_rate = (row.completed_lessons / row.total_lessons * 100) if row.total_lessons > 0 else 0
                
                rankings.append({
                    'rank': rank,
                    'user_id': row.user_id,
                    'username': row.username,
                    'full_name': row.full_name,
                    'total_lessons': row.total_lessons,
                    'completed_lessons': row.completed_lessons,
                    'completion_rate': round(completion_rate, 1),
                    'avg_completion': row.avg_completion or 0,
                    'total_time_spent': row.total_time_spent or 0
                })
                rank += 1
            
            return rankings
            
        except Exception as e:
            current_app.logger.error(f"Failed to get lesson progress ranking: {e}")
            return []
    
    @staticmethod
    def get_vocabulary_ranking(class_id: int = None, limit: int = 10) -> List[Dict[str, Any]]:
        """語彙習熟度ランキングを取得"""
        try:
            query = """
            SELECT 
                u.id as user_id,
                u.username,
                u.full_name,
                COUNT(wpr.id) as total_words,
                AVG(wpr.proficiency_score) as avg_proficiency,
                SUM(wpr.correct_count) as total_correct,
                SUM(wpr.attempt_count) as total_attempts
            FROM users u
            LEFT JOIN word_proficiency_records wpr ON u.id = wpr.user_id
            WHERE u.role = 'student'
            """
            
            params = {}
            if class_id:
                query += " AND u.class_id = :class_id"
                params['class_id'] = class_id
            
            query += """
            GROUP BY u.id, u.username, u.full_name
            HAVING total_words > 0
            ORDER BY avg_proficiency DESC, total_correct DESC
            LIMIT :limit
            """
            params['limit'] = limit
            
            result = db.session.execute(text(query), params)
            
            rankings = []
            rank = 1
            for row in result:
                accuracy = (row.total_correct / row.total_attempts * 100) if row.total_attempts > 0 else 0
                
                rankings.append({
                    'rank': rank,
                    'user_id': row.user_id,
                    'username': row.username,
                    'full_name': row.full_name,
                    'total_words': row.total_words,
                    'avg_proficiency': round(row.avg_proficiency or 0, 2),
                    'total_correct': row.total_correct or 0,
                    'total_attempts': row.total_attempts or 0,
                    'accuracy': round(accuracy, 1)
                })
                rank += 1
            
            return rankings
            
        except Exception as e:
            current_app.logger.error(f"Failed to get vocabulary ranking: {e}")
            return []
    
    @staticmethod
    def get_overall_ranking(class_id: int = None, limit: int = 10) -> List[Dict[str, Any]]:
        """総合ランキングを取得"""
        try:
            # レッスン進捗スコア（40%）+ 語彙スコア（30%）+ 活動スコア（30%）
            query = """
            SELECT 
                u.id as user_id,
                u.username,
                u.full_name,
                -- レッスン進捗スコア
                COALESCE(
                    (COUNT(CASE WHEN slp.is_completed = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(slp.id), 0)), 
                    0
                ) as lesson_score,
                -- 語彙スコア
                COALESCE(AVG(wpr.proficiency_score), 0) as vocab_score,
                -- 活動スコア（アクセス頻度）
                COALESCE(
                    (SELECT COUNT(*) FROM activity_logs al 
                     WHERE al.user_id = u.id 
                     AND al.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)), 
                    0
                ) as activity_score
            FROM users u
            LEFT JOIN student_lesson_progress slp ON u.id = slp.student_id
            LEFT JOIN word_proficiency_records wpr ON u.id = wpr.user_id
            WHERE u.role = 'student'
            """
            
            params = {}
            if class_id:
                query += " AND u.class_id = :class_id"
                params['class_id'] = class_id
            
            query += """
            GROUP BY u.id, u.username, u.full_name
            ORDER BY 
                (lesson_score * 0.4 + vocab_score * 0.3 + LEAST(activity_score, 100) * 0.3) DESC
            LIMIT :limit
            """
            params['limit'] = limit
            
            result = db.session.execute(text(query), params)
            
            rankings = []
            rank = 1
            for row in result:
                # 総合スコア計算
                lesson_weighted = row.lesson_score * 0.4
                vocab_weighted = row.vocab_score * 0.3
                activity_weighted = min(row.activity_score, 100) * 0.3
                total_score = lesson_weighted + vocab_weighted + activity_weighted
                
                rankings.append({
                    'rank': rank,
                    'user_id': row.user_id,
                    'username': row.username,
                    'full_name': row.full_name,
                    'total_score': round(total_score, 1),
                    'lesson_score': round(row.lesson_score, 1),
                    'vocab_score': round(row.vocab_score, 1),
                    'activity_score': row.activity_score
                })
                rank += 1
            
            return rankings
            
        except Exception as e:
            current_app.logger.error(f"Failed to get overall ranking: {e}")
            return []
    
    @staticmethod
    def get_student_rank_position(student_id: int, ranking_type: str = 'overall', class_id: int = None) -> Optional[Dict[str, Any]]:
        """特定の学生のランキング順位を取得"""
        try:
            if ranking_type == 'lesson':
                rankings = RankingService.get_lesson_progress_ranking(class_id, limit=1000)
            elif ranking_type == 'vocabulary':
                rankings = RankingService.get_vocabulary_ranking(class_id, limit=1000)
            else:
                rankings = RankingService.get_overall_ranking(class_id, limit=1000)
            
            for ranking in rankings:
                if ranking['user_id'] == student_id:
                    return ranking
            
            return None
            
        except Exception as e:
            current_app.logger.error(f"Failed to get student rank position: {e}")
            return None
    
    @staticmethod
    def get_student_rank(student_id: int, class_id: int = None) -> Dict[str, Any]:
        """学生の各ランキング順位を取得"""
        try:
            return {
                'lesson_rank': RankingService.get_student_rank_position(student_id, 'lesson', class_id),
                'vocabulary_rank': RankingService.get_student_rank_position(student_id, 'vocabulary', class_id),
                'overall_rank': RankingService.get_student_rank_position(student_id, 'overall', class_id)
            }
        except Exception as e:
            current_app.logger.error(f"Failed to get student rank: {e}")
            return {
                'lesson_rank': None,
                'vocabulary_rank': None,
                'overall_rank': None
            }
    
    @staticmethod
    def get_ranking_statistics(class_id: int = None) -> Dict[str, Any]:
        """ランキング統計情報を取得"""
        try:
            # 基本統計
            query = "SELECT COUNT(*) as total_students FROM users WHERE role = 'student'"
            params = {}
            
            if class_id:
                query += " AND class_id = :class_id"
                params['class_id'] = class_id
            
            result = db.session.execute(text(query), params)
            total_students = result.fetchone().total_students
            
            # 今日のアクティブユーザー数
            today = datetime.now().date()
            active_query = """
            SELECT COUNT(DISTINCT user_id) as active_today 
            FROM activity_logs 
            WHERE DATE(created_at) = :today
            """
            
            if class_id:
                active_query += " AND user_id IN (SELECT id FROM users WHERE class_id = :class_id)"
                params['today'] = today
                params['class_id'] = class_id
            else:
                params = {'today': today}
            
            result = db.session.execute(text(active_query), params)
            active_today = result.fetchone().active_today
            
            return {
                'total_students': total_students,
                'active_today': active_today,
                'activity_rate': (active_today / total_students * 100) if total_students > 0 else 0,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            current_app.logger.error(f"Failed to get ranking statistics: {e}")
            return {
                'total_students': 0,
                'active_today': 0,
                'activity_rate': 0,
                'last_updated': datetime.now().isoformat()
            }
    
    @staticmethod
    def get_detailed_ranking_statistics(class_id: int) -> Dict[str, Any]:
        """詳細なランキング統計情報を取得（教師用）"""
        try:
            # 基本統計
            basic_stats = RankingService.get_ranking_statistics(class_id)
            
            # 週別活動統計
            weekly_query = """
            SELECT 
                DATE(created_at) as date,
                COUNT(DISTINCT user_id) as active_users,
                COUNT(*) as total_activities
            FROM activity_logs 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            AND user_id IN (SELECT id FROM users WHERE class_id = :class_id)
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            """
            
            result = db.session.execute(text(weekly_query), {'class_id': class_id})
            weekly_activity = [
                {
                    'date': row.date.strftime('%Y-%m-%d'),
                    'active_users': row.active_users,
                    'total_activities': row.total_activities
                }
                for row in result
            ]
            
            # 上位パフォーマー
            top_performers = RankingService.get_overall_ranking(class_id, 5)
            
            return {
                **basic_stats,
                'weekly_activity': weekly_activity,
                'top_performers': top_performers
            }
            
        except Exception as e:
            current_app.logger.error(f"Failed to get detailed ranking statistics: {e}")
            return RankingService.get_ranking_statistics(class_id)
    
    @staticmethod
    def get_ranking_summary(class_id: int = None) -> Dict[str, Any]:
        """ランキングサマリーを取得"""
        return RankingService.get_ranking_statistics(class_id)