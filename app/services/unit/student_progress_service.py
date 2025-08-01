# -*- coding: utf-8 -*-
"""
StudentProgressService

学生の単元進捗管理専門サービス
ProgressManagerの進捗更新ロジックを抽出・統合（重複排除）
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask_login import current_user

from app.models import (
    CurriculumUnit, StudentUnitSelection, UnitItemMapping, db
)

logger = logging.getLogger(__name__)


class StudentProgressService:
    """学生進捗管理専門サービス"""

    def update_progress(self, unit_id: int, progress_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        学生の単元進捗を更新
        
        Args:
            unit_id: 単元ID
            progress_data: 進捗データ
            
        Returns:
            Dict: 更新結果
        """
        try:
            logger.info(f"Updating progress for unit {unit_id} by student {current_user.id}")
            
            # 単元の存在確認
            unit = CurriculumUnit.query.get(unit_id)
            if not unit:
                return {
                    "success": False,
                    "message": "指定された単元が見つかりません"
                }

            # 学生の選択レコード取得または作成
            selection = self._get_or_create_selection(unit_id)
            
            # 進捗データの更新
            updated_selection = self._update_selection_progress(selection, progress_data)
            
            # 完了判定
            completion_status = self._check_completion_status(updated_selection, unit)
            
            db.session.commit()
            
            result = {
                "success": True,
                "message": "進捗が正常に更新されました",
                "progress": {
                    "unit_id": unit_id,
                    "progress_percentage": updated_selection.progress_percentage,
                    "status": updated_selection.status,
                    "completion_status": completion_status,
                    "updated_at": datetime.utcnow().isoformat()
                }
            }
            
            logger.info(f"Progress updated successfully for unit {unit_id}")
            return result

        except Exception as e:
            logger.error(f"Error updating progress for unit {unit_id}: {str(e)}")
            db.session.rollback()
            return {
                "success": False,
                "message": f"進捗更新中にエラーが発生しました: {str(e)}"
            }

    def get_completion_history(self, limit: int = 50) -> Dict[str, Any]:
        """
        学生の完了履歴を取得
        
        Args:
            limit: 取得件数上限
            
        Returns:
            Dict: 完了履歴データ
        """
        try:
            logger.info(f"Getting completion history for student {current_user.id}")
            
            # 完了済みの選択を取得
            completed_selections = StudentUnitSelection.query.filter_by(
                student_id=current_user.id,
                status='completed'
            ).order_by(StudentUnitSelection.completed_at.desc()).limit(limit).all()
            
            history_data = []
            for selection in completed_selections:
                unit = CurriculumUnit.query.get(selection.unit_id)
                if unit:
                    history_item = {
                        "selection_id": selection.id,
                        "unit_id": unit.id,
                        "unit_title": unit.title,
                        "subject_id": unit.subject_id,
                        "progress_percentage": selection.progress_percentage,
                        "completed_at": selection.completed_at.isoformat() if selection.completed_at else None,
                        "selected_at": selection.selected_at.isoformat() if selection.selected_at else None,
                        "study_time_minutes": selection.study_time_minutes or 0
                    }
                    history_data.append(history_item)
            
            return {
                "success": True,
                "history": history_data,
                "total_completed": len(history_data)
            }

        except Exception as e:
            logger.error(f"Error getting completion history: {str(e)}")
            return {
                "success": False,
                "message": f"完了履歴の取得中にエラーが発生しました: {str(e)}"
            }

    def get_user_selections(self, status_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        ユーザーの単元選択一覧を取得
        
        Args:
            status_filter: ステータスフィルタ
            
        Returns:
            Dict: 選択一覧データ
        """
        try:
            logger.info(f"Getting unit selections for user {current_user.id}")
            
            query = StudentUnitSelection.query.filter_by(student_id=current_user.id)
            
            if status_filter:
                query = query.filter(StudentUnitSelection.status == status_filter)
            
            selections = query.order_by(StudentUnitSelection.selected_at.desc()).all()
            
            selections_data = []
            for selection in selections:
                unit = CurriculumUnit.query.get(selection.unit_id)
                if unit:
                    selection_item = {
                        "selection_id": selection.id,
                        "unit_id": unit.id,
                        "unit_title": unit.title,
                        "subject_id": unit.subject_id,
                        "progress_percentage": selection.progress_percentage or 0,
                        "status": selection.status,
                        "selected_at": selection.selected_at.isoformat() if selection.selected_at else None,
                        "last_accessed": selection.last_accessed.isoformat() if selection.last_accessed else None,
                        "study_time_minutes": selection.study_time_minutes or 0
                    }
                    selections_data.append(selection_item)
            
            return {
                "success": True,
                "selections": selections_data,
                "total_count": len(selections_data)
            }

        except Exception as e:
            logger.error(f"Error getting user selections: {str(e)}")
            return {
                "success": False,
                "message": f"選択一覧の取得中にエラーが発生しました: {str(e)}"
            }

    def batch_update_progress(self, progress_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        複数の進捗を一括更新
        
        Args:
            progress_updates: 進捗更新データのリスト
            
        Returns:
            Dict: 一括更新結果
        """
        try:
            logger.info(f"Batch updating progress for {len(progress_updates)} units")
            
            successful_updates = []
            failed_updates = []
            
            for update_data in progress_updates:
                unit_id = update_data.get('unit_id')
                if not unit_id:
                    failed_updates.append({
                        "unit_id": None,
                        "error": "unit_idが指定されていません"
                    })
                    continue
                
                try:
                    result = self.update_progress(unit_id, update_data)
                    if result['success']:
                        successful_updates.append({
                            "unit_id": unit_id,
                            "progress": result['progress']
                        })
                    else:
                        failed_updates.append({
                            "unit_id": unit_id,
                            "error": result['message']
                        })
                        
                except Exception as e:
                    failed_updates.append({
                        "unit_id": unit_id,
                        "error": str(e)
                    })
            
            return {
                "success": len(failed_updates) == 0,
                "successful_updates": successful_updates,
                "failed_updates": failed_updates,
                "total_processed": len(progress_updates),
                "success_count": len(successful_updates),
                "failure_count": len(failed_updates)
            }

        except Exception as e:
            logger.error(f"Error in batch progress update: {str(e)}")
            return {
                "success": False,
                "message": f"一括進捗更新中にエラーが発生しました: {str(e)}"
            }

    def _get_or_create_selection(self, unit_id: int) -> StudentUnitSelection:
        """選択レコードの取得または作成"""
        selection = StudentUnitSelection.query.filter_by(
            unit_id=unit_id,
            student_id=current_user.id
        ).first()
        
        if not selection:
            selection = StudentUnitSelection(
                unit_id=unit_id,
                student_id=current_user.id,
                selected_at=datetime.utcnow(),
                progress_percentage=0,
                status='started'
            )
            db.session.add(selection)
            db.session.flush()  # IDを取得するため
            logger.info(f"Created new selection record for unit {unit_id}")
        
        return selection

    def _update_selection_progress(self, selection: StudentUnitSelection, 
                                 progress_data: Dict[str, Any]) -> StudentUnitSelection:
        """選択レコードの進捗情報更新"""
        # 進捗率の更新
        if 'progress_percentage' in progress_data:
            new_progress = progress_data['progress_percentage']
            if 0 <= new_progress <= 100:
                selection.progress_percentage = new_progress
        
        # 学習時間の更新
        if 'study_time_minutes' in progress_data:
            additional_time = progress_data['study_time_minutes']
            if additional_time > 0:
                current_time = selection.study_time_minutes or 0
                selection.study_time_minutes = current_time + additional_time
        
        # アクセス時刻の更新
        selection.last_accessed = datetime.utcnow()
        
        # ステータスの更新
        if 'status' in progress_data:
            new_status = progress_data['status']
            if new_status in ['started', 'in_progress', 'completed']:
                selection.status = new_status
                
                if new_status == 'completed':
                    selection.completed_at = datetime.utcnow()
        
        return selection

    def _check_completion_status(self, selection: StudentUnitSelection, 
                               unit: CurriculumUnit) -> Dict[str, Any]:
        """完了状況の判定"""
        completion_status = {
            "is_completed": selection.status == 'completed',
            "progress_percentage": selection.progress_percentage or 0,
            "meets_completion_criteria": False
        }
        
        # 完了基準の判定（80%以上で完了とみなす）
        if selection.progress_percentage and selection.progress_percentage >= 80:
            completion_status["meets_completion_criteria"] = True
            
            # 自動完了処理（オプション）
            if selection.status != 'completed':
                selection.status = 'completed'
                selection.completed_at = datetime.utcnow()
                completion_status["auto_completed"] = True
        
        return completion_status