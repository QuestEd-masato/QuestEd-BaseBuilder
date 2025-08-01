"""
学生単元サービス

学生視点での学習単元の選択・進捗管理を行う
自由進度学習機能の核となる学習単元の管理を行う
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_

from app.models import (
    Class,
    ClassLearningSettings,
    CurriculumUnit,
    LearningPath,
    StudentUnitSelection,
    Subject,
    UnitItemMapping,
    User,
)

# LearningPathUnit は RDSに存在しないためコメントアウト
from basebuilder.models import BasicKnowledgeItem
from extensions import db


class StudentUnitService:
    """学生単元サービス - 学生視点での単元選択・進捗管理"""

    @staticmethod
    def get_units_for_student(
        student_id: int,
        class_id: int = None,
        subject_id: int = None,
        include_progress: bool = True,
    ) -> List[Dict]:
        """
        生徒が利用可能な学習単元一覧を取得

        Args:
            student_id: 生徒ID
            class_id: クラスID（指定された場合はそのクラスの教科でフィルタ）
            subject_id: 教科ID（直接指定）
            include_progress: 進捗情報を含めるか

        Returns:
            単元情報のリスト
        """
        # クラスまたは教科IDの取得
        target_subject_id = subject_id
        if not target_subject_id and class_id:
            class_obj = Class.query.get(class_id)
            if class_obj:
                target_subject_id = class_obj.subject_id

        # 基本クエリ
        query = db.session.query(CurriculumUnit).filter(
            CurriculumUnit.is_active == True
        )

        # 教科フィルタ
        if target_subject_id:
            query = query.filter(CurriculumUnit.subject_id == target_subject_id)

        # 学校フィルタ（生徒の学校または全校共通）
        student = User.query.get(student_id)
        if student and student.school_id:
            query = query.filter(
                or_(
                    CurriculumUnit.school_id == student.school_id,
                    CurriculumUnit.school_id.is_(None),
                )
            )

        # 順序でソート
        query = query.order_by(CurriculumUnit.order_index, CurriculumUnit.id)

        units = query.all()

        # 結果の構築
        result = []
        for unit in units:
            unit_data = unit.to_dict()

            # 進捗情報の追加
            if include_progress:
                progress = StudentUnitService.get_student_progress(
                    student_id, unit.id, class_id
                )
                unit_data["progress"] = progress

                # 開始可能かチェック
                can_start, reason = StudentUnitService.can_student_start_unit(
                    student_id, unit.id, class_id
                )
                unit_data["can_start"] = can_start
                unit_data["unlock_reason"] = reason

            result.append(unit_data)

        return result

    @staticmethod
    def get_unit_detail(
        unit_id: int, student_id: int = None, class_id: int = None
    ) -> Optional[Dict]:
        """
        単元の詳細情報を取得

        Args:
            unit_id: 単元ID
            student_id: 生徒ID（指定されれば進捗情報も含める）
            class_id: クラスID

        Returns:
            単元詳細情報
        """
        unit = CurriculumUnit.query.filter_by(id=unit_id, is_active=True).first()
        if not unit:
            return None

        unit_data = unit.to_dict()

        # 前提単元の詳細情報
        if unit.prerequisites:
            prerequisites_detail = []
            for prereq_id in unit.prerequisites:
                prereq_unit = CurriculumUnit.query.get(prereq_id)
                if prereq_unit:
                    prereq_data = {
                        "id": prereq_unit.id,
                        "title": prereq_unit.title,
                        "status": "not_started",
                    }

                    # 生徒の進捗確認
                    if student_id:
                        progress = StudentUnitService.get_student_progress(
                            student_id, prereq_id, class_id
                        )
                        if progress:
                            prereq_data["status"] = progress.get(
                                "status", "not_started"
                            )

                    prerequisites_detail.append(prereq_data)

            unit_data["prerequisites"] = prerequisites_detail

        # 紐付けられた問題一覧
        problems = StudentUnitService.get_unit_problems(unit_id)
        unit_data["problems"] = problems

        # 生徒の進捗情報
        if student_id:
            progress = StudentUnitService.get_student_progress(
                student_id, unit_id, class_id
            )
            unit_data["progress"] = progress

        return unit_data

    @staticmethod
    def get_unit_problems(unit_id: int) -> List[Dict]:
        """
        単元に紐付けられた問題一覧を取得

        Args:
            unit_id: 単元ID

        Returns:
            問題情報のリスト
        """
        mappings = (
            db.session.query(UnitItemMapping, BasicKnowledgeItem)
            .join(BasicKnowledgeItem, UnitItemMapping.item_id == BasicKnowledgeItem.id)
            .filter(UnitItemMapping.unit_id == unit_id)
            .order_by(UnitItemMapping.order_index)
            .all()
        )

        problems = []
        for mapping, item in mappings:
            problem_data = {
                "id": item.id,
                "title": item.title,
                "difficulty": item.difficulty,
                "is_required": mapping.is_required,
                "order_index": mapping.order_index,
                "weight": float(mapping.weight) if mapping.weight else 1.0,
            }
            problems.append(problem_data)

        return problems

    @staticmethod
    def get_student_progress(
        student_id: int, unit_id: int, class_id: int = None
    ) -> Optional[Dict]:
        """
        生徒の単元学習進捗を取得

        Args:
            student_id: 生徒ID
            unit_id: 単元ID
            class_id: クラスID

        Returns:
            進捗情報
        """
        selection = StudentUnitSelection.query.filter_by(
            student_id=student_id, unit_id=unit_id, class_id=class_id
        ).first()

        if not selection:
            return {
                "status": "not_started",
                "progress_percentage": 0.0,
                "total_items": 0,
                "completed_items": 0,
                "correct_items": 0,
                "accuracy_rate": 0.0,
                "study_time_minutes": 0,
            }

        return selection.to_dict()

    @staticmethod
    def can_student_start_unit(
        student_id: int, unit_id: int, class_id: int = None
    ) -> Tuple[bool, Optional[str]]:
        """
        生徒が単元を開始できるかチェック

        Args:
            student_id: 生徒ID
            unit_id: 単元ID
            class_id: クラスID

        Returns:
            (開始可能か, 理由)
        """
        unit = CurriculumUnit.query.get(unit_id)
        if not unit or not unit.is_active:
            return False, "単元が見つからないか無効です"

        # クラス設定の確認
        if class_id:
            settings = ClassLearningSettings.query.filter_by(class_id=class_id).first()
            if settings:
                # 同時学習可能単元数のチェック
                current_units = StudentUnitSelection.query.filter(
                    StudentUnitSelection.student_id == student_id,
                    StudentUnitSelection.class_id == class_id,
                    StudentUnitSelection.status.in_(["in_progress", "not_started"]),
                ).count()

                if current_units >= settings.max_concurrent_units:
                    return (
                        False,
                        f"同時学習可能単元数の上限（{settings.max_concurrent_units}）に達しています",
                    )

        # 前提条件のチェック
        if unit.prerequisites:
            for prereq_id in unit.prerequisites:
                prereq_progress = StudentUnitService.get_student_progress(
                    student_id, prereq_id, class_id
                )

                if not prereq_progress or prereq_progress["status"] != "completed":
                    prereq_unit = CurriculumUnit.query.get(prereq_id)
                    prereq_title = (
                        prereq_unit.title if prereq_unit else f"単元{prereq_id}"
                    )
                    return False, f"前提単元「{prereq_title}」を完了してください"

                # 最低正解率のチェック
                if class_id:
                    settings = ClassLearningSettings.query.filter_by(
                        class_id=class_id
                    ).first()
                    if settings and prereq_progress["accuracy_rate"] < float(
                        settings.min_completion_rate
                    ):
                        return (
                            False,
                            f"前提単元の正解率が不足しています（最低{settings.min_completion_rate}%必要）",
                        )

        return True, None

    @staticmethod
    def select_unit(
        student_id: int, unit_id: int, class_id: int = None, notes: str = None
    ) -> Dict:
        """
        生徒が単元を選択

        Args:
            student_id: 生徒ID
            unit_id: 単元ID
            class_id: クラスID
            notes: 学習メモ

        Returns:
            選択結果
        """
        # 開始可能かチェック
        can_start, reason = StudentUnitService.can_student_start_unit(
            student_id, unit_id, class_id
        )

        if not can_start:
            raise ValueError(reason)

        # 既存の選択レコードをチェック
        existing = StudentUnitSelection.query.filter_by(
            student_id=student_id, unit_id=unit_id, class_id=class_id
        ).first()

        if existing:
            if existing.status == "completed":
                raise ValueError("この単元は既に完了しています")
            # 既存レコードを返す
            return existing.to_dict()

        # 単元の問題数を取得
        problem_count = UnitItemMapping.query.filter_by(
            unit_id=unit_id, is_required=True
        ).count()

        # 新しい選択レコードを作成
        selection = StudentUnitSelection(
            student_id=student_id,
            unit_id=unit_id,
            class_id=class_id,
            status="not_started",
            total_items=problem_count,
            notes=notes,
        )

        db.session.add(selection)
        db.session.commit()

        return selection.to_dict()

    @staticmethod
    def update_progress(
        student_id: int,
        unit_id: int,
        class_id: int = None,
        completed_items: int = None,
        correct_items: int = None,
        study_time_minutes: int = None,
        notes: str = None,
    ) -> Dict:
        """
        学習進捗を更新

        Args:
            student_id: 生徒ID
            unit_id: 単元ID
            class_id: クラスID
            completed_items: 完了問題数
            correct_items: 正解問題数
            study_time_minutes: 学習時間（分）
            notes: 学習メモ

        Returns:
            更新後の進捗情報
        """
        selection = StudentUnitSelection.query.filter_by(
            student_id=student_id, unit_id=unit_id, class_id=class_id
        ).first()

        if not selection:
            raise ValueError("単元が選択されていません")

        # 進捗の更新
        if completed_items is not None:
            selection.completed_items = completed_items
        if correct_items is not None:
            selection.correct_items = correct_items
        if study_time_minutes is not None:
            selection.study_time_minutes += study_time_minutes
        if notes is not None:
            selection.notes = notes

        # 進捗率とステータスの自動更新
        selection.update_progress()

        db.session.commit()

        # 成果判定
        achievements = []
        if selection.status == "completed":
            achievements.append("単元完了")

        accuracy = selection.get_accuracy_rate()
        if accuracy >= 90:
            achievements.append("正解率90%達成")
        elif accuracy >= 80:
            achievements.append("正解率80%達成")

        result = selection.to_dict()
        result["achievements"] = achievements

        return result

    @staticmethod
    def get_class_learning_settings(class_id: int) -> Dict:
        """
        クラス学習設定を取得

        Args:
            class_id: クラスID

        Returns:
            クラス学習設定
        """
        settings = ClassLearningSettings.query.filter_by(class_id=class_id).first()

        if not settings:
            # デフォルト設定を返す
            return {
                "allow_free_progress": True,
                "require_unit_order": False,
                "max_concurrent_units": 3,
                "min_completion_rate": 80.0,
                "allow_unit_skip": False,
                "show_difficulty_level": True,
                "enable_peer_comparison": False,
            }

        return settings.to_dict()

    @staticmethod
    def create_class_learning_settings(
        class_id: int, created_by: int, settings: Dict
    ) -> Dict:
        """
        クラス学習設定を作成・更新

        Args:
            class_id: クラスID
            created_by: 作成者ID
            settings: 設定値

        Returns:
            作成された設定
        """
        existing = ClassLearningSettings.query.filter_by(class_id=class_id).first()

        if existing:
            # 既存設定を更新
            for key, value in settings.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            db.session.commit()
            return existing.to_dict()

        # 新規作成
        new_settings = ClassLearningSettings(
            class_id=class_id, created_by=created_by, **settings
        )

        db.session.add(new_settings)
        db.session.commit()

        return new_settings.to_dict()

    @staticmethod
    def get_learning_path(class_id: int, path_id: int = None) -> Optional[Dict]:
        """
        学習パスを取得

        Args:
            class_id: クラスID
            path_id: パスID（指定されない場合はデフォルトパス）

        Returns:
            学習パス情報
        """
        if path_id:
            path = LearningPath.query.filter_by(
                id=path_id, class_id=class_id, is_active=True
            ).first()
        else:
            # デフォルトパスを取得
            path = LearningPath.query.filter_by(
                class_id=class_id, is_default=True, is_active=True
            ).first()

        if not path:
            return None

        path_data = path.to_dict()

        # パス内の単元を取得
        path_units = (
            db.session.query(LearningPathUnit, CurriculumUnit)
            .join(CurriculumUnit, LearningPathUnit.unit_id == CurriculumUnit.id)
            .filter(LearningPathUnit.path_id == path.id)
            .order_by(LearningPathUnit.sequence_order)
            .all()
        )

        units = []
        for path_unit, unit in path_units:
            unit_data = unit.to_dict()
            unit_data.update(
                {
                    "sequence_order": path_unit.sequence_order,
                    "is_required": path_unit.is_required,
                    "unlock_condition": path_unit.unlock_condition,
                }
            )
            units.append(unit_data)

        path_data["units"] = units

        return path_data
