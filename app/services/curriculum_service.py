"""
カリキュラムデータの処理を統一的に扱うサービスクラス
データ構造の一貫性を保証し、エラーハンドリングを一元化

Author: QuestEd Development Team
Created: 2025-01-15
Version: 1.0.0
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app import db
from app.models import Class, Curriculum


class CurriculumService:
    """カリキュラム関連の処理を担当するサービスクラス"""

    # デフォルトのカリキュラム構造定義
    DEFAULT_STRUCTURE = {
        "phases": [],
        "rubric_suggestion": [],
        "overview": "",
        "objectives": [],
        "schedule": [],
        "assessment": {"methods": [], "criteria": []},
        "resources": [],
        "total_hours": 0,
        "has_fieldwork": False,
        "fieldwork_count": 0,
        "has_presentation": False,
        "presentation_format": "",
        "group_work_level": "medium",
        "external_collaboration": False,
    }

    @staticmethod
    def parse_curriculum_content(curriculum: Curriculum) -> Dict[str, Any]:
        """
        カリキュラムのcontentをパースして統一された形式で返す

        Args:
            curriculum: Curriculumモデルインスタンス

        Returns:
            統一された形式のカリキュラムデータ
        """
        logger = logging.getLogger(__name__)

        # デフォルトの構造をコピー
        default_structure = CurriculumService.DEFAULT_STRUCTURE.copy()

        # contentが空の場合
        if not curriculum.content:
            logger.info(
                f"Curriculum ID {curriculum.id} has empty content, using default structure"
            )
            return default_structure

        try:
            # JSONパース
            content = json.loads(curriculum.content)

            # コンテンツが文字列の場合（レガシーデータ対応）
            if isinstance(content, str):
                logger.warning(
                    f"Curriculum ID {curriculum.id} has string content, converting to structure"
                )
                return {
                    **default_structure,
                    "overview": content,
                    "phases": [{"name": "学習フェーズ", "description": content, "weeks": []}],
                }

            # デフォルト構造とマージ（再帰的）
            result = CurriculumService._merge_dict_recursive(default_structure, content)

            # データ型検証と修正
            result = CurriculumService._validate_and_fix_structure(result)

            logger.debug(
                f"Successfully parsed curriculum content for ID {curriculum.id}"
            )
            return result

        except json.JSONDecodeError as e:
            # JSONパースエラーの場合
            logger.error(
                f"Failed to parse curriculum content for ID {curriculum.id}: {str(e)}"
            )
            return default_structure
        except Exception as e:
            # その他のエラー
            logger.error(
                f"Error processing curriculum content for ID {curriculum.id}: {str(e)}"
            )
            return default_structure

    @staticmethod
    def _merge_dict_recursive(
        base: Dict[str, Any], update: Dict[str, Any]
    ) -> Dict[str, Any]:
        """辞書を再帰的にマージ"""
        result = base.copy()

        for key, value in update.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = CurriculumService._merge_dict_recursive(
                    result[key], value
                )
            else:
                result[key] = value

        return result

    @staticmethod
    def _validate_and_fix_structure(data: Dict[str, Any]) -> Dict[str, Any]:
        """データ構造の検証と修正"""

        # phasesの検証（辞書から配列への変換対応）
        if isinstance(data.get("phases"), dict):
            data["phases"] = list(data["phases"].values())
        elif not isinstance(data.get("phases"), list):
            data["phases"] = []

        # rubric_suggestionの検証
        if not isinstance(data.get("rubric_suggestion"), list):
            data["rubric_suggestion"] = []

        # objectivesの検証
        if not isinstance(data.get("objectives"), list):
            data["objectives"] = []

        # scheduleの検証
        if not isinstance(data.get("schedule"), list):
            data["schedule"] = []

        # resourcesの検証
        if not isinstance(data.get("resources"), list):
            data["resources"] = []

        # assessmentの検証
        if not isinstance(data.get("assessment"), dict):
            data["assessment"] = {"methods": [], "criteria": []}
        else:
            if not isinstance(data["assessment"].get("methods"), list):
                data["assessment"]["methods"] = []
            if not isinstance(data["assessment"].get("criteria"), list):
                data["assessment"]["criteria"] = []

        # 数値フィールドの検証
        numeric_fields = ["total_hours", "fieldwork_count"]
        for field in numeric_fields:
            try:
                data[field] = int(data.get(field, 0))
            except (ValueError, TypeError):
                data[field] = 0

        # ブール値フィールドの検証
        boolean_fields = ["has_fieldwork", "has_presentation", "external_collaboration"]
        for field in boolean_fields:
            data[field] = bool(data.get(field, False))

        # 文字列フィールドの検証
        string_fields = ["overview", "presentation_format", "group_work_level"]
        for field in string_fields:
            if not isinstance(data.get(field), str):
                data[field] = data.get(field, "")

        return data

    @staticmethod
    def get_curriculum_display_data(curriculum: Curriculum) -> Dict[str, Any]:
        """
        テンプレート表示用のカリキュラムデータを取得

        Args:
            curriculum: Curriculumモデルインスタンス

        Returns:
            テンプレート用の完全なデータセット
        """
        # パース済みのコンテンツを取得
        curriculum_data = CurriculumService.parse_curriculum_content(curriculum)

        # 表示用データの構築
        display_data = {
            "id": curriculum.id,
            "title": curriculum.title,
            "description": curriculum.description,
            "created_at": curriculum.created_at,
            "updated_at": curriculum.updated_at,
            "teacher_id": curriculum.teacher_id,
            "class_id": curriculum.class_id,
            # パース済みデータを展開
            **curriculum_data,
        }

        # カリキュラムの統計情報を計算
        display_data.update(
            CurriculumService._calculate_curriculum_stats(curriculum_data)
        )

        return display_data

    @staticmethod
    def _calculate_curriculum_stats(curriculum_data: Dict[str, Any]) -> Dict[str, Any]:
        """カリキュラムの統計情報を計算"""
        stats = {
            "calculated_total_hours": 0,
            "total_phases": len(curriculum_data.get("phases", [])),
            "total_objectives": len(curriculum_data.get("objectives", [])),
            "total_resources": len(curriculum_data.get("resources", [])),
            "has_assessment": bool(
                curriculum_data.get("assessment", {}).get("methods")
            ),
            "completion_percentage": 0,
        }

        # フェーズごとの総時間を計算
        total_hours = 0
        total_activities = 0

        for phase in curriculum_data.get("phases", []):
            for week in phase.get("weeks", []):
                total_hours += week.get("hours", 0)
                total_activities += len(week.get("activities", []))

        stats["calculated_total_hours"] = total_hours
        stats["total_activities"] = total_activities

        # 完成度の計算（概算）
        completion_score = 0
        max_score = 6

        if curriculum_data.get("overview"):
            completion_score += 1
        if curriculum_data.get("objectives"):
            completion_score += 1
        if curriculum_data.get("phases"):
            completion_score += 1
        if curriculum_data.get("assessment", {}).get("methods"):
            completion_score += 1
        if curriculum_data.get("resources"):
            completion_score += 1
        if total_hours > 0:
            completion_score += 1

        stats["completion_percentage"] = round((completion_score / max_score) * 100)

        return stats

    @staticmethod
    def update_curriculum_content(
        curriculum: Curriculum, content_data: Dict[str, Any]
    ) -> bool:
        """
        カリキュラムのcontentを更新

        Args:
            curriculum: Curriculumモデルインスタンス
            content_data: 更新するコンテンツデータ

        Returns:
            更新成功の可否
        """
        logger = logging.getLogger(__name__)

        try:
            # 既存のコンテンツを取得
            current_data = CurriculumService.parse_curriculum_content(curriculum)

            # 新しいデータとマージ
            updated_data = CurriculumService._merge_dict_recursive(
                current_data, content_data
            )

            # データ構造の検証
            validated_data = CurriculumService._validate_and_fix_structure(updated_data)

            # JSON文字列に変換して保存
            curriculum.content = json.dumps(
                validated_data, ensure_ascii=False, indent=2
            )
            curriculum.updated_at = datetime.utcnow()

            db.session.commit()

            logger.info(
                f"Successfully updated curriculum content for ID {curriculum.id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to update curriculum content for ID {curriculum.id}: {str(e)}"
            )
            db.session.rollback()
            return False

    @staticmethod
    def create_curriculum_from_ai_data(
        ai_data: Dict[str, Any],
        class_id: int,
        teacher_id: int,
        title: str,
        description: str = "",
    ) -> Optional[Curriculum]:
        """
        AI生成データからカリキュラムを作成

        Args:
            ai_data: AI生成されたカリキュラムデータ
            class_id: クラスID
            teacher_id: 教師ID
            title: カリキュラムタイトル
            description: カリキュラム説明

        Returns:
            作成されたCurriculumインスタンス、失敗時はNone
        """
        logger = logging.getLogger(__name__)

        try:
            # AI データを標準構造に変換
            normalized_data = CurriculumService._normalize_ai_data(ai_data)

            # カリキュラムインスタンスを作成
            curriculum = Curriculum(
                class_id=class_id,
                teacher_id=teacher_id,
                title=title,
                description=description,
                content=json.dumps(normalized_data, ensure_ascii=False, indent=2),
            )

            db.session.add(curriculum)
            db.session.commit()

            logger.info(
                f"Successfully created curriculum from AI data: ID {curriculum.id}"
            )
            return curriculum

        except Exception as e:
            logger.error(f"Failed to create curriculum from AI data: {str(e)}")
            db.session.rollback()
            return None

    @staticmethod
    def _normalize_ai_data(ai_data: Dict[str, Any]) -> Dict[str, Any]:
        """AI生成データを標準構造に正規化"""
        normalized = CurriculumService.DEFAULT_STRUCTURE.copy()

        # AI データのマッピング
        if "overview" in ai_data:
            normalized["overview"] = ai_data["overview"]

        if "objectives" in ai_data:
            normalized["objectives"] = (
                ai_data["objectives"] if isinstance(ai_data["objectives"], list) else []
            )

        if "schedule" in ai_data:
            normalized["schedule"] = (
                ai_data["schedule"] if isinstance(ai_data["schedule"], list) else []
            )
            # scheduleからphasesを生成
            normalized["phases"] = CurriculumService._convert_schedule_to_phases(
                ai_data["schedule"]
            )

        if "assessment" in ai_data:
            normalized["assessment"] = (
                ai_data["assessment"] if isinstance(ai_data["assessment"], dict) else {}
            )

        if "resources" in ai_data:
            normalized["resources"] = (
                ai_data["resources"] if isinstance(ai_data["resources"], list) else []
            )

        return normalized

    @staticmethod
    def _convert_schedule_to_phases(
        schedule: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """スケジュールデータをフェーズ形式に変換"""
        phases = []

        for item in schedule:
            if isinstance(item, dict):
                phase = {
                    "name": item.get("phase", "学習フェーズ"),
                    "description": item.get("description", ""),
                    "duration": item.get("duration", ""),
                    "activities": item.get("activities", []),
                    "milestones": item.get("milestones", []),
                    "weeks": [],
                }
                phases.append(phase)

        return phases

    @staticmethod
    def validate_curriculum_data(data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        カリキュラムデータの妥当性を検証

        Args:
            data: 検証するデータ

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        # 必須フィールドの確認
        if not data.get("overview"):
            errors.append("カリキュラムの概要は必須です")

        if not data.get("objectives"):
            errors.append("学習目標を少なくとも1つ設定してください")

        # データ型の確認
        if not isinstance(data.get("phases", []), list):
            errors.append("フェーズデータの形式が正しくありません")

        if not isinstance(data.get("assessment", {}), dict):
            errors.append("評価データの形式が正しくありません")

        # 数値の範囲確認
        total_hours = data.get("total_hours", 0)
        if not isinstance(total_hours, (int, float)) or total_hours < 0:
            errors.append("総時間数は0以上の数値で入力してください")

        return len(errors) == 0, errors

    @staticmethod
    def get_curriculum_safe(
        curriculum_id: int, user_id: int = None
    ) -> tuple[Optional[Curriculum], Optional[Dict[str, Any]], Optional[str]]:
        """
        カリキュラムデータの安全な取得

        Args:
            curriculum_id: カリキュラムID
            user_id: ユーザーID（権限チェック用）

        Returns:
            (curriculum, curriculum_data, error_message)
        """
        logger = logging.getLogger(__name__)

        try:
            # カリキュラム取得
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                logger.error(f"Curriculum {curriculum_id} not found")
                return None, None, "カリキュラムが見つかりません"

            # 権限チェック（必要に応じて）
            if user_id:
                from app.models import User

                user = User.query.get(user_id)
                if user and user.role == "teacher" and curriculum.teacher_id != user_id:
                    return None, None, "このカリキュラムにアクセスする権限がありません"

            # コンテンツのパース
            curriculum_data = CurriculumService.parse_curriculum_content(curriculum)

            return curriculum, curriculum_data, None

        except Exception as e:
            logger.error(f"Error getting curriculum data: {str(e)}", exc_info=True)
            return None, None, "データ読み込み中にエラーが発生しました"

    @staticmethod
    def update_curriculum_safe(
        curriculum_id: int, update_data: Dict[str, Any], user_id: int = None
    ) -> tuple[bool, str]:
        """
        カリキュラムの安全な更新

        Args:
            curriculum_id: カリキュラムID
            update_data: 更新データ
            user_id: ユーザーID（権限チェック用）

        Returns:
            (success, message)
        """
        logger = logging.getLogger(__name__)

        try:
            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return False, "カリキュラムが見つかりません"

            # 権限チェック
            if user_id:
                from app.models import User

                user = User.query.get(user_id)
                if user and user.role == "teacher" and curriculum.teacher_id != user_id:
                    return False, "編集権限がありません"

            # 基本情報の更新
            if "title" in update_data and update_data["title"]:
                curriculum.title = update_data["title"]
            if "description" in update_data:
                curriculum.description = update_data["description"]

            # カリキュラム設定の更新
            curriculum_fields = [
                "total_hours",
                "has_fieldwork",
                "fieldwork_count",
                "has_presentation",
                "presentation_format",
                "group_work_level",
                "external_collaboration",
            ]

            for field in curriculum_fields:
                if field in update_data:
                    setattr(curriculum, field, update_data[field])

            # コンテンツの更新
            if "content" in update_data:
                content_data = update_data["content"]
                if isinstance(content_data, str):
                    try:
                        # JSON検証
                        json.loads(content_data)
                        curriculum.content = content_data
                    except json.JSONDecodeError:
                        return False, "コンテンツの形式が正しくありません"
                else:
                    curriculum.content = json.dumps(content_data, ensure_ascii=False)

            curriculum.updated_at = datetime.utcnow()
            db.session.commit()

            logger.info(f"Curriculum {curriculum_id} updated successfully")
            return True, "更新しました"

        except Exception as e:
            db.session.rollback()
            logger.error(
                f"Error updating curriculum {curriculum_id}: {str(e)}", exc_info=True
            )
            return False, "更新中にエラーが発生しました"

    @staticmethod
    def export_curriculum_to_csv(
        curriculum_id: int,
    ) -> tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        カリキュラムのCSVエクスポート用データ生成

        Args:
            curriculum_id: カリキュラムID

        Returns:
            (csv_data, error_message)
        """
        logger = logging.getLogger(__name__)

        try:
            curriculum, curriculum_data, error = CurriculumService.get_curriculum_safe(
                curriculum_id
            )
            if error:
                return None, error

            csv_data = []

            # フェーズデータを展開
            phases = curriculum_data.get("phases", [])
            if not phases:
                # フェーズがない場合は基本情報のみ
                csv_data.append(
                    {
                        "カリキュラム名": curriculum.title,
                        "説明": curriculum.description or "",
                        "総時間数": curriculum_data.get(
                            "total_hours", curriculum.total_hours
                        ),
                        "フィールドワーク": "有り"
                        if curriculum_data.get("has_fieldwork")
                        else "無し",
                        "フィールドワーク回数": curriculum_data.get("fieldwork_count", 0),
                        "発表会": "有り"
                        if curriculum_data.get("has_presentation")
                        else "無し",
                        "発表形式": curriculum_data.get("presentation_format", ""),
                        "グループワーク": curriculum_data.get("group_work_level", ""),
                        "外部連携": "有り"
                        if curriculum_data.get("external_collaboration")
                        else "無し",
                    }
                )
            else:
                # フェーズとウィークデータを展開
                for phase_idx, phase in enumerate(phases):
                    phase_name = phase.get(
                        "name", phase.get("phase", f"フェーズ{phase_idx + 1}")
                    )
                    weeks = phase.get("weeks", [])

                    if not weeks:
                        # ウィークがない場合はフェーズ情報のみ
                        csv_data.append(
                            {
                                "フェーズ番号": phase_idx + 1,
                                "フェーズ名": phase_name,
                                "説明": phase.get("description", ""),
                                "週": "",
                                "時間数": "",
                                "テーマ": "",
                                "活動内容": "",
                                "教師のサポート": "",
                                "評価方法": "",
                            }
                        )
                    else:
                        for week_idx, week in enumerate(weeks):
                            csv_data.append(
                                {
                                    "フェーズ番号": phase_idx + 1,
                                    "フェーズ名": phase_name,
                                    "説明": phase.get("description", "")
                                    if week_idx == 0
                                    else "",
                                    "週": week.get("week", f"{week_idx + 1}週目"),
                                    "時間数": week.get("hours", ""),
                                    "テーマ": week.get("theme", ""),
                                    "活動内容": week.get("activities", ""),
                                    "教師のサポート": week.get("teacher_support", ""),
                                    "評価方法": week.get("evaluation", ""),
                                }
                            )

            # データがない場合のフォールバック
            if not csv_data:
                csv_data = [
                    {
                        "カリキュラム名": curriculum.title,
                        "状態": "データなし",
                        "メッセージ": "カリキュラムの詳細データがまだ設定されていません",
                    }
                ]

            logger.info(
                f"Generated CSV data for curriculum {curriculum_id}: {len(csv_data)} rows"
            )
            return csv_data, None

        except Exception as e:
            logger.error(
                f"Error exporting curriculum {curriculum_id}: {str(e)}", exc_info=True
            )
            return None, "エクスポート中にエラーが発生しました"
