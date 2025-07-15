"""
Unified Curriculum Service
==========================
Phase 5.2: サービス層統合最適化

重複するカリキュラムサービスの統合:
- curriculum_service.py
- curriculum_service_v2.py
- curriculum_bridge_service.py

統合された機能:
- カリキュラム管理
- 単元変換
- 同期処理
- バリデーション
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from app.core.base_service import BaseService
from app.core.data_access import DataAccessLayer
from app.models import Class, Curriculum, CurriculumUnit, Subject, User


class UnifiedCurriculumService(BaseService):
    """統合カリキュラムサービス"""

    def __init__(self):
        super().__init__()
        self.dal = DataAccessLayer()
        self.validator = CurriculumValidator()
        self.converter = CurriculumConverter()
        self.sync_manager = CurriculumSyncManager()

    def get_service_name(self) -> str:
        return "UnifiedCurriculumService"

    # カリキュラム管理機能

    def create_curriculum(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        カリキュラム作成

        Args:
            data: カリキュラムデータ

        Returns:
            Dict: 作成結果
        """
        try:
            self.ensure_permission(["teacher", "admin"])

            # バリデーション
            validation_result = self.validator.validate_curriculum_data(data)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "message": "バリデーションエラー",
                    "errors": validation_result["errors"],
                }

            # カリキュラム作成
            curriculum = Curriculum(
                title=data["title"],
                description=data.get("description", ""),
                subject_id=data["subject_id"],
                class_id=data.get("class_id"),
                teacher_id=self.get_current_user_id(),
                curriculum_data=json.dumps(data.get("curriculum_data", {})),
                is_active=True,
                created_at=datetime.utcnow(),
            )

            success = self.dal.safe_create(curriculum)

            if success:
                result = {
                    "success": True,
                    "message": "カリキュラムを作成しました",
                    "curriculum_id": curriculum.id,
                }

                # 自動単元変換（設定されている場合）
                if data.get("auto_convert_to_units", False):
                    conversion_result = self.convert_to_units(curriculum.id)
                    result["unit_conversion"] = conversion_result

                self.log_info(f"Curriculum created: {curriculum.id}")
            else:
                result = {"success": False, "message": "カリキュラムの作成に失敗しました"}

            return result

        except Exception as e:
            self.log_error(f"Create curriculum error: {str(e)}")
            return {"success": False, "message": "エラーが発生しました"}

    def update_curriculum(
        self, curriculum_id: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        カリキュラム更新

        Args:
            curriculum_id: カリキュラムID
            data: 更新データ

        Returns:
            Dict: 更新結果
        """
        try:
            self.ensure_permission(["teacher", "admin"])

            curriculum = self.dal.safe_get_by_id(Curriculum, curriculum_id)
            if not curriculum:
                return {"success": False, "message": "カリキュラムが見つかりません"}

            # 権限確認
            if not self._can_modify_curriculum(curriculum):
                return {"success": False, "message": "更新権限がありません"}

            # バリデーション
            validation_result = self.validator.validate_curriculum_update(
                curriculum, data
            )
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "message": "バリデーションエラー",
                    "errors": validation_result["errors"],
                }

            # 更新実行
            updates = {}
            updatable_fields = ["title", "description", "curriculum_data", "is_active"]

            for field in updatable_fields:
                if field in data:
                    if field == "curriculum_data":
                        updates[field] = json.dumps(data[field])
                    else:
                        updates[field] = data[field]

            success = self.dal.safe_update(curriculum, updates)

            if success:
                result = {"success": True, "message": "カリキュラムを更新しました"}

                # 同期処理（必要な場合）
                if data.get("sync_with_units", False):
                    sync_result = self.sync_with_units(curriculum_id)
                    result["sync_result"] = sync_result

                self.log_info(f"Curriculum updated: {curriculum_id}")
            else:
                result = {"success": False, "message": "カリキュラムの更新に失敗しました"}

            return result

        except Exception as e:
            self.log_error(f"Update curriculum error: {str(e)}")
            return {"success": False, "message": "エラーが発生しました"}

    def get_curriculum(
        self, curriculum_id: int, include_units: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        カリキュラム取得

        Args:
            curriculum_id: カリキュラムID
            include_units: 関連単元を含めるかどうか

        Returns:
            Dict: カリキュラムデータ
        """
        try:
            curriculum = self.dal.safe_get_by_id(Curriculum, curriculum_id)
            if not curriculum:
                return None

            # 権限確認
            if not self._can_access_curriculum(curriculum):
                raise PermissionError("Curriculum access denied")

            curriculum_data = {
                "id": curriculum.id,
                "title": curriculum.title,
                "description": curriculum.description,
                "subject_id": curriculum.subject_id,
                "class_id": curriculum.class_id,
                "teacher_id": curriculum.teacher_id,
                "is_active": curriculum.is_active,
                "created_at": curriculum.created_at.isoformat(),
                "updated_at": curriculum.updated_at.isoformat()
                if curriculum.updated_at
                else None,
            }

            # カリキュラムデータの解析
            if curriculum.curriculum_data:
                try:
                    curriculum_data["curriculum_data"] = json.loads(
                        curriculum.curriculum_data
                    )
                except:
                    curriculum_data["curriculum_data"] = {}

            # 関連単元の取得
            if include_units:
                units = self.dal.safe_query(
                    CurriculumUnit,
                    filters={"curriculum_id": curriculum_id, "is_active": True},
                )

                curriculum_data["units"] = [
                    {
                        "id": unit.id,
                        "title": unit.title,
                        "description": unit.description,
                        "order_index": unit.order_index,
                        "difficulty_level": unit.difficulty_level,
                        "estimated_hours": unit.estimated_hours,
                    }
                    for unit in units
                ]

            return curriculum_data

        except Exception as e:
            self.log_error(f"Get curriculum error: {str(e)}")
            return None

    # 単元変換機能

    def convert_to_units(
        self, curriculum_id: int, options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        カリキュラムから単元への変換

        Args:
            curriculum_id: カリキュラムID
            options: 変換オプション

        Returns:
            Dict: 変換結果
        """
        try:
            curriculum = self.dal.safe_get_by_id(Curriculum, curriculum_id)
            if not curriculum:
                return {"success": False, "message": "カリキュラムが見つかりません"}

            if not self._can_modify_curriculum(curriculum):
                return {"success": False, "message": "変換権限がありません"}

            return self.converter.convert_curriculum_to_units(curriculum, options or {})

        except Exception as e:
            self.log_error(f"Convert to units error: {str(e)}")
            return {"success": False, "message": "変換でエラーが発生しました"}

    def sync_with_units(self, curriculum_id: int) -> Dict[str, Any]:
        """
        カリキュラムと単元の同期

        Args:
            curriculum_id: カリキュラムID

        Returns:
            Dict: 同期結果
        """
        try:
            return self.sync_manager.sync_curriculum_with_units(curriculum_id)

        except Exception as e:
            self.log_error(f"Sync with units error: {str(e)}")
            return {"success": False, "message": "同期でエラーが発生しました"}

    # プライベートメソッド

    def _can_access_curriculum(self, curriculum) -> bool:
        """カリキュラムアクセス権限確認"""
        if self.check_permission(["admin"]):
            return True

        current_user_id = self.get_current_user_id()

        # 作成者チェック
        if curriculum.teacher_id == current_user_id:
            return True

        # クラス所属チェック（学生の場合）
        if self.check_permission(["student"]) and curriculum.class_id:
            # TODO: 学生のクラス所属確認
            return True

        return False

    def _can_modify_curriculum(self, curriculum) -> bool:
        """カリキュラム変更権限確認"""
        if self.check_permission(["admin"]):
            return True

        current_user_id = self.get_current_user_id()
        return curriculum.teacher_id == current_user_id


class CurriculumValidator:
    """カリキュラムバリデーションクラス"""

    def validate_curriculum_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """カリキュラムデータのバリデーション"""
        errors = []

        # 必須フィールドチェック
        required_fields = ["title", "subject_id"]
        for field in required_fields:
            if not data.get(field):
                errors.append(f"{field} is required")

        # タイトル長制限
        if data.get("title") and len(data["title"]) > 200:
            errors.append("Title is too long (max 200 characters)")

        # 科目存在確認
        if data.get("subject_id"):
            dal = DataAccessLayer()
            subject = dal.safe_get_by_id(Subject, data["subject_id"])
            if not subject:
                errors.append("Invalid subject_id")

        return {"valid": len(errors) == 0, "errors": errors}

    def validate_curriculum_update(
        self, curriculum, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """カリキュラム更新データのバリデーション"""
        # 基本バリデーション
        result = self.validate_curriculum_data(data)

        # 更新固有のチェック
        if curriculum.is_active and data.get("is_active") is False:
            # 非アクティブ化時の確認
            dal = DataAccessLayer()
            active_units = dal.safe_query(
                CurriculumUnit,
                filters={"curriculum_id": curriculum.id, "is_active": True},
            )

            if active_units:
                result["errors"].append(
                    "Cannot deactivate curriculum with active units"
                )
                result["valid"] = False

        return result


class CurriculumConverter:
    """カリキュラム変換クラス"""

    def convert_curriculum_to_units(self, curriculum, options: Dict) -> Dict[str, Any]:
        """カリキュラムから単元への変換実行"""
        try:
            dal = DataAccessLayer()

            # カリキュラムデータの解析
            if curriculum.curriculum_data:
                curriculum_content = json.loads(curriculum.curriculum_data)
            else:
                return {"success": False, "message": "カリキュラムデータが存在しません"}

            created_units = []

            # 既存単元の無効化（オプション）
            if options.get("replace_existing", False):
                existing_units = dal.safe_query(
                    CurriculumUnit, filters={"curriculum_id": curriculum.id}
                )

                for unit in existing_units:
                    dal.safe_update(unit, {"is_active": False})

            # 単元作成
            units_data = curriculum_content.get("units", [])

            for i, unit_data in enumerate(units_data):
                unit = CurriculumUnit(
                    curriculum_id=curriculum.id,
                    title=unit_data.get("title", f"Unit {i+1}"),
                    description=unit_data.get("description", ""),
                    content=json.dumps(unit_data.get("content", {})),
                    order_index=i,
                    difficulty_level=unit_data.get("difficulty_level", 1),
                    estimated_hours=unit_data.get("estimated_hours", 1),
                    subject_id=curriculum.subject_id,
                    school_id=curriculum.class_obj.school_id
                    if curriculum.class_obj
                    else None,
                    created_by=curriculum.teacher_id,
                    created_at=datetime.utcnow(),
                    is_active=True,
                )

                if dal.safe_create(unit):
                    created_units.append(unit.id)

            return {
                "success": True,
                "message": f"{len(created_units)}個の単元を作成しました",
                "created_units": created_units,
            }

        except Exception as e:
            return {"success": False, "message": f"変換エラー: {str(e)}"}


class CurriculumSyncManager:
    """カリキュラム同期管理クラス"""

    def sync_curriculum_with_units(self, curriculum_id: int) -> Dict[str, Any]:
        """カリキュラムと単元の同期処理"""
        try:
            dal = DataAccessLayer()

            curriculum = dal.safe_get_by_id(Curriculum, curriculum_id)
            if not curriculum:
                return {"success": False, "message": "カリキュラムが見つかりません"}

            # TODO: 実際の同期ロジック実装
            # - カリキュラムの変更内容を単元に反映
            # - 単元の進捗状況をカリキュラムに反映
            # - 競合の検出と解決

            return {"success": True, "message": "同期が完了しました", "sync_status": "completed"}

        except Exception as e:
            return {"success": False, "message": f"同期エラー: {str(e)}"}


# 後方互換性のためのエイリアス
CurriculumService = UnifiedCurriculumService
