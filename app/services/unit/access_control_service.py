# -*- coding: utf-8 -*-
"""
AccessControlService

アクセス制御・権限管理専門サービス
散在していた権限チェックロジックを統一・一元化
"""
import logging
from typing import Any, Dict, List, Optional

from flask_login import current_user

from app.models import (
    CurriculumUnit, StudentUnitSelection, ClassEnrollment, db
)

logger = logging.getLogger(__name__)


class AccessControlService:
    """アクセス制御専門サービス"""

    def check_unit_access_permission(self, unit_id: int, 
                                   action: str = 'read') -> Dict[str, Any]:
        """
        単元へのアクセス権限をチェック
        
        Args:
            unit_id: 単元ID
            action: アクション ('read', 'write', 'delete', 'select')
            
        Returns:
            Dict: 権限チェック結果
        """
        try:
            logger.info(f"Checking unit access permission for unit {unit_id}, action {action}, user {current_user.id}")
            
            # 認証チェック
            if not current_user.is_authenticated:
                return {
                    "allowed": False,
                    "reason": "認証が必要です",
                    "error_code": "AUTH_REQUIRED"
                }

            # 単元の存在確認
            unit = CurriculumUnit.query.get(unit_id)
            if not unit:
                return {
                    "allowed": False,
                    "reason": "指定された単元が見つかりません",
                    "error_code": "UNIT_NOT_FOUND"
                }

            # 単元の有効性チェック
            if not unit.is_active:
                return {
                    "allowed": False,
                    "reason": "この単元は無効化されています",
                    "error_code": "UNIT_INACTIVE"
                }

            # 役割ベースの権限チェック
            role_check = self._check_role_based_permission(unit, action)
            if not role_check['allowed']:
                return role_check

            # アクション固有の権限チェック
            action_check = self._check_action_specific_permission(unit, action)
            if not action_check['allowed']:
                return action_check

            return {
                "allowed": True,
                "reason": "アクセス権限が確認されました",
                "unit_info": {
                    "id": unit.id,
                    "title": unit.title,
                    "subject_id": unit.subject_id
                }
            }

        except Exception as e:
            logger.error(f"Error checking unit access permission: {str(e)}")
            return {
                "allowed": False,
                "reason": f"権限チェック中にエラーが発生しました: {str(e)}",
                "error_code": "PERMISSION_CHECK_ERROR"
            }

    def check_curriculum_access_permission(self, curriculum_id: int, 
                                         action: str = 'read') -> Dict[str, Any]:
        """
        カリキュラムへのアクセス権限をチェック
        
        Args:
            curriculum_id: カリキュラムID
            action: アクション
            
        Returns:
            Dict: 権限チェック結果
        """
        try:
            logger.info(f"Checking curriculum access permission for curriculum {curriculum_id}")
            
            # 認証チェック
            if not current_user.is_authenticated:
                return {
                    "allowed": False,
                    "reason": "認証が必要です",
                    "error_code": "AUTH_REQUIRED"
                }

            # カリキュラムの存在確認
            curriculum = self._get_curriculum(curriculum_id)
            if not curriculum:
                return {
                    "allowed": False,
                    "reason": "指定されたカリキュラムが見つかりません",
                    "error_code": "CURRICULUM_NOT_FOUND"
                }

            # 学生の場合：所属クラスのカリキュラムかチェック
            if current_user.role == 'student':
                class_access = self._check_student_class_access(curriculum)
                if not class_access['allowed']:
                    return class_access

            # 教師の場合：担当カリキュラムかチェック
            elif current_user.role == 'teacher':
                teacher_access = self._check_teacher_curriculum_access(curriculum)
                if not teacher_access['allowed']:
                    return teacher_access

            # 管理者は全アクセス可能
            elif current_user.role == 'admin':
                pass
            
            else:
                return {
                    "allowed": False,
                    "reason": "不明な役割です",
                    "error_code": "UNKNOWN_ROLE"
                }

            return {
                "allowed": True,
                "reason": "カリキュラムアクセス権限が確認されました",
                "curriculum_info": {
                    "id": curriculum.id,
                    "title": curriculum.title
                }
            }

        except Exception as e:
            logger.error(f"Error checking curriculum access permission: {str(e)}")
            return {
                "allowed": False,
                "reason": f"カリキュラム権限チェック中にエラーが発生しました: {str(e)}",
                "error_code": "CURRICULUM_PERMISSION_ERROR"
            }

    def check_unit_selection_permission(self, unit_id: int) -> Dict[str, Any]:
        """
        単元選択権限をチェック
        
        Args:
            unit_id: 単元ID
            
        Returns:
            Dict: 選択権限チェック結果
        """
        try:
            logger.info(f"Checking unit selection permission for unit {unit_id}")
            
            # 基本的なアクセス権限チェック
            access_check = self.check_unit_access_permission(unit_id, 'select')
            if not access_check['allowed']:
                return access_check

            # 学生のみ選択可能
            if current_user.role != 'student':
                return {
                    "allowed": False,
                    "reason": "単元選択は学生のみ可能です",
                    "error_code": "STUDENT_ONLY"
                }

            # 既に選択済みかチェック
            existing_selection = StudentUnitSelection.query.filter_by(
                unit_id=unit_id,
                student_id=current_user.id
            ).first()

            if existing_selection:
                return {
                    "allowed": False,
                    "reason": "この単元は既に選択済みです",
                    "error_code": "ALREADY_SELECTED",
                    "existing_selection": {
                        "id": existing_selection.id,
                        "status": existing_selection.status,
                        "selected_at": existing_selection.selected_at.isoformat() if existing_selection.selected_at else None
                    }
                }

            # 選択数制限チェック
            selection_limit_check = self._check_selection_limits()
            if not selection_limit_check['allowed']:
                return selection_limit_check

            return {
                "allowed": True,
                "reason": "単元選択権限が確認されました"
            }

        except Exception as e:
            logger.error(f"Error checking unit selection permission: {str(e)}")
            return {
                "allowed": False,
                "reason": f"選択権限チェック中にエラーが発生しました: {str(e)}",
                "error_code": "SELECTION_PERMISSION_ERROR"
            }

    def check_completion_approval_permission(self, selection_id: int) -> Dict[str, Any]:
        """
        完了承認権限をチェック
        
        Args:
            selection_id: 選択ID
            
        Returns:
            Dict: 承認権限チェック結果
        """
        try:
            logger.info(f"Checking completion approval permission for selection {selection_id}")
            
            # 教師・管理者のみ承認可能
            if current_user.role not in ['teacher', 'admin']:
                return {
                    "allowed": False,
                    "reason": "完了承認は教師・管理者のみ可能です",
                    "error_code": "TEACHER_ADMIN_ONLY"
                }

            # 選択レコードの存在確認
            selection = StudentUnitSelection.query.get(selection_id)
            if not selection:
                return {
                    "allowed": False,
                    "reason": "指定された選択が見つかりません",
                    "error_code": "SELECTION_NOT_FOUND"
                }

            # 承認可能な状態かチェック
            if selection.status not in ['submitted', 'pending_approval']:
                return {
                    "allowed": False,
                    "reason": "承認可能な状態ではありません",
                    "error_code": "NOT_APPROVABLE_STATUS",
                    "current_status": selection.status
                }

            # 教師の場合：担当単元かチェック
            if current_user.role == 'teacher':
                unit_access = self.check_unit_access_permission(selection.unit_id, 'write')
                if not unit_access['allowed']:
                    return {
                        "allowed": False,
                        "reason": "この単元の承認権限がありません",
                        "error_code": "NO_UNIT_APPROVAL_PERMISSION"
                    }

            return {
                "allowed": True,
                "reason": "完了承認権限が確認されました",
                "selection_info": {
                    "id": selection.id,
                    "unit_id": selection.unit_id,
                    "student_id": selection.student_id,
                    "status": selection.status
                }
            }

        except Exception as e:
            logger.error(f"Error checking completion approval permission: {str(e)}")
            return {
                "allowed": False,
                "reason": f"承認権限チェック中にエラーが発生しました: {str(e)}",
                "error_code": "APPROVAL_PERMISSION_ERROR"
            }

    def get_user_accessible_units(self, subject_id: Optional[int] = None) -> Dict[str, Any]:
        """
        ユーザーがアクセス可能な単元一覧を取得
        
        Args:
            subject_id: 科目ID（フィルタ用）
            
        Returns:
            Dict: アクセス可能単元一覧
        """
        try:
            logger.info(f"Getting accessible units for user {current_user.id}")
            
            accessible_units = []
            
            if current_user.role == 'student':
                # 学生：所属クラスに関連する単元
                accessible_units = self._get_student_accessible_units(subject_id)
            
            elif current_user.role == 'teacher':
                # 教師：担当する単元
                accessible_units = self._get_teacher_accessible_units(subject_id)
            
            elif current_user.role == 'admin':
                # 管理者：全単元
                accessible_units = self._get_admin_accessible_units(subject_id)

            return {
                "success": True,
                "accessible_units": accessible_units,
                "total_count": len(accessible_units)
            }

        except Exception as e:
            logger.error(f"Error getting accessible units: {str(e)}")
            return {
                "success": False,
                "message": f"アクセス可能単元の取得中にエラーが発生しました: {str(e)}"
            }

    def _check_role_based_permission(self, unit: CurriculumUnit, action: str) -> Dict[str, Any]:
        """役割ベースの権限チェック"""
        if current_user.role == 'admin':
            return {"allowed": True}
        
        elif current_user.role == 'teacher':
            # 教師は基本的に読み取り・書き込み可能
            if action in ['read', 'write']:
                return {"allowed": True}
            elif action == 'delete':
                return {
                    "allowed": False,
                    "reason": "単元の削除権限がありません",
                    "error_code": "NO_DELETE_PERMISSION"
                }
        
        elif current_user.role == 'student':
            # 学生は読み取り・選択のみ可能
            if action in ['read', 'select']:
                return {"allowed": True}
            else:
                return {
                    "allowed": False,
                    "reason": "この操作の権限がありません",
                    "error_code": "STUDENT_NO_PERMISSION"
                }
        
        return {
            "allowed": False,
            "reason": "不明な役割です",
            "error_code": "UNKNOWN_ROLE"
        }

    def _check_action_specific_permission(self, unit: CurriculumUnit, action: str) -> Dict[str, Any]:
        """アクション固有の権限チェック"""
        if action == 'select':
            # 学生の場合：学校・クラス制限チェック
            if current_user.role == 'student':
                return self._check_student_school_access(unit)
        
        return {"allowed": True}

    def _check_student_school_access(self, unit: CurriculumUnit) -> Dict[str, Any]:
        """学生の学校アクセス権限チェック"""
        try:
            # 学生の所属クラスを取得
            enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
            
            if not enrollments:
                return {
                    "allowed": False,
                    "reason": "クラスに所属していません",
                    "error_code": "NO_CLASS_ENROLLMENT"
                }
            
            # 学生の所属学校を取得
            student_school_ids = set()
            for enrollment in enrollments:
                if enrollment.class_obj and enrollment.class_obj.school_id:
                    student_school_ids.add(enrollment.class_obj.school_id)
            
            # 単元の学校IDが学生の所属学校に含まれるかチェック
            if unit.school_id not in student_school_ids:
                return {
                    "allowed": False,
                    "reason": "この単元は所属学校の範囲外です",
                    "error_code": "SCHOOL_ACCESS_DENIED"
                }
            
            return {"allowed": True}
            
        except Exception as e:
            logger.error(f"Error checking student school access: {str(e)}")
            return {
                "allowed": False,
                "reason": "学校アクセス権限チェックでエラーが発生しました",
                "error_code": "SCHOOL_ACCESS_ERROR"
            }

    def _check_selection_limits(self) -> Dict[str, Any]:
        """選択数制限チェック"""
        try:
            # 現在の選択数を取得
            current_selections = StudentUnitSelection.query.filter_by(
                student_id=current_user.id
            ).filter(
                StudentUnitSelection.status.in_(['started', 'in_progress', 'submitted'])
            ).count()
            
            # 制限数の確認（設定により変更可能）
            max_concurrent_selections = 10  # デフォルト値
            
            if current_selections >= max_concurrent_selections:
                return {
                    "allowed": False,
                    "reason": f"同時選択可能数の上限（{max_concurrent_selections}個）に達しています",
                    "error_code": "SELECTION_LIMIT_EXCEEDED",
                    "current_count": current_selections,
                    "max_allowed": max_concurrent_selections
                }
            
            return {"allowed": True}
            
        except Exception as e:
            logger.error(f"Error checking selection limits: {str(e)}")
            return {
                "allowed": False,
                "reason": "選択数制限チェックでエラーが発生しました",
                "error_code": "LIMIT_CHECK_ERROR"
            }

    def _get_curriculum(self, curriculum_id: int):
        """カリキュラム取得"""
        try:
            from app.models import Curriculum
            return Curriculum.query.get(curriculum_id)
        except ImportError:
            return None

    def _check_student_class_access(self, curriculum) -> Dict[str, Any]:
        """学生のクラスアクセス権限チェック"""
        # 実装は必要に応じて詳細化
        return {"allowed": True}

    def _check_teacher_curriculum_access(self, curriculum) -> Dict[str, Any]:
        """教師のカリキュラムアクセス権限チェック"""
        # 実装は必要に応じて詳細化
        return {"allowed": True}

    def _get_student_accessible_units(self, subject_id: Optional[int]) -> List[Dict[str, Any]]:
        """学生のアクセス可能単元取得"""
        # 実装の簡略化
        return []

    def _get_teacher_accessible_units(self, subject_id: Optional[int]) -> List[Dict[str, Any]]:
        """教師のアクセス可能単元取得"""
        # 実装の簡略化
        return []

    def _get_admin_accessible_units(self, subject_id: Optional[int]) -> List[Dict[str, Any]]:
        """管理者のアクセス可能単元取得"""
        query = CurriculumUnit.query.filter_by(is_active=True)
        
        if subject_id:
            query = query.filter_by(subject_id=subject_id)
        
        units = query.all()
        
        return [
            {
                "id": unit.id,
                "title": unit.title,
                "subject_id": unit.subject_id,
                "school_id": unit.school_id
            }
            for unit in units
        ]