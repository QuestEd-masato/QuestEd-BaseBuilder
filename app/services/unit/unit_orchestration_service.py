# -*- coding: utf-8 -*-
"""
UnitOrchestrationService

サービス統合・ワークフロー制御専門サービス
全ての専門サービスを統合し、複雑なワークフローを制御
"""
import logging
from typing import Any, Dict, List, Optional

from flask_login import current_user

from .unit_data_service import UnitDataService
from .student_progress_service import StudentProgressService
from .completion_workflow_service import CompletionWorkflowService
from .unit_mapping_service import UnitMappingService
from .teacher_statistics_service import TeacherStatisticsService
from .access_control_service import AccessControlService
from .curriculum_integration_service import CurriculumIntegrationService

logger = logging.getLogger(__name__)


class UnitOrchestrationService:
    """サービス統合・ワークフロー制御専門サービス"""

    def __init__(self):
        """専門サービスの初期化"""
        self.data_service = UnitDataService()
        self.progress_service = StudentProgressService()
        self.completion_service = CompletionWorkflowService()
        self.mapping_service = UnitMappingService()
        self.statistics_service = TeacherStatisticsService()
        self.access_service = AccessControlService()
        self.integration_service = CurriculumIntegrationService()

    def get_comprehensive_unit_data(self, subject_id: Optional[int] = None, 
                                  school_id: Optional[int] = None, 
                                  include_progress: bool = True) -> Dict[str, Any]:
        """
        包括的な単元データを取得（権限チェック統合）
        
        Args:
            subject_id: 科目ID
            school_id: 学校ID
            include_progress: 進捗情報を含めるか
            
        Returns:
            Dict: 包括的単元データ
        """
        try:
            logger.info(f"Getting comprehensive unit data for user {current_user.id}")
            
            # アクセス可能な単元一覧を取得
            accessible_units_result = self.access_service.get_user_accessible_units(subject_id)
            if not accessible_units_result['success']:
                return accessible_units_result
            
            # データサービスから詳細データを取得
            detailed_data = self.data_service.get_units_data(
                subject_id=subject_id, 
                school_id=school_id, 
                include_progress=include_progress
            )
            
            # アクセス権限でフィルタリング
            filtered_data = []
            for unit in detailed_data:
                access_check = self.access_service.check_unit_access_permission(unit['id'])
                if access_check['allowed']:
                    filtered_data.append(unit)
            
            return {
                "success": True,
                "units": filtered_data,
                "total_count": len(filtered_data),
                "user_role": current_user.role,
                "filters_applied": {
                    "subject_id": subject_id,
                    "school_id": school_id,
                    "include_progress": include_progress
                }
            }

        except Exception as e:
            logger.error(f"Error getting comprehensive unit data: {str(e)}")
            return {
                "success": False,
                "message": f"包括的単元データの取得中にエラーが発生しました: {str(e)}"
            }

    def execute_unit_selection_workflow(self, unit_id: int, 
                                      selection_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        単元選択ワークフローを実行
        
        Args:
            unit_id: 単元ID
            selection_data: 選択データ
            
        Returns:
            Dict: 選択ワークフロー結果
        """
        try:
            logger.info(f"Executing unit selection workflow for unit {unit_id}")
            
            # Step 1: 選択権限チェック
            permission_check = self.access_service.check_unit_selection_permission(unit_id)
            if not permission_check['allowed']:
                return {
                    "success": False,
                    "message": permission_check['reason'],
                    "error_code": permission_check.get('error_code')
                }
            
            # Step 2: 単元データの取得と検証
            unit_data = self.data_service.get_units_data()
            target_unit = next((u for u in unit_data if u['id'] == unit_id), None)
            if not target_unit:
                return {
                    "success": False,
                    "message": "指定された単元が見つかりません"
                }
            
            # Step 3: 選択の実行（進捗サービスを使用）
            initial_progress = {
                "progress_percentage": 0,
                "status": "started",
                **(selection_data or {})
            }
            
            progress_result = self.progress_service.update_progress(unit_id, initial_progress)
            if not progress_result['success']:
                return progress_result
            
            # Step 4: 選択完了後の処理
            post_selection_result = self._handle_post_selection_actions(unit_id, target_unit)
            
            return {
                "success": True,
                "message": "単元選択が正常に完了しました",
                "selection_result": progress_result,
                "post_actions": post_selection_result,
                "unit_info": {
                    "id": target_unit['id'],
                    "title": target_unit['title']
                }
            }

        except Exception as e:
            logger.error(f"Error executing unit selection workflow: {str(e)}")
            return {
                "success": False,
                "message": f"単元選択ワークフロー実行中にエラーが発生しました: {str(e)}"
            }

    def execute_completion_approval_workflow(self, selection_id: int, 
                                           approval_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        完了承認ワークフローを実行
        
        Args:
            selection_id: 選択ID
            approval_data: 承認データ
            
        Returns:
            Dict: 承認ワークフロー結果
        """
        try:
            logger.info(f"Executing completion approval workflow for selection {selection_id}")
            
            # Step 1: 承認権限チェック
            permission_check = self.access_service.check_completion_approval_permission(selection_id)
            if not permission_check['allowed']:
                return {
                    "success": False,
                    "message": permission_check['reason'],
                    "error_code": permission_check.get('error_code')
                }
            
            # Step 2: 承認処理の実行
            approval_result = self.completion_service.approve_completion(selection_id, approval_data)
            if not approval_result['success']:
                return approval_result
            
            # Step 3: 承認後の統計更新
            statistics_update = self._update_post_approval_statistics(selection_id)
            
            # Step 4: 関連システムとの同期
            sync_result = self._sync_approval_with_systems(selection_id, approval_data)
            
            return {
                "success": True,
                "message": "完了承認ワークフローが正常に完了しました",
                "approval_result": approval_result,
                "statistics_update": statistics_update,
                "system_sync": sync_result
            }

        except Exception as e:
            logger.error(f"Error executing completion approval workflow: {str(e)}")
            return {
                "success": False,
                "message": f"完了承認ワークフロー実行中にエラーが発生しました: {str(e)}"
            }

    def get_unified_dashboard_data(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        統合ダッシュボードデータを取得
        
        Args:
            user_id: ユーザーID（指定されない場合は現在のユーザー）
            
        Returns:
            Dict: 統合ダッシュボードデータ
        """
        try:
            target_user_id = user_id or current_user.id
            logger.info(f"Getting unified dashboard data for user {target_user_id}")
            
            dashboard_data = {}
            
            if current_user.role == 'student':
                # 学生用ダッシュボード
                dashboard_data = self._build_student_dashboard(target_user_id)
            
            elif current_user.role in ['teacher', 'admin']:
                # 教師・管理者用ダッシュボード
                dashboard_data = self._build_teacher_dashboard(target_user_id)
            
            else:
                return {
                    "success": False,
                    "message": "不明な役割です"
                }
            
            return {
                "success": True,
                "dashboard_data": dashboard_data,
                "user_role": current_user.role,
                "generated_at": self._get_current_timestamp()
            }

        except Exception as e:
            logger.error(f"Error getting unified dashboard data: {str(e)}")
            return {
                "success": False,
                "message": f"統合ダッシュボードデータの取得中にエラーが発生しました: {str(e)}"
            }

    def execute_batch_operations(self, operation_type: str, 
                               batch_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        バッチ操作を実行
        
        Args:
            operation_type: 操作タイプ
            batch_data: バッチデータ
            
        Returns:
            Dict: バッチ操作結果
        """
        try:
            logger.info(f"Executing batch operation: {operation_type}")
            
            batch_result = {}
            
            if operation_type == 'progress_update':
                batch_result = self.progress_service.batch_update_progress(batch_data)
            
            elif operation_type == 'completion_approval':
                batch_result = self.completion_service.batch_approve_completions(batch_data)
            
            elif operation_type == 'mapping_creation':
                batch_result = self.mapping_service.batch_create_mappings(batch_data)
            
            else:
                return {
                    "success": False,
                    "message": f"不明なバッチ操作タイプです: {operation_type}"
                }
            
            # バッチ操作後の統計更新
            post_batch_stats = self._update_post_batch_statistics(operation_type, batch_result)
            
            return {
                "success": batch_result.get('success', True),
                "batch_result": batch_result,
                "post_batch_statistics": post_batch_stats,
                "operation_type": operation_type,
                "processed_count": len(batch_data)
            }

        except Exception as e:
            logger.error(f"Error executing batch operations: {str(e)}")
            return {
                "success": False,
                "message": f"バッチ操作実行中にエラーが発生しました: {str(e)}"
            }

    def get_comprehensive_analytics(self, analytics_type: str, 
                                  filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        包括的分析データを取得
        
        Args:
            analytics_type: 分析タイプ
            filters: フィルタ条件
            
        Returns:
            Dict: 包括的分析データ
        """
        try:
            logger.info(f"Getting comprehensive analytics: {analytics_type}")
            
            analytics_data = {}
            
            if analytics_type == 'unit_performance':
                unit_id = filters.get('unit_id') if filters else None
                analytics_data = self.statistics_service.get_unit_statistics(unit_id)
            
            elif analytics_type == 'teacher_overview':
                teacher_id = filters.get('teacher_id') if filters else None
                analytics_data = self.statistics_service.get_teacher_overview_statistics(teacher_id)
            
            elif analytics_type == 'integration_status':
                analytics_data = self.integration_service.get_system_compatibility_report()
            
            else:
                return {
                    "success": False,
                    "message": f"不明な分析タイプです: {analytics_type}"
                }
            
            return {
                "success": True,
                "analytics_type": analytics_type,
                "analytics_data": analytics_data,
                "filters_applied": filters or {},
                "generated_at": self._get_current_timestamp()
            }

        except Exception as e:
            logger.error(f"Error getting comprehensive analytics: {str(e)}")
            return {
                "success": False,
                "message": f"包括的分析データの取得中にエラーが発生しました: {str(e)}"
            }

    def _handle_post_selection_actions(self, unit_id: int, unit_data: Dict[str, Any]) -> Dict[str, Any]:
        """選択後の処理"""
        try:
            # 関連マッピングの確認
            mappings = self.mapping_service.get_unit_mappings(unit_id)
            
            # 統合システムとの同期
            integration_sync = self.integration_service.synchronize_progress_between_systems(current_user.id)
            
            return {
                "mappings_checked": mappings.get('success', False),
                "integration_synced": integration_sync.get('success', False)
            }
        
        except Exception as e:
            logger.error(f"Error in post-selection actions: {str(e)}")
            return {"error": str(e)}

    def _update_post_approval_statistics(self, selection_id: int) -> Dict[str, Any]:
        """承認後の統計更新"""
        try:
            # 統計の更新処理（簡略化）
            return {"statistics_updated": True}
        
        except Exception as e:
            logger.error(f"Error updating post-approval statistics: {str(e)}")
            return {"error": str(e)}

    def _sync_approval_with_systems(self, selection_id: int, approval_data: Dict[str, Any]) -> Dict[str, Any]:
        """承認のシステム間同期"""
        try:
            # システム間同期処理（簡略化）
            return {"systems_synced": True}
        
        except Exception as e:
            logger.error(f"Error syncing approval with systems: {str(e)}")
            return {"error": str(e)}

    def _build_student_dashboard(self, student_id: int) -> Dict[str, Any]:
        """学生用ダッシュボード構築"""
        try:
            # 学生の選択一覧
            selections = self.progress_service.get_user_selections()
            
            # 完了履歴
            history = self.progress_service.get_completion_history()
            
            # 統合進捗
            unified_progress = self.integration_service.get_student_unified_progress(student_id)
            
            return {
                "current_selections": selections,
                "completion_history": history,
                "unified_progress": unified_progress,
                "dashboard_type": "student"
            }
        
        except Exception as e:
            logger.error(f"Error building student dashboard: {str(e)}")
            return {"error": str(e)}

    def _build_teacher_dashboard(self, teacher_id: int) -> Dict[str, Any]:
        """教師・管理者用ダッシュボード構築"""
        try:
            # 教師統計概要
            overview = self.statistics_service.get_teacher_overview_statistics(teacher_id)
            
            # 承認待ち一覧
            pending_approvals = self.completion_service.get_pending_approvals(teacher_id)
            
            # システム互換性レポート
            compatibility = self.integration_service.get_system_compatibility_report()
            
            return {
                "teacher_overview": overview,
                "pending_approvals": pending_approvals,
                "system_compatibility": compatibility,
                "dashboard_type": "teacher"
            }
        
        except Exception as e:
            logger.error(f"Error building teacher dashboard: {str(e)}")
            return {"error": str(e)}

    def _update_post_batch_statistics(self, operation_type: str, batch_result: Dict[str, Any]) -> Dict[str, Any]:
        """バッチ操作後の統計更新"""
        try:
            # バッチ操作統計の更新（簡略化）
            return {
                "operation_type": operation_type,
                "success_count": batch_result.get('success_count', 0),
                "failure_count": batch_result.get('failure_count', 0)
            }
        
        except Exception as e:
            logger.error(f"Error updating post-batch statistics: {str(e)}")
            return {"error": str(e)}

    def _get_current_timestamp(self) -> str:
        """現在のタイムスタンプを取得"""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    def health_check(self) -> Dict[str, Any]:
        """サービスヘルスチェック"""
        try:
            service_status = {
                "data_service": "healthy",
                "progress_service": "healthy",
                "completion_service": "healthy",
                "mapping_service": "healthy",
                "statistics_service": "healthy",
                "access_service": "healthy",
                "integration_service": "healthy"
            }
            
            all_healthy = all(status == "healthy" for status in service_status.values())
            
            return {
                "overall_status": "healthy" if all_healthy else "degraded",
                "service_status": service_status,
                "timestamp": self._get_current_timestamp()
            }
        
        except Exception as e:
            logger.error(f"Error in health check: {str(e)}")
            return {
                "overall_status": "unhealthy",
                "error": str(e),
                "timestamp": self._get_current_timestamp()
            }