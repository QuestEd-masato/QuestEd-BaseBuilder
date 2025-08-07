# -*- coding: utf-8 -*-
"""
TeacherCurriculumUnitService

教師向けカリキュラム単元の管理と変換を担当する専門サービス
Phase8C: curriculum_management.pyの単元関連機能から分離
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from app.models import Curriculum, CurriculumUnit, db
from app.services.curriculum_bridge_service import CurriculumBridgeService

logger = logging.getLogger(__name__)


class TeacherCurriculumUnitService:
    """教師向けカリキュラム単元管理専門サービス"""

    def convert_curriculum_to_units(self, curriculum_id: int) -> Dict[str, Any]:
        """
        カリキュラムを単元に変換
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: 変換結果
        """
        try:
            # カリキュラム存在確認と権限チェック
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {
                    "success": False,
                    "message": "カリキュラムが見つかりません"
                }

            if curriculum.class_obj.teacher_id != current_user.id:
                return {
                    "success": False,
                    "message": "権限がありません"
                }

            # 既に変換済みかチェック
            existing_units = CurriculumUnit.query.filter_by(
                curriculum_id=curriculum_id
            ).count()
            
            if existing_units > 0:
                return {
                    "success": False,
                    "message": "このカリキュラムは既に単元に変換されています",
                    "existing_units_count": existing_units
                }

            # CurriculumBridgeServiceを使用して変換
            conversion_result = CurriculumBridgeService.convert_curriculum_to_units(
                curriculum_id=curriculum_id,
                conversion_options={
                    "auto_create_units": True,
                    "preserve_order": True,
                    "default_duration_weeks": 2
                }
            )
            
            if not conversion_result.get("success"):
                return {
                    "success": False,
                    "message": conversion_result.get("message", "変換中にエラーが発生しました")
                }

            return {
                "success": True,
                "curriculum": curriculum,
                "units_created": conversion_result.get("units_created", 0),
                "message": f"カリキュラムが{conversion_result.get('units_created', 0)}個の単元に正常に変換されました"
            }

        except Exception as e:
            logger.error(f"Error converting curriculum {curriculum_id} to units: {str(e)}")
            return {
                "success": False,
                "message": f"カリキュラム変換中にエラーが発生しました: {str(e)}"
            }

    def get_converted_units(self, curriculum_id: int) -> Dict[str, Any]:
        """
        変換された単元一覧を取得
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: 単元一覧
        """
        try:
            # カリキュラム存在確認と権限チェック
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {
                    "success": False,
                    "message": "カリキュラムが見つかりません"
                }

            if curriculum.class_obj.teacher_id != current_user.id:
                return {
                    "success": False,
                    "message": "権限がありません"
                }

            # 単元一覧取得
            units = CurriculumUnit.query.filter_by(
                curriculum_id=curriculum_id
            ).order_by(CurriculumUnit.order_index).all()

            return {
                "success": True,
                "curriculum": curriculum,
                "units": units,
                "total_count": len(units)
            }

        except Exception as e:
            logger.error(f"Error getting converted units: {str(e)}")
            return {
                "success": False,
                "message": f"単元一覧の取得中にエラーが発生しました: {str(e)}"
            }

    def get_unit_detail(self, unit_id: int) -> Dict[str, Any]:
        """
        単元の詳細情報を取得
        
        Args:
            unit_id: 単元ID
            
        Returns:
            Dict: 単元詳細
        """
        try:
            unit = CurriculumUnit.query.get(unit_id)
            if not unit:
                return {
                    "success": False,
                    "message": "単元が見つかりません"
                }

            # 権限チェック
            if unit.curriculum.class_obj.teacher_id != current_user.id:
                return {
                    "success": False,
                    "message": "権限がありません"
                }

            return {
                "success": True,
                "unit": unit,
                "curriculum": unit.curriculum,
                "class": unit.curriculum.class_obj
            }

        except Exception as e:
            logger.error(f"Error getting unit detail {unit_id}: {str(e)}")
            return {
                "success": False,
                "message": f"単元詳細の取得中にエラーが発生しました: {str(e)}"
            }

    def update_unit(self, unit_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        単元を更新
        
        Args:
            unit_id: 単元ID
            update_data: 更新データ
            
        Returns:
            Dict: 更新結果
        """
        try:
            unit = CurriculumUnit.query.get(unit_id)
            if not unit:
                return {
                    "success": False,
                    "message": "単元が見つかりません"
                }

            # 権限チェック
            if unit.curriculum.class_obj.teacher_id != current_user.id:
                return {
                    "success": False,
                    "message": "権限がありません"
                }

            # データ検証
            validation_result = self._validate_unit_data(update_data)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "message": "入力データに誤りがあります",
                    "errors": validation_result["errors"]
                }

            # 順序インデックス重複チェック（自分以外）
            if "order_index" in update_data:
                existing_unit = CurriculumUnit.query.filter(
                    CurriculumUnit.legacy_curriculum_id == unit.legacy_curriculum_id,
                    CurriculumUnit.order_index == update_data["order_index"],
                    CurriculumUnit.id != unit_id
                ).first()
                
                if existing_unit:
                    return {
                        "success": False,
                        "message": "同じ順序の単元が既に存在します"
                    }

            # 更新処理
            for key, value in update_data.items():
                if hasattr(unit, key):
                    setattr(unit, key, value)
            
            unit.updated_at = datetime.utcnow()
            db.session.commit()

            return {
                "success": True,
                "unit": unit,
                "message": "単元が正常に更新されました"
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error updating unit: {str(e)}")
            return {
                "success": False,
                "message": "データベースエラーが発生しました"
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating unit {unit_id}: {str(e)}")
            return {
                "success": False,
                "message": f"単元更新中にエラーが発生しました: {str(e)}"
            }

    def delete_unit(self, unit_id: int) -> Dict[str, Any]:
        """
        単元を削除
        
        Args:
            unit_id: 単元ID
            
        Returns:
            Dict: 削除結果
        """
        try:
            unit = CurriculumUnit.query.get(unit_id)
            if not unit:
                return {
                    "success": False,
                    "message": "単元が見つかりません"
                }

            # 権限チェック
            if unit.curriculum.class_obj.teacher_id != current_user.id:
                return {
                    "success": False,
                    "message": "権限がありません"
                }

            # 削除実行
            curriculum_id = unit.curriculum_id
            order_index = unit.order_index
            
            db.session.delete(unit)
            
            # 後続の単元の順序を調整
            subsequent_units = CurriculumUnit.query.filter(
                CurriculumUnit.legacy_curriculum_id == curriculum_id,
                CurriculumUnit.order_index > order_index
            ).all()
            
            for subsequent_unit in subsequent_units:
                subsequent_unit.order_index -= 1
            
            db.session.commit()

            return {
                "success": True,
                "message": "単元が正常に削除されました",
                "adjusted_units": len(subsequent_units)
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error deleting unit: {str(e)}")
            return {
                "success": False,
                "message": "データベースエラーが発生しました"
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting unit {unit_id}: {str(e)}")
            return {
                "success": False,
                "message": f"単元削除中にエラーが発生しました: {str(e)}"
            }

    def reorder_units(self, curriculum_id: int, new_order: List[int]) -> Dict[str, Any]:
        """
        単元の順序を変更
        
        Args:
            curriculum_id: カリキュラムID
            new_order: 新しい順序（単元IDのリスト）
            
        Returns:
            Dict: 順序変更結果
        """
        try:
            # カリキュラム存在確認と権限チェック
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {
                    "success": False,
                    "message": "カリキュラムが見つかりません"
                }

            if curriculum.class_obj.teacher_id != current_user.id:
                return {
                    "success": False,
                    "message": "権限がありません"
                }

            # 全単元の取得
            units = CurriculumUnit.query.filter_by(
                curriculum_id=curriculum_id
            ).all()
            
            unit_dict = {unit.id: unit for unit in units}
            
            # 順序の検証
            if len(new_order) != len(units):
                return {
                    "success": False,
                    "message": "指定された順序の単元数が正しくありません"
                }
            
            for unit_id in new_order:
                if unit_id not in unit_dict:
                    return {
                        "success": False,
                        "message": f"単元ID {unit_id} が見つかりません"
                    }

            # 順序の更新
            for index, unit_id in enumerate(new_order, 1):
                unit_dict[unit_id].order_index = index
                unit_dict[unit_id].updated_at = datetime.utcnow()
            
            db.session.commit()

            return {
                "success": True,
                "message": "単元の順序が正常に更新されました",
                "reordered_count": len(new_order)
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error reordering units: {str(e)}")
            return {
                "success": False,
                "message": "データベースエラーが発生しました"
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error reordering units: {str(e)}")
            return {
                "success": False,
                "message": f"単元順序変更中にエラーが発生しました: {str(e)}"
            }

    def _validate_unit_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
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
        order_index = data.get("order_index")
        if order_index is not None:
            if not isinstance(order_index, int) or order_index < 1:
                errors.append("単元順序は1以上の整数で指定してください")

        # 期間チェック
        duration_weeks = data.get("duration_weeks")
        if duration_weeks is not None:
            if not isinstance(duration_weeks, int) or duration_weeks < 1 or duration_weeks > 52:
                errors.append("期間は1〜52週の範囲で指定してください")

        # タイトル長さチェック
        if data.get("title") and len(data["title"]) > 100:
            errors.append("タイトルは100文字以内で入力してください")

        # 説明長さチェック
        if data.get("description") and len(data["description"]) > 1000:
            errors.append("説明は1000文字以内で入力してください")

        if errors:
            return {
                "valid": False,
                "errors": errors
            }

        return {
            "valid": True,
            "data": data
        }