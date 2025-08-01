# -*- coding: utf-8 -*-
"""
DashboardOrchestrationService

全サービス統合・エラーハンドリング・フォールバック管理サービス
Phase8D: dashboard.pyから分離した統合制御機能
"""
import logging
import traceback
from typing import Dict, List, Any, Optional

from flask import current_app, flash, url_for, redirect
from flask_login import current_user

from .student_dashboard_data_service import StudentDashboardDataService
from .learning_progress_service import LearningProgressService
from .activity_analytics_service import ActivityAnalyticsService
from app.services.student_dashboard.basebuilder_analytics_service import BaseBuilderAnalyticsService as BaseBuilderIntegrationService

# Phase6-B既存サービス
from app.services import DashboardService, DashboardRendererService

logger = logging.getLogger(__name__)


class DashboardOrchestrationService:
    """ダッシュボード統合制御専門サービス"""

    def __init__(self):
        """サービス初期化"""
        self.data_service = StudentDashboardDataService()
        self.progress_service = LearningProgressService()
        self.analytics_service = ActivityAnalyticsService()
        self.basebuilder_service = BaseBuilderIntegrationService()
        
        # Phase6-B既存サービス活用
        self.legacy_dashboard_service = DashboardService()
        self.legacy_renderer_service = DashboardRendererService()

    def build_complete_dashboard(self, student_id: int) -> Dict[str, Any]:
        """
        完全なダッシュボードデータを構築
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 完全なダッシュボードデータ
        """
        try:
            logger.info(f"Building complete dashboard for student {student_id}")

            # 基本データ取得
            basic_data = self._get_basic_dashboard_data(student_id)
            
            # 学習進捗データ取得
            progress_data = self._get_progress_data(student_id)
            
            # 活動分析データ取得
            analytics_data = self._get_analytics_data(student_id)
            
            # BaseBuilderデータ取得
            basebuilder_data = self._get_basebuilder_data(student_id)
            
            # Phase6-B既存サービス統合
            legacy_data = self._get_legacy_dashboard_data(student_id)

            # 全データ統合
            complete_data = self._merge_dashboard_data(
                basic_data, progress_data, analytics_data, 
                basebuilder_data, legacy_data
            )

            # テンプレートコンテキスト構築
            template_context = self.build_template_context(complete_data)
            
            logger.info(f"Dashboard data prepared successfully for student {student_id}")
            return template_context

        except Exception as e:
            logger.error(f"Dashboard building error for student {student_id}: {str(e)}")
            return self.handle_dashboard_error(e)

    def handle_dashboard_error(self, error: Exception) -> Dict[str, Any]:
        """
        ダッシュボードエラーハンドリング
        
        Args:
            error: 発生したエラー
            
        Returns:
            Dict: エラー処理済みダッシュボードデータ
        """
        try:
            logger.error(f"Dashboard error for student {current_user.id if current_user else 'unknown'}: {str(error)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # フォールバック用最小限データ
            fallback_data = self._get_fallback_dashboard_data()
            
            # エラーメッセージをフラッシュ
            flash("ダッシュボードの読み込み中にエラーが発生しました。基本機能のみ表示しています。", "warning")
            
            return fallback_data

        except Exception as fallback_error:
            logger.error(f"Fallback error: {str(fallback_error)}")
            return self._get_emergency_fallback_data()

    def build_template_context(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        テンプレートコンテキストを構築
        
        Args:
            dashboard_data: ダッシュボードデータ
            
        Returns:
            Dict: テンプレートコンテキスト
        """
        try:
            # 後方互換性データの構築
            legacy_compatibility_data = self.ensure_backward_compatibility(dashboard_data)
            
            # Phase6-B形式のデータ統合
            template_context = {
                **legacy_compatibility_data,
                'student_info': dashboard_data.get('student_basic_info', {}),
                'dashboard_data': dashboard_data,
                'rendered_sections': dashboard_data.get('rendered_sections', {}),
                'phase8d_enabled': True,  # Phase8D有効フラグ
                'service_status': self._get_all_service_status()
            }
            
            return template_context

        except Exception as e:
            logger.error(f"Template context building error: {str(e)}")
            return self._get_fallback_template_context()

    def ensure_backward_compatibility(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        後方互換性を確保
        
        Args:
            data: 新しいダッシュボードデータ
            
        Returns:
            Dict: 後方互換性対応データ
        """
        try:
            classes = data.get('classes', [])
            
            return {
                # クラス情報（既存テンプレートが期待する形式）
                'class_details': data.get('class_details', {}),
                'class_count': len(classes),
                
                # 基本統計（既存テンプレートが期待する形式）
                'weekly_stats': data.get('weekly_activity_stats', []),
                'progress_stats': {
                    'todo_completion_rate': data.get('todo_completion_rate', 0),
                    'goal_completion_rate': data.get('goal_completion_rate', 0)
                },
                'learning_progress': data.get('learning_progress_summary', {}),
                
                # BaseBuilder統計（エラー回避）
                'total_words_attempted': data.get('basebuilder_data', {}).get('total_words_attempted', 0),
                'total_mastered_words': data.get('basebuilder_data', {}).get('total_mastered_words', 0),
                'weekly_words_learned': data.get('basebuilder_data', {}).get('weekly_words_learned', 0),
                'mastery_rate': data.get('basebuilder_data', {}).get('mastery_rate', 0),
                'weekly_target': data.get('basebuilder_data', {}).get('weekly_target', 20),
                'total_basic_words': data.get('basebuilder_data', {}).get('total_basic_words', 0),
                
                # 学習単元統計
                'total_units': data.get('unit_statistics', {}).get('total_units', 0),
                'completed_units': data.get('unit_statistics', {}).get('completed_units', 0),
                'in_progress_units': data.get('unit_statistics', {}).get('in_progress_units', 0),
                'completion_rate': data.get('unit_statistics', {}).get('completion_rate', 0),
                'total_study_time': data.get('unit_statistics', {}).get('total_study_time', 0),
                
                # アンケート情報
                'interest_survey': None,
                'personality_survey': None,
                
                # アクティビティ情報
                'all_class_themes': data.get('class_themes', []),
                'class_info': {'class_count': len(classes)},
                'class_todos': data.get('pending_todos', []),
                'class_goals': data.get('active_goals', []),
                'pending_todos_count': len(data.get('pending_todos', [])),
                'active_goals_count': len(data.get('active_goals', [])),
                'recent_activities': data.get('recent_activities', []),
                'weekly_activities_count': data.get('recent_activity_count', 0),
                'monthly_chat_count': 0,
                'class_top_learners': [],
                'weekly_top_learners': [],
                
                # スタイル
                'btn_primary_style': "display: inline-block; padding: 0.375rem 0.75rem; font-size: 0.875rem; border-radius: 0.25rem; text-decoration: none; background-color: #0056b3; color: white; border: 1px solid #0056b3;",
                'btn_outline_style': "display: inline-block; padding: 0.375rem 0.75rem; font-size: 0.875rem; border-radius: 0.25rem; text-decoration: none; background-color: transparent; color: #0056b3; border: 1px solid #0056b3;",
            }

        except Exception as e:
            logger.error(f"Backward compatibility error: {str(e)}")
            return {}

    def _get_basic_dashboard_data(self, student_id: int) -> Dict[str, Any]:
        """基本ダッシュボードデータ取得"""
        try:
            classes = self.data_service.get_student_classes(student_id)
            basic_info = self.data_service.build_basic_info(student_id, classes)
            class_details = self.data_service.build_class_details(classes)
            class_themes = self.data_service.build_class_themes(classes)

            return {
                'classes': classes,
                'student_basic_info': basic_info,
                'class_details': class_details,
                'class_themes': class_themes,
                'pending_todos': basic_info.get('pending_todos', []),
                'active_goals': basic_info.get('active_goals', []),
                'recent_activities': basic_info.get('recent_activities', [])
            }

        except Exception as e:
            logger.error(f"Basic dashboard data error: {str(e)}")
            return {}

    def _get_progress_data(self, student_id: int) -> Dict[str, Any]:
        """学習進捗データ取得"""
        try:
            progress_summary = self.progress_service.get_learning_progress_summary(student_id)
            unit_statistics = self.progress_service.generate_unit_statistics(student_id)
            completion_rates = self.progress_service.calculate_completion_rates(student_id)
            curriculum_progress = self.progress_service.get_curriculum_progress(student_id)

            return {
                'learning_progress_summary': progress_summary,
                'unit_statistics': unit_statistics,
                'completion_rates': completion_rates,
                'curriculum_progress': curriculum_progress
            }

        except Exception as e:
            logger.error(f"Progress data error: {str(e)}")
            return {}

    def _get_analytics_data(self, student_id: int) -> Dict[str, Any]:
        """活動分析データ取得"""
        try:
            weekly_stats = self.analytics_service.generate_weekly_activity_stats(student_id)
            progress_stats = self.analytics_service.generate_progress_statistics(student_id)
            recent_activities = self.analytics_service.get_recent_activities(student_id)
            activity_summary = self.analytics_service.get_activity_summary(student_id)

            return {
                'weekly_activity_stats': weekly_stats,
                'progress_statistics': progress_stats,
                'recent_activities_detailed': recent_activities,
                'activity_summary': activity_summary,
                'todo_completion_rate': progress_stats.get('todo_completion_rate', 0),
                'goal_completion_rate': progress_stats.get('goal_completion_rate', 0),
                'recent_activity_count': activity_summary.get('total_activities', 0)
            }

        except Exception as e:
            logger.error(f"Analytics data error: {str(e)}")
            return {}

    def _get_basebuilder_data(self, student_id: int) -> Dict[str, Any]:
        """BaseBuilderデータ取得"""
        try:
            basebuilder_stats = self.basebuilder_service.generate_basebuilder_statistics(student_id)
            mastery_rates = self.basebuilder_service.calculate_mastery_rates(student_id)
            weekly_progress = self.basebuilder_service.calculate_weekly_progress(student_id)
            proficiency_breakdown = self.basebuilder_service.get_proficiency_breakdown(student_id)

            return {
                'basebuilder_data': {
                    **basebuilder_stats,
                    **mastery_rates,
                    **weekly_progress,
                    'proficiency_breakdown': proficiency_breakdown
                }
            }

        except Exception as e:
            logger.error(f"BaseBuilder data error: {str(e)}")
            return {'basebuilder_data': {}}

    def _get_legacy_dashboard_data(self, student_id: int) -> Dict[str, Any]:
        """Phase6-B既存ダッシュボードデータ取得"""
        try:
            dashboard_data = self.legacy_dashboard_service.build_dashboard_data(student_id)
            rendered_sections = self.legacy_renderer_service.render_complete_dashboard(dashboard_data)

            return {
                'legacy_dashboard_data': dashboard_data,
                'rendered_sections': rendered_sections
            }

        except Exception as e:
            logger.error(f"Legacy dashboard data error: {str(e)}")
            return {}

    def _merge_dashboard_data(self, *data_sources) -> Dict[str, Any]:
        """複数のデータソースをマージ"""
        merged_data = {}
        for data in data_sources:
            if isinstance(data, dict):
                merged_data.update(data)
        return merged_data

    def _get_fallback_dashboard_data(self) -> Dict[str, Any]:
        """フォールバック用ダッシュボードデータ"""
        return {
            'student_info': {'class_count': 0},
            'classes': [],
            'dashboard_data': {},
            'rendered_sections': {},
            'error_mode': True
        }

    def _get_emergency_fallback_data(self) -> Dict[str, Any]:
        """緊急フォールバックデータ"""
        return {
            'student_info': {'class_count': 0},
            'emergency_mode': True
        }

    def _get_fallback_template_context(self) -> Dict[str, Any]:
        """フォールバック用テンプレートコンテキスト"""
        return self._get_fallback_dashboard_data()

    def _get_all_service_status(self) -> Dict[str, Any]:
        """全サービス状態取得"""
        try:
            return {
                'data_service': self.data_service.get_service_status(),
                'progress_service': self.progress_service.get_service_status(),
                'analytics_service': self.analytics_service.get_service_status(),
                'basebuilder_service': self.basebuilder_service.get_service_status()
            }
        except Exception as e:
            logger.error(f"Service status error: {str(e)}")
            return {}

    def get_service_status(self) -> Dict[str, Any]:
        """サービス状態取得"""
        return {
            "service_name": "DashboardOrchestrationService",
            "status": "active",
            "version": "1.0.0",
            "sub_services": self._get_all_service_status(),
            "capabilities": [
                "complete_dashboard_building",
                "error_handling_and_fallback",
                "template_context_building",
                "backward_compatibility_management",
                "multi_service_orchestration"
            ]
        }