# -*- coding: utf-8 -*-
"""
Dashboard Presentation Service

ダッシュボード表示・テンプレート管理専門サービス
Phase8E: student dashboard.pyから分離した表示制御機能
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from flask import current_app, flash, url_for, render_template
from flask_login import current_user

from app.models import Class, ClassEnrollment

logger = logging.getLogger(__name__)


class DashboardPresentationService:
    """ダッシュボード表示・テンプレート管理専門サービス"""

    def render_main_dashboard(self, student_id: int, dashboard_data: Dict[str, Any]) -> str:
        """
        メインダッシュボード表示制御
        
        Args:
            student_id: 学生ID
            dashboard_data: 統合ダッシュボードデータ
            
        Returns:
            str: レンダリング済みHTML
        """
        try:
            logger.info(f"Rendering main dashboard for student {student_id}")
            
            # テンプレートコンテキスト構築
            template_context = self.build_template_context(dashboard_data)
            
            # Phase6-B後方互換性データ統合
            legacy_data = self.handle_legacy_compatibility(dashboard_data)
            template_context.update(legacy_data)
            
            # スタイルデータ追加
            style_data = self.prepare_style_data()
            template_context.update(style_data)
            
            return render_template("student/dashboard.html", **template_context)
            
        except Exception as e:
            logger.error(f"Main dashboard rendering error for student {student_id}: {str(e)}")
            return self.render_error_fallback()

    def render_minimal_dashboard(self, student_id: int) -> str:
        """
        最小限ダッシュボード表示（エラー時フォールバック）
        
        Args:
            student_id: 学生ID
            
        Returns:
            str: 最小限レンダリング済みHTML
        """
        try:
            logger.info(f"Rendering minimal dashboard for student {student_id}")
            
            minimal_context = {
                "student_info": {"class_count": 0},
                "classes": [],
                "error_mode": True,
                "message": "基本機能のみ表示しています。"
            }
            
            return render_template("student/dashboard_minimal.html", **minimal_context)
            
        except Exception as e:
            logger.error(f"Minimal dashboard rendering error: {str(e)}")
            return self.render_emergency_fallback()

    def build_template_context(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        テンプレートコンテキスト構築
        
        Args:
            dashboard_data: ダッシュボードデータ
            
        Returns:
            Dict: テンプレートコンテキスト
        """
        try:
            # 基本コンテキスト構築
            context = {
                "student_info": dashboard_data.get("student_info", {}),
                "dashboard_data": dashboard_data,
                "classes": dashboard_data.get("classes", []),
                "phase8e_enabled": True,  # Phase8E有効フラグ
                "rendered_at": datetime.now().isoformat()
            }
            
            # 統計データ統合
            if "statistics" in dashboard_data:
                context["statistics"] = dashboard_data["statistics"]
            
            # 進捗データ統合
            if "progress_data" in dashboard_data:
                context["progress_data"] = dashboard_data["progress_data"]
            
            # ランキングデータ統合
            if "ranking_data" in dashboard_data:
                context["ranking_data"] = dashboard_data["ranking_data"]
                
            return context
            
        except Exception as e:
            logger.error(f"Template context building error: {str(e)}")
            return self._get_fallback_template_context()

    def handle_legacy_compatibility(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase6-B後方互換性管理
        
        Args:
            data: 新しいダッシュボードデータ
            
        Returns:
            Dict: 後方互換性対応データ
        """
        try:
            # 既存テンプレートが期待するデータ構造を維持
            classes = data.get("classes", [])
            
            compatibility_data = {
                # クラス情報（既存テンプレートが期待する形式）
                "class_details": self._build_legacy_class_details(classes),
                "class_count": len(classes),
                
                # 基本統計（既存テンプレートが期待する形式）
                "weekly_stats": data.get("weekly_activity_stats", []),
                "progress_stats": {
                    "todo_completion_rate": data.get("progress_statistics", {}).get("todo_completion_rate", 0),
                    "goal_completion_rate": data.get("progress_statistics", {}).get("goal_completion_rate", 0)
                },
                "learning_progress": {
                    "selected_units": data.get("learning_progress", {}).get("selected_units", []),
                    "stats": data.get("learning_progress", {}).get("stats", {"total_selected": 0})
                },
                
                # BaseBuilder統計（エラー回避）
                "total_words_attempted": data.get("basebuilder_stats", {}).get("total_words_attempted", 0),
                "total_mastered_words": data.get("basebuilder_stats", {}).get("total_mastered_words", 0),
                "weekly_words_learned": data.get("basebuilder_stats", {}).get("weekly_words_learned", 0),
                "mastery_rate": data.get("basebuilder_stats", {}).get("mastery_rate", 0),
                "weekly_target": data.get("basebuilder_stats", {}).get("weekly_target", 20),
                "total_basic_words": data.get("basebuilder_stats", {}).get("total_basic_words", 0),
                
                # 学習単元統計
                "total_units": data.get("curriculum_stats", {}).get("total_units", 0),
                "completed_units": data.get("curriculum_stats", {}).get("completed_units", 0),
                "in_progress_units": data.get("curriculum_stats", {}).get("in_progress_units", 0),
                "completion_rate": data.get("curriculum_stats", {}).get("completion_rate", 0),
                "total_study_time": data.get("curriculum_stats", {}).get("total_study_time", 0),
                
                # アンケート情報
                "interest_survey": data.get("survey_data", {}).get("interest_survey"),
                "personality_survey": data.get("survey_data", {}).get("personality_survey"),
                
                # アクティビティ情報
                "all_class_themes": self._build_legacy_class_themes(classes),
                "class_info": {"class_count": len(classes)},
                "class_todos": data.get("todos", []),
                "class_goals": data.get("goals", []),
                "pending_todos_count": len(data.get("todos", [])),
                "active_goals_count": len(data.get("goals", [])),
                "recent_activities": data.get("recent_activities", []),
                "weekly_activities_count": data.get("activity_summary", {}).get("weekly_count", 0),
                "monthly_chat_count": data.get("chat_stats", {}).get("monthly_count", 0),
                "class_top_learners": data.get("ranking_data", {}).get("class_top_learners", []),
                "weekly_top_learners": data.get("ranking_data", {}).get("weekly_top_learners", [])
            }
            
            return compatibility_data
            
        except Exception as e:
            logger.error(f"Legacy compatibility handling error: {str(e)}")
            return {}

    def prepare_style_data(self) -> Dict[str, str]:
        """
        スタイルデータ準備
        
        Returns:
            Dict: CSS inline スタイル定義
        """
        return {
            "btn_primary_style": (
                "display: inline-block; padding: 0.375rem 0.75rem; "
                "font-size: 0.875rem; border-radius: 0.25rem; text-decoration: none; "
                "background-color: #0056b3; color: white; border: 1px solid #0056b3;"
            ),
            "btn_outline_style": (
                "display: inline-block; padding: 0.375rem 0.75rem; "
                "font-size: 0.875rem; border-radius: 0.25rem; text-decoration: none; "
                "background-color: transparent; color: #0056b3; border: 1px solid #0056b3;"
            )
        }

    def render_error_fallback(self) -> str:
        """エラー時フォールバック表示"""
        try:
            flash("ダッシュボードの読み込み中にエラーが発生しました。", "error")
            return self.render_minimal_dashboard(current_user.id if current_user else 0)
        except Exception:
            return self.render_emergency_fallback()

    def render_emergency_fallback(self) -> str:
        """緊急時フォールバック表示"""
        return "<h1>システムエラー</h1><p>一時的にサービスを利用できません。</p>"

    def _build_legacy_class_details(self, classes: List[Any]) -> Dict[str, Any]:
        """レガシークラス詳細構築"""
        try:
            class_details = {}
            for class_obj in classes:
                class_details[class_obj.id] = {
                    "name": class_obj.name,
                    "description": getattr(class_obj, "description", ""),
                    "teacher_name": getattr(class_obj.teacher, "username", "不明") if hasattr(class_obj, "teacher") else "不明"
                }
            return class_details
        except Exception as e:
            logger.error(f"Legacy class details error: {str(e)}")
            return {}

    def _build_legacy_class_themes(self, classes: List[Any]) -> List[Dict[str, Any]]:
        """レガシークラステーマ構築"""
        try:
            themes = []
            for class_obj in classes:
                # 基本的なテーマ情報を構築
                themes.append({
                    "class_id": class_obj.id,
                    "class_name": class_obj.name,
                    "themes": []  # テーマ詳細は必要に応じて拡張
                })
            return themes
        except Exception as e:
            logger.error(f"Legacy class themes error: {str(e)}")
            return []

    def _get_fallback_template_context(self) -> Dict[str, Any]:
        """フォールバック用テンプレートコンテキスト"""
        return {
            "student_info": {"class_count": 0},
            "dashboard_data": {},
            "classes": [],
            "error_mode": True
        }

    def get_service_status(self) -> Dict[str, Any]:
        """サービス状態取得"""
        return {
            "service_name": "DashboardPresentationService",
            "status": "active",
            "version": "1.0.0",
            "capabilities": [
                "main_dashboard_rendering",
                "minimal_dashboard_fallback",
                "template_context_building",
                "legacy_compatibility_management",
                "error_handling_and_fallback"
            ]
        }