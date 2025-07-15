"""
承認サービス

学習完了申請の承認・却下・再申請を管理
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.models import db, StudentUnitSelection


class ApprovalService:
    """学習承認管理サービス"""
    
    @staticmethod
    def request_completion(student_id: int, unit_id: int, completion_data: Dict[str, Any] = None) -> bool:
        """学習完了申請"""
        try:
            selection = StudentUnitSelection.query.filter_by(
                student_id=student_id,
                unit_id=unit_id
            ).first()
            
            if not selection:
                current_app.logger.warning(f"No unit selection found for student {student_id}, unit {unit_id}")
                return False
            
            # 進捗率チェック（80%以上必要）
            if (selection.progress_percentage or 0) < 80:
                current_app.logger.warning(f"Insufficient progress for completion request: {selection.progress_percentage}%")
                return False
            
            # 申請状態に変更
            selection.approval_status = 'pending'
            selection.completion_request_date = datetime.utcnow()
            
            # 申請データがあれば保存
            if completion_data:
                selection.completion_notes = completion_data.get('notes', '')
            
            db.session.commit()
            
            current_app.logger.info(f"Completion requested for student {student_id}, unit {unit_id}")
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to request completion: {e}")
            return False
    
    @staticmethod
    def approve_completion(teacher_id: int, selection_id: int, approval_data: Dict[str, Any] = None) -> bool:
        """学習完了を承認"""
        try:
            selection = StudentUnitSelection.query.get(selection_id)
            if not selection:
                return False
            
            if selection.approval_status != 'pending':
                current_app.logger.warning(f"Invalid status for approval: {selection.approval_status}")
                return False
            
            # 承認処理
            selection.approval_status = 'approved'
            selection.approved_at = datetime.utcnow()
            selection.approved_by = teacher_id
            selection.completed_at = datetime.utcnow()
            
            # 承認コメントがあれば保存
            if approval_data and approval_data.get('comment'):
                selection.approval_comment = approval_data['comment']
            
            db.session.commit()
            
            current_app.logger.info(f"Completion approved for selection {selection_id} by teacher {teacher_id}")
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to approve completion: {e}")
            return False
    
    @staticmethod
    def reject_completion(teacher_id: int, selection_id: int, rejection_data: Dict[str, Any]) -> bool:
        """学習完了を却下"""
        try:
            selection = StudentUnitSelection.query.get(selection_id)
            if not selection:
                return False
            
            if selection.approval_status != 'pending':
                current_app.logger.warning(f"Invalid status for rejection: {selection.approval_status}")
                return False
            
            # 却下処理
            selection.approval_status = 'rejected'
            selection.rejected_at = datetime.utcnow()
            selection.rejected_by = teacher_id
            selection.rejection_reason = rejection_data.get('reason', '')
            selection.rejection_date = datetime.utcnow()
            
            db.session.commit()
            
            current_app.logger.info(f"Completion rejected for selection {selection_id} by teacher {teacher_id}")
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to reject completion: {e}")
            return False
    
    @staticmethod
    def resubmit_completion(student_id: int, unit_id: int, resubmit_data: Dict[str, Any] = None) -> bool:
        """学習完了を再申請"""
        try:
            selection = StudentUnitSelection.query.filter_by(
                student_id=student_id,
                unit_id=unit_id
            ).first()
            
            if not selection:
                return False
            
            if selection.approval_status != 'rejected':
                current_app.logger.warning(f"Invalid status for resubmission: {selection.approval_status}")
                return False
            
            # 進捗率チェック（80%以上必要）
            if (selection.progress_percentage or 0) < 80:
                current_app.logger.warning(f"Insufficient progress for resubmission: {selection.progress_percentage}%")
                return False
            
            # 再申請処理
            selection.approval_status = 'pending'
            selection.completion_request_date = datetime.utcnow()
            selection.resubmission_count = (selection.resubmission_count or 0) + 1
            
            # 再申請データがあれば保存
            if resubmit_data:
                selection.completion_notes = resubmit_data.get('notes', '')
                selection.resubmission_notes = resubmit_data.get('improvement_notes', '')
            
            db.session.commit()
            
            current_app.logger.info(f"Completion resubmitted for student {student_id}, unit {unit_id}")
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to resubmit completion: {e}")
            return False
    
    @staticmethod
    def get_pending_approvals(teacher_id: int = None, class_id: int = None) -> List[StudentUnitSelection]:
        """承認待ちの申請一覧を取得"""
        try:
            query = StudentUnitSelection.query.filter_by(approval_status='pending')
            
            # 教師またはクラスでフィルタ
            if class_id:
                from app.models import CurriculumUnit, Curriculum
                query = query.join(CurriculumUnit).join(Curriculum).filter(
                    Curriculum.class_id == class_id
                )
            
            return query.order_by(StudentUnitSelection.completion_request_date.desc()).all()
            
        except SQLAlchemyError as e:
            current_app.logger.error(f"Failed to fetch pending approvals: {e}")
            return []
    
    @staticmethod
    def get_student_approval_history(student_id: int) -> List[StudentUnitSelection]:
        """学生の承認履歴を取得"""
        try:
            return StudentUnitSelection.query.filter_by(
                student_id=student_id
            ).filter(
                StudentUnitSelection.approval_status.in_(['approved', 'rejected'])
            ).order_by(StudentUnitSelection.completion_request_date.desc()).all()
            
        except SQLAlchemyError as e:
            current_app.logger.error(f"Failed to fetch student approval history: {e}")
            return []
    
    @staticmethod
    def get_approval_statistics(class_id: int = None) -> Dict[str, Any]:
        """承認統計を取得"""
        try:
            base_query = StudentUnitSelection.query
            
            if class_id:
                from app.models import CurriculumUnit, Curriculum
                base_query = base_query.join(CurriculumUnit).join(Curriculum).filter(
                    Curriculum.class_id == class_id
                )
            
            total_requests = base_query.filter(
                StudentUnitSelection.completion_request_date.isnot(None)
            ).count()
            
            approved_count = base_query.filter_by(approval_status='approved').count()
            rejected_count = base_query.filter_by(approval_status='rejected').count()
            pending_count = base_query.filter_by(approval_status='pending').count()
            
            # 再申請統計
            resubmissions = base_query.filter(
                StudentUnitSelection.resubmission_count > 0
            ).count()
            
            return {
                'total_requests': total_requests,
                'approved_count': approved_count,
                'rejected_count': rejected_count,
                'pending_count': pending_count,
                'resubmission_count': resubmissions,
                'approval_rate': (approved_count / total_requests * 100) if total_requests > 0 else 0,
                'rejection_rate': (rejected_count / total_requests * 100) if total_requests > 0 else 0
            }
            
        except Exception as e:
            current_app.logger.error(f"Failed to calculate approval statistics: {e}")
            return {
                'total_requests': 0,
                'approved_count': 0,
                'rejected_count': 0,
                'pending_count': 0,
                'resubmission_count': 0,
                'approval_rate': 0,
                'rejection_rate': 0
            }