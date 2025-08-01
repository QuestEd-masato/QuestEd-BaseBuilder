# -*- coding: utf-8 -*-
"""
TaskCRUDService

課題のCRUD操作専門サービス
データ検証・整形・データベース操作の抽象化を担当
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models import (
    CurriculumTask, StudentTaskProgress, TaskFileAttachment,
    TaskType, TaskStatus, DueDateType, db
)

logger = logging.getLogger(__name__)


class TaskCRUDService:
    """課題CRUD操作専門サービス"""

    def get_curriculum_tasks(self, curriculum_id: int) -> Dict[str, Any]:
        """
        カリキュラムの課題一覧を取得
        
        Args:
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: 週ごとにグループ化された課題データ
        """
        try:
            # 週番号でソート
            tasks = CurriculumTask.query.filter_by(curriculum_id=curriculum_id) \
                                       .order_by(CurriculumTask.week_number, CurriculumTask.order_in_week) \
                                       .all()

            # 週ごとにグループ化
            weeks_data = {}
            for task in tasks:
                week_num = task.week_number
                if week_num not in weeks_data:
                    weeks_data[week_num] = {
                        'week_number': week_num,
                        'tasks': []
                    }
                
                task_data = self._format_task_data(task)
                weeks_data[week_num]['tasks'].append(task_data)

            # 週番号順でソート
            sorted_weeks = sorted(weeks_data.values(), key=lambda x: x['week_number'])
            
            return {
                "status": "success",
                "weeks": sorted_weeks,
                "total_tasks": len(tasks)
            }

        except Exception as e:
            logger.error(f"Error getting curriculum tasks: {str(e)}")
            return {
                "status": "error",
                "message": f"課題一覧の取得に失敗しました: {str(e)}"
            }

    def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        新しい課題を作成
        
        Args:
            task_data: 課題データ
            
        Returns:
            Dict: 作成結果
        """
        try:
            # 必須フィールドの検証
            required_fields = ['curriculum_id', 'title', 'week_number', 'task_type']
            for field in required_fields:
                if field not in task_data:
                    return {
                        "status": "error",
                        "message": f"必須フィールド '{field}' が不足しています"
                    }

            # 新しい課題を作成
            task = CurriculumTask(
                curriculum_id=task_data['curriculum_id'],
                title=task_data['title'],
                description=task_data.get('description', ''),
                week_number=task_data['week_number'],
                order_in_week=task_data.get('order_in_week', 1),
                task_type=TaskType(task_data['task_type']),
                estimated_time_minutes=task_data.get('estimated_time_minutes', 60),
                max_score=task_data.get('max_score', 100),
                is_required=task_data.get('is_required', True),
                due_date_type=DueDateType(task_data.get('due_date_type', 'relative')),
                due_date_offset_days=task_data.get('due_date_offset_days', 7),
                instructions=task_data.get('instructions', ''),
                resources=task_data.get('resources', ''),
                created_at=datetime.utcnow()
            )

            db.session.add(task)
            db.session.commit()

            logger.info(f"Task created successfully: {task.id}")
            return {
                "status": "success",
                "message": "課題が作成されました",
                "task_id": task.id,
                "task": self._format_task_data(task)
            }

        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            db.session.rollback()
            return {
                "status": "error",
                "message": f"課題の作成に失敗しました: {str(e)}"
            }

    def update_task(self, task_id: int, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        課題を更新
        
        Args:
            task_id: 課題ID
            task_data: 更新データ
            
        Returns:
            Dict: 更新結果
        """
        try:
            task = CurriculumTask.query.get(task_id)
            if not task:
                return {
                    "status": "error",
                    "message": "課題が見つかりません"
                }

            # 更新可能なフィールドを更新
            updatable_fields = [
                'title', 'description', 'week_number', 'order_in_week',
                'task_type', 'estimated_time_minutes', 'max_score',
                'is_required', 'due_date_type', 'due_date_offset_days',
                'instructions', 'resources'
            ]

            for field in updatable_fields:
                if field in task_data:
                    if field == 'task_type':
                        setattr(task, field, TaskType(task_data[field]))
                    elif field == 'due_date_type':
                        setattr(task, field, DueDateType(task_data[field]))
                    else:
                        setattr(task, field, task_data[field])

            task.updated_at = datetime.utcnow()
            db.session.commit()

            logger.info(f"Task updated successfully: {task_id}")
            return {
                "status": "success",
                "message": "課題が更新されました",
                "task": self._format_task_data(task)
            }

        except Exception as e:
            logger.error(f"Error updating task: {str(e)}")
            db.session.rollback()
            return {
                "status": "error",
                "message": f"課題の更新に失敗しました: {str(e)}"
            }

    def delete_task(self, task_id: int) -> Dict[str, Any]:
        """
        課題を削除
        
        Args:
            task_id: 課題ID
            
        Returns:
            Dict: 削除結果
        """
        try:
            task = CurriculumTask.query.get(task_id)
            if not task:
                return {
                    "status": "error",
                    "message": "課題が見つかりません"
                }

            # 関連する学生進捗をチェック
            progress_count = StudentTaskProgress.query.filter_by(curriculum_task_id=task_id).count()
            if progress_count > 0:
                return {
                    "status": "error",
                    "message": f"この課題には{progress_count}件の学生進捗が関連付けられているため削除できません"
                }

            # ファイル添付を削除
            TaskFileAttachment.query.filter_by(curriculum_task_id=task_id).delete()
            
            # 課題を削除
            db.session.delete(task)
            db.session.commit()

            logger.info(f"Task deleted successfully: {task_id}")
            return {
                "status": "success",
                "message": "課題が削除されました"
            }

        except Exception as e:
            logger.error(f"Error deleting task: {str(e)}")
            db.session.rollback()
            return {
                "status": "error",
                "message": f"課題の削除に失敗しました: {str(e)}"
            }

    def get_task_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        IDで課題を取得
        
        Args:
            task_id: 課題ID
            
        Returns:
            Optional[Dict]: 課題データ（見つからない場合はNone）
        """
        try:
            task = CurriculumTask.query.get(task_id)
            if not task:
                return None
                
            return self._format_task_data(task)

        except Exception as e:
            logger.error(f"Error getting task by ID: {str(e)}")
            return None

    def get_student_tasks(self, curriculum_id: int, student_id: int) -> Dict[str, Any]:
        """
        学生向けの課題一覧を取得
        
        Args:
            curriculum_id: カリキュラムID
            student_id: 学生ID
            
        Returns:
            Dict: 学生用課題データ
        """
        try:
            # 課題一覧を取得
            tasks = CurriculumTask.query.filter_by(curriculum_id=curriculum_id) \
                                       .order_by(CurriculumTask.week_number, CurriculumTask.order_in_week) \
                                       .all()

            # 学生の進捗情報を取得
            progress_records = {
                p.curriculum_task_id: p for p in
                StudentTaskProgress.query.filter_by(student_id=student_id).all()
            }

            # 週ごとにグループ化（進捗情報付き）
            weeks_data = {}
            for task in tasks:
                week_num = task.week_number
                if week_num not in weeks_data:
                    weeks_data[week_num] = {
                        'week_number': week_num,
                        'tasks': []
                    }
                
                task_data = self._format_task_data(task)
                
                # 進捗情報を追加
                progress = progress_records.get(task.id)
                if progress:
                    task_data['progress'] = {
                        'status': progress.status.value,
                        'score': progress.score,
                        'started_at': progress.started_at.isoformat() if progress.started_at else None,
                        'completed_at': progress.completed_at.isoformat() if progress.completed_at else None,
                        'submission_text': progress.submission_text,
                        'feedback': progress.feedback
                    }
                else:
                    task_data['progress'] = {
                        'status': 'not_started',
                        'score': None,
                        'started_at': None,
                        'completed_at': None,
                        'submission_text': None,
                        'feedback': None
                    }

                weeks_data[week_num]['tasks'].append(task_data)

            sorted_weeks = sorted(weeks_data.values(), key=lambda x: x['week_number'])
            
            return {
                "status": "success",
                "weeks": sorted_weeks,
                "total_tasks": len(tasks)
            }

        except Exception as e:
            logger.error(f"Error getting student tasks: {str(e)}")
            return {
                "status": "error",
                "message": f"学生課題一覧の取得に失敗しました: {str(e)}"
            }

    def get_task_types(self) -> List[Dict[str, str]]:
        """課題タイプ一覧を取得"""
        return [
            {"value": task_type.value, "label": task_type.value}
            for task_type in TaskType
        ]

    def get_task_statuses(self) -> List[Dict[str, str]]:
        """課題ステータス一覧を取得"""
        return [
            {"value": status.value, "label": status.value}
            for status in TaskStatus
        ]

    # プライベートメソッド

    def _format_task_data(self, task: CurriculumTask) -> Dict[str, Any]:
        """課題データを辞書形式にフォーマット"""
        return {
            'id': task.id,
            'curriculum_id': task.curriculum_id,
            'title': task.title,
            'description': task.description,
            'week_number': task.week_number,
            'order_in_week': task.order_in_week,
            'task_type': task.task_type.value if task.task_type else None,
            'estimated_time_minutes': task.estimated_time_minutes,
            'max_score': task.max_score,
            'is_required': task.is_required,
            'due_date_type': task.due_date_type.value if task.due_date_type else None,
            'due_date_offset_days': task.due_date_offset_days,
            'instructions': task.instructions,
            'resources': task.resources,
            'created_at': task.created_at.isoformat() if task.created_at else None,
            'updated_at': task.updated_at.isoformat() if task.updated_at else None
        }