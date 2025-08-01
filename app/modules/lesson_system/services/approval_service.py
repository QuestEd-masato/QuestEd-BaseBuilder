"""
レッスン承認サービス

レッスン完了申請・承認機能のビジネスロジックを担当
Phase5で追加された承認ワークフロー機能を管理
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import desc

from app.models import db, User, Class, ClassEnrollment
from ..models.lesson_models import StudentLessonProgress, CurriculumLesson
from .progress_service import LessonProgressService


class LessonApprovalService:
    """レッスン承認管理サービス"""
    
    @staticmethod
    def submit_completion_request(student_id: int, lesson_id: int, notes: str = None) -> Dict[str, Any]:
        """生徒からの完了申請処理
        
        Args:
            student_id: 申請する生徒のID
            lesson_id: 申請対象のレッスンID
            notes: 申請時のメモ（任意）
            
        Returns:
            Dict[str, Any]: 処理結果
                - success: bool
                - message: str
                - progress_id: int (成功時)
        """
        try:
            # 進捗レコードの取得または作成
            progress = LessonProgressService.get_student_progress(student_id, lesson_id)
            
            if not progress:
                current_app.logger.warning(f"No progress found for student {student_id}, lesson {lesson_id}")
                return {
                    'success': False,
                    'message': 'レッスンの進捗が見つかりません。先にレッスンを開始してください。'
                }
            
            # 申請可能かチェック
            if not progress.can_request_completion():
                return {
                    'success': False,
                    'message': f'完了申請の条件を満たしていません。進捗率: {progress.completion_percentage}%（80%以上必要）'
                }
            
            # 既に申請済みかチェック
            if progress.approval_status == 'pending':
                return {
                    'success': False,
                    'message': '既に完了申請が送信されています。教師の承認をお待ちください。'
                }
            
            # 完了申請の実行
            progress.request_completion(notes)
            
            current_app.logger.info(f"Completion request submitted: student {student_id}, lesson {lesson_id}")
            
            return {
                'success': True,
                'message': '完了申請を送信しました。教師の承認をお待ちください。',
                'progress_id': progress.id
            }
            
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error in submit_completion_request: {e}")
            db.session.rollback()
            return {
                'success': False,
                'message': 'データベースエラーが発生しました。'
            }
        except Exception as e:
            current_app.logger.error(f"Unexpected error in submit_completion_request: {e}")
            return {
                'success': False,
                'message': '予期しないエラーが発生しました。'
            }
    
    @staticmethod
    def approve_lesson(teacher_id: int, progress_id: int, comments: str = None) -> Dict[str, Any]:
        """教師による承認処理
        
        Args:
            teacher_id: 承認する教師のID
            progress_id: 承認対象の進捗レコードID
            comments: 承認時のコメント（任意）
            
        Returns:
            Dict[str, Any]: 処理結果
                - success: bool
                - message: str
                - lesson_title: str (成功時)
        """
        try:
            # 進捗レコードの取得
            progress = StudentLessonProgress.query.get(progress_id)
            if not progress:
                return {
                    'success': False,
                    'message': '指定された進捗レコードが見つかりません。'
                }
            
            # 承認待ち状態かチェック
            if progress.approval_status != 'pending':
                return {
                    'success': False,
                    'message': f'承認待ち状態ではありません。現在の状態: {progress.get_approval_status_label()}'
                }
            
            # 教師の権限確認
            lesson = CurriculumLesson.query.get(progress.lesson_id)
            if not lesson:
                return {
                    'success': False,
                    'message': 'レッスンが見つかりません。'
                }
            
            # カリキュラムから担当教師を確認（簡易版チェック）
            # 本来はより厳密な権限チェックが必要だが、Phase5では基本実装
            user = User.query.get(teacher_id)
            if not user or user.role != 'teacher':
                return {
                    'success': False,
                    'message': '教師権限が必要です。'
                }
            
            # 承認の実行
            progress.approve_completion(teacher_id, comments)
            
            current_app.logger.info(f"Lesson approved: teacher {teacher_id}, progress {progress_id}")
            
            return {
                'success': True,
                'message': 'レッスン完了を承認しました。',
                'lesson_title': lesson.title
            }
            
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error in approve_lesson: {e}")
            db.session.rollback()
            return {
                'success': False,
                'message': 'データベースエラーが発生しました。'
            }
        except Exception as e:
            current_app.logger.error(f"Unexpected error in approve_lesson: {e}")
            return {
                'success': False,
                'message': '予期しないエラーが発生しました。'
            }
    
    @staticmethod
    def reject_lesson(teacher_id: int, progress_id: int, reason: str) -> Dict[str, Any]:
        """教師による却下処理
        
        Args:
            teacher_id: 却下する教師のID
            progress_id: 却下対象の進捗レコードID
            reason: 却下理由（必須）
            
        Returns:
            Dict[str, Any]: 処理結果
                - success: bool
                - message: str
                - lesson_title: str (成功時)
        """
        try:
            # 却下理由の必須チェック
            if not reason or not reason.strip():
                return {
                    'success': False,
                    'message': '却下理由を入力してください。'
                }
            
            # 進捗レコードの取得
            progress = StudentLessonProgress.query.get(progress_id)
            if not progress:
                return {
                    'success': False,
                    'message': '指定された進捗レコードが見つかりません。'
                }
            
            # 承認待ち状態かチェック
            if progress.approval_status != 'pending':
                return {
                    'success': False,
                    'message': f'承認待ち状態ではありません。現在の状態: {progress.get_approval_status_label()}'
                }
            
            # 教師の権限確認
            lesson = CurriculumLesson.query.get(progress.lesson_id)
            if not lesson:
                return {
                    'success': False,
                    'message': 'レッスンが見つかりません。'
                }
            
            user = User.query.get(teacher_id)
            if not user or user.role != 'teacher':
                return {
                    'success': False,
                    'message': '教師権限が必要です。'
                }
            
            # 却下の実行
            progress.reject_completion(teacher_id, reason)
            
            current_app.logger.info(f"Lesson rejected: teacher {teacher_id}, progress {progress_id}, reason: {reason}")
            
            return {
                'success': True,
                'message': 'レッスン完了申請を却下しました。',
                'lesson_title': lesson.title
            }
            
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error in reject_lesson: {e}")
            db.session.rollback()
            return {
                'success': False,
                'message': 'データベースエラーが発生しました。'
            }
        except Exception as e:
            current_app.logger.error(f"Unexpected error in reject_lesson: {e}")
            return {
                'success': False,
                'message': '予期しないエラーが発生しました。'
            }
    
    @staticmethod
    def get_pending_approvals(teacher_id: int, class_id: int = None) -> List[Dict[str, Any]]:
        """承認待ちレッスン一覧取得
        
        Args:
            teacher_id: 教師のID
            class_id: 特定のクラスに絞り込む場合のクラスID（任意）
            
        Returns:
            List[Dict[str, Any]]: 承認待ちレッスンのリスト
                各要素には以下が含まれる:
                - progress_id: int
                - student_name: str
                - lesson_title: str
                - completion_request_date: str
                - completion_percentage: int
                - reflection: str
        """
        try:
            # 基本クエリ: 承認待ち状態の進捗レコード
            query = db.session.query(
                StudentLessonProgress,
                User.full_name.label('student_name'),
                CurriculumLesson.title.label('lesson_title')
            ).join(
                User, StudentLessonProgress.student_id == User.id
            ).join(
                CurriculumLesson, StudentLessonProgress.lesson_id == CurriculumLesson.id
            ).filter(
                StudentLessonProgress.approval_status == 'pending'
            )
            
            # class_id指定がある場合の絞り込み
            if class_id:
                # 指定されたクラスの生徒のみに絞り込み
                query = query.join(
                    ClassEnrollment, StudentLessonProgress.student_id == ClassEnrollment.student_id
                ).filter(
                    ClassEnrollment.class_id == class_id,
                    ClassEnrollment.is_active == True
                )
            
            # 申請日時順でソート（新しい順）
            query = query.order_by(desc(StudentLessonProgress.completion_request_date))
            
            results = query.all()
            
            # 結果を辞書形式に変換
            pending_approvals = []
            for progress, student_name, lesson_title in results:
                pending_approvals.append({
                    'progress_id': progress.id,
                    'student_id': progress.student_id,
                    'student_name': student_name or 'Unknown',
                    'lesson_id': progress.lesson_id,
                    'lesson_title': lesson_title,
                    'completion_request_date': progress.completion_request_date.isoformat() if progress.completion_request_date else None,
                    'completion_percentage': progress.completion_percentage,
                    'reflection': progress.reflection,
                    'time_spent_minutes': progress.time_spent_minutes
                })
            
            current_app.logger.info(f"Retrieved {len(pending_approvals)} pending approvals for teacher {teacher_id}")
            
            return pending_approvals
            
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error in get_pending_approvals: {e}")
            return []
        except Exception as e:
            current_app.logger.error(f"Unexpected error in get_pending_approvals: {e}")
            return []