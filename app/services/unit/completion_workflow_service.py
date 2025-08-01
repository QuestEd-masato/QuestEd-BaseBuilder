# -*- coding: utf-8 -*-
"""
CompletionWorkflowService

完了申請・承認ワークフロー専門サービス
CompletionRequestManager + ApprovalManager + 関連ルートロジックを統合
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask_login import current_user

from app.models import (
    CurriculumUnit, StudentUnitSelection, db
)
from app.services.unit_completion_service import UnitCompletionService

logger = logging.getLogger(__name__)


class CompletionWorkflowService:
    """完了ワークフロー専門サービス"""

    def __init__(self):
        self.completion_service = UnitCompletionService()

    def request_unit_completion(self, unit_id: int, completion_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        単元完了申請
        
        Args:
            unit_id: 単元ID
            completion_data: 完了データ（オプション）
            
        Returns:
            Dict: 申請結果
        """
        try:
            logger.info(f"Unit completion request for unit {unit_id} by student {current_user.id}")
            
            # 単元の存在確認
            unit = CurriculumUnit.query.get(unit_id)
            if not unit:
                return {
                    "success": False,
                    "message": "指定された単元が見つかりません"
                }

            # 学生の選択レコード確認
            selection = StudentUnitSelection.query.filter_by(
                unit_id=unit_id,
                student_id=current_user.id
            ).first()
            
            if not selection:
                return {
                    "success": False,
                    "message": "この単元を選択していません"
                }

            # 完了申請の前提条件チェック
            validation_result = self._validate_completion_request(selection, unit)
            if not validation_result['valid']:
                return {
                    "success": False,
                    "message": validation_result['message']
                }

            # UnitCompletionServiceに委譲
            result = self.completion_service.request_completion(
                selection_id=selection.id,
                completion_data=completion_data or {}
            )
            
            return result

        except Exception as e:
            logger.error(f"Error in unit completion request: {str(e)}")
            return {
                "success": False,
                "message": f"完了申請中にエラーが発生しました: {str(e)}"
            }

    def request_curriculum_completion(self, curriculum_id: int, 
                                   completion_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        カリキュラム完了申請
        
        Args:
            curriculum_id: カリキュラムID
            completion_data: 完了データ（オプション）
            
        Returns:
            Dict: 申請結果
        """
        try:
            logger.info(f"Curriculum completion request for curriculum {curriculum_id} by student {current_user.id}")
            
            # カリキュラムの存在確認
            curriculum = self._get_curriculum(curriculum_id)
            if not curriculum:
                return {
                    "success": False,
                    "message": "指定されたカリキュラムが見つかりません"
                }

            # カリキュラム完了条件チェック
            validation_result = self._validate_curriculum_completion(curriculum)
            if not validation_result['valid']:
                return {
                    "success": False,
                    "message": validation_result['message']
                }

            # レッスンシステムとの連携
            lesson_completion_result = self._handle_lesson_completion(curriculum_id, completion_data)
            
            return lesson_completion_result

        except Exception as e:
            logger.error(f"Error in curriculum completion request: {str(e)}")
            return {
                "success": False,
                "message": f"カリキュラム完了申請中にエラーが発生しました: {str(e)}"
            }

    def resubmit_completion(self, unit_id: int, resubmit_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        完了再申請
        
        Args:
            unit_id: 単元ID
            resubmit_data: 再申請データ
            
        Returns:
            Dict: 再申請結果
        """
        try:
            logger.info(f"Completion resubmission for unit {unit_id} by student {current_user.id}")
            
            # 学生の選択レコード確認
            selection = StudentUnitSelection.query.filter_by(
                unit_id=unit_id,
                student_id=current_user.id
            ).first()
            
            if not selection:
                return {
                    "success": False,
                    "message": "この単元を選択していません"
                }

            # 再申請の前提条件チェック
            if selection.status not in ['rejected', 'revision_requested']:
                return {
                    "success": False,
                    "message": "再申請できる状態ではありません"
                }

            # UnitCompletionServiceに委譲
            result = self.completion_service.resubmit_completion(
                selection_id=selection.id,
                resubmit_data=resubmit_data
            )
            
            return result

        except Exception as e:
            logger.error(f"Error in completion resubmission: {str(e)}")
            return {
                "success": False,
                "message": f"再申請中にエラーが発生しました: {str(e)}"
            }

    def get_pending_approvals(self, teacher_id: Optional[int] = None) -> Dict[str, Any]:
        """
        承認待ち一覧取得
        
        Args:
            teacher_id: 教師ID（指定されない場合は現在のユーザー）
            
        Returns:
            Dict: 承認待ち一覧
        """
        try:
            target_teacher_id = teacher_id or current_user.id
            logger.info(f"Getting pending approvals for teacher {target_teacher_id}")
            
            # 承認権限チェック
            if current_user.role not in ['teacher', 'admin']:
                return {
                    "success": False,
                    "message": "承認権限がありません"
                }

            # UnitCompletionServiceに委譲
            result = self.completion_service.get_pending_approvals(teacher_id=target_teacher_id)
            
            return result

        except Exception as e:
            logger.error(f"Error getting pending approvals: {str(e)}")
            return {
                "success": False,
                "message": f"承認待ち一覧の取得中にエラーが発生しました: {str(e)}"
            }

    def approve_completion(self, selection_id: int, approval_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        完了承認
        
        Args:
            selection_id: 選択ID
            approval_data: 承認データ
            
        Returns:
            Dict: 承認結果
        """
        try:
            logger.info(f"Approving completion for selection {selection_id} by teacher {current_user.id}")
            
            # 承認権限チェック
            if current_user.role not in ['teacher', 'admin']:
                return {
                    "success": False,
                    "message": "承認権限がありません"
                }

            # UnitCompletionServiceに委譲
            result = self.completion_service.approve_completion(
                selection_id=selection_id,
                teacher_id=current_user.id,
                approval_data=approval_data
            )
            
            return result

        except Exception as e:
            logger.error(f"Error approving completion: {str(e)}")
            return {
                "success": False,
                "message": f"承認処理中にエラーが発生しました: {str(e)}"
            }

    def reject_completion(self, selection_id: int, rejection_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        完了却下
        
        Args:
            selection_id: 選択ID
            rejection_data: 却下データ
            
        Returns:
            Dict: 却下結果
        """
        try:
            logger.info(f"Rejecting completion for selection {selection_id} by teacher {current_user.id}")
            
            # 承認権限チェック
            if current_user.role not in ['teacher', 'admin']:
                return {
                    "success": False,
                    "message": "承認権限がありません"
                }

            # UnitCompletionServiceに委譲
            result = self.completion_service.reject_completion(
                selection_id=selection_id,
                teacher_id=current_user.id,
                rejection_data=rejection_data
            )
            
            return result

        except Exception as e:
            logger.error(f"Error rejecting completion: {str(e)}")
            return {
                "success": False,
                "message": f"却下処理中にエラーが発生しました: {str(e)}"
            }

    def batch_approve_completions(self, approval_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        完了一括承認
        
        Args:
            approval_list: 承認リスト
            
        Returns:
            Dict: 一括承認結果
        """
        try:
            logger.info(f"Batch approving {len(approval_list)} completions by teacher {current_user.id}")
            
            # 承認権限チェック
            if current_user.role not in ['teacher', 'admin']:
                return {
                    "success": False,
                    "message": "承認権限がありません"
                }

            successful_approvals = []
            failed_approvals = []
            
            for approval_data in approval_list:
                selection_id = approval_data.get('selection_id')
                if not selection_id:
                    failed_approvals.append({
                        "selection_id": None,
                        "error": "selection_idが指定されていません"
                    })
                    continue
                
                try:
                    result = self.approve_completion(selection_id, approval_data)
                    if result['success']:
                        successful_approvals.append({
                            "selection_id": selection_id,
                            "result": result
                        })
                    else:
                        failed_approvals.append({
                            "selection_id": selection_id,
                            "error": result['message']
                        })
                        
                except Exception as e:
                    failed_approvals.append({
                        "selection_id": selection_id,
                        "error": str(e)
                    })
            
            return {
                "success": len(failed_approvals) == 0,
                "successful_approvals": successful_approvals,
                "failed_approvals": failed_approvals,
                "total_processed": len(approval_list),
                "success_count": len(successful_approvals),
                "failure_count": len(failed_approvals)
            }

        except Exception as e:
            logger.error(f"Error in batch approval: {str(e)}")
            return {
                "success": False,
                "message": f"一括承認中にエラーが発生しました: {str(e)}"
            }

    def get_approval_statistics(self, teacher_id: Optional[int] = None) -> Dict[str, Any]:
        """
        承認統計情報取得
        
        Args:
            teacher_id: 教師ID（指定されない場合は現在のユーザー）
            
        Returns:
            Dict: 統計情報
        """
        try:
            target_teacher_id = teacher_id or current_user.id
            logger.info(f"Getting approval statistics for teacher {target_teacher_id}")
            
            # 統計権限チェック
            if current_user.role not in ['teacher', 'admin']:
                return {
                    "success": False,
                    "message": "統計閲覧権限がありません"
                }

            # UnitCompletionServiceに委譲
            result = self.completion_service.get_approval_statistics(teacher_id=target_teacher_id)
            
            return result

        except Exception as e:
            logger.error(f"Error getting approval statistics: {str(e)}")
            return {
                "success": False,
                "message": f"統計情報の取得中にエラーが発生しました: {str(e)}"
            }

    def _validate_completion_request(self, selection: StudentUnitSelection, 
                                   unit: CurriculumUnit) -> Dict[str, Any]:
        """完了申請の前提条件チェック"""
        # 既に完了済みの場合
        if selection.status == 'completed':
            return {
                "valid": False,
                "message": "この単元は既に完了しています"
            }
        
        # 申請済みの場合
        if selection.status in ['pending_approval', 'submitted']:
            return {
                "valid": False,
                "message": "この単元は既に完了申請済みです"
            }
        
        # 進捗が不十分な場合
        if not selection.progress_percentage or selection.progress_percentage < 80:
            return {
                "valid": False,
                "message": "完了申請には80%以上の進捗が必要です"
            }
        
        return {"valid": True}

    def _validate_curriculum_completion(self, curriculum) -> Dict[str, Any]:
        """カリキュラム完了条件チェック"""
        # 基本的な存在チェック
        if not curriculum:
            return {
                "valid": False,
                "message": "カリキュラムが見つかりません"
            }
        
        # 追加の完了条件チェックはここに実装
        return {"valid": True}

    def _get_curriculum(self, curriculum_id: int):
        """カリキュラム取得"""
        try:
            from app.models import Curriculum
            return Curriculum.query.get(curriculum_id)
        except ImportError:
            return None

    def _handle_lesson_completion(self, curriculum_id: int, completion_data: Dict[str, Any]) -> Dict[str, Any]:
        """レッスン完了処理"""
        try:
            # レッスンシステムとの連携ロジック
            # 実際の実装は requirements に基づいて調整
            return {
                "success": True,
                "message": "カリキュラム完了申請が正常に処理されました",
                "curriculum_id": curriculum_id
            }
        except Exception as e:
            logger.error(f"Error in lesson completion handling: {str(e)}")
            return {
                "success": False,
                "message": f"レッスン完了処理中にエラーが発生しました: {str(e)}"
            }