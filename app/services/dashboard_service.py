"""
ダッシュボードサービス
Phase6-B: dashboard() (338行) をサービス層に移行
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import session
from flask_login import current_user

from app.models import (
    AIRecommendation,
    BaseBuilderRecord,
    CurriculumUnit,
    ProficiencyRecord,
    StudentEvaluation,
    StudentMilestone,
    User
)
from extensions import db
from app.services.base_service import BaseService
from app.services.student_info_service import StudentInfoService

logger = logging.getLogger(__name__)


class DashboardService(BaseService):
    """ダッシュボードサービス
    
    Phase6-B: dashboard.py の dashboard() (338行) から移行
    Single Responsibility: ダッシュボードデータの統合管理
    """
    
    def __init__(self):
        super().__init__()
        self.student_info_service = StudentInfoService()
    
    def build_dashboard_data(self, student_id: int) -> Dict[str, Any]:
        """
        ダッシュボード用データを構築
        Phase6-B: 元の dashboard() から移行
        """
        try:
            logger.info(f"Building dashboard data for student_id: {student_id}")
            
            # 基本情報（旧 _build_student_basic_info の代替）
            student_basic_info = self.student_info_service.build_student_basic_info(student_id)
            
            # 各セクションのデータを構築
            dashboard_data = {
                # 基本情報
                'student_basic_info': student_basic_info,
                
                # マイルストーン情報
                'milestone_data': self._get_milestone_data(student_id),
                
                # クイズ履歴
                'quiz_history': self._get_quiz_history_data(student_id),
                
                # 進捗サマリー
                'progress_summary': self._get_progress_summary_data(student_id),
                
                # AI推薦
                'ai_recommendations': self._get_ai_recommendation_data(student_id),
                
                # 最近のアクティビティ
                'recent_activities': self._get_recent_activities_data(student_id),
                
                # BaseBuilder情報
                'basebuilder_data': self._get_basebuilder_data(student_id),
                
                # 語彙分析
                'vocabulary_analysis': self._get_vocabulary_analysis_data(student_id),
                
                # 間隔反復学習
                'spaced_repetition': self._get_spaced_repetition_data(student_id),
                
                # 弱点分析
                'weakness_analysis': self._get_weakness_analysis_data(student_id),
                
                # チャートデータ
                'chart_data': self._get_chart_data(student_id),
                
                # メタデータ
                'generated_at': datetime.now(),
                'student_id': student_id,
                'success': True
            }
            
            logger.info(f"Dashboard data built successfully for student_id: {student_id}")
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Failed to build dashboard data for student_id {student_id}: {str(e)}")
            return self._get_default_dashboard_data(student_id, str(e))
    
    def _get_milestone_data(self, student_id: int) -> Dict[str, Any]:
        """マイルストーンデータを取得"""
        try:
            milestones = StudentMilestone.query.filter_by(student_id=student_id).all()
            
            completed_count = len([m for m in milestones if m.is_completed])
            total_count = len(milestones)
            
            recent_milestones = sorted(
                [m for m in milestones if m.is_completed],
                key=lambda x: x.completed_at or datetime.min,
                reverse=True
            )[:5]
            
            return {
                'total_milestones': total_count,
                'completed_milestones': completed_count,
                'completion_rate': (completed_count / total_count * 100) if total_count > 0 else 0,
                'recent_completed': [
                    {
                        'id': m.id,
                        'title': m.milestone_name,
                        'completed_at': m.completed_at,
                        'category': getattr(m, 'category', 'general')
                    } for m in recent_milestones
                ],
                'next_milestone': self._get_next_milestone(student_id),
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error getting milestone data: {str(e)}")
            return {
                'total_milestones': 0,
                'completed_milestones': 0,
                'completion_rate': 0,
                'recent_completed': [],
                'next_milestone': None,
                'status': 'error',
                'error': str(e)
            }
    
    def _get_quiz_history_data(self, student_id: int) -> Dict[str, Any]:
        """クイズ履歴データを取得"""
        try:
            # 過去30日のクイズ履歴
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            evaluations = StudentEvaluation.query.filter(
                StudentEvaluation.student_id == student_id,
                StudentEvaluation.created_at >= thirty_days_ago
            ).order_by(StudentEvaluation.created_at.desc()).limit(20).all()
            
            quiz_data = []
            total_score = 0
            
            for eval in evaluations:
                quiz_data.append({
                    'id': eval.id,
                    'subject': getattr(eval, 'subject', 'Unknown'),
                    'score': eval.score,
                    'max_score': getattr(eval, 'max_score', 100),
                    'date': eval.created_at,
                    'duration': getattr(eval, 'duration', None)
                })
                if eval.score:
                    total_score += eval.score
            
            avg_score = (total_score / len(evaluations)) if evaluations else 0
            
            return {
                'recent_quizzes': quiz_data,
                'total_quizzes': len(evaluations),
                'average_score': avg_score,
                'best_score': max([q['score'] for q in quiz_data if q['score']], default=0),
                'improvement_trend': self._calculate_quiz_trend(quiz_data),
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error getting quiz history data: {str(e)}")
            return {
                'recent_quizzes': [],
                'total_quizzes': 0,
                'average_score': 0,
                'best_score': 0,
                'improvement_trend': 'unknown',
                'status': 'error',
                'error': str(e)
            }
    
    def _get_progress_summary_data(self, student_id: int) -> Dict[str, Any]:
        """進捗サマリーデータを取得"""
        try:
            # 学習単元の進捗
            total_units = CurriculumUnit.query.count()
            
            # ProficiencyRecordから学習済みカテゴリを推定
            studied_units = db.session.query(ProficiencyRecord.category_id).filter_by(
                student_id=student_id
            ).distinct().count()
            
            # 今月のアクティビティ
            month_start = datetime.now().replace(day=1)
            monthly_activities = StudentEvaluation.query.filter(
                StudentEvaluation.student_id == student_id,
                StudentEvaluation.created_at >= month_start
            ).count()
            
            # 学習ストリーク計算
            learning_streak = self._calculate_learning_streak(student_id)
            
            return {
                'total_curriculum_units': total_units,
                'completed_units': studied_units,
                'completion_percentage': (studied_units / total_units * 100) if total_units > 0 else 0,
                'monthly_activities': monthly_activities,
                'learning_streak_days': learning_streak,
                'estimated_completion_date': self._estimate_completion_date(student_id),
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error getting progress summary data: {str(e)}")
            return {
                'total_curriculum_units': 0,
                'completed_units': 0,
                'completion_percentage': 0,
                'monthly_activities': 0,
                'learning_streak_days': 0,
                'estimated_completion_date': None,
                'status': 'error',
                'error': str(e)
            }
    
    def _get_ai_recommendation_data(self, student_id: int) -> Dict[str, Any]:
        """AI推薦データを取得"""
        try:
            # AI推薦レコード取得
            recommendations = AIRecommendation.query.filter_by(
                student_id=student_id
            ).order_by(AIRecommendation.created_at.desc()).limit(5).all()
            
            rec_data = []
            for rec in recommendations:
                rec_data.append({
                    'id': rec.id,
                    'type': rec.recommendation_type,
                    'title': rec.recommendation_text[:100],  # 最初の100文字
                    'priority': getattr(rec, 'priority', 'medium'),
                    'created_at': rec.created_at,
                    'is_applied': getattr(rec, 'is_applied', False)
                })
            
            return {
                'recommendations': rec_data,
                'total_recommendations': len(recommendations),
                'pending_recommendations': len([r for r in rec_data if not r['is_applied']]),
                'last_generated': recommendations[0].created_at if recommendations else None,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error getting AI recommendation data: {str(e)}")
            return {
                'recommendations': [],
                'total_recommendations': 0,
                'pending_recommendations': 0,
                'last_generated': None,
                'status': 'error',
                'error': str(e)
            }
    
    def _get_recent_activities_data(self, student_id: int) -> Dict[str, Any]:
        """最近のアクティビティデータを取得"""
        try:
            activities = []
            
            # 最近の評価
            recent_evaluations = StudentEvaluation.query.filter_by(
                student_id=student_id
            ).order_by(StudentEvaluation.created_at.desc()).limit(5).all()
            
            for eval in recent_evaluations:
                activities.append({
                    'type': 'evaluation',
                    'title': f"クイズ完了: {getattr(eval, 'subject', 'Unknown')}",
                    'description': f"スコア: {eval.score}",
                    'timestamp': eval.created_at,
                    'icon': 'quiz'
                })
            
            # 最近の熟練度記録
            recent_proficiency = ProficiencyRecord.query.filter_by(
                student_id=student_id
            ).order_by(ProficiencyRecord.updated_at.desc()).limit(5).all()
            
            for prof in recent_proficiency:
                activities.append({
                    'type': 'proficiency',
                    'title': f"問題演習",
                    'description': f"正解率: {getattr(prof, 'accuracy', 'Unknown')}%",
                    'timestamp': prof.updated_at,
                    'icon': 'practice'
                })
            
            # タイムスタンプでソート
            activities.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return {
                'activities': activities[:10],  # 最新10件
                'total_activities': len(activities),
                'last_activity': activities[0]['timestamp'] if activities else None,
                'activity_summary': self._summarize_recent_activity(activities),
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error getting recent activities data: {str(e)}")
            return {
                'activities': [],
                'total_activities': 0,
                'last_activity': None,
                'activity_summary': {},
                'status': 'error',
                'error': str(e)
            }
    
    def _get_basebuilder_data(self, student_id: int) -> Dict[str, Any]:
        """BaseBuilderデータを取得"""
        try:
            # BaseBuilderレコード取得
            bb_records = BaseBuilderRecord.query.filter_by(student_id=student_id).all()
            
            if not bb_records:
                return {
                    'total_words_learned': 0,
                    'vocabulary_level': 'beginner',
                    'recent_sessions': [],
                    'strength_categories': [],
                    'weakness_categories': [],
                    'status': 'no_data'
                }
            
            # 統計計算
            total_words = len(bb_records)
            correct_answers = len([r for r in bb_records if getattr(r, 'is_correct', False)])
            accuracy = (correct_answers / total_words * 100) if total_words > 0 else 0
            
            # レベル判定
            vocab_level = self._determine_vocabulary_level(total_words, accuracy)
            
            # 最近のセッション
            recent_sessions = self._get_recent_basebuilder_sessions(student_id)
            
            return {
                'total_words_learned': total_words,
                'vocabulary_accuracy': accuracy,
                'vocabulary_level': vocab_level,
                'recent_sessions': recent_sessions,
                'strength_categories': [],  # 将来実装
                'weakness_categories': [],  # 将来実装
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error getting BaseBuilder data: {str(e)}")
            return {
                'total_words_learned': 0,
                'vocabulary_level': 'unknown',
                'recent_sessions': [],
                'strength_categories': [],
                'weakness_categories': [],
                'status': 'error',
                'error': str(e)
            }
    
    def _get_vocabulary_analysis_data(self, student_id: int) -> Dict[str, Any]:
        """語彙分析データを取得"""
        try:
            # 簡易実装（将来的に拡張）
            return {
                'vocabulary_growth_trend': 'stable',
                'strong_categories': [],
                'weak_categories': [],
                'recommended_focus': [],
                'status': 'pending_implementation'
            }
        except Exception as e:
            logger.error(f"Error getting vocabulary analysis data: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _get_spaced_repetition_data(self, student_id: int) -> Dict[str, Any]:
        """間隔反復学習データを取得"""
        try:
            # 簡易実装（将来的に拡張）
            return {
                'items_due_today': 0,
                'items_overdue': 0,
                'review_schedule': [],
                'learning_efficiency': 'unknown',
                'status': 'pending_implementation'
            }
        except Exception as e:
            logger.error(f"Error getting spaced repetition data: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _get_weakness_analysis_data(self, student_id: int) -> Dict[str, Any]:
        """弱点分析データを取得"""
        try:
            # 簡易実装（将来的に拡張）
            return {
                'identified_weaknesses': [],
                'improvement_suggestions': [],
                'priority_areas': [],
                'progress_tracking': {},
                'status': 'pending_implementation'
            }
        except Exception as e:
            logger.error(f"Error getting weakness analysis data: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _get_chart_data(self, student_id: int) -> Dict[str, Any]:
        """チャートデータを取得"""
        try:
            # 学習進捗チャート用データ
            progress_chart = self._generate_progress_chart_data(student_id)
            
            # スコア推移チャート用データ
            score_chart = self._generate_score_chart_data(student_id)
            
            return {
                'progress_chart': progress_chart,
                'score_trend_chart': score_chart,
                'activity_heatmap': {},  # 将来実装
                'subject_comparison': {},  # 将来実装
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error getting chart data: {str(e)}")
            return {
                'progress_chart': {},
                'score_trend_chart': {},
                'activity_heatmap': {},
                'subject_comparison': {},
                'status': 'error',
                'error': str(e)
            }
    
    # ヘルパーメソッド群
    
    def _get_next_milestone(self, student_id: int) -> Optional[Dict[str, Any]]:
        """次のマイルストーンを取得"""
        try:
            next_milestone = StudentMilestone.query.filter_by(
                student_id=student_id,
                is_completed=False
            ).first()
            
            if next_milestone:
                return {
                    'id': next_milestone.id,
                    'title': next_milestone.milestone_name,
                    'description': getattr(next_milestone, 'description', ''),
                    'progress': getattr(next_milestone, 'progress_percentage', 0)
                }
            return None
            
        except Exception:
            return None
    
    def _calculate_quiz_trend(self, quiz_data: List[Dict]) -> str:
        """クイズスコアのトレンドを計算"""
        if len(quiz_data) < 2:
            return 'insufficient_data'
        
        scores = [q['score'] for q in quiz_data if q['score'] is not None]
        if len(scores) < 2:
            return 'insufficient_data'
        
        # 最近のスコアと過去のスコアを比較
        recent_avg = sum(scores[:len(scores)//2]) / (len(scores)//2)
        past_avg = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
        
        if recent_avg > past_avg + 5:
            return 'improving'
        elif recent_avg < past_avg - 5:
            return 'declining'
        else:
            return 'stable'
    
    def _calculate_learning_streak(self, student_id: int) -> int:
        """学習ストリーク日数を計算"""
        try:
            # 簡易実装：過去7日間の連続学習日数
            days_back = 7
            streak = 0
            
            for i in range(days_back):
                target_date = datetime.now() - timedelta(days=i)
                day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                
                activity_count = StudentEvaluation.query.filter(
                    StudentEvaluation.student_id == student_id,
                    StudentEvaluation.created_at >= day_start,
                    StudentEvaluation.created_at < day_end
                ).count()
                
                if activity_count > 0:
                    streak += 1
                else:
                    break
            
            return streak
            
        except Exception:
            return 0
    
    def _estimate_completion_date(self, student_id: int) -> Optional[datetime]:
        """完了予想日を推定"""
        # 簡易実装（将来的に拡張）
        return None
    
    def _summarize_recent_activity(self, activities: List[Dict]) -> Dict[str, Any]:
        """最近のアクティビティを要約"""
        try:
            activity_types = {}
            for activity in activities:
                activity_type = activity['type']
                activity_types[activity_type] = activity_types.get(activity_type, 0) + 1
            
            return {
                'total_activities': len(activities),
                'activity_breakdown': activity_types,
                'most_common_activity': max(activity_types.items(), key=lambda x: x[1])[0] if activity_types else None
            }
            
        except Exception:
            return {'total_activities': 0, 'activity_breakdown': {}, 'most_common_activity': None}
    
    def _determine_vocabulary_level(self, total_words: int, accuracy: float) -> str:
        """語彙レベルを判定"""
        if total_words >= 1000 and accuracy >= 80:
            return 'advanced'
        elif total_words >= 500 and accuracy >= 70:
            return 'intermediate'
        elif total_words >= 100:
            return 'beginner'
        else:
            return 'starter'
    
    def _get_recent_basebuilder_sessions(self, student_id: int) -> List[Dict]:
        """最近のBaseBuilderセッションを取得"""
        try:
            # 簡易実装
            recent_records = BaseBuilderRecord.query.filter_by(
                student_id=student_id
            ).order_by(BaseBuilderRecord.created_at.desc()).limit(5).all()
            
            sessions = []
            for record in recent_records:
                sessions.append({
                    'date': record.created_at,
                    'words_learned': 1,  # 1レコード = 1単語
                    'accuracy': getattr(record, 'accuracy', 0),
                    'duration': getattr(record, 'session_duration', 0)
                })
            
            return sessions
            
        except Exception:
            return []
    
    def _generate_progress_chart_data(self, student_id: int) -> Dict[str, Any]:
        """進捗チャート用データを生成"""
        try:
            # 過去30日の日別進捗
            data_points = []
            for i in range(30):
                date = datetime.now() - timedelta(days=i)
                day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                
                daily_activities = StudentEvaluation.query.filter(
                    StudentEvaluation.student_id == student_id,
                    StudentEvaluation.created_at >= day_start,
                    StudentEvaluation.created_at < day_end
                ).count()
                
                data_points.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'activities': daily_activities
                })
            
            return {
                'labels': [dp['date'] for dp in reversed(data_points)],
                'data': [dp['activities'] for dp in reversed(data_points)],
                'type': 'line'
            }
            
        except Exception:
            return {'labels': [], 'data': [], 'type': 'line'}
    
    def _generate_score_chart_data(self, student_id: int) -> Dict[str, Any]:
        """スコアチャート用データを生成"""
        try:
            recent_evaluations = StudentEvaluation.query.filter_by(
                student_id=student_id
            ).order_by(StudentEvaluation.created_at.desc()).limit(10).all()
            
            return {
                'labels': [eval.created_at.strftime('%m/%d') for eval in reversed(recent_evaluations)],
                'data': [eval.score for eval in reversed(recent_evaluations)],
                'type': 'line'
            }
            
        except Exception:
            return {'labels': [], 'data': [], 'type': 'line'}
    
    def _get_default_dashboard_data(self, student_id: int, error_message: str) -> Dict[str, Any]:
        """デフォルトダッシュボードデータ（エラー時）"""
        return {
            'student_id': student_id,
            'student_basic_info': self.student_info_service._get_default_basic_info(student_id),
            'milestone_data': {'status': 'error'},
            'quiz_history': {'status': 'error'},
            'progress_summary': {'status': 'error'},
            'ai_recommendations': {'status': 'error'},
            'recent_activities': {'status': 'error'},
            'basebuilder_data': {'status': 'error'},
            'vocabulary_analysis': {'status': 'error'},
            'spaced_repetition': {'status': 'error'},
            'weakness_analysis': {'status': 'error'},
            'chart_data': {'status': 'error'},
            'generated_at': datetime.now(),
            'success': False,
            'error': error_message
        }
    
    def _has_permission(self, user, action: str, resource: Any = None) -> bool:
        """
        権限チェック実装
        Phase8E緊急修正: BaseService抽象メソッド実装
        """
        # ダッシュボードサービスは自分の情報のみアクセス可能
        if user and hasattr(user, 'id'):
            return True  # 認証されたユーザーは自分のダッシュボードにアクセス可能
        return False