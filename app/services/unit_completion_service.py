"""
QuestEd 単元完了申請・承認サービス

単元完了の申請、承認、却下の処理を管理し、
教師の承認ワークフローを提供します。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import and_, or_, func, desc
from flask import current_app

from extensions import db
from app.models import (
    StudentUnitSelection, CurriculumUnit, User, Class, ClassLearningSettings
)

logger = logging.getLogger(__name__)


class UnitCompletionService:
    """単元完了申請・承認サービス"""
    
    @staticmethod
    def request_completion(student_id: int, unit_id: int, class_id: int = None, notes: str = None) -> Dict[str, any]:
        """
        単元完了申請を送信
        
        Args:
            student_id: 学生ID
            unit_id: 単元ID
            class_id: クラスID (オプション)
            notes: 申請メモ
            
        Returns:
            申請結果
        """
        try:
            # 単元選択履歴を取得
            selection = StudentUnitSelection.query.filter_by(
                student_id=student_id,
                unit_id=unit_id,
                class_id=class_id
            ).first()
            
            if not selection:
                return {
                    'success': False,
                    'message': 'この単元は選択されていません',
                    'error_type': 'not_selected'
                }
            
            # 申請可能性チェック
            if not selection.can_request_completion():
                return {
                    'success': False,
                    'message': '申請条件を満たしていません（進捗率80%以上必要）',
                    'error_type': 'insufficient_progress',
                    'current_progress': float(selection.progress_percentage)
                }
            
            # クラス設定を確認
            class_settings = None
            if class_id:
                class_settings = ClassLearningSettings.query.filter_by(class_id=class_id).first()
            
            # 自動承認判定
            auto_approve = False
            if class_settings and not class_settings.require_teacher_approval:
                auto_approve = True
            elif (class_settings and 
                  class_settings.auto_approve_threshold and 
                  selection.progress_percentage >= class_settings.auto_approve_threshold):
                auto_approve = True
            
            if auto_approve:
                # 自動承認
                selection.approval_status = 'approved'
                selection.approved_at = datetime.utcnow()
                selection.status = 'completed'
                if not selection.completed_at:
                    selection.completed_at = datetime.utcnow()
                message = '自動承認により単元完了が確定しました'
            else:
                # 手動承認申請
                selection.request_completion(notes)
                message = '完了申請を送信しました。教師の承認をお待ちください'
            
            db.session.commit()
            
            logger.info(f"Unit completion requested: student_id={student_id}, unit_id={unit_id}, auto_approve={auto_approve}")
            
            return {
                'success': True,
                'message': message,
                'auto_approved': auto_approve,
                'approval_status': selection.approval_status,
                'selection_data': selection.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to request unit completion: {str(e)}")
            return {
                'success': False,
                'message': f'申請中にエラーが発生しました: {str(e)}',
                'error_type': 'system_error'
            }
    
    @staticmethod
    def approve_completion(selection_id: int, teacher_id: int, comments: str = None) -> Dict[str, any]:
        """
        単元完了申請を承認
        
        Args:
            selection_id: 選択履歴ID
            teacher_id: 教師ID
            comments: 承認コメント
            
        Returns:
            承認結果
        """
        try:
            selection = StudentUnitSelection.query.get(selection_id)
            if not selection:
                return {
                    'success': False,
                    'message': '申請が見つかりません',
                    'error_type': 'not_found'
                }
            
            if selection.approval_status != 'pending':
                return {
                    'success': False,
                    'message': 'この申請は既に処理済みです',
                    'error_type': 'already_processed'
                }
            
            # 承認実行
            selection.approve_completion(teacher_id, comments)
            db.session.commit()
            
            logger.info(f"Unit completion approved: selection_id={selection_id}, teacher_id={teacher_id}")
            
            return {
                'success': True,
                'message': '単元完了を承認しました',
                'selection_data': selection.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to approve unit completion: {str(e)}")
            return {
                'success': False,
                'message': f'承認中にエラーが発生しました: {str(e)}',
                'error_type': 'system_error'
            }
    
    @staticmethod
    def reject_completion(selection_id: int, teacher_id: int, reason: str) -> Dict[str, any]:
        """
        単元完了申請を却下
        
        Args:
            selection_id: 選択履歴ID
            teacher_id: 教師ID
            reason: 却下理由
            
        Returns:
            却下結果
        """
        try:
            selection = StudentUnitSelection.query.get(selection_id)
            if not selection:
                return {
                    'success': False,
                    'message': '申請が見つかりません',
                    'error_type': 'not_found'
                }
            
            if selection.approval_status != 'pending':
                return {
                    'success': False,
                    'message': 'この申請は既に処理済みです',
                    'error_type': 'already_processed'
                }
            
            if not reason or len(reason.strip()) < 5:
                return {
                    'success': False,
                    'message': '却下理由は5文字以上入力してください',
                    'error_type': 'invalid_reason'
                }
            
            # 却下実行
            selection.reject_completion(teacher_id, reason)
            db.session.commit()
            
            logger.info(f"Unit completion rejected: selection_id={selection_id}, teacher_id={teacher_id}")
            
            return {
                'success': True,
                'message': '申請を却下しました',
                'selection_data': selection.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to reject unit completion: {str(e)}")
            return {
                'success': False,
                'message': f'却下処理中にエラーが発生しました: {str(e)}',
                'error_type': 'system_error'
            }
    
    @staticmethod
    def get_pending_approvals(teacher_id: int, class_id: int = None, limit: int = 50) -> Dict[str, any]:
        """
        承認待ち申請一覧を取得
        
        Args:
            teacher_id: 教師ID
            class_id: クラスID (指定時はそのクラスのみ)
            limit: 取得件数上限
            
        Returns:
            承認待ち申請一覧
        """
        try:
            # 基本クエリ
            query = db.session.query(StudentUnitSelection).join(
                CurriculumUnit, StudentUnitSelection.unit_id == CurriculumUnit.id
            ).join(
                User, StudentUnitSelection.student_id == User.id
            ).filter(
                StudentUnitSelection.approval_status == 'pending'
            )
            
            # クラスフィルタ
            if class_id:
                query = query.filter(StudentUnitSelection.class_id == class_id)
            else:
                # 教師の担当クラスのみ
                query = query.join(
                    Class, StudentUnitSelection.class_id == Class.id
                ).filter(Class.teacher_id == teacher_id)
            
            # 申請日時の降順でソート
            selections = query.order_by(
                desc(StudentUnitSelection.completion_request_date)
            ).limit(limit).all()
            
            # 詳細データ構築
            approval_list = []
            for selection in selections:
                unit_data = selection.curriculum_unit.to_dict()
                student_data = {
                    'id': selection.student.id,
                    'username': selection.student.username,
                    'full_name': selection.student.full_name
                }
                
                approval_list.append({
                    'selection': selection.to_dict(),
                    'unit': unit_data,
                    'student': student_data,
                    'days_pending': (datetime.utcnow() - selection.completion_request_date).days
                })
            
            return {
                'success': True,
                'pending_approvals': approval_list,
                'total_count': len(approval_list)
            }
            
        except Exception as e:
            logger.error(f"Failed to get pending approvals: {str(e)}")
            return {
                'success': False,
                'message': f'承認待ち一覧の取得に失敗しました: {str(e)}',
                'pending_approvals': []
            }
    
    @staticmethod
    def get_approval_statistics(teacher_id: int, days: int = 30) -> Dict[str, any]:
        """
        承認統計を取得
        
        Args:
            teacher_id: 教師ID
            days: 集計期間（日数）
            
        Returns:
            承認統計データ
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # 教師の担当クラス
            teacher_classes = Class.query.filter_by(teacher_id=teacher_id).all()
            class_ids = [c.id for c in teacher_classes]
            
            if not class_ids:
                return {
                    'success': True,
                    'statistics': {
                        'total_requests': 0,
                        'approved_count': 0,
                        'rejected_count': 0,
                        'pending_count': 0,
                        'approval_rate': 0.0
                    }
                }
            
            # 承認統計クエリ
            total_requests = StudentUnitSelection.query.filter(
                and_(
                    StudentUnitSelection.class_id.in_(class_ids),
                    StudentUnitSelection.completion_request_date >= start_date,
                    StudentUnitSelection.approval_status.in_(['approved', 'rejected', 'pending'])
                )
            ).count()
            
            approved_count = StudentUnitSelection.query.filter(
                and_(
                    StudentUnitSelection.class_id.in_(class_ids),
                    StudentUnitSelection.completion_request_date >= start_date,
                    StudentUnitSelection.approval_status == 'approved'
                )
            ).count()
            
            rejected_count = StudentUnitSelection.query.filter(
                and_(
                    StudentUnitSelection.class_id.in_(class_ids),
                    StudentUnitSelection.completion_request_date >= start_date,
                    StudentUnitSelection.approval_status == 'rejected'
                )
            ).count()
            
            pending_count = StudentUnitSelection.query.filter(
                and_(
                    StudentUnitSelection.class_id.in_(class_ids),
                    StudentUnitSelection.approval_status == 'pending'
                )
            ).count()
            
            # 承認率計算
            approval_rate = (approved_count / (approved_count + rejected_count) * 100) if (approved_count + rejected_count) > 0 else 0.0
            
            return {
                'success': True,
                'statistics': {
                    'total_requests': total_requests,
                    'approved_count': approved_count,
                    'rejected_count': rejected_count,
                    'pending_count': pending_count,
                    'approval_rate': round(approval_rate, 1),
                    'period_days': days
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get approval statistics: {str(e)}")
            return {
                'success': False,
                'message': f'統計データの取得に失敗しました: {str(e)}',
                'statistics': {}
            }
    
    @staticmethod
    def batch_approve(selection_ids: List[int], teacher_id: int, comments: str = None) -> Dict[str, any]:
        """
        一括承認処理
        
        Args:
            selection_ids: 選択履歴IDリスト
            teacher_id: 教師ID
            comments: 承認コメント
            
        Returns:
            一括承認結果
        """
        try:
            approved_count = 0
            failed_count = 0
            failed_selections = []
            
            for selection_id in selection_ids:
                result = UnitCompletionService.approve_completion(selection_id, teacher_id, comments)
                if result['success']:
                    approved_count += 1
                else:
                    failed_count += 1
                    failed_selections.append({
                        'selection_id': selection_id,
                        'error': result.get('message', '不明なエラー')
                    })
            
            return {
                'success': True,
                'approved_count': approved_count,
                'failed_count': failed_count,
                'failed_selections': failed_selections,
                'message': f'{approved_count}件の申請を承認しました'
            }
            
        except Exception as e:
            logger.error(f"Failed to batch approve: {str(e)}")
            return {
                'success': False,
                'message': f'一括承認中にエラーが発生しました: {str(e)}',
                'approved_count': 0,
                'failed_count': len(selection_ids)
            }
    
    @staticmethod
    def get_student_completion_history(student_id: int, limit: int = 20) -> Dict[str, any]:
        """
        学生の完了履歴を取得
        
        Args:
            student_id: 学生ID
            limit: 取得件数上限
            
        Returns:
            完了履歴データ
        """
        try:
            # 承認済み単元を取得
            approved_selections = StudentUnitSelection.query.filter(
                and_(
                    StudentUnitSelection.student_id == student_id,
                    StudentUnitSelection.approval_status == 'approved'
                )
            ).order_by(desc(StudentUnitSelection.approved_at)).limit(limit).all()
            
            history_list = []
            for selection in approved_selections:
                unit_data = selection.curriculum_unit.to_dict()
                approver_name = selection.approver.full_name if selection.approver else '自動承認'
                
                history_list.append({
                    'selection': selection.to_dict(),
                    'unit': unit_data,
                    'approver_name': approver_name
                })
            
            return {
                'success': True,
                'completion_history': history_list,
                'total_completed': len(history_list)
            }
            
        except Exception as e:
            logger.error(f"Failed to get completion history: {str(e)}")
            return {
                'success': False,
                'message': f'完了履歴の取得に失敗しました: {str(e)}',
                'completion_history': []
            }