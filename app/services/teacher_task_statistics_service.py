"""
教師タスク統計サービス
Phase 7-2: teacher/modules/task_management.py から統計計算機能を分離
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import current_app
from flask_login import current_user

from app.models import (
    Class,
    ClassEnrollment, 
    Curriculum,
    CurriculumUnit,
    StudentUnitSelection,
    User,
    db,
)
from app.services.base_service import BaseService

logger = logging.getLogger(__name__)


class TeacherTaskStatisticsService(BaseService):
    """教師タスク統計サービス
    
    Phase 7-2: task_management.py から統計計算機能を分離
    Single Responsibility: 教師用のタスク統計計算・分析
    """
    
    def __init__(self):
        super().__init__()
        self._cache_timeout = 300  # 5分キャッシュ
    
    def calculate_teacher_statistics(
        self, 
        teacher_classes: List[Class], 
        class_filter: Optional[int] = None, 
        curriculum_filter: Optional[int] = None, 
        status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        教師の担当クラスの統計データを計算
        Phase 7-2: 元 calculate_statistics() から移行
        """
        try:
            logger.info(f"Calculating statistics for teacher {current_user.id}")
            
            # 対象クラスの決定
            target_class_ids = self._get_target_class_ids(teacher_classes, class_filter)
            
            # 対象学生の取得
            student_ids = self._get_students_in_classes(target_class_ids)
            
            # 各統計項目を計算
            stats = {
                'pending_submissions': self._calculate_pending_submissions(student_ids, curriculum_filter),
                'completion_rate': self._calculate_completion_rate(student_ids, curriculum_filter),
                'active_students': self._calculate_active_students(student_ids),
                'overdue_tasks': self._calculate_overdue_tasks(student_ids, curriculum_filter)
            }
            
            logger.info(f"Statistics calculated: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating teacher statistics: {str(e)}")
            return self._get_default_statistics()
    
    def get_class_statistics(self, class_id: int) -> Dict[str, Any]:
        """クラス別統計の取得"""
        try:
            # 権限チェック
            class_obj = Class.query.get(class_id)
            if not class_obj or class_obj.teacher_id != current_user.id:
                raise ValueError("Access denied or class not found")
            
            # クラスの学生取得
            student_ids = self._get_students_in_classes([class_id])
            
            # 基本統計
            basic_stats = {
                'total_students': len(student_ids),
                'pending_submissions': self._calculate_pending_submissions(student_ids),
                'completion_rate': self._calculate_completion_rate(student_ids),
                'active_students': self._calculate_active_students(student_ids)
            }
            
            # 学生別統計
            student_statistics = []
            for student_id in student_ids:
                student = User.query.get(student_id)
                if student:
                    student_stats = self._get_student_individual_stats(student_id)
                    student_stats.update({
                        'id': student.id,
                        'name': student.full_name or student.username,
                        'username': student.username
                    })
                    student_statistics.append(student_stats)
            
            return {
                'class_id': class_id,
                'class_name': class_obj.name,
                'basic_statistics': basic_stats,
                'student_statistics': student_statistics,
                'generated_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error getting class statistics for class {class_id}: {str(e)}")
            return {'error': str(e)}
    
    def get_curriculum_statistics(self, curriculum_id: int) -> Dict[str, Any]:
        """カリキュラム別統計の取得"""
        try:
            # カリキュラムの存在確認
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                raise ValueError("Curriculum not found")
            
            # 教師の担当クラス取得
            teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
            target_class_ids = [c.id for c in teacher_classes]
            student_ids = self._get_students_in_classes(target_class_ids)
            
            # カリキュラム関連の単元取得
            curriculum_units = CurriculumUnit.query.filter_by(curriculum_id=curriculum_id).all()
            unit_ids = [u.id for u in curriculum_units]
            
            # 統計計算
            stats = {
                'curriculum_id': curriculum_id,
                'curriculum_title': curriculum.title,
                'total_units': len(unit_ids),
                'total_students': len(student_ids),
                'unit_statistics': self._calculate_unit_statistics(unit_ids, student_ids),
                'progress_distribution': self._calculate_progress_distribution(unit_ids, student_ids),
                'completion_trends': self._calculate_completion_trends(unit_ids, student_ids)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting curriculum statistics for curriculum {curriculum_id}: {str(e)}")
            return {'error': str(e)}
    
    def get_weekly_statistics(self, week_number: Optional[int] = None) -> Dict[str, Any]:
        """週別統計の取得"""
        try:
            # 教師の担当クラス取得
            teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
            target_class_ids = [c.id for c in teacher_classes]
            student_ids = self._get_students_in_classes(target_class_ids)
            
            if week_number:
                # 特定週の統計
                return self._calculate_week_statistics(week_number, student_ids)
            else:
                # 全週の統計
                weekly_stats = {}
                for week in range(1, 6):  # 第1-5週
                    weekly_stats[f'week_{week}'] = self._calculate_week_statistics(week, student_ids)
                
                return {
                    'weekly_statistics': weekly_stats,
                    'overall_trend': self._calculate_weekly_trend(weekly_stats),
                    'generated_at': datetime.now()
                }
                
        except Exception as e:
            logger.error(f"Error getting weekly statistics: {str(e)}")
            return {'error': str(e)}
    
    def _get_target_class_ids(self, teacher_classes: List[Class], class_filter: Optional[int]) -> List[int]:
        """対象クラスIDの決定"""
        if class_filter:
            # フィルターが指定された場合、教師の担当クラスか確認
            if any(c.id == class_filter for c in teacher_classes):
                return [class_filter]
            else:
                logger.warning(f"Class filter {class_filter} not in teacher's classes")
                return []
        else:
            return [c.id for c in teacher_classes]
    
    def _get_students_in_classes(self, class_ids: List[int]) -> List[int]:
        """クラス内の学生ID一覧を取得"""
        if not class_ids:
            return []
            
        enrollments = ClassEnrollment.query.filter(
            ClassEnrollment.class_id.in_(class_ids)
        ).all()
        return [e.student_id for e in enrollments]
    
    def _calculate_pending_submissions(
        self, 
        student_ids: List[int], 
        curriculum_filter: Optional[int] = None
    ) -> int:
        """承認待ち提出数の計算"""
        if not student_ids:
            return 0
            
        try:
            # レッスンシステムの完了申請（承認待ち）
            unit_query = StudentUnitSelection.query.filter(
                StudentUnitSelection.student_id.in_(student_ids),
                StudentUnitSelection.approval_status == 'none',
                StudentUnitSelection.completion_request_date.isnot(None)
            )
            
            if curriculum_filter:
                # カリキュラムフィルターが指定された場合
                unit_ids = db.session.query(CurriculumUnit.id).filter_by(
                    curriculum_id=curriculum_filter
                ).subquery()
                unit_query = unit_query.filter(
                    StudentUnitSelection.curriculum_unit_id.in_(unit_ids)
                )
            
            pending_count = unit_query.count()
            logger.debug(f"Pending submissions calculated: {pending_count}")
            return pending_count
            
        except Exception as e:
            logger.error(f"Error calculating pending submissions: {str(e)}")
            return 0
    
    def _calculate_completion_rate(
        self, 
        student_ids: List[int], 
        curriculum_filter: Optional[int] = None
    ) -> float:
        """完了率の計算"""
        if not student_ids:
            return 0.0
            
        try:
            base_query = StudentUnitSelection.query.filter(
                StudentUnitSelection.student_id.in_(student_ids)
            )
            
            if curriculum_filter:
                unit_ids = db.session.query(CurriculumUnit.id).filter_by(
                    curriculum_id=curriculum_filter
                ).subquery()
                base_query = base_query.filter(
                    StudentUnitSelection.curriculum_unit_id.in_(unit_ids)
                )
            
            total_selections = base_query.count()
            completed_selections = base_query.filter_by(approval_status='approved').count()
            
            completion_rate = round(
                (completed_selections / total_selections * 100) if total_selections > 0 else 0, 
                1
            )
            
            logger.debug(f"Completion rate: {completion_rate}% ({completed_selections}/{total_selections})")
            return completion_rate
            
        except Exception as e:
            logger.error(f"Error calculating completion rate: {str(e)}")
            return 0.0
    
    def _calculate_active_students(self, student_ids: List[int]) -> int:
        """アクティブ学生数の計算（過去7日間に活動した学生）"""
        if not student_ids:
            return 0
            
        try:
            seven_days_ago = datetime.now() - timedelta(days=7)
            
            active_students = db.session.query(
                StudentUnitSelection.student_id
            ).filter(
                StudentUnitSelection.student_id.in_(student_ids),
                StudentUnitSelection.last_accessed_at >= seven_days_ago
            ).distinct().count()
            
            logger.debug(f"Active students: {active_students}")
            return active_students
            
        except Exception as e:
            logger.error(f"Error calculating active students: {str(e)}")
            return 0
    
    def _calculate_overdue_tasks(
        self, 
        student_ids: List[int], 
        curriculum_filter: Optional[int] = None
    ) -> int:
        """期限超過タスク数の計算（現在は簡易実装）"""
        # TODO: 期限管理機能実装後に正確な計算を行う
        logger.debug("Overdue tasks calculation not yet implemented")
        return 0
    
    def _get_student_individual_stats(self, student_id: int) -> Dict[str, Any]:
        """個別学生統計の取得"""
        try:
            # 学生の単元選択統計
            selections = StudentUnitSelection.query.filter_by(student_id=student_id).all()
            
            total_selections = len(selections)
            completed_selections = len([s for s in selections if s.approval_status == 'approved'])
            in_progress_selections = len([s for s in selections if s.approval_status == 'none' and s.progress_percentage > 0])
            pending_approvals = len([s for s in selections if s.completion_request_date and s.approval_status == 'none'])
            
            # 平均進捗率
            avg_progress = sum(s.progress_percentage for s in selections) / total_selections if total_selections > 0 else 0
            
            # 最終アクセス時刻
            last_activity = None
            if selections:
                last_accessed_times = [s.last_accessed_at for s in selections if s.last_accessed_at]
                if last_accessed_times:
                    last_activity = max(last_accessed_times)
            
            return {
                'total_units': total_selections,
                'completed_units': completed_selections,
                'in_progress_units': in_progress_selections,
                'pending_approvals': pending_approvals,
                'average_progress': round(avg_progress, 1),
                'completion_rate': round((completed_selections / total_selections * 100) if total_selections > 0 else 0, 1),
                'last_activity': last_activity
            }
            
        except Exception as e:
            logger.error(f"Error getting individual stats for student {student_id}: {str(e)}")
            return {
                'total_units': 0,
                'completed_units': 0,
                'in_progress_units': 0,
                'pending_approvals': 0,
                'average_progress': 0.0,
                'completion_rate': 0.0,
                'last_activity': None
            }
    
    def _calculate_unit_statistics(self, unit_ids: List[int], student_ids: List[int]) -> List[Dict[str, Any]]:
        """単元別統計の計算"""
        try:
            unit_stats = []
            
            for unit_id in unit_ids:
                unit = CurriculumUnit.query.get(unit_id)
                if not unit:
                    continue
                
                # この単元の選択数・完了数
                selections = StudentUnitSelection.query.filter(
                    StudentUnitSelection.curriculum_unit_id == unit_id,
                    StudentUnitSelection.student_id.in_(student_ids)
                ).all()
                
                total_selections = len(selections)
                completed = len([s for s in selections if s.approval_status == 'approved'])
                in_progress = len([s for s in selections if s.progress_percentage > 0 and s.approval_status == 'none'])
                
                avg_progress = sum(s.progress_percentage for s in selections) / total_selections if total_selections > 0 else 0
                
                unit_stats.append({
                    'unit_id': unit_id,
                    'unit_title': unit.title,
                    'unit_difficulty': unit.difficulty,
                    'total_selections': total_selections,
                    'completed_count': completed,
                    'in_progress_count': in_progress,
                    'completion_rate': round((completed / total_selections * 100) if total_selections > 0 else 0, 1),
                    'average_progress': round(avg_progress, 1)
                })
            
            return sorted(unit_stats, key=lambda x: x['completion_rate'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error calculating unit statistics: {str(e)}")
            return []
    
    def _calculate_progress_distribution(self, unit_ids: List[int], student_ids: List[int]) -> Dict[str, int]:
        """進捗分布の計算"""
        try:
            selections = StudentUnitSelection.query.filter(
                StudentUnitSelection.curriculum_unit_id.in_(unit_ids),
                StudentUnitSelection.student_id.in_(student_ids)
            ).all()
            
            distribution = {
                '0-20%': 0,
                '21-40%': 0,
                '41-60%': 0,
                '61-80%': 0,
                '81-100%': 0
            }
            
            for selection in selections:
                progress = selection.progress_percentage
                if progress <= 20:
                    distribution['0-20%'] += 1
                elif progress <= 40:
                    distribution['21-40%'] += 1
                elif progress <= 60:
                    distribution['41-60%'] += 1
                elif progress <= 80:
                    distribution['61-80%'] += 1
                else:
                    distribution['81-100%'] += 1
            
            return distribution
            
        except Exception as e:
            logger.error(f"Error calculating progress distribution: {str(e)}")
            return {}
    
    def _calculate_completion_trends(self, unit_ids: List[int], student_ids: List[int]) -> Dict[str, Any]:
        """完了トレンドの計算"""
        try:
            # 過去30日間の完了履歴
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            completed_selections = StudentUnitSelection.query.filter(
                StudentUnitSelection.curriculum_unit_id.in_(unit_ids),
                StudentUnitSelection.student_id.in_(student_ids),
                StudentUnitSelection.approval_status == 'approved',
                StudentUnitSelection.approved_at >= thirty_days_ago
            ).all()
            
            # 日別集計
            daily_completions = {}
            for selection in completed_selections:
                if selection.approved_at:
                    date_key = selection.approved_at.strftime('%Y-%m-%d')
                    daily_completions[date_key] = daily_completions.get(date_key, 0) + 1
            
            # トレンド分析
            recent_week = sum(
                count for date, count in daily_completions.items()
                if datetime.strptime(date, '%Y-%m-%d') >= datetime.now() - timedelta(days=7)
            )
            previous_week = sum(
                count for date, count in daily_completions.items()
                if datetime.now() - timedelta(days=14) <= datetime.strptime(date, '%Y-%m-%d') < datetime.now() - timedelta(days=7)
            )
            
            trend = "increasing" if recent_week > previous_week else "decreasing" if recent_week < previous_week else "stable"
            
            return {
                'daily_completions': daily_completions,
                'recent_week_total': recent_week,
                'previous_week_total': previous_week,
                'trend': trend,
                'total_completions': len(completed_selections)
            }
            
        except Exception as e:
            logger.error(f"Error calculating completion trends: {str(e)}")
            return {}
    
    def _calculate_week_statistics(self, week_number: int, student_ids: List[int]) -> Dict[str, Any]:
        """特定週の統計計算"""
        try:
            # 注意: 新カリキュラムタスクシステムは削除済みのため、週別統計は簡易実装
            return {
                'week_number': week_number,
                'total_tasks': 0,
                'completed_tasks': 0,
                'in_progress_tasks': 0,
                'completion_rate': 0.0,
                'note': 'Week-based task system is not currently implemented'
            }
            
        except Exception as e:
            logger.error(f"Error calculating week {week_number} statistics: {str(e)}")
            return {}
    
    def _calculate_weekly_trend(self, weekly_stats: Dict[str, Any]) -> Dict[str, Any]:
        """週間トレンドの分析"""
        try:
            # 簡易実装
            return {
                'trend_direction': 'stable',
                'improvement_rate': 0.0,
                'note': 'Weekly trend analysis requires week-based task system'
            }
            
        except Exception as e:
            logger.error(f"Error calculating weekly trend: {str(e)}")
            return {}
    
    def _get_default_statistics(self) -> Dict[str, Any]:
        """デフォルト統計値"""
        return {
            'pending_submissions': 0,
            'completion_rate': 0.0,
            'active_students': 0,
            'overdue_tasks': 0
        }