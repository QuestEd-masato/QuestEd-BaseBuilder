# -*- coding: utf-8 -*-
"""
TaskProgressService

学生進捗管理専門サービス
進捗計算・統計・完了判定ロジックを担当
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models import (
    CurriculumTask, StudentTaskProgress, TaskFileAttachment,
    TaskStatus, User, db
)

logger = logging.getLogger(__name__)


class TaskProgressService:
    """学生進捗管理専門サービス"""

    def start_task(self, task_id: int, student_id: int) -> Dict[str, Any]:
        """
        課題を開始
        
        Args:
            task_id: 課題ID
            student_id: 学生ID
            
        Returns:
            Dict: 開始結果
        """
        try:
            # 課題の存在確認
            task = CurriculumTask.query.get(task_id)
            if not task:
                return {
                    "status": "error",
                    "message": "課題が見つかりません"
                }

            # 既存の進捗レコードをチェック
            existing_progress = StudentTaskProgress.query.filter_by(
                curriculum_task_id=task_id,
                student_id=student_id
            ).first()

            if existing_progress:
                if existing_progress.status == TaskStatus.COMPLETED:
                    return {
                        "status": "error",
                        "message": "この課題は既に完了しています"
                    }
                else:
                    # 既に開始済みの場合は現在の進捗を返す
                    return {
                        "status": "success",
                        "message": "課題は既に開始されています",
                        "progress": self._format_progress_data(existing_progress)
                    }

            # 新しい進捗レコードを作成
            progress = StudentTaskProgress(
                curriculum_task_id=task_id,
                student_id=student_id,
                status=TaskStatus.IN_PROGRESS,
                started_at=datetime.utcnow(),
                score=0
            )

            db.session.add(progress)
            db.session.commit()

            logger.info(f"Task started: task_id={task_id}, student_id={student_id}")
            return {
                "status": "success",
                "message": "課題を開始しました",
                "progress": self._format_progress_data(progress)
            }

        except Exception as e:
            logger.error(f"Error starting task: {str(e)}")
            db.session.rollback()
            return {
                "status": "error",
                "message": f"課題の開始に失敗しました: {str(e)}"
            }

    def update_task_progress(
        self, task_id: int, student_id: int, progress_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        課題の進捗を更新
        
        Args:
            task_id: 課題ID
            student_id: 学生ID
            progress_data: 進捗データ
            
        Returns:
            Dict: 更新結果
        """
        try:
            progress = StudentTaskProgress.query.filter_by(
                curriculum_task_id=task_id,
                student_id=student_id
            ).first()

            if not progress:
                return {
                    "status": "error",
                    "message": "進捗レコードが見つかりません。まず課題を開始してください"
                }

            # 更新可能なフィールドを更新
            updatable_fields = ['submission_text', 'score']
            for field in updatable_fields:
                if field in progress_data:
                    setattr(progress, field, progress_data[field])

            progress.updated_at = datetime.utcnow()
            
            # ステータス更新ロジック
            if 'status' in progress_data:
                new_status = TaskStatus(progress_data['status'])
                progress.status = new_status
                
                if new_status == TaskStatus.COMPLETED:
                    progress.completed_at = datetime.utcnow()

            db.session.commit()

            logger.info(f"Task progress updated: task_id={task_id}, student_id={student_id}")
            return {
                "status": "success",
                "message": "進捗が更新されました",
                "progress": self._format_progress_data(progress)
            }

        except Exception as e:
            logger.error(f"Error updating task progress: {str(e)}")
            db.session.rollback()
            return {
                "status": "error",
                "message": f"進捗の更新に失敗しました: {str(e)}"
            }

    def submit_task(
        self, task_id: int, student_id: int, submission_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        課題を提出
        
        Args:
            task_id: 課題ID
            student_id: 学生ID
            submission_data: 提出データ
            
        Returns:
            Dict: 提出結果
        """
        try:
            progress = StudentTaskProgress.query.filter_by(
                curriculum_task_id=task_id,
                student_id=student_id
            ).first()

            if not progress:
                return {
                    "status": "error",
                    "message": "進捗レコードが見つかりません"
                }

            if progress.status == TaskStatus.COMPLETED:
                return {
                    "status": "error",
                    "message": "この課題は既に提出済みです"
                }

            # 提出データを更新
            progress.submission_text = submission_data.get('submission_text', '')
            progress.status = TaskStatus.SUBMITTED
            progress.submitted_at = datetime.utcnow()

            db.session.commit()

            logger.info(f"Task submitted: task_id={task_id}, student_id={student_id}")
            return {
                "status": "success",
                "message": "課題が提出されました",
                "progress": self._format_progress_data(progress)
            }

        except Exception as e:
            logger.error(f"Error submitting task: {str(e)}")
            db.session.rollback()
            return {
                "status": "error",
                "message": f"課題の提出に失敗しました: {str(e)}"
            }

    def get_pending_submissions(self, teacher_id: int) -> Dict[str, Any]:
        """
        承認待ちの提出物を取得
        
        Args:
            teacher_id: 教師ID
            
        Returns:
            Dict: 承認待ち提出物一覧
        """
        try:
            # 教師のカリキュラムに関連する提出待ち課題を取得
            submissions = db.session.query(StudentTaskProgress) \
                .join(CurriculumTask) \
                .join(User, StudentTaskProgress.student_id == User.id) \
                .filter(
                    StudentTaskProgress.status == TaskStatus.SUBMITTED,
                    CurriculumTask.curriculum_id.in_(
                        db.session.query(CurriculumTask.curriculum_id).distinct()
                        .filter_by(created_by=teacher_id)
                    )
                ) \
                .order_by(StudentTaskProgress.submitted_at.desc()) \
                .all()

            submissions_data = []
            for submission in submissions:
                task = submission.curriculum_task
                student = User.query.get(submission.student_id)
                
                submission_data = {
                    'id': submission.id,
                    'task': {
                        'id': task.id,
                        'title': task.title,
                        'week_number': task.week_number,
                        'max_score': task.max_score
                    },
                    'student': {
                        'id': student.id,
                        'username': student.username,
                        'full_name': student.full_name
                    },
                    'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
                    'submission_text': submission.submission_text,
                    'score': submission.score
                }
                submissions_data.append(submission_data)

            return {
                "status": "success",
                "submissions": submissions_data,
                "total_count": len(submissions_data)
            }

        except Exception as e:
            logger.error(f"Error getting pending submissions: {str(e)}")
            return {
                "status": "error",
                "message": f"承認待ち提出物の取得に失敗しました: {str(e)}"
            }

    def approve_submission(
        self, progress_id: int, teacher_id: int, approval_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        提出物を承認
        
        Args:
            progress_id: 進捗ID
            teacher_id: 教師ID
            approval_data: 承認データ
            
        Returns:
            Dict: 承認結果
        """
        try:
            progress = StudentTaskProgress.query.get(progress_id)
            if not progress:
                return {
                    "status": "error",
                    "message": "進捗レコードが見つかりません"
                }

            if progress.status != TaskStatus.SUBMITTED:
                return {
                    "status": "error",
                    "message": "提出済みの課題のみ承認できます"
                }

            # 承認情報を更新
            progress.status = TaskStatus.COMPLETED
            progress.score = approval_data.get('score', progress.score)
            progress.feedback = approval_data.get('feedback', '')
            progress.approved_by = teacher_id
            progress.approved_at = datetime.utcnow()
            progress.completed_at = datetime.utcnow()

            db.session.commit()

            logger.info(f"Submission approved: progress_id={progress_id}, teacher_id={teacher_id}")
            return {
                "status": "success",
                "message": "提出物が承認されました",
                "progress": self._format_progress_data(progress)
            }

        except Exception as e:
            logger.error(f"Error approving submission: {str(e)}")
            db.session.rollback()
            return {
                "status": "error",
                "message": f"提出物の承認に失敗しました: {str(e)}"
            }

    def request_revision(
        self, progress_id: int, teacher_id: int, revision_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        修正を要求
        
        Args:
            progress_id: 進捗ID
            teacher_id: 教師ID
            revision_data: 修正要求データ
            
        Returns:
            Dict: 修正要求結果
        """
        try:
            progress = StudentTaskProgress.query.get(progress_id)
            if not progress:
                return {
                    "status": "error",
                    "message": "進捗レコードが見つかりません"
                }

            if progress.status != TaskStatus.SUBMITTED:
                return {
                    "status": "error",
                    "message": "提出済みの課題のみ修正要求できます"
                }

            # 修正要求情報を更新
            progress.status = TaskStatus.REVISION_REQUESTED
            progress.feedback = revision_data.get('feedback', '')
            progress.reviewed_by = teacher_id
            progress.reviewed_at = datetime.utcnow()

            db.session.commit()

            logger.info(f"Revision requested: progress_id={progress_id}, teacher_id={teacher_id}")
            return {
                "status": "success",
                "message": "修正が要求されました",
                "progress": self._format_progress_data(progress)
            }

        except Exception as e:
            logger.error(f"Error requesting revision: {str(e)}")
            db.session.rollback()
            return {
                "status": "error",
                "message": f"修正要求に失敗しました: {str(e)}"
            }

    def get_student_progress_summary(self, student_id: int, curriculum_id: int) -> Dict[str, Any]:
        """
        学生の進捗サマリーを取得
        
        Args:
            student_id: 学生ID
            curriculum_id: カリキュラムID
            
        Returns:
            Dict: 進捗サマリー
        """
        try:
            # 全課題数を取得
            total_tasks = CurriculumTask.query.filter_by(curriculum_id=curriculum_id).count()
            
            # 学生の進捗を集計
            progress_summary = db.session.query(
                StudentTaskProgress.status,
                db.func.count(StudentTaskProgress.id).label('count')
            ).join(CurriculumTask) \
             .filter(
                 StudentTaskProgress.student_id == student_id,
                 CurriculumTask.curriculum_id == curriculum_id
             ).group_by(StudentTaskProgress.status).all()

            # ステータス別カウント
            status_counts = {status.value: 0 for status in TaskStatus}
            for status, count in progress_summary:
                status_counts[status.value] = count

            # 未開始の課題数を計算
            started_tasks = sum(status_counts.values())
            status_counts['not_started'] = max(0, total_tasks - started_tasks)

            return {
                "status": "success",
                "summary": {
                    "total_tasks": total_tasks,
                    "status_counts": status_counts,
                    "completion_rate": (status_counts.get('completed', 0) / total_tasks * 100) if total_tasks > 0 else 0
                }
            }

        except Exception as e:
            logger.error(f"Error getting student progress summary: {str(e)}")
            return {
                "status": "error",
                "message": f"進捗サマリーの取得に失敗しました: {str(e)}"
            }

    # プライベートメソッド

    def _format_progress_data(self, progress: StudentTaskProgress) -> Dict[str, Any]:
        """進捗データを辞書形式にフォーマット"""
        return {
            'id': progress.id,
            'curriculum_task_id': progress.curriculum_task_id,
            'student_id': progress.student_id,
            'status': progress.status.value if progress.status else None,
            'score': progress.score,
            'started_at': progress.started_at.isoformat() if progress.started_at else None,
            'completed_at': progress.completed_at.isoformat() if progress.completed_at else None,
            'submitted_at': progress.submitted_at.isoformat() if progress.submitted_at else None,
            'approved_at': progress.approved_at.isoformat() if progress.approved_at else None,
            'reviewed_at': progress.reviewed_at.isoformat() if progress.reviewed_at else None,
            'submission_text': progress.submission_text,
            'feedback': progress.feedback,
            'approved_by': progress.approved_by,
            'reviewed_by': progress.reviewed_by,
            'created_at': progress.created_at.isoformat() if progress.created_at else None,
            'updated_at': progress.updated_at.isoformat() if progress.updated_at else None
        }