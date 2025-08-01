# -*- coding: utf-8 -*-
"""
TaskValidationService

入力検証専門サービス
権限チェック・ビジネスルール検証・入力値サニタイゼーションを担当
"""
import logging
import re
from typing import Any, Dict, List, Optional

from flask_login import current_user

from app.models import (
    CurriculumTask, User, Class, Curriculum, TaskType, TaskStatus, DueDateType
)

logger = logging.getLogger(__name__)


class TaskValidationService:
    """入力検証専門サービス"""

    def validate_user_permissions(self, action: str, resource_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        ユーザー権限を検証
        
        Args:
            action: アクション名 ('create', 'read', 'update', 'delete')
            resource_data: リソースデータ
            
        Returns:
            Dict: 検証結果
        """
        try:
            if not current_user.is_authenticated:
                return {
                    "valid": False,
                    "message": "認証が必要です"
                }

            user_role = current_user.role

            # 管理者は全権限
            if user_role == 'admin':
                return {"valid": True}

            # 教師権限のチェック
            if user_role == 'teacher':
                if action in ['create', 'update', 'delete']:
                    # 教師は自分のカリキュラムの課題のみ操作可能
                    if resource_data and 'curriculum_id' in resource_data:
                        curriculum = Curriculum.query.get(resource_data['curriculum_id'])
                        if curriculum and curriculum.teacher_id == current_user.id:
                            return {"valid": True}
                        else:
                            return {
                                "valid": False,
                                "message": "この操作は自分のカリキュラムに対してのみ実行できます"
                            }
                    else:
                        return {
                            "valid": False,
                            "message": "カリキュラムIDが必要です"
                        }
                elif action == 'read':
                    return {"valid": True}  # 教師は読み取り権限あり

            # 学生権限のチェック
            if user_role == 'student':
                if action == 'read':
                    # 学生は自分がアクセス可能なカリキュラムの課題のみ読み取り可能
                    if resource_data and 'curriculum_id' in resource_data:
                        # 学生が所属するクラスのカリキュラムかチェック
                        student_class = Class.query.filter_by(id=current_user.class_id).first()
                        if student_class and student_class.curriculum_id == resource_data['curriculum_id']:
                            return {"valid": True}
                        else:
                            return {
                                "valid": False,
                                "message": "アクセス権限がありません"
                            }
                    return {"valid": True}  # 基本的な読み取り権限
                else:
                    return {
                        "valid": False,
                        "message": "学生はこの操作を実行できません"
                    }

            return {
                "valid": False,
                "message": "権限が不足しています"
            }

        except Exception as e:
            logger.error(f"Error validating user permissions: {str(e)}")
            return {
                "valid": False,
                "message": f"権限確認中にエラーが発生しました: {str(e)}"
            }

    def validate_task_data(self, task_data: Dict[str, Any], action: str = 'create') -> Dict[str, Any]:
        """
        課題データを検証
        
        Args:
            task_data: 課題データ
            action: アクション ('create' or 'update')
            
        Returns:
            Dict: 検証結果
        """
        errors = []
        warnings = []

        try:
            # 必須フィールドの検証（作成時のみ）
            if action == 'create':
                required_fields = ['curriculum_id', 'title', 'week_number', 'task_type']
                for field in required_fields:
                    if field not in task_data or task_data[field] is None:
                        errors.append(f"必須フィールド '{field}' が不足しています")

            # タイトルの検証
            if 'title' in task_data:
                title = str(task_data['title']).strip()
                if not title:
                    errors.append("タイトルを入力してください")
                elif len(title) > 200:
                    errors.append("タイトルは200文字以内で入力してください")
                elif len(title) < 3:
                    warnings.append("タイトルは3文字以上が推奨されます")

            # 説明の検証
            if 'description' in task_data and task_data['description']:
                description = str(task_data['description']).strip()
                if len(description) > 1000:
                    errors.append("説明は1000文字以内で入力してください")

            # 週番号の検証
            if 'week_number' in task_data:
                week_number = task_data['week_number']
                if not isinstance(week_number, int) or week_number < 1 or week_number > 52:
                    errors.append("週番号は1-52の範囲で入力してください")

            # 週内順序の検証
            if 'order_in_week' in task_data:
                order_in_week = task_data['order_in_week']
                if not isinstance(order_in_week, int) or order_in_week < 1 or order_in_week > 10:
                    errors.append("週内順序は1-10の範囲で入力してください")

            # 課題タイプの検証
            if 'task_type' in task_data:
                task_type = task_data['task_type']
                valid_types = [t.value for t in TaskType]
                if task_type not in valid_types:
                    errors.append(f"無効な課題タイプです。有効な値: {', '.join(valid_types)}")

            # 予想時間の検証
            if 'estimated_time_minutes' in task_data:
                time_minutes = task_data['estimated_time_minutes']
                if not isinstance(time_minutes, int) or time_minutes < 1 or time_minutes > 480:
                    errors.append("予想時間は1-480分の範囲で入力してください")

            # 最大得点の検証
            if 'max_score' in task_data:
                max_score = task_data['max_score']
                if not isinstance(max_score, (int, float)) or max_score < 1 or max_score > 1000:
                    errors.append("最大得点は1-1000の範囲で入力してください")

            # 期限オフセットの検証
            if 'due_date_offset_days' in task_data:
                offset_days = task_data['due_date_offset_days']
                if not isinstance(offset_days, int) or offset_days < 0 or offset_days > 365:
                    errors.append("期限オフセットは0-365日の範囲で入力してください")

            # 期限タイプの検証
            if 'due_date_type' in task_data:
                due_date_type = task_data['due_date_type']
                valid_types = [t.value for t in DueDateType]
                if due_date_type not in valid_types:
                    errors.append(f"無効な期限タイプです。有効な値: {', '.join(valid_types)}")

            # 指示文の検証
            if 'instructions' in task_data and task_data['instructions']:
                instructions = str(task_data['instructions']).strip()
                if len(instructions) > 2000:
                    errors.append("指示文は2000文字以内で入力してください")

            # リソースの検証
            if 'resources' in task_data and task_data['resources']:
                resources = str(task_data['resources']).strip()
                if len(resources) > 1000:
                    errors.append("リソース情報は1000文字以内で入力してください")

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }

        except Exception as e:
            logger.error(f"Error validating task data: {str(e)}")
            return {
                "valid": False,
                "errors": [f"データ検証中にエラーが発生しました: {str(e)}"],
                "warnings": warnings
            }

    def validate_progress_data(self, progress_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        進捗データを検証
        
        Args:
            progress_data: 進捗データ
            
        Returns:
            Dict: 検証結果
        """
        errors = []
        warnings = []

        try:
            # 提出テキストの検証
            if 'submission_text' in progress_data:
                submission_text = progress_data['submission_text']
                if submission_text and len(str(submission_text)) > 5000:
                    errors.append("提出テキストは5000文字以内で入力してください")

            # スコアの検証
            if 'score' in progress_data:
                score = progress_data['score']
                if score is not None:
                    if not isinstance(score, (int, float)) or score < 0 or score > 1000:
                        errors.append("スコアは0-1000の範囲で入力してください")

            # ステータスの検証
            if 'status' in progress_data:
                status = progress_data['status']
                valid_statuses = [s.value for s in TaskStatus]
                if status not in valid_statuses:
                    errors.append(f"無効なステータスです。有効な値: {', '.join(valid_statuses)}")

            # フィードバックの検証
            if 'feedback' in progress_data:
                feedback = progress_data['feedback']
                if feedback and len(str(feedback)) > 2000:
                    errors.append("フィードバックは2000文字以内で入力してください")

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }

        except Exception as e:
            logger.error(f"Error validating progress data: {str(e)}")
            return {
                "valid": False,
                "errors": [f"進捗データ検証中にエラーが発生しました: {str(e)}"],
                "warnings": warnings
            }

    def sanitize_input_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        入力データをサニタイズ
        
        Args:
            data: 入力データ
            
        Returns:
            Dict: サニタイズ済みデータ
        """
        sanitized = {}

        try:
            for key, value in data.items():
                if value is None:
                    sanitized[key] = None
                elif isinstance(value, str):
                    # 文字列のサニタイズ
                    sanitized_value = value.strip()
                    
                    # HTMLタグの除去（基本的なもの）
                    sanitized_value = re.sub(r'<[^>]+>', '', sanitized_value)
                    
                    # 改行文字の正規化
                    sanitized_value = re.sub(r'\r\n|\r', '\n', sanitized_value)
                    
                    # 連続する改行の制限（最大3個）
                    sanitized_value = re.sub(r'\n{4,}', '\n\n\n', sanitized_value)
                    
                    sanitized[key] = sanitized_value
                elif isinstance(value, (int, float, bool)):
                    sanitized[key] = value
                elif isinstance(value, dict):
                    # 辞書の再帰的サニタイズ
                    sanitized[key] = self.sanitize_input_data(value)
                elif isinstance(value, list):
                    # リストの各要素をサニタイズ
                    sanitized[key] = [
                        self.sanitize_input_data(item) if isinstance(item, dict)
                        else str(item).strip() if isinstance(item, str)
                        else item
                        for item in value
                    ]
                else:
                    sanitized[key] = value

            return sanitized

        except Exception as e:
            logger.error(f"Error sanitizing input data: {str(e)}")
            return data  # エラー時は元データを返す

    def validate_curriculum_access(self, curriculum_id: int, user_id: int) -> Dict[str, Any]:
        """
        カリキュラムアクセス権限を確認
        
        Args:
            curriculum_id: カリキュラムID
            user_id: ユーザーID
            
        Returns:
            Dict: アクセス権限確認結果
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return {
                    "valid": False,
                    "message": "ユーザーが見つかりません"
                }

            curriculum = Curriculum.query.get(curriculum_id)
            if not curriculum:
                return {
                    "valid": False,
                    "message": "カリキュラムが見つかりません"
                }

            # 管理者は全アクセス可能
            if user.role == 'admin':
                return {"valid": True}

            # 教師は自分のカリキュラムにアクセス可能
            if user.role == 'teacher':
                if curriculum.teacher_id == user_id:
                    return {"valid": True}
                else:
                    return {
                        "valid": False,
                        "message": "このカリキュラムにアクセスする権限がありません"
                    }

            # 学生は所属クラスのカリキュラムにアクセス可能
            if user.role == 'student':
                if user.class_id:
                    student_class = Class.query.get(user.class_id)
                    if student_class and student_class.curriculum_id == curriculum_id:
                        return {"valid": True}
                
                return {
                    "valid": False,
                    "message": "このカリキュラムにアクセスする権限がありません"
                }

            return {
                "valid": False,
                "message": "不明な権限レベルです"
            }

        except Exception as e:
            logger.error(f"Error validating curriculum access: {str(e)}")
            return {
                "valid": False,
                "message": f"アクセス権限確認中にエラーが発生しました: {str(e)}"
            }

    def check_task_dependencies(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        課題の依存関係をチェック
        
        Args:
            task_data: 課題データ
            
        Returns:
            Dict: 依存関係チェック結果
        """
        issues = []
        warnings = []

        try:
            if 'curriculum_id' in task_data and 'week_number' in task_data:
                curriculum_id = task_data['curriculum_id']
                week_number = task_data['week_number']
                
                # 同じ週の課題数をチェック
                same_week_tasks = CurriculumTask.query.filter_by(
                    curriculum_id=curriculum_id,
                    week_number=week_number
                ).count()
                
                if same_week_tasks >= 10:
                    warnings.append(f"第{week_number}週には既に{same_week_tasks}個の課題があります")

                # 前週の課題が存在するかチェック
                if week_number > 1:
                    prev_week_tasks = CurriculumTask.query.filter_by(
                        curriculum_id=curriculum_id,
                        week_number=week_number - 1
                    ).count()
                    
                    if prev_week_tasks == 0:
                        warnings.append(f"第{week_number - 1}週に課題がありません。順序が正しいか確認してください")

            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "warnings": warnings
            }

        except Exception as e:
            logger.error(f"Error checking task dependencies: {str(e)}")
            return {
                "valid": True,  # エラー時は依存関係チェックをスキップ
                "issues": [],
                "warnings": [f"依存関係チェック中にエラーが発生しました: {str(e)}"]
            }