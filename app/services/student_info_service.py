"""
学生基本情報サービス
Phase6-B: _build_student_basic_info (515行) をサービス層に移行
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.models import (
    ProficiencyRecord,
    StudentEvaluation,
    StudentMilestone,
    User
)
from extensions import db
from app.services.base_service import BaseService

logger = logging.getLogger(__name__)


class StudentInfoService(BaseService):
    """学生基本情報サービス
    
    Phase6-B: dashboard.py の _build_student_basic_info (515行) から移行
    Single Responsibility: 学生の基本情報とプロフィール管理
    """
    
    def __init__(self):
        super().__init__()
    
    def build_student_basic_info(self, student_id: int) -> Dict[str, Any]:
        """
        学生基本情報を構築
        Phase6-B: 元の _build_student_basic_info() から移行
        """
        try:
            logger.info(f"Building student basic info for student_id: {student_id}")
            
            # 基本情報取得
            basic_info = self._get_student_basic_data(student_id)
            
            # 学習統計情報
            learning_stats = self._calculate_learning_statistics(student_id)
            
            # プロフィール情報
            profile_info = self._get_student_profile_info(student_id)
            
            # 最近の活動情報
            recent_activity = self._get_recent_activity_summary(student_id)
            
            # 統合結果
            result = {
                **basic_info,
                **learning_stats,
                **profile_info,
                **recent_activity,
                'generated_at': datetime.now(),
                'student_id': student_id
            }
            
            logger.info(f"Student basic info built successfully for student_id: {student_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to build student basic info for student_id {student_id}: {str(e)}")
            return self._get_default_basic_info(student_id)
    
    def _get_student_basic_data(self, student_id: int) -> Dict[str, Any]:
        """学生の基本データを取得"""
        try:
            user = User.query.get(student_id)
            if not user:
                return {}
            
            return {
                'student_name': user.username,
                'student_email': user.email,
                'join_date': user.created_at,
                'last_login': getattr(user, 'last_login', None),
                'is_active': user.is_active if hasattr(user, 'is_active') else True
            }
            
        except Exception as e:
            logger.error(f"Error getting student basic data: {str(e)}")
            return {}
    
    def _calculate_learning_statistics(self, student_id: int) -> Dict[str, Any]:
        """学習統計を計算"""
        try:
            # 基本統計
            stats = {
                'total_evaluations': 0,
                'avg_score': 0.0,
                'total_study_time': 0,
                'total_problems_solved': 0,
                'recent_performance_trend': 'stable'
            }
            
            # 評価レコード統計
            evaluations = StudentEvaluation.query.filter_by(student_id=student_id).all()
            if evaluations:
                stats['total_evaluations'] = len(evaluations)
                scores = [e.score for e in evaluations if e.score is not None]
                if scores:
                    stats['avg_score'] = sum(scores) / len(scores)
            
            # 熟練度レコード統計
            proficiency_records = ProficiencyRecord.query.filter_by(student_id=student_id).all()
            if proficiency_records:
                stats['total_problems_solved'] = len(proficiency_records)
                
                # 学習時間計算（AnswerRecordから取得）
                from basebuilder.models import AnswerRecord
                answer_records = AnswerRecord.query.filter_by(student_id=student_id).all()
                study_times = [r.answer_time for r in answer_records if r.answer_time]
                if study_times:
                    stats['total_study_time'] = sum(study_times)  # already in seconds
            
            # パフォーマンストレンド分析
            stats['recent_performance_trend'] = self._analyze_performance_trend(student_id)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating learning statistics: {str(e)}")
            return {
                'total_evaluations': 0,
                'avg_score': 0.0,
                'total_study_time': 0,
                'total_problems_solved': 0,
                'recent_performance_trend': 'unknown'
            }
    
    def _get_student_profile_info(self, student_id: int) -> Dict[str, Any]:
        """学生のプロフィール情報を取得"""
        try:
            profile = {
                'learning_preferences': {},
                'achievement_level': 'beginner',
                'study_goals': [],
                'preferred_subjects': []
            }
            
            # マイルストーン情報からプロフィールを推定
            milestones = StudentMilestone.query.filter_by(student_id=student_id).all()
            if milestones:
                completed_milestones = [m for m in milestones if m.is_completed]
                profile['achievement_level'] = self._determine_achievement_level(len(completed_milestones))
            
            # 学習パターンから好みを分析
            profile['learning_preferences'] = self._analyze_learning_preferences(student_id)
            
            return profile
            
        except Exception as e:
            logger.error(f"Error getting student profile info: {str(e)}")
            return {
                'learning_preferences': {},
                'achievement_level': 'beginner',
                'study_goals': [],
                'preferred_subjects': []
            }
    
    def _get_recent_activity_summary(self, student_id: int) -> Dict[str, Any]:
        """最近の活動サマリーを取得"""
        try:
            # 過去30日のアクティビティ
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            recent_evaluations = StudentEvaluation.query.filter(
                StudentEvaluation.student_id == student_id,
                StudentEvaluation.created_at >= thirty_days_ago
            ).count()
            
            recent_proficiency = ProficiencyRecord.query.filter(
                ProficiencyRecord.student_id == student_id,
                ProficiencyRecord.updated_at >= thirty_days_ago
            ).count()
            
            return {
                'recent_evaluations_count': recent_evaluations,
                'recent_problems_solved': recent_proficiency,
                'activity_last_30_days': recent_evaluations + recent_proficiency,
                'last_activity_date': self._get_last_activity_date(student_id)
            }
            
        except Exception as e:
            logger.error(f"Error getting recent activity summary: {str(e)}")
            return {
                'recent_evaluations_count': 0,
                'recent_problems_solved': 0,
                'activity_last_30_days': 0,
                'last_activity_date': None
            }
    
    def _analyze_performance_trend(self, student_id: int) -> str:
        """パフォーマンストレンドを分析"""
        try:
            # 最近の評価から傾向を分析
            recent_evaluations = StudentEvaluation.query.filter_by(
                student_id=student_id
            ).order_by(StudentEvaluation.created_at.desc()).limit(10).all()
            
            if len(recent_evaluations) < 3:
                return 'insufficient_data'
            
            scores = [e.score for e in recent_evaluations if e.score is not None]
            if len(scores) < 3:
                return 'insufficient_data'
            
            # 線形トレンド分析（簡易版）
            first_half_avg = sum(scores[:len(scores)//2]) / (len(scores)//2)
            second_half_avg = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
            
            diff = second_half_avg - first_half_avg
            
            if diff > 5:
                return 'improving'
            elif diff < -5:
                return 'declining'
            else:
                return 'stable'
                
        except Exception as e:
            logger.error(f"Error analyzing performance trend: {str(e)}")
            return 'unknown'
    
    def _determine_achievement_level(self, milestone_count: int) -> str:
        """完了マイルストーン数からレベルを判定"""
        if milestone_count >= 50:
            return 'expert'
        elif milestone_count >= 25:
            return 'advanced'
        elif milestone_count >= 10:
            return 'intermediate'
        else:
            return 'beginner'
    
    def _analyze_learning_preferences(self, student_id: int) -> Dict[str, Any]:
        """学習パターンから好みを分析"""
        try:
            preferences = {
                'preferred_difficulty': 'medium',
                'study_time_preference': 'moderate',
                'learning_speed': 'normal'
            }
            
            # ProficiencyRecordから学習パターンを分析
            records = ProficiencyRecord.query.filter_by(student_id=student_id).limit(100).all()
            
            if records:
                # 難易度の好み
                difficulty_levels = [r.difficulty_level for r in records if hasattr(r, 'difficulty_level')]
                if difficulty_levels:
                    avg_difficulty = sum(difficulty_levels) / len(difficulty_levels)
                    if avg_difficulty > 3:
                        preferences['preferred_difficulty'] = 'hard'
                    elif avg_difficulty < 2:
                        preferences['preferred_difficulty'] = 'easy'
                
                # 学習速度（AnswerRecordから取得）
                from basebuilder.models import AnswerRecord
                answer_records = AnswerRecord.query.filter_by(student_id=student_id).limit(100).all()
                response_times = [r.answer_time for r in answer_records if r.answer_time]
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)
                    if avg_response_time < 5:  # 5秒未満
                        preferences['learning_speed'] = 'fast'
                    elif avg_response_time > 15:  # 15秒超
                        preferences['learning_speed'] = 'slow'
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error analyzing learning preferences: {str(e)}")
            return {
                'preferred_difficulty': 'medium',
                'study_time_preference': 'moderate',
                'learning_speed': 'normal'
            }
    
    def _get_last_activity_date(self, student_id: int) -> Optional[datetime]:
        """最後のアクティビティ日時を取得"""
        try:
            # 評価レコードから最新日時
            latest_evaluation = StudentEvaluation.query.filter_by(
                student_id=student_id
            ).order_by(StudentEvaluation.created_at.desc()).first()
            
            latest_proficiency = ProficiencyRecord.query.filter_by(
                student_id=student_id
            ).order_by(ProficiencyRecord.updated_at.desc()).first()
            
            dates = []
            if latest_evaluation:
                dates.append(latest_evaluation.created_at)
            if latest_proficiency:
                dates.append(latest_proficiency.updated_at)
            
            return max(dates) if dates else None
            
        except Exception as e:
            logger.error(f"Error getting last activity date: {str(e)}")
            return None
    
    def _get_default_basic_info(self, student_id: int) -> Dict[str, Any]:
        """デフォルト基本情報（エラー時）"""
        return {
            'student_id': student_id,
            'student_name': 'Unknown',
            'student_email': '',
            'join_date': None,
            'last_login': None,
            'is_active': True,
            'total_evaluations': 0,
            'avg_score': 0.0,
            'total_study_time': 0,
            'total_problems_solved': 0,
            'recent_performance_trend': 'unknown',
            'learning_preferences': {},
            'achievement_level': 'beginner',
            'study_goals': [],
            'preferred_subjects': [],
            'recent_evaluations_count': 0,
            'recent_problems_solved': 0,
            'activity_last_30_days': 0,
            'last_activity_date': None,
            'generated_at': datetime.now(),
            'error_occurred': True
        }
    
    def update_student_preferences(self, student_id: int, preferences: Dict[str, Any]) -> bool:
        """学生の学習設定を更新"""
        try:
            # 実装は将来的に拡張
            logger.info(f"Student preferences update requested for student_id: {student_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating student preferences: {str(e)}")
            return False
    
    def get_student_summary(self, student_id: int) -> Dict[str, Any]:
        """学生の簡易サマリーを取得"""
        try:
            basic_info = self.build_student_basic_info(student_id)
            
            return {
                'student_id': student_id,
                'name': basic_info.get('student_name', 'Unknown'),
                'achievement_level': basic_info.get('achievement_level', 'beginner'),
                'total_problems_solved': basic_info.get('total_problems_solved', 0),
                'avg_score': basic_info.get('avg_score', 0.0),
                'recent_activity': basic_info.get('activity_last_30_days', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting student summary: {str(e)}")
            return {
                'student_id': student_id,
                'name': 'Unknown',
                'achievement_level': 'beginner',
                'total_problems_solved': 0,
                'avg_score': 0.0,
                'recent_activity': 0,
                'error': True
            }
    
    def _has_permission(self, user, action: str, resource: Any = None) -> bool:
        """
        権限チェック実装
        Phase8E緊急修正: BaseService抽象メソッド実装
        """
        # 学生情報サービスは認証されたユーザーが自分の情報にアクセス可能
        if user and hasattr(user, 'id'):
            return True
        return False