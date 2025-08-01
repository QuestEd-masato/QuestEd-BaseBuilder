"""
教師承認管理サービス
Phase 7-2: teacher/modules/task_management.py から承認管理機能を分離
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import current_app
from flask_login import current_user

from app.models import (
    Class,
    ClassEnrollment,
    CurriculumUnit,
    StudentUnitSelection,
    User,
    db,
)
from app.services.base_service import BaseService

logger = logging.getLogger(__name__)


class TeacherApprovalService(BaseService):
    """教師承認管理サービス
    
    Phase 7-2: task_management.py から承認管理機能を分離
    Single Responsibility: 教師による学習完了承認・却下処理
    """
    
    def __init__(self):
        super().__init__()
    
    def get_pending_submissions(
        self,
        teacher_classes: List[Class],
        class_filter: Optional[int] = None,
        curriculum_filter: Optional[int] = None,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        承認待ち課題詳細の取得
        Phase 7-2: 元 get_pending_submissions() から移行
        """
        try:
            logger.info(f"Getting pending submissions for teacher {current_user.id}")
            
            # 対象クラスIDの決定
            target_class_ids = self._get_target_class_ids(teacher_classes, class_filter)
            
            # 対象学生IDの取得
            student_ids = self._get_students_in_classes(target_class_ids)
            
            logger.info(f"Target classes: {target_class_ids}, Students: {len(student_ids)}")
            
            pending_submissions = []
            
            # レッスンシステムの完了申請取得
            unit_submissions = self._get_unit_completion_requests(
                student_ids, curriculum_filter, status_filter
            )
            pending_submissions.extend(unit_submissions)
            
            # 提出日時でソート
            pending_submissions = self._sort_submissions_by_date(pending_submissions)
            
            logger.info(f"Retrieved {len(pending_submissions)} pending submissions")
            return pending_submissions
            
        except Exception as e:
            logger.error(f"Error getting pending submissions: {str(e)}")
            return []
    
    def get_submission_detail(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """
        個別提出詳細の取得
        Phase 7-2: 元 submission_detail ルートの処理を移行
        """
        try:
            logger.info(f"Getting submission detail for {submission_id}")
            
            # 提出タイプの判定
            if str(submission_id).startswith('unit_'):
                return self._get_unit_submission_detail(submission_id)
            else:
                logger.warning(f"Unknown submission type for ID: {submission_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting submission detail for {submission_id}: {str(e)}")
            return None
    
    def approve_submission(self, submission_id: str, approval_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        提出承認処理
        Phase 7-2: 元 approve_unit_submission() から移行
        """
        try:
            logger.info(f"Approving submission {submission_id}")
            
            # 提出タイプに応じた承認処理
            if str(submission_id).startswith('unit_'):
                return self._approve_unit_completion(submission_id, approval_data)
            else:
                return {
                    'success': False,
                    'error': '無効な申請IDです'
                }
                
        except Exception as e:
            logger.error(f"Error approving submission {submission_id}: {str(e)}")
            db.session.rollback()
            return {
                'success': False,
                'error': 'システムエラーが発生しました'
            }
    
    def reject_submission(self, submission_id: str, rejection_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        提出却下処理
        Phase 7-2: 元 reject_unit_submission() から移行
        """
        try:
            logger.info(f"Rejecting submission {submission_id}")
            
            # 提出タイプに応じた却下処理
            if str(submission_id).startswith('unit_'):
                return self._reject_unit_completion(submission_id, rejection_data)
            else:
                return {
                    'success': False,
                    'error': '無効な申請IDです'
                }
                
        except Exception as e:
            logger.error(f"Error rejecting submission {submission_id}: {str(e)}")
            db.session.rollback()
            return {
                'success': False,
                'error': 'システムエラーが発生しました'
            }
    
    def batch_approve_submissions(self, submission_ids: List[str], approval_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """一括承認処理"""
        try:
            logger.info(f"Batch approving {len(submission_ids)} submissions")
            
            success_count = 0
            failed_approvals = []
            
            for submission_id in submission_ids:
                result = self.approve_submission(submission_id, approval_data)
                if result['success']:
                    success_count += 1
                else:
                    failed_approvals.append({
                        'submission_id': submission_id,
                        'error': result['error']
                    })
            
            return {
                'success': True,
                'message': f'一括承認完了: {success_count}件成功, {len(failed_approvals)}件失敗',
                'success_count': success_count,
                'failed_count': len(failed_approvals),
                'failed_approvals': failed_approvals
            }
            
        except Exception as e:
            logger.error(f"Error in batch approval: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_approval_history(
        self,
        days_back: int = 30,
        class_filter: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """承認履歴の取得"""
        try:
            logger.info(f"Getting approval history for past {days_back} days")
            
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            # 教師の担当クラス取得
            teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
            target_class_ids = [c.id for c in teacher_classes]
            
            if class_filter:
                target_class_ids = [class_filter] if class_filter in target_class_ids else []
            
            # 対象学生の取得
            student_ids = self._get_students_in_classes(target_class_ids)
            
            # 承認済み・却下済み申請の取得
            approved_units = StudentUnitSelection.query.filter(
                StudentUnitSelection.student_id.in_(student_ids),
                StudentUnitSelection.approved_by == current_user.id,
                StudentUnitSelection.approved_at >= cutoff_date
            ).options(db.joinedload(StudentUnitSelection.curriculum_unit)).all()
            
            history = []
            for unit_selection in approved_units:
                student = User.query.get(unit_selection.student_id)
                unit = unit_selection.curriculum_unit
                
                history_item = {
                    'id': f"unit_{unit_selection.id}",
                    'type': 'unit_completion',
                    'action': 'approved' if unit_selection.approval_status == 'approved' else 'rejected',
                    'student_name': student.full_name or student.username if student else 'Unknown',
                    'student_id': unit_selection.student_id,
                    'unit_title': unit.title if unit else 'Unknown',
                    'unit_id': unit_selection.curriculum_unit_id,
                    'final_progress': unit_selection.progress_percentage,
                    'approved_at': unit_selection.approved_at,
                    'approval_status': unit_selection.approval_status,
                    'rejection_reason': getattr(unit_selection, 'rejection_reason', None)
                }
                history.append(history_item)
            
            # 承認日時でソート（新しい順）
            history.sort(key=lambda x: x['approved_at'] or datetime.min, reverse=True)
            
            logger.info(f"Retrieved {len(history)} approval history items")
            return history
            
        except Exception as e:
            logger.error(f"Error getting approval history: {str(e)}")
            return []
    
    def get_approval_statistics(self) -> Dict[str, Any]:
        """承認統計の取得"""
        try:
            # 教師の担当クラス取得
            teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
            target_class_ids = [c.id for c in teacher_classes]
            student_ids = self._get_students_in_classes(target_class_ids)
            
            # 期間別統計
            today = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)
            
            # 今週の承認数
            this_week_approvals = StudentUnitSelection.query.filter(
                StudentUnitSelection.student_id.in_(student_ids),
                StudentUnitSelection.approved_by == current_user.id,
                StudentUnitSelection.approved_at >= datetime.combine(week_start, datetime.min.time())
            ).count()
            
            # 今月の承認数
            this_month_approvals = StudentUnitSelection.query.filter(
                StudentUnitSelection.student_id.in_(student_ids),
                StudentUnitSelection.approved_by == current_user.id,
                StudentUnitSelection.approved_at >= datetime.combine(month_start, datetime.min.time())
            ).count()
            
            # 全体の承認数
            total_approvals = StudentUnitSelection.query.filter(
                StudentUnitSelection.student_id.in_(student_ids),
                StudentUnitSelection.approved_by == current_user.id,
                StudentUnitSelection.approval_status == 'approved'
            ).count()
            
            # 却下数
            total_rejections = StudentUnitSelection.query.filter(
                StudentUnitSelection.student_id.in_(student_ids),
                StudentUnitSelection.approved_by == current_user.id,
                StudentUnitSelection.approval_status == 'rejected'
            ).count()
            
            # 承認率
            total_decisions = total_approvals + total_rejections
            approval_rate = round((total_approvals / total_decisions * 100) if total_decisions > 0 else 0, 1)
            
            # 平均承認時間（申請から承認までの時間）
            avg_approval_time = self._calculate_average_approval_time(student_ids)
            
            return {
                'this_week_approvals': this_week_approvals,
                'this_month_approvals': this_month_approvals,
                'total_approvals': total_approvals,
                'total_rejections': total_rejections,
                'approval_rate': approval_rate,
                'average_approval_time_hours': avg_approval_time,
                'pending_count': len(self.get_pending_submissions(teacher_classes))
            }
            
        except Exception as e:
            logger.error(f"Error getting approval statistics: {str(e)}")
            return {}
    
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
    
    def _get_unit_completion_requests(
        self,
        student_ids: List[int],
        curriculum_filter: Optional[int] = None,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """単元完了申請の取得"""
        try:
            logger.info(f"Getting unit completion requests for {len(student_ids)} students")
            
            # 基本クエリ: 完了申請済み・承認待ち
            query = StudentUnitSelection.query.filter(
                StudentUnitSelection.student_id.in_(student_ids),
                StudentUnitSelection.approval_status == 'none',
                StudentUnitSelection.completion_request_date.isnot(None)
            )
            
            # カリキュラムフィルター適用
            if curriculum_filter:
                curriculum_unit_ids = db.session.query(CurriculumUnit.id).filter_by(
                    curriculum_id=curriculum_filter
                ).subquery()
                query = query.filter(
                    StudentUnitSelection.curriculum_unit_id.in_(curriculum_unit_ids)
                )
            
            unit_requests = query.options(
                db.joinedload(StudentUnitSelection.curriculum_unit)
            ).all()
            
            logger.info(f"Found {len(unit_requests)} unit completion requests")
            
            submissions = []
            for request in unit_requests:
                try:
                    student = User.query.get(request.student_id)
                    unit = request.curriculum_unit
                    
                    # 期限超過チェック
                    is_overdue = self._is_request_overdue(request.completion_request_date)
                    
                    # 優先度の決定
                    priority = self._determine_request_priority(request, is_overdue)
                    
                    submission_data = {
                        'id': f"unit_{request.id}",
                        'type': 'unit_completion',
                        'task_title': f"{unit.title} 完了申請" if unit else "完了申請",
                        'student_name': student.full_name or student.username if student else "Unknown",
                        'student_id': request.student_id,
                        'submitted_at': request.completion_request_date,
                        'submission_type': 'unit_completion',
                        'content': f"進捗率: {request.progress_percentage}%",
                        'self_evaluation': None,
                        'is_overdue': is_overdue,
                        'priority': priority,
                        'unit_id': request.curriculum_unit_id,
                        'selection_id': request.id,
                        'unit_difficulty': unit.difficulty if unit else None,
                        'unit_order': unit.order if unit else None,
                        'days_since_request': (datetime.now() - request.completion_request_date).days if request.completion_request_date else 0
                    }
                    submissions.append(submission_data)
                    
                except Exception as e:
                    logger.error(f"Error processing unit request {request.id}: {str(e)}")
                    continue
            
            return submissions
            
        except Exception as e:
            logger.error(f"Error getting unit completion requests: {str(e)}")
            return []
    
    def _get_unit_submission_detail(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """単元提出詳細の取得"""
        try:
            unit_selection_id = str(submission_id).replace('unit_', '')
            unit_selection = StudentUnitSelection.query.get(unit_selection_id)
            
            if not unit_selection:
                return None
            
            # 権限チェック
            if not self._can_access_submission(unit_selection.student_id):
                logger.warning(f"Access denied for submission {submission_id}")
                return None
            
            student = User.query.get(unit_selection.student_id)
            unit = unit_selection.curriculum_unit
            
            # 学生統計データ取得
            student_stats = self._get_student_submission_stats(unit_selection.student_id)
            
            # 提出履歴取得
            submission_history = self._get_unit_submission_history(unit_selection)
            
            return {
                'submission_id': submission_id,
                'type': 'unit_completion',
                'unit_selection': unit_selection,
                'unit': unit,
                'student': student,
                'student_stats': student_stats,
                'submission_history': submission_history,
                'can_approve': unit_selection.approval_status == 'none',
                'request_age_days': (datetime.now() - unit_selection.completion_request_date).days if unit_selection.completion_request_date else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting unit submission detail for {submission_id}: {str(e)}")
            return None
    
    def _approve_unit_completion(self, submission_id: str, approval_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """単元完了承認処理"""
        try:
            unit_selection_id = str(submission_id).replace('unit_', '')
            unit_selection = StudentUnitSelection.query.get(unit_selection_id)
            
            if not unit_selection:
                return {'success': False, 'error': '申請が見つかりません'}
            
            # 権限チェック
            if not self._can_access_submission(unit_selection.student_id):
                return {'success': False, 'error': 'アクセス権限がありません'}
            
            # 承認処理
            unit_selection.approval_status = 'approved'
            unit_selection.approved_by = current_user.id
            unit_selection.approved_at = datetime.now()
            
            # 承認コメント（オプション）
            if approval_data and approval_data.get('comment'):
                unit_selection.teacher_comments = approval_data['comment']
            
            db.session.commit()
            
            logger.info(f"Unit completion approved: ID={unit_selection_id}, Student={unit_selection.student_id}, Teacher={current_user.id}")
            
            return {
                'success': True,
                'message': '単元完了申請を承認しました'
            }
            
        except Exception as e:
            logger.error(f"Error approving unit completion {submission_id}: {str(e)}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def _reject_unit_completion(self, submission_id: str, rejection_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """単元完了却下処理"""
        try:
            unit_selection_id = str(submission_id).replace('unit_', '')
            unit_selection = StudentUnitSelection.query.get(unit_selection_id)
            
            if not unit_selection:
                return {'success': False, 'error': '申請が見つかりません'}
            
            # 権限チェック
            if not self._can_access_submission(unit_selection.student_id):
                return {'success': False, 'error': 'アクセス権限がありません'}
            
            # 却下処理
            unit_selection.approval_status = 'rejected'
            unit_selection.approved_by = current_user.id
            unit_selection.approved_at = datetime.now()
            unit_selection.completion_request_date = None  # 再申請を可能にする
            
            # 却下理由の保存
            if rejection_data and rejection_data.get('reason'):
                unit_selection.rejection_reason = rejection_data['reason']
                unit_selection.rejection_date = datetime.now()
            
            # 教師コメント
            if rejection_data and rejection_data.get('comment'):
                unit_selection.teacher_comments = rejection_data['comment']
            
            db.session.commit()
            
            logger.info(f"Unit completion rejected: ID={unit_selection_id}, Student={unit_selection.student_id}, Teacher={current_user.id}")
            
            return {
                'success': True,
                'message': '単元完了申請を却下しました'
            }
            
        except Exception as e:
            logger.error(f"Error rejecting unit completion {submission_id}: {str(e)}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def _can_access_submission(self, student_id: int) -> bool:
        """提出へのアクセス権限チェック"""
        try:
            # 教師が担当するクラスの学生かチェック
            teacher_classes = Class.query.filter_by(teacher_id=current_user.id).all()
            teacher_class_ids = [c.id for c in teacher_classes]
            
            student_classes = ClassEnrollment.query.filter_by(student_id=student_id).all()
            student_class_ids = [sc.class_id for sc in student_classes]
            
            return any(class_id in teacher_class_ids for class_id in student_class_ids)
            
        except Exception as e:
            logger.error(f"Error checking submission access for student {student_id}: {str(e)}")
            return False
    
    def _sort_submissions_by_date(self, submissions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提出を日時でソート"""
        try:
            return sorted(
                submissions,
                key=lambda x: x['submitted_at'] or datetime.min,
                reverse=True
            )
        except Exception as e:
            logger.error(f"Error sorting submissions: {str(e)}")
            return submissions
    
    def _is_request_overdue(self, request_date: Optional[datetime]) -> bool:
        """申請が期限超過かどうかの判定"""
        if not request_date:
            return False
        
        # 3日以上経過した申請を期限超過とする
        days_since_request = (datetime.now() - request_date).days
        return days_since_request > 3
    
    def _determine_request_priority(self, request: StudentUnitSelection, is_overdue: bool) -> str:
        """申請の優先度決定"""
        try:
            if is_overdue:
                return 'high'
            
            # 高難易度単元は優先度高
            if request.curriculum_unit and request.curriculum_unit.difficulty >= 4:
                return 'high'
            
            # 進捗率が高い申請は優先度中
            if request.progress_percentage >= 95:
                return 'medium'
            
            return 'low'
            
        except Exception as e:
            logger.error(f"Error determining priority for request {request.id}: {str(e)}")
            return 'low'
    
    def _get_student_submission_stats(self, student_id: int) -> Dict[str, Any]:
        """学生の提出統計取得"""
        try:
            # 学生の全単元選択を取得
            selections = StudentUnitSelection.query.filter_by(student_id=student_id).all()
            
            total_selections = len(selections)
            completed_selections = len([s for s in selections if s.approval_status == 'approved'])
            rejected_selections = len([s for s in selections if s.approval_status == 'rejected'])
            pending_selections = len([s for s in selections if s.completion_request_date and s.approval_status == 'none'])
            
            # 平均進捗率
            avg_progress = sum(s.progress_percentage for s in selections) / total_selections if total_selections > 0 else 0
            
            # 完了率
            completion_rate = (completed_selections / total_selections * 100) if total_selections > 0 else 0
            
            # 承認率（申請したもののうち承認された割合）
            total_submitted = completed_selections + rejected_selections
            approval_rate = (completed_selections / total_submitted * 100) if total_submitted > 0 else 0
            
            # クラス情報
            enrollment = ClassEnrollment.query.filter_by(student_id=student_id).first()
            class_name = None
            if enrollment:
                class_obj = Class.query.get(enrollment.class_id)
                class_name = class_obj.name if class_obj else None
            
            return {
                'total_units': total_selections,
                'completed_units': completed_selections,
                'rejected_units': rejected_selections,
                'pending_approvals': pending_selections,
                'average_progress': round(avg_progress, 1),
                'completion_rate': round(completion_rate, 1),
                'approval_rate': round(approval_rate, 1),
                'class_name': class_name
            }
            
        except Exception as e:
            logger.error(f"Error getting student submission stats for student {student_id}: {str(e)}")
            return {}
    
    def _get_unit_submission_history(self, unit_selection: StudentUnitSelection) -> List[Dict[str, Any]]:
        """単元提出履歴の取得"""
        try:
            history = []
            
            # 選択開始
            if unit_selection.selected_at:
                history.append({
                    'timestamp': unit_selection.selected_at,
                    'action': '単元選択',
                    'description': '学習開始',
                    'actor': '学生'
                })
            
            # 最終アクセス
            if unit_selection.last_accessed_at and unit_selection.last_accessed_at != unit_selection.selected_at:
                history.append({
                    'timestamp': unit_selection.last_accessed_at,
                    'action': '学習活動',
                    'description': f'進捗: {unit_selection.progress_percentage}%',
                    'actor': '学生'
                })
            
            # 完了申請
            if unit_selection.completion_request_date:
                history.append({
                    'timestamp': unit_selection.completion_request_date,
                    'action': '完了申請',
                    'description': '教師承認待ち',
                    'actor': '学生'
                })
            
            # 承認・却下
            if unit_selection.approved_at:
                action = '承認' if unit_selection.approval_status == 'approved' else '却下'
                description = unit_selection.teacher_comments or ('正式完了' if action == '承認' else '再学習が必要')
                
                history.append({
                    'timestamp': unit_selection.approved_at,
                    'action': action,
                    'description': description,
                    'actor': '教師'
                })
            
            return sorted(history, key=lambda x: x['timestamp'] or datetime.min)
            
        except Exception as e:
            logger.error(f"Error getting unit submission history: {str(e)}")
            return []
    
    def _calculate_average_approval_time(self, student_ids: List[int]) -> float:
        """平均承認時間の計算（時間単位）"""
        try:
            approved_selections = StudentUnitSelection.query.filter(
                StudentUnitSelection.student_id.in_(student_ids),
                StudentUnitSelection.approved_by == current_user.id,
                StudentUnitSelection.completion_request_date.isnot(None),
                StudentUnitSelection.approved_at.isnot(None)
            ).all()
            
            if not approved_selections:
                return 0.0
            
            total_hours = 0
            for selection in approved_selections:
                time_diff = selection.approved_at - selection.completion_request_date
                total_hours += time_diff.total_seconds() / 3600  # 秒を時間に変換
            
            avg_hours = total_hours / len(approved_selections)
            return round(avg_hours, 1)
            
        except Exception as e:
            logger.error(f"Error calculating average approval time: {str(e)}")
            return 0.0