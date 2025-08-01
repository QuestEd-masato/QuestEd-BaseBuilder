"""
教師進捗管理サービス
Phase 7-2: teacher/modules/task_management.py から進捗管理機能を分離
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


class TeacherProgressService(BaseService):
    """教師進捗管理サービス
    
    Phase 7-2: task_management.py から進捗管理機能を分離
    Single Responsibility: 教師視点での学生進捗管理・監視
    """
    
    def __init__(self):
        super().__init__()
    
    def get_classes_progress(
        self,
        teacher_classes: List[Class],
        class_filter: Optional[int] = None,
        curriculum_filter: Optional[int] = None,
        week_filter: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        クラス別進捗データの取得
        Phase 7-2: 元 get_classes_progress() から移行
        """
        try:
            logger.info(f"Getting classes progress for teacher {current_user.id}")
            
            # 対象クラスの決定
            target_classes = self._filter_target_classes(teacher_classes, class_filter)
            
            classes_progress = []
            
            for class_obj in target_classes:
                # クラス進捗データを取得
                class_progress = self._get_single_class_progress(
                    class_obj, curriculum_filter, week_filter
                )
                classes_progress.append(class_progress)
            
            logger.info(f"Retrieved progress for {len(classes_progress)} classes")
            return classes_progress
            
        except Exception as e:
            logger.error(f"Error getting classes progress: {str(e)}")
            return []
    
    def get_class_progress_detail(self, class_id: int) -> Dict[str, Any]:
        """
        クラス別進捗詳細の取得
        Phase 7-2: 元 class_progress ルートの処理を移行
        """
        try:
            # クラス取得と権限チェック
            class_obj = Class.query.get(class_id)
            if not class_obj or class_obj.teacher_id != current_user.id:
                raise ValueError("Access denied or class not found")
            
            logger.info(f"Getting detailed progress for class {class_id}")
            
            # クラスの学生取得
            students = self._get_class_students(class_id)
            
            # 学生別詳細進捗データ取得
            students_progress = []
            for student in students:
                if student:
                    progress_data = self.get_student_progress_detail(student.id, class_id)
                    if progress_data:
                        students_progress.append(progress_data)
            
            return {
                'class_id': class_id,
                'class_name': class_obj.name,
                'total_students': len(students),
                'students_progress': students_progress,
                'class_statistics': self._calculate_class_statistics(students_progress),
                'generated_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error getting class progress detail for class {class_id}: {str(e)}")
            return {'error': str(e)}
    
    def get_student_progress_detail(self, student_id: int, class_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        学生詳細進捗データ取得
        Phase 7-2: 元 get_student_progress_detail() から移行
        """
        try:
            student = User.query.get(student_id)
            if not student:
                return None
            
            # 権限チェック（教師が担当する学生かどうか）
            if not self._can_access_student_progress(student_id):
                logger.warning(f"Access denied for student {student_id}")
                return None
            
            logger.debug(f"Getting progress detail for student {student_id}")
            
            # 学生の単元選択進捗を取得
            unit_selections = StudentUnitSelection.query.filter_by(
                student_id=student_id
            ).options(db.joinedload(StudentUnitSelection.curriculum_unit)).all()
            
            # 週別進捗分析（レッスンシステムベース）
            weekly_progress = self._analyze_weekly_progress(unit_selections)
            
            # 全体統計
            overall_stats = self._calculate_student_overall_stats(unit_selections)
            
            return {
                'student_id': student.id,
                'student_name': student.full_name or student.username,
                'student_username': student.username,
                'class_id': class_id,
                'unit_selections': self._format_unit_selections(unit_selections),
                'weekly_progress': weekly_progress,
                'overall_statistics': overall_stats,
                'recommendations': self._generate_student_recommendations(unit_selections, overall_stats)
            }
            
        except Exception as e:
            logger.error(f"Error getting student progress detail for student {student_id}: {str(e)}")
            return None
    
    def get_student_weekly_progress(
        self,
        student_id: int,
        curriculum_filter: Optional[int] = None,
        week_filter: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        学生の週別進捗取得
        Phase 7-2: 元 get_student_weekly_progress() から移行
        """
        try:
            logger.debug(f"Getting weekly progress for student {student_id}")
            
            # レッスンシステムベースの進捗取得
            unit_selections = StudentUnitSelection.query.filter_by(student_id=student_id).all()
            
            if curriculum_filter:
                # カリキュラムフィルター適用
                curriculum_unit_ids = db.session.query(CurriculumUnit.id).filter_by(
                    curriculum_id=curriculum_filter
                ).subquery()
                unit_selections = [
                    selection for selection in unit_selections
                    if selection.curriculum_unit_id in [u.id for u in curriculum_unit_ids]
                ]
            
            # 週別グループ化（単元の難易度・順序ベース）
            weeks_progress = self._group_selections_by_weeks(unit_selections, week_filter)
            
            # 承認待ち数の計算
            pending_count = len([
                s for s in unit_selections 
                if s.completion_request_date and s.approval_status == 'none'
            ])
            
            return {
                'student_id': student_id,
                'weeks': weeks_progress,
                'pending_count': pending_count,
                'total_selections': len(unit_selections)
            }
            
        except Exception as e:
            logger.error(f"Error getting student weekly progress for student {student_id}: {str(e)}")
            return {'weeks': [], 'pending_count': 0, 'total_selections': 0}
    
    def get_progress_analytics(
        self,
        class_ids: Optional[List[int]] = None,
        time_range_days: int = 30
    ) -> Dict[str, Any]:
        """進捗分析データの取得"""
        try:
            if class_ids is None:
                # 教師の全クラス
                teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
                class_ids = [c.id for c in teacher_classes]
            
            # 対象学生の取得
            student_ids = []
            for class_id in class_ids:
                enrollments = ClassEnrollment.query.filter_by(class_id=class_id).all()
                student_ids.extend([e.student_id for e in enrollments])
            
            # 期間内の進捗データ取得
            cutoff_date = datetime.now() - timedelta(days=time_range_days)
            
            recent_selections = StudentUnitSelection.query.filter(
                StudentUnitSelection.student_id.in_(student_ids),
                StudentUnitSelection.last_accessed_at >= cutoff_date
            ).all()
            
            # 分析実行
            analytics = {
                'time_range_days': time_range_days,
                'total_students': len(set(student_ids)),
                'active_students': len(set(s.student_id for s in recent_selections)),
                'progress_trends': self._analyze_progress_trends(recent_selections),
                'completion_patterns': self._analyze_completion_patterns(recent_selections),
                'difficulty_analysis': self._analyze_difficulty_progress(recent_selections),
                'engagement_metrics': self._calculate_engagement_metrics(recent_selections, student_ids)
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting progress analytics: {str(e)}")
            return {'error': str(e)}
    
    def _filter_target_classes(self, teacher_classes: List[Class], class_filter: Optional[int]) -> List[Class]:
        """対象クラスのフィルタリング"""
        if class_filter:
            return [c for c in teacher_classes if c.id == class_filter]
        return teacher_classes
    
    def _get_single_class_progress(
        self,
        class_obj: Class,
        curriculum_filter: Optional[int] = None,
        week_filter: Optional[int] = None
    ) -> Dict[str, Any]:
        """単一クラスの進捗データ取得"""
        try:
            # クラスの学生取得
            students = self._get_class_students(class_obj.id)
            
            # 学生別進捗データ取得
            students_data = []
            for student in students:
                if student:
                    student_progress = self.get_student_weekly_progress(
                        student.id, curriculum_filter, week_filter
                    )
                    student_data = {
                        'id': student.id,
                        'name': student.full_name or student.username,
                        'username': student.username,
                        'weeks_progress': student_progress['weeks'],
                        'pending_tasks': student_progress['pending_count']
                    }
                    students_data.append(student_data)
            
            # クラス統計計算
            class_stats = self._calculate_class_summary_stats(students_data)
            
            return {
                'class_id': class_obj.id,
                'class_name': class_obj.name,
                'students': students_data,
                'statistics': class_stats,
                'weeks': self._get_week_structure(week_filter)  # 週構造情報
            }
            
        except Exception as e:
            logger.error(f"Error getting single class progress for class {class_obj.id}: {str(e)}")
            return {
                'class_id': class_obj.id,
                'class_name': class_obj.name,
                'students': [],
                'statistics': {},
                'weeks': []
            }
    
    def _get_class_students(self, class_id: int) -> List[User]:
        """クラスの学生一覧を取得"""
        enrollments = ClassEnrollment.query.filter_by(class_id=class_id).all()
        students = []
        for enrollment in enrollments:
            student = User.query.get(enrollment.student_id)
            if student:
                students.append(student)
        return students
    
    def _can_access_student_progress(self, student_id: int) -> bool:
        """学生進捗へのアクセス権限チェック"""
        try:
            # 管理者は全員アクセス可能
            if current_user.role == 'admin':
                return True
            
            # 教師は担当クラスの学生のみアクセス可能
            if current_user.role == 'teacher':
                teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
                teacher_class_ids = [c.id for c in teacher_classes]
                
                student_classes = ClassEnrollment.query.filter_by(student_id=student_id).all()
                student_class_ids = [sc.class_id for sc in student_classes]
                
                return any(class_id in teacher_class_ids for class_id in student_class_ids)
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking access permission for student {student_id}: {str(e)}")
            return False
    
    def _analyze_weekly_progress(self, unit_selections: List[StudentUnitSelection]) -> Dict[str, Any]:
        """週別進捗分析"""
        try:
            # 単元を難易度・順序で週に分類
            weekly_data = {}
            
            for selection in unit_selections:
                unit = selection.curriculum_unit
                if not unit:
                    continue
                
                # 単元の難易度・順序から週を推定（簡易ロジック）
                week_num = self._estimate_week_from_unit(unit)
                
                if week_num not in weekly_data:
                    weekly_data[week_num] = {
                        'week': week_num,
                        'units': [],
                        'total_progress': 0,
                        'completed_count': 0,
                        'in_progress_count': 0
                    }
                
                weekly_data[week_num]['units'].append({
                    'unit_id': unit.id,
                    'unit_title': unit.title,
                    'progress_percentage': selection.progress_percentage,
                    'approval_status': selection.approval_status,
                    'completion_requested': selection.completion_request_date is not None
                })
                
                weekly_data[week_num]['total_progress'] += selection.progress_percentage
                
                if selection.approval_status == 'approved':
                    weekly_data[week_num]['completed_count'] += 1
                elif selection.progress_percentage > 0:
                    weekly_data[week_num]['in_progress_count'] += 1
            
            # 平均進捗率を計算
            for week_data in weekly_data.values():
                unit_count = len(week_data['units'])
                if unit_count > 0:
                    week_data['average_progress'] = round(week_data['total_progress'] / unit_count, 1)
                else:
                    week_data['average_progress'] = 0.0
            
            return weekly_data
            
        except Exception as e:
            logger.error(f"Error analyzing weekly progress: {str(e)}")
            return {}
    
    def _calculate_student_overall_stats(self, unit_selections: List[StudentUnitSelection]) -> Dict[str, Any]:
        """学生全体統計の計算"""
        try:
            total_units = len(unit_selections)
            if total_units == 0:
                return self._get_empty_student_stats()
            
            completed_units = len([s for s in unit_selections if s.approval_status == 'approved'])
            in_progress_units = len([s for s in unit_selections if s.progress_percentage > 0 and s.approval_status != 'approved'])
            pending_approvals = len([s for s in unit_selections if s.completion_request_date and s.approval_status == 'none'])
            
            # 平均進捗率
            total_progress = sum(s.progress_percentage for s in unit_selections)
            average_progress = round(total_progress / total_units, 1)
            
            # 完了率
            completion_rate = round((completed_units / total_units) * 100, 1)
            
            # 最終アクセス時刻
            last_accessed_times = [s.last_accessed_at for s in unit_selections if s.last_accessed_at]
            last_activity = max(last_accessed_times) if last_accessed_times else None
            
            # 学習期間
            selected_times = [s.selected_at for s in unit_selections if s.selected_at]
            if selected_times:
                first_selection = min(selected_times)
                study_duration_days = (datetime.now() - first_selection).days
            else:
                study_duration_days = 0
            
            return {
                'total_units': total_units,
                'completed_units': completed_units,
                'in_progress_units': in_progress_units,
                'pending_approvals': pending_approvals,
                'average_progress': average_progress,
                'completion_rate': completion_rate,
                'last_activity': last_activity,
                'study_duration_days': study_duration_days
            }
            
        except Exception as e:
            logger.error(f"Error calculating student overall stats: {str(e)}")
            return self._get_empty_student_stats()
    
    def _format_unit_selections(self, unit_selections: List[StudentUnitSelection]) -> List[Dict[str, Any]]:
        """単元選択データのフォーマット"""
        formatted_selections = []
        
        for selection in unit_selections:
            unit = selection.curriculum_unit
            formatted_selection = {
                'selection_id': selection.id,
                'unit_id': selection.curriculum_unit_id,
                'unit_title': unit.title if unit else 'Unknown',
                'unit_difficulty': unit.difficulty if unit else None,
                'progress_percentage': selection.progress_percentage,
                'approval_status': selection.approval_status,
                'selected_at': selection.selected_at,
                'last_accessed_at': selection.last_accessed_at,
                'completion_request_date': selection.completion_request_date,
                'approved_at': selection.approved_at,
                'is_completed': selection.approval_status == 'approved',
                'needs_attention': self._needs_attention(selection)
            }
            formatted_selections.append(formatted_selection)
        
        return sorted(formatted_selections, key=lambda x: x['selected_at'] or datetime.min, reverse=True)
    
    def _generate_student_recommendations(
        self,
        unit_selections: List[StudentUnitSelection],
        overall_stats: Dict[str, Any]
    ) -> List[str]:
        """学生向け推奨事項の生成"""
        recommendations = []
        
        try:
            # 停滞している単元の特定
            stagnant_units = [
                s for s in unit_selections
                if s.progress_percentage > 0 and s.progress_percentage < 80 and s.last_accessed_at
                and (datetime.now() - s.last_accessed_at).days > 7
            ]
            
            if stagnant_units:
                recommendations.append(f"{len(stagnant_units)}つの単元で学習が停滞しています。継続的な取り組みを推奨します。")
            
            # 完了申請可能な単元
            ready_for_completion = [
                s for s in unit_selections
                if s.progress_percentage >= 80 and not s.completion_request_date
            ]
            
            if ready_for_completion:
                recommendations.append(f"{len(ready_for_completion)}つの単元で完了申請が可能です。")
            
            # 高難易度単元の進捗チェック
            difficult_units = [
                s for s in unit_selections
                if s.curriculum_unit and s.curriculum_unit.difficulty >= 4 and s.progress_percentage < 50
            ]
            
            if difficult_units:
                recommendations.append("高難易度単元で苦戦しています。基礎単元の復習を検討してください。")
            
            # 学習活動の継続性チェック
            if overall_stats.get('last_activity'):
                days_since_last = (datetime.now() - overall_stats['last_activity']).days
                if days_since_last > 3:
                    recommendations.append(f"{days_since_last}日間学習活動がありません。定期的な学習を心がけましょう。")
            
            if not recommendations:
                recommendations.append("順調に学習が進んでいます。この調子で続けてください。")
            
        except Exception as e:
            logger.error(f"Error generating student recommendations: {str(e)}")
            recommendations = ["推奨事項の生成中にエラーが発生しました。"]
        
        return recommendations
    
    def _group_selections_by_weeks(
        self,
        unit_selections: List[StudentUnitSelection],
        week_filter: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """単元選択を週別にグループ化"""
        try:
            weeks_data = {}
            
            # 週1-5の初期化
            for week in range(1, 6):
                if week_filter is None or week_filter == week:
                    weeks_data[week] = {
                        'week': week,
                        'total': 0,
                        'completed': 0,
                        'in_progress': 0,
                        'pending_count': 0,
                        'percentage': 0.0
                    }
            
            # 単元を週に分類
            for selection in unit_selections:
                unit = selection.curriculum_unit
                if not unit:
                    continue
                
                week_num = self._estimate_week_from_unit(unit)
                
                if week_num in weeks_data:
                    weeks_data[week_num]['total'] += 1
                    
                    if selection.approval_status == 'approved':
                        weeks_data[week_num]['completed'] += 1
                    elif selection.progress_percentage > 0:
                        weeks_data[week_num]['in_progress'] += 1
                    
                    if selection.completion_request_date and selection.approval_status == 'none':
                        weeks_data[week_num]['pending_count'] += 1
            
            # 完了率を計算
            for week_data in weeks_data.values():
                if week_data['total'] > 0:
                    week_data['percentage'] = round(
                        (week_data['completed'] / week_data['total']) * 100, 1
                    )
            
            return list(weeks_data.values())
            
        except Exception as e:
            logger.error(f"Error grouping selections by weeks: {str(e)}")
            return []
    
    def _estimate_week_from_unit(self, unit: CurriculumUnit) -> int:
        """単元から週番号を推定（簡易ロジック）"""
        try:
            # 難易度と順序から週を推定
            difficulty = unit.difficulty or 1
            order = unit.order or 1
            
            # 簡易計算: 順序と難易度を組み合わせて週を決定
            week = min(5, max(1, (order - 1) // 3 + 1))
            return week
            
        except Exception as e:
            logger.error(f"Error estimating week from unit {unit.id}: {str(e)}")
            return 1
    
    def _calculate_class_statistics(self, students_progress: List[Dict[str, Any]]) -> Dict[str, Any]:
        """クラス統計の計算"""
        try:
            if not students_progress:
                return {}
            
            total_students = len(students_progress)
            
            # 全体平均の計算
            total_completed = sum(s['overall_statistics']['completed_units'] for s in students_progress)
            total_units = sum(s['overall_statistics']['total_units'] for s in students_progress)
            total_pending = sum(s['overall_statistics']['pending_approvals'] for s in students_progress)
            
            avg_completion_rate = sum(s['overall_statistics']['completion_rate'] for s in students_progress) / total_students
            avg_progress = sum(s['overall_statistics']['average_progress'] for s in students_progress) / total_students
            
            return {
                'total_students': total_students,
                'total_completed_units': total_completed,
                'total_units': total_units,
                'total_pending_approvals': total_pending,
                'average_completion_rate': round(avg_completion_rate, 1),
                'average_progress': round(avg_progress, 1),
                'class_completion_rate': round((total_completed / total_units * 100) if total_units > 0 else 0, 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating class statistics: {str(e)}")
            return {}
    
    def _calculate_class_summary_stats(self, students_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """クラスサマリー統計の計算"""
        try:
            if not students_data:
                return {}
            
            total_students = len(students_data)
            total_pending = sum(s['pending_tasks'] for s in students_data)
            
            # 平均進捗率の計算
            avg_progress = 0
            if students_data:
                total_progress = 0
                total_weeks = 0
                for student in students_data:
                    for week in student['weeks_progress']:
                        total_progress += week['percentage']
                        total_weeks += 1
                
                avg_progress = round(total_progress / total_weeks if total_weeks > 0 else 0, 1)
            
            return {
                'total_students': total_students,
                'average_progress': avg_progress,
                'total_pending': total_pending
            }
            
        except Exception as e:
            logger.error(f"Error calculating class summary stats: {str(e)}")
            return {}
    
    def _get_week_structure(self, week_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """週構造情報の取得"""
        weeks = []
        for week_num in range(1, 6):
            if week_filter is None or week_filter == week_num:
                weeks.append({
                    'number': week_num,
                    'name': f'第{week_num}週',
                    'task_count': 0  # 現在のシステムでは週別タスクは無し
                })
        return weeks
    
    def _get_empty_student_stats(self) -> Dict[str, Any]:
        """空の学生統計"""
        return {
            'total_units': 0,
            'completed_units': 0,
            'in_progress_units': 0,
            'pending_approvals': 0,
            'average_progress': 0.0,
            'completion_rate': 0.0,
            'last_activity': None,
            'study_duration_days': 0
        }
    
    def _needs_attention(self, selection: StudentUnitSelection) -> bool:
        """注意が必要な単元かどうかの判定"""
        try:
            # 進捗が停滞している（1週間以上更新なし）
            if selection.last_accessed_at:
                days_since_access = (datetime.now() - selection.last_accessed_at).days
                if days_since_access > 7 and selection.progress_percentage < 100:
                    return True
            
            # 完了申請から時間が経過
            if selection.completion_request_date:
                days_since_request = (datetime.now() - selection.completion_request_date).days
                if days_since_request > 3:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if selection needs attention: {str(e)}")
            return False
    
    def _analyze_progress_trends(self, selections: List[StudentUnitSelection]) -> Dict[str, Any]:
        """進捗トレンドの分析"""
        try:
            # 実装予定: 時系列での進捗変化分析
            return {
                'trend': 'stable',
                'weekly_progress_change': 0.0,
                'note': 'Trend analysis implementation pending'
            }
        except Exception as e:
            logger.error(f"Error analyzing progress trends: {str(e)}")
            return {}
    
    def _analyze_completion_patterns(self, selections: List[StudentUnitSelection]) -> Dict[str, Any]:
        """完了パターンの分析"""
        try:
            # 実装予定: 完了パターンの分析
            return {
                'common_completion_time': '不明',
                'completion_rate_by_difficulty': {},
                'note': 'Completion pattern analysis implementation pending'
            }
        except Exception as e:
            logger.error(f"Error analyzing completion patterns: {str(e)}")
            return {}
    
    def _analyze_difficulty_progress(self, selections: List[StudentUnitSelection]) -> Dict[str, Any]:
        """難易度別進捗分析"""
        try:
            difficulty_stats = {}
            
            for selection in selections:
                if selection.curriculum_unit and selection.curriculum_unit.difficulty:
                    difficulty = selection.curriculum_unit.difficulty
                    if difficulty not in difficulty_stats:
                        difficulty_stats[difficulty] = {
                            'count': 0,
                            'total_progress': 0,
                            'completed': 0
                        }
                    
                    difficulty_stats[difficulty]['count'] += 1
                    difficulty_stats[difficulty]['total_progress'] += selection.progress_percentage
                    if selection.approval_status == 'approved':
                        difficulty_stats[difficulty]['completed'] += 1
            
            # 平均進捗率を計算
            for difficulty, stats in difficulty_stats.items():
                if stats['count'] > 0:
                    stats['average_progress'] = round(stats['total_progress'] / stats['count'], 1)
                    stats['completion_rate'] = round((stats['completed'] / stats['count']) * 100, 1)
            
            return difficulty_stats
            
        except Exception as e:
            logger.error(f"Error analyzing difficulty progress: {str(e)}")
            return {}
    
    def _calculate_engagement_metrics(
        self,
        selections: List[StudentUnitSelection],
        all_student_ids: List[int]
    ) -> Dict[str, Any]:
        """エンゲージメント指標の計算"""
        try:
            active_student_ids = set(s.student_id for s in selections)
            engagement_rate = len(active_student_ids) / len(all_student_ids) if all_student_ids else 0
            
            # 平均アクセス頻度（簡易計算）
            recent_accesses = [
                s for s in selections 
                if s.last_accessed_at and (datetime.now() - s.last_accessed_at).days <= 7
            ]
            
            return {
                'engagement_rate': round(engagement_rate * 100, 1),
                'active_students_this_week': len(set(s.student_id for s in recent_accesses)),
                'average_sessions_per_student': round(len(recent_accesses) / len(active_student_ids) if active_student_ids else 0, 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating engagement metrics: {str(e)}")
            return {}