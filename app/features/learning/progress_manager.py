"""
Learning Progress Manager
=========================
統合学習進捗管理システム

既存の重複するサービスを統合:
- UnitProgressManager
- UnifiedProgressService 
- UnitCompletionService
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from app.core.base_service import BaseService
from app.models import StudentUnitSelection, CurriculumUnit, User


class LearningProgressManager(BaseService):
    """統合学習進捗管理クラス"""
    
    def get_service_name(self) -> str:
        return "LearningProgressManager"
    
    def get_student_progress(self, student_id: int, unit_id: Optional[int] = None) -> Dict[str, Any]:
        """
        学生の学習進捗を取得
        
        Args:
            student_id: 学生ID
            unit_id: 単元ID（省略時は全単元）
            
        Returns:
            Dict: 進捗情報
        """
        try:
            self.ensure_permission(['student', 'teacher', 'admin'])
            
            # 権限チェック（学生は自分のみ、教師は担当クラス）
            if not self._can_access_student_data(student_id):
                raise PermissionError("Student data access denied")
            
            filters = {'student_id': student_id}
            if unit_id:
                filters['unit_id'] = unit_id
            
            from app.core.data_access import DataAccessLayer
            dal = DataAccessLayer()
            
            selections = dal.safe_query(StudentUnitSelection, filters=filters)
            
            # 進捗データの整形
            progress_data = {
                'student_id': student_id,
                'total_units': len(selections),
                'completed_units': len([s for s in selections if s.status == 'completed']),
                'in_progress_units': len([s for s in selections if s.status == 'in_progress']),
                'units': []
            }
            
            for selection in selections:
                unit_data = {
                    'unit_id': selection.unit_id,
                    'unit_title': selection.unit.title if selection.unit else 'Unknown',
                    'status': selection.status,
                    'progress_percentage': selection.progress_percentage,
                    'started_at': selection.started_at.isoformat() if selection.started_at else None,
                    'completed_at': selection.completed_at.isoformat() if selection.completed_at else None,
                    'approval_status': selection.approval_status
                }
                progress_data['units'].append(unit_data)
            
            # 完了率計算
            if progress_data['total_units'] > 0:
                progress_data['completion_rate'] = progress_data['completed_units'] / progress_data['total_units']
            else:
                progress_data['completion_rate'] = 0.0
            
            self.log_info(f"Progress retrieved for student {student_id}")
            return progress_data
            
        except Exception as e:
            self.log_error(f"Get student progress error: {str(e)}")
            raise
    
    def update_unit_progress(self, student_id: int, unit_id: int, 
                           progress_percentage: float, completed_items: Optional[List[int]] = None) -> bool:
        """
        単元進捗を更新
        
        Args:
            student_id: 学生ID
            unit_id: 単元ID
            progress_percentage: 進捗率（0-100）
            completed_items: 完了アイテムIDリスト
            
        Returns:
            bool: 更新成功フラグ
        """
        try:
            self.ensure_permission(['student', 'teacher', 'admin'])
            
            if not self._can_update_student_progress(student_id):
                raise PermissionError("Progress update denied")
            
            from app.core.data_access import DataAccessLayer
            dal = DataAccessLayer()
            
            # 単元選択の取得
            selection = dal.safe_query(
                StudentUnitSelection,
                filters={'student_id': student_id, 'unit_id': unit_id}
            )
            
            if not selection:
                # 新規選択の作成
                selection = StudentUnitSelection(
                    student_id=student_id,
                    unit_id=unit_id,
                    status='not_started',
                    progress_percentage=0,
                    created_at=datetime.utcnow()
                )
                dal.safe_create(selection)
                selection = selection  # 作成後のインスタンスを取得
            else:
                selection = selection[0]  # リストの最初の要素
            
            # 進捗更新
            updates = {
                'progress_percentage': min(100.0, max(0.0, progress_percentage)),
                'last_activity_at': datetime.utcnow()
            }
            
            # ステータス更新
            if updates['progress_percentage'] == 0:
                updates['status'] = 'not_started'
            elif updates['progress_percentage'] >= 100:
                updates['status'] = 'completed'
                if not selection.completed_at:
                    updates['completed_at'] = datetime.utcnow()
            else:
                updates['status'] = 'in_progress'
                if not selection.started_at:
                    updates['started_at'] = datetime.utcnow()
            
            success = dal.safe_update(selection, updates)
            
            # 完了アイテムの処理
            if completed_items and success:
                self._update_completed_items(student_id, unit_id, completed_items)
            
            if success:
                self.log_info(f"Progress updated: student {student_id}, unit {unit_id}, progress {progress_percentage}%")
            
            return success
            
        except Exception as e:
            self.log_error(f"Update unit progress error: {str(e)}")
            return False
    
    def request_completion(self, student_id: int, unit_id: int, comment: str = '') -> Dict[str, Any]:
        """
        単元完了申請
        
        Args:
            student_id: 学生ID
            unit_id: 単元ID
            comment: 申請コメント
            
        Returns:
            Dict: 申請結果
        """
        try:
            self.ensure_permission(['student'])
            
            if student_id != self.get_current_user_id():
                raise PermissionError("Can only request completion for yourself")
            
            from app.core.data_access import DataAccessLayer
            dal = DataAccessLayer()
            
            # 単元選択の確認
            selection = dal.safe_query(
                StudentUnitSelection,
                filters={'student_id': student_id, 'unit_id': unit_id}
            )
            
            if not selection:
                return {'success': False, 'message': '単元が選択されていません'}
            
            selection = selection[0]
            
            if selection.status == 'completed':
                return {'success': False, 'message': '既に完了しています'}
            
            if selection.progress_percentage < 80:
                return {'success': False, 'message': '完了申請には80%以上の進捗が必要です'}
            
            # 申請処理
            updates = {
                'approval_status': 'pending',
                'completion_request_date': datetime.utcnow(),
                'student_comments': comment
            }
            
            success = dal.safe_update(selection, updates)
            
            if success:
                result = {
                    'success': True,
                    'message': '完了申請を送信しました',
                    'requires_approval': True
                }
                self.log_info(f"Completion requested: student {student_id}, unit {unit_id}")
            else:
                result = {'success': False, 'message': '申請の送信に失敗しました'}
            
            return result
            
        except Exception as e:
            self.log_error(f"Request completion error: {str(e)}")
            return {'success': False, 'message': 'エラーが発生しました'}
    
    def approve_completion(self, selection_id: int, teacher_id: int, comment: str = '') -> Dict[str, Any]:
        """
        完了申請の承認
        
        Args:
            selection_id: 選択ID
            teacher_id: 教師ID
            comment: 承認コメント
            
        Returns:
            Dict: 承認結果
        """
        try:
            self.ensure_permission(['teacher', 'admin'])
            
            from app.core.data_access import DataAccessLayer
            dal = DataAccessLayer()
            
            selection = dal.safe_get_by_id(StudentUnitSelection, selection_id)
            
            if not selection:
                return {'success': False, 'message': '申請が見つかりません'}
            
            if selection.approval_status != 'pending':
                return {'success': False, 'message': '承認待ち状態ではありません'}
            
            # 教師の権限確認
            if not self._can_approve_student(selection.student_id, teacher_id):
                raise PermissionError("Cannot approve this student's completion")
            
            # 承認処理
            updates = {
                'approval_status': 'approved',
                'status': 'completed',
                'progress_percentage': 100.0,
                'completed_at': datetime.utcnow(),
                'approved_by': teacher_id,
                'approved_at': datetime.utcnow(),
                'teacher_comments': comment
            }
            
            success = dal.safe_update(selection, updates)
            
            if success:
                result = {'success': True, 'message': '完了を承認しました'}
                self.log_info(f"Completion approved: selection {selection_id}, teacher {teacher_id}")
            else:
                result = {'success': False, 'message': '承認処理に失敗しました'}
            
            return result
            
        except Exception as e:
            self.log_error(f"Approve completion error: {str(e)}")
            return {'success': False, 'message': 'エラーが発生しました'}
    
    # プライベートメソッド
    
    def _can_access_student_data(self, student_id: int) -> bool:
        """学生データへのアクセス権限確認"""
        current_user_id = self.get_current_user_id()
        
        # 管理者は全アクセス可能
        if self.check_permission(['admin']):
            return True
        
        # 学生は自分のデータのみ
        if self.check_permission(['student']):
            return current_user_id == student_id
        
        # 教師は担当クラスの学生のみ
        if self.check_permission(['teacher']):
            # TODO: 教師-学生の関係チェック実装
            return True
        
        return False
    
    def _can_update_student_progress(self, student_id: int) -> bool:
        """進捗更新権限確認"""
        return self._can_access_student_data(student_id)
    
    def _can_approve_student(self, student_id: int, teacher_id: int) -> bool:
        """学生承認権限確認"""
        # TODO: 教師が担当している学生かチェック
        return True
    
    def _update_completed_items(self, student_id: int, unit_id: int, completed_items: List[int]):
        """完了アイテムの更新"""
        # TODO: UnitItemMapping関連の実装
        pass