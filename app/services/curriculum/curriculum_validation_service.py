# -*- coding: utf-8 -*-
"""
CurriculumValidationService

カリキュラム関連の検証・権限チェックを管理する専門サービス
Phase8C: curriculum_management.pyから分離
"""
import logging
from typing import Dict, Optional, Any

from flask_login import current_user

from app.models import (
    Class,
    Curriculum,
    CurriculumUnit,
    MainTheme,
    User
)

logger = logging.getLogger(__name__)


class CurriculumValidationService:
    """カリキュラム検証・権限チェック専門サービス"""

    def validate_teacher_permission(self, class_id: int) -> Dict[str, Any]:
        """
        教師の権限をチェック
        
        Args:
            class_id: クラスID
            
        Returns:
            Dict: 権限チェック結果
        """
        try:
            # クラス存在確認
            class_obj = Class.query.get(class_id)
            if not class_obj:
                return {
                    "valid": False,
                    "message": "クラスが見つかりません",
                    "error_code": "CLASS_NOT_FOUND"
                }

            # 権限チェック
            if class_obj.teacher_id != current_user.id:
                return {
                    "valid": False,
                    "message": "このクラスの操作権限がありません",
                    "error_code": "PERMISSION_DENIED"
                }

            return {
                "valid": True,
                "class": class_obj
            }

        except Exception as e:
            logger.error(f"Error validating teacher permission: {str(e)}")
            return {
                "valid": False,
                "message": f"権限チェック中にエラーが発生しました: {str(e)}",
                "error_code": "VALIDATION_ERROR"
            }

    def validate_curriculum_permission(self, curriculum_id: int) -> Dict[str, Any]:
        """
        カリキュラムの操作権限をチェック
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: 権限チェック結果
        """
        try:
            # カリキュラム存在確認
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {
                    "valid": False,
                    "message": "カリキュラムが見つかりません",
                    "error_code": "CURRICULUM_NOT_FOUND"
                }

            # クラス経由で権限チェック
            if curriculum.class_obj.teacher_id != current_user.id:
                return {
                    "valid": False,
                    "message": "このカリキュラムの操作権限がありません",
                    "error_code": "PERMISSION_DENIED"
                }

            return {
                "valid": True,
                "curriculum": curriculum
            }

        except Exception as e:
            logger.error(f"Error validating curriculum permission: {str(e)}")
            return {
                "valid": False,
                "message": f"権限チェック中にエラーが発生しました: {str(e)}",
                "error_code": "VALIDATION_ERROR"
            }

    def validate_curriculum_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        カリキュラムデータの妥当性を検証
        
        Args:
            data: カリキュラムデータ
            
        Returns:
            Dict: 検証結果
        """
        errors = []

        # 必須フィールドチェック
        if not data.get("title"):
            errors.append("タイトルは必須です")

        # 数値フィールドの範囲チェック
        total_classes = data.get("total_classes", 35)
        if not isinstance(total_classes, int) or total_classes < 1 or total_classes > 100:
            errors.append("総授業数は1〜100の範囲で指定してください")

        total_hours = data.get("total_hours", 29.2)
        if not isinstance(total_hours, (int, float)) or total_hours < 0.1 or total_hours > 1000:
            errors.append("総時間数は0.1〜1000の範囲で指定してください")

        difficulty_level = data.get("difficulty_level", 2)
        if not isinstance(difficulty_level, int) or difficulty_level < 1 or difficulty_level > 5:
            errors.append("難易度は1〜5の範囲で指定してください")

        mastery_threshold = data.get("mastery_threshold", 80)
        if not isinstance(mastery_threshold, int) or mastery_threshold < 0 or mastery_threshold > 100:
            errors.append("習得基準は0〜100の範囲で指定してください")

        # メインテーマの存在確認
        if data.get("main_theme_id"):
            theme = MainTheme.query.get(data["main_theme_id"])
            if not theme:
                errors.append("指定されたメインテーマが見つかりません")

        # 自己ペースモードの検証
        valid_modes = ["flexible", "fixed", "guided"]
        if data.get("self_paced_mode") and data["self_paced_mode"] not in valid_modes:
            errors.append(f"自己ペースモードは {', '.join(valid_modes)} のいずれかを指定してください")

        if errors:
            return {
                "valid": False,
                "errors": errors
            }

        return {
            "valid": True,
            "data": data
        }

    def validate_unit_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        単元データの妥当性を検証
        
        Args:
            data: 単元データ
            
        Returns:
            Dict: 検証結果
        """
        errors = []

        # 必須フィールドチェック
        if not data.get("title"):
            errors.append("単元タイトルは必須です")

        # 順序インデックスチェック
        order_index = data.get("order_index", 1)
        if not isinstance(order_index, int) or order_index < 1:
            errors.append("単元順序は1以上の整数で指定してください")

        # 期間チェック
        duration_weeks = data.get("duration_weeks", 1)
        if not isinstance(duration_weeks, int) or duration_weeks < 1 or duration_weeks > 52:
            errors.append("期間は1〜52週の範囲で指定してください")

        if errors:
            return {
                "valid": False,
                "errors": errors
            }

        return {
            "valid": True,
            "data": data
        }

    def validate_theme_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        テーマデータの妥当性を検証
        
        Args:
            data: テーマデータ
            
        Returns:
            Dict: 検証結果
        """
        errors = []

        # 必須フィールドチェック
        if not data.get("title"):
            errors.append("テーマタイトルは必須です")

        if not data.get("description"):
            errors.append("テーマ説明は必須です")

        # カテゴリチェック
        valid_categories = ["exploration", "project", "skill", "other"]
        if data.get("category") and data["category"] not in valid_categories:
            errors.append(f"カテゴリは {', '.join(valid_categories)} のいずれかを指定してください")

        if errors:
            return {
                "valid": False,
                "errors": errors
            }

        return {
            "valid": True,
            "data": data
        }