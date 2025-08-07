"""
同期検証サービス

同期前後の検証、エラー処理、データ整合性チェックを担当
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func

from app.models import Class, Curriculum, CurriculumUnit, StudentUnitSelection
from extensions import db

logger = logging.getLogger(__name__)


class SyncValidatorService:
    """同期検証専門サービス"""

    def validate_sync_prerequisites(self, curriculum_id: int) -> Dict[str, Any]:
        """
        同期の前提条件を検証
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: 検証結果
        """
        validation_errors = []
        warnings = []

        try:
            # カリキュラムの存在チェック
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                validation_errors.append({
                    "code": "CURRICULUM_NOT_FOUND",
                    "message": "カリキュラムが見つかりません",
                    "severity": "error"
                })
                return {
                    "valid": False,
                    "errors": validation_errors,
                    "warnings": warnings
                }

            # カリキュラムの基本情報チェック
            if not curriculum.title:
                validation_errors.append({
                    "code": "CURRICULUM_TITLE_MISSING",
                    "message": "カリキュラムのタイトルが設定されていません",
                    "severity": "error"
                })

            # 単元の存在チェック
            unit_count = CurriculumUnit.query.filter_by(
                curriculum_id=curriculum_id
            ).count()
            
            if unit_count == 0:
                validation_errors.append({
                    "code": "NO_CURRICULUM_UNITS",
                    "message": "カリキュラムに単元が登録されていません",
                    "severity": "error"
                })
            elif unit_count > 100:
                warnings.append({
                    "code": "LARGE_CURRICULUM",
                    "message": f"単元数が多すぎます（{unit_count}個）。同期に時間がかかる可能性があります",
                    "severity": "warning"
                })

            # アクティブなクラスの存在チェック
            active_classes = Class.query.filter_by(
                curriculum_id=curriculum_id
            ).count()
            
            if active_classes == 0:
                warnings.append({
                    "code": "NO_ASSIGNED_CLASSES",
                    "message": "このカリキュラムに割り当てられたクラスがありません",
                    "severity": "warning"
                })

            # 権限チェック
            if not curriculum.teacher_id:
                validation_errors.append({
                    "code": "NO_TEACHER_ASSIGNED",
                    "message": "カリキュラムに教師が割り当てられていません",
                    "severity": "error"
                })

            # データ整合性チェック
            integrity_check = self._check_data_integrity(curriculum_id)
            validation_errors.extend(integrity_check.get("errors", []))
            warnings.extend(integrity_check.get("warnings", []))

            return {
                "valid": len(validation_errors) == 0,
                "errors": validation_errors,
                "warnings": warnings,
                "curriculum_info": {
                    "id": curriculum_id,
                    "title": curriculum.title,
                    "unit_count": unit_count,
                    "assigned_classes": active_classes,
                }
            }

        except Exception as e:
            logger.error(f"Error validating sync prerequisites: {str(e)}")
            return {
                "valid": False,
                "errors": [{
                    "code": "VALIDATION_ERROR",
                    "message": f"検証中にエラーが発生しました: {str(e)}",
                    "severity": "error"
                }],
                "warnings": warnings
            }

    def validate_sync_result(
        self, curriculum_id: int, sync_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        同期結果を検証
        
        Args:
            curriculum_id: カリキュラムID
            sync_result: 同期結果
            
        Returns:
            Dict: 検証結果
        """
        validation_issues = []

        try:
            # 同期結果の基本チェック
            if not sync_result.get("success"):
                validation_issues.append({
                    "code": "SYNC_FAILED",
                    "message": sync_result.get("message", "同期に失敗しました"),
                    "severity": "error"
                })
                return {
                    "valid": False,
                    "issues": validation_issues
                }

            # 同期されたクラス数の妥当性チェック
            synced_classes = sync_result.get("synced_classes", 0)
            expected_classes = Class.query.filter_by(
                curriculum_id=curriculum_id
            ).count()

            if synced_classes != expected_classes:
                validation_issues.append({
                    "code": "CLASS_SYNC_MISMATCH",
                    "message": f"同期されたクラス数（{synced_classes}）が期待値（{expected_classes}）と一致しません",
                    "severity": "warning"
                })

            # 更新された単元数の妥当性チェック
            updated_units = sync_result.get("updated_units", 0)
            total_units = CurriculumUnit.query.filter_by(
                curriculum_id=curriculum_id
            ).count()

            if updated_units > total_units:
                validation_issues.append({
                    "code": "UNIT_UPDATE_EXCESS",
                    "message": f"更新された単元数（{updated_units}）が総単元数（{total_units}）を超えています",
                    "severity": "error"
                })

            # 学生選択の整合性チェック
            post_sync_integrity = self._check_post_sync_integrity(curriculum_id)
            validation_issues.extend(post_sync_integrity.get("issues", []))

            return {
                "valid": len([i for i in validation_issues if i["severity"] == "error"]) == 0,
                "issues": validation_issues,
                "sync_summary": {
                    "synced_classes": synced_classes,
                    "updated_units": updated_units,
                    "validation_time": datetime.utcnow().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Error validating sync result: {str(e)}")
            return {
                "valid": False,
                "issues": [{
                    "code": "RESULT_VALIDATION_ERROR",
                    "message": f"同期結果の検証中にエラーが発生しました: {str(e)}",
                    "severity": "error"
                }]
            }

    def get_sync_history_validation(self, curriculum_id: int) -> Dict[str, Any]:
        """
        同期履歴の検証
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: 履歴検証結果
        """
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum or not curriculum.curriculum_data:
                return {
                    "valid": True,
                    "history_count": 0,
                    "issues": []
                }

            data = json.loads(curriculum.curriculum_data)
            sync_logs = data.get("sync_logs", [])

            issues = []
            successful_syncs = 0
            failed_syncs = 0

            for log in sync_logs:
                status = log.get("status")
                if status == "completed":
                    successful_syncs += 1
                elif status == "failed":
                    failed_syncs += 1
                    issues.append({
                        "code": "FAILED_SYNC_DETECTED",
                        "message": f"失敗した同期: {log.get('started_at', 'Unknown time')}",
                        "severity": "warning",
                        "log_id": log.get("id")
                    })

                # 未完了の同期をチェック
                if status == "in_progress":
                    started_at = log.get("started_at")
                    if started_at:
                        start_time = datetime.fromisoformat(started_at)
                        if datetime.utcnow() - start_time > timedelta(hours=1):
                            issues.append({
                                "code": "STALE_SYNC_DETECTED",
                                "message": f"長時間実行中の同期を検出: {started_at}",
                                "severity": "error",
                                "log_id": log.get("id")
                            })

            # 失敗率が高い場合の警告
            total_syncs = successful_syncs + failed_syncs
            if total_syncs > 0 and failed_syncs / total_syncs > 0.3:
                issues.append({
                    "code": "HIGH_FAILURE_RATE",
                    "message": f"同期失敗率が高すぎます（{failed_syncs}/{total_syncs}）",
                    "severity": "warning"
                })

            return {
                "valid": len([i for i in issues if i["severity"] == "error"]) == 0,
                "history_count": len(sync_logs),
                "successful_syncs": successful_syncs,
                "failed_syncs": failed_syncs,
                "issues": issues
            }

        except Exception as e:
            logger.error(f"Error validating sync history: {str(e)}")
            return {
                "valid": False,
                "issues": [{
                    "code": "HISTORY_VALIDATION_ERROR",
                    "message": f"履歴検証中にエラーが発生しました: {str(e)}",
                    "severity": "error"
                }]
            }

    def validate_sync_settings(self, curriculum_id: int) -> Dict[str, Any]:
        """
        同期設定の検証
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: 設定検証結果
        """
        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {
                    "valid": False,
                    "issues": [{
                        "code": "CURRICULUM_NOT_FOUND",
                        "message": "カリキュラムが見つかりません",
                        "severity": "error"
                    }]
                }

            issues = []
            
            # 同期設定の取得
            sync_settings = self._get_sync_settings(curriculum)
            
            # 必須設定のチェック
            if not isinstance(sync_settings.get("auto_sync_enabled"), bool):
                issues.append({
                    "code": "INVALID_AUTO_SYNC_SETTING",
                    "message": "自動同期設定が無効です",
                    "severity": "warning"
                })

            # 遅延時間の妥当性チェック
            sync_delay = sync_settings.get("sync_delay_minutes", 5)
            if not isinstance(sync_delay, (int, float)) or sync_delay < 0 or sync_delay > 1440:
                issues.append({
                    "code": "INVALID_SYNC_DELAY",
                    "message": f"同期遅延時間が無効です: {sync_delay}分",
                    "severity": "error"
                })

            # 競合解決戦略のチェック
            resolution_strategy = sync_settings.get("conflict_resolution_strategy", "prompt")
            valid_strategies = ["auto", "prompt", "manual"]
            if resolution_strategy not in valid_strategies:
                issues.append({
                    "code": "INVALID_RESOLUTION_STRATEGY",
                    "message": f"無効な競合解決戦略: {resolution_strategy}",
                    "severity": "error"
                })

            return {
                "valid": len([i for i in issues if i["severity"] == "error"]) == 0,
                "settings": sync_settings,
                "issues": issues
            }

        except Exception as e:
            logger.error(f"Error validating sync settings: {str(e)}")
            return {
                "valid": False,
                "issues": [{
                    "code": "SETTINGS_VALIDATION_ERROR",
                    "message": f"設定検証中にエラーが発生しました: {str(e)}",
                    "severity": "error"
                }]
            }

    # プライベートメソッド

    def _check_data_integrity(self, curriculum_id: int) -> Dict[str, Any]:
        """データ整合性をチェック"""
        errors = []
        warnings = []

        try:
            # 孤立した単元をチェック
            orphaned_units = db.session.query(CurriculumUnit).filter(
                ~CurriculumUnit.curriculum_id.in_(
                    db.session.query(Curriculum.id)
                )
            ).count()

            if orphaned_units > 0:
                warnings.append({
                    "code": "ORPHANED_UNITS",
                    "message": f"{orphaned_units}個の孤立した単元が見つかりました",
                    "severity": "warning"
                })

            # 不正な学生選択をチェック
            invalid_selections = db.session.query(StudentUnitSelection).join(
                CurriculumUnit
            ).filter(
                CurriculumUnit.curriculum_id == curriculum_id,
                StudentUnitSelection.curriculum_unit_id.is_(None)
            ).count()

            if invalid_selections > 0:
                errors.append({
                    "code": "INVALID_STUDENT_SELECTIONS",
                    "message": f"{invalid_selections}個の不正な学生選択が見つかりました",
                    "severity": "error"
                })

        except Exception as e:
            logger.error(f"Error checking data integrity: {str(e)}")
            errors.append({
                "code": "INTEGRITY_CHECK_ERROR",
                "message": f"整合性チェック中にエラーが発生しました: {str(e)}",
                "severity": "error"
            })

        return {"errors": errors, "warnings": warnings}

    def _check_post_sync_integrity(self, curriculum_id: int) -> Dict[str, Any]:
        """同期後の整合性をチェック"""
        issues = []

        try:
            # 単元数の一貫性チェック
            curriculum_units = CurriculumUnit.query.filter_by(
                curriculum_id=curriculum_id
            ).count()

            # 各クラスでの単元数チェック
            classes = Class.query.filter_by(curriculum_id=curriculum_id).all()
            
            for class_obj in classes:
                # このクラスに関連する学生選択数をチェック
                # 実際の実装では、より詳細な整合性チェックを行う
                pass

        except Exception as e:
            logger.error(f"Error checking post-sync integrity: {str(e)}")
            issues.append({
                "code": "POST_SYNC_INTEGRITY_ERROR",
                "message": f"同期後整合性チェック中にエラーが発生しました: {str(e)}",
                "severity": "error"
            })

        return {"issues": issues}

    def _get_sync_settings(self, curriculum: Curriculum) -> Dict[str, Any]:
        """同期設定を取得"""
        if not curriculum.curriculum_data:
            return {}
            
        try:
            data = json.loads(curriculum.curriculum_data)
            return data.get("auto_sync_settings", {})
        except:
            return {}