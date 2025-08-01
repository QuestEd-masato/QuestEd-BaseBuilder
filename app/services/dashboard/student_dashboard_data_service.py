# -*- coding: utf-8 -*-
"""
StudentDashboardDataService

学生基本データ・クラス情報の一元管理サービス
Phase8D: dashboard.py から分離した基本データ取得機能
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from flask import current_app
from flask_login import current_user

from app.models import (
    ActivityLog, Class, ClassEnrollment, Goal, Todo, db
)
from app.student.utils import (
    get_student_survey_status, get_student_theme_status
)

logger = logging.getLogger(__name__)


class StudentDashboardDataService:
    """学生ダッシュボード基本データ管理専門サービス"""

    def get_student_classes(self, student_id: int) -> List[Class]:
        """
        学生の履修クラスを取得
        
        Args:
            student_id: 学生ID
            
        Returns:
            List[Class]: 履修クラスリスト
        """
        try:
            # ClassEnrollmentから履修クラスを取得
            enrollments = ClassEnrollment.query.filter_by(student_id=student_id).all()
            classes = [enrollment.class_obj for enrollment in enrollments if enrollment.class_obj]

            # ClassEnrollmentが空の場合、User.class_idから取得を試行
            if not classes and current_user and current_user.class_id:
                direct_class = Class.query.get(current_user.class_id)
                if direct_class:
                    classes = [direct_class]
                    logger.info(
                        f"[DASHBOARD_DATA] Student {student_id}: Using direct class_id {current_user.class_id}"
                    )

            # デバッグ情報をログに記録
            logger.info(
                f"[DASHBOARD_DATA] Student {student_id}: "
                f"Found {len(enrollments)} enrollments, {len(classes)} classes"
            )

            return classes

        except Exception as e:
            logger.error(f"Error getting student classes for {student_id}: {str(e)}")
            return []

    def build_basic_info(self, student_id: int, classes: List[Class]) -> Dict[str, Any]:
        """
        学生の基本情報を構築
        
        Args:
            student_id: 学生ID
            classes: 履修クラスリスト
            
        Returns:
            Dict: 学生基本情報
        """
        try:
            student_info = {
                "has_completed_surveys": False,
                "selected_theme": None,
                "recent_activities": [],
                "pending_todos": [],
                "active_goals": [],
                "class_count": len(classes),
            }

            # アンケート完了状況をチェック
            try:
                survey_status = get_student_survey_status()
                student_info["has_completed_surveys"] = survey_status.get("all_completed", False)
            except Exception as e:
                logger.error(f"Error getting survey status for student {student_id}: {str(e)}")
                student_info["has_completed_surveys"] = False

            # 選択中のテーマを取得
            try:
                theme_status = get_student_theme_status()
                student_info["selected_theme"] = theme_status.get("selected_theme")
            except Exception as e:
                logger.error(f"Error getting theme status for student {student_id}: {str(e)}")
                student_info["selected_theme"] = None

            # 最近の活動記録を取得（5件）
            student_info["recent_activities"] = self._get_recent_activities(student_id)
            
            # 未完了のTodoを取得（5件）
            student_info["pending_todos"] = self._get_pending_todos(student_id)
            
            # アクティブな目標を取得（5件）
            student_info["active_goals"] = self._get_active_goals(student_id)

            return student_info

        except Exception as e:
            logger.error(f"Error building basic info for student {student_id}: {str(e)}")
            return {
                "has_completed_surveys": False,
                "selected_theme": None,
                "recent_activities": [],
                "pending_todos": [],
                "active_goals": [],
                "class_count": len(classes),
            }

    def build_class_details(self, classes: List[Class]) -> Dict[str, Any]:
        """
        クラス詳細情報を構築
        
        Args:
            classes: クラスリスト
            
        Returns:
            Dict: クラス詳細情報
        """
        try:
            if not classes:
                return {"classes": [], "class_count": 0}

            class_details = []
            for class_obj in classes:
                try:
                    detail = {
                        "id": class_obj.id,
                        "name": class_obj.name,
                        "teacher_name": class_obj.teacher.username if class_obj.teacher else "不明",
                        "description": class_obj.description or "",
                        "created_at": class_obj.created_at
                    }
                    class_details.append(detail)
                except Exception as e:
                    logger.error(f"Error processing class {class_obj.id}: {str(e)}")
                    continue

            return {
                "classes": class_details,
                "class_count": len(class_details)
            }

        except Exception as e:
            logger.error(f"Error building class details: {str(e)}")
            return {"classes": [], "class_count": 0}

    def build_class_themes(self, classes: List[Class]) -> List[Dict[str, Any]]:
        """
        クラステーマ情報を構築
        
        Args:
            classes: クラスリスト
            
        Returns:
            List[Dict]: クラステーマリスト
        """
        try:
            all_themes = []
            for class_obj in classes:
                try:
                    if hasattr(class_obj, 'main_themes'):
                        for theme in class_obj.main_themes:
                            theme_info = {
                                "id": theme.id,
                                "title": theme.title,
                                "description": theme.description or "",
                                "class_name": class_obj.name,
                                "class_id": class_obj.id
                            }
                            all_themes.append(theme_info)
                except Exception as e:
                    logger.error(f"Error processing themes for class {class_obj.id}: {str(e)}")
                    continue

            return all_themes

        except Exception as e:
            logger.error(f"Error building class themes: {str(e)}")
            return []

    def _get_recent_activities(self, student_id: int, limit: int = 5) -> List[ActivityLog]:
        """最近の活動記録を取得"""
        try:
            recent_activities = (
                ActivityLog.query.filter_by(student_id=student_id)
                .order_by(ActivityLog.created_at.desc())
                .limit(limit)
                .all()
            )
            return recent_activities
        except Exception as e:
            logger.error(f"ActivityLog query error for student {student_id}: {str(e)}")
            return []

    def _get_pending_todos(self, student_id: int, limit: int = 5) -> List[Todo]:
        """未完了のTodoを取得"""
        try:
            pending_todos = (
                Todo.query.filter_by(student_id=student_id, is_completed=False)
                .order_by(Todo.created_at.desc())
                .limit(limit)
                .all()
            )
            return pending_todos
        except Exception as e:
            logger.error(f"Todo query error for student {student_id}: {str(e)}")
            return []

    def _get_active_goals(self, student_id: int, limit: int = 5) -> List[Goal]:
        """アクティブな目標を取得"""
        try:
            active_goals = (
                Goal.query.filter_by(student_id=student_id, is_completed=False)
                .limit(limit)
                .all()
            )
            return active_goals
        except Exception as e:
            logger.error(f"Goal query error for student {student_id}: {str(e)}")
            return []

    def get_service_status(self) -> Dict[str, Any]:
        """サービス状態取得"""
        return {
            "service_name": "StudentDashboardDataService",
            "status": "active",
            "version": "1.0.0",
            "capabilities": [
                "student_classes_retrieval",
                "basic_info_construction",
                "class_details_building",
                "class_themes_building"
            ]
        }