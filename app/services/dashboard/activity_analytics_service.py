# -*- coding: utf-8 -*-
"""
ActivityAnalyticsService

活動統計・進捗分析の専門処理サービス
Phase8D: dashboard.pyから分離した活動分析機能
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from flask import current_app
from flask_login import current_user
from sqlalchemy import func

from app.models import ActivityLog, Goal, Todo, db

logger = logging.getLogger(__name__)


class ActivityAnalyticsService:
    """活動統計・進捗分析専門サービス"""

    def generate_weekly_activity_stats(self, student_id: int) -> List[Dict[str, Any]]:
        """
        週間活動統計を生成
        
        Args:
            student_id: 学生ID
            
        Returns:
            List[Dict]: 週間活動統計
        """
        try:
            # 認証状態チェック
            if not current_user or not current_user.is_authenticated:
                logger.warning(f"User not authenticated, returning empty weekly stats")
                return []

            # 過去7日間の活動統計
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)

            daily_activities = (
                db.session.query(
                    func.date(ActivityLog.created_at).label("date"),
                    func.count(ActivityLog.id).label("count"),
                )
                .filter(
                    ActivityLog.student_id == student_id,
                    ActivityLog.created_at >= start_date,
                    ActivityLog.created_at <= end_date,
                )
                .group_by(func.date(ActivityLog.created_at))
                .all()
            )

            # 7日分のデータを準備（活動がない日は0）
            stats = []
            for i in range(7):
                date = (start_date + timedelta(days=i)).date()
                count = 0

                for activity in daily_activities:
                    if activity.date == date:
                        count = activity.count
                        break

                stats.append({"date": date.strftime("%m/%d"), "count": count})

            return stats

        except Exception as e:
            logger.error(f"Weekly stats error for student {student_id}: {str(e)}")
            return []

    def generate_progress_statistics(self, student_id: int) -> Dict[str, Any]:
        """
        進捗統計を生成
        
        Args:
            student_id: 学生ID
            
        Returns:
            Dict: 進捗統計
        """
        try:
            # 認証状態チェック
            if not current_user or not current_user.is_authenticated:
                logger.warning(f"User not authenticated, returning empty progress stats")
                return {"todo_completion_rate": 0, "goal_completion_rate": 0}

            # Todo完了率計算
            todo_completion_rate = self.calculate_todo_completion_rate(student_id)
            
            # 目標完了率計算
            goal_completion_rate = self.calculate_goal_completion_rate(student_id)

            # 最近の活動数
            recent_activity_count = self._get_recent_activity_count(student_id)

            return {
                "todo_completion_rate": todo_completion_rate,
                "goal_completion_rate": goal_completion_rate,
                "recent_activities_count": recent_activity_count,
                "last_activity_date": self._get_last_activity_date(student_id)
            }

        except Exception as e:
            logger.error(f"Progress stats error for student {student_id}: {str(e)}")
            return {"todo_completion_rate": 0, "goal_completion_rate": 0}

    def calculate_todo_completion_rate(self, student_id: int) -> float:
        """
        Todo完了率を計算
        
        Args:
            student_id: 学生ID
            
        Returns:
            float: 完了率（0-100）
        """
        try:
            total_todos = Todo.query.filter_by(student_id=student_id).count()
            if total_todos == 0:
                return 0.0

            completed_todos = Todo.query.filter_by(
                student_id=student_id, 
                is_completed=True
            ).count()

            return (completed_todos / total_todos) * 100

        except Exception as e:
            logger.error(f"Todo completion rate error for student {student_id}: {str(e)}")
            return 0.0

    def calculate_goal_completion_rate(self, student_id: int) -> float:
        """
        目標完了率を計算
        
        Args:
            student_id: 学生ID
            
        Returns:
            float: 完了率（0-100）
        """
        try:
            total_goals = Goal.query.filter_by(student_id=student_id).count()
            if total_goals == 0:
                return 0.0

            completed_goals = Goal.query.filter_by(
                student_id=student_id, 
                is_completed=True
            ).count()

            return (completed_goals / total_goals) * 100

        except Exception as e:
            logger.error(f"Goal completion rate error for student {student_id}: {str(e)}")
            return 0.0

    def get_recent_activities(self, student_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        最近のアクティビティを取得
        
        Args:
            student_id: 学生ID
            limit: 取得件数
            
        Returns:
            List[Dict]: アクティビティリスト
        """
        try:
            activities = (
                ActivityLog.query.filter_by(student_id=student_id)
                .order_by(ActivityLog.created_at.desc())
                .limit(limit)
                .all()
            )

            activity_list = []
            for activity in activities:
                activity_info = {
                    "id": activity.id,
                    "activity_type": activity.activity_type,
                    "description": activity.description,
                    "created_at": activity.created_at,
                    "formatted_date": activity.created_at.strftime("%Y-%m-%d %H:%M")
                }
                activity_list.append(activity_info)

            return activity_list

        except Exception as e:
            logger.error(f"Recent activities error for student {student_id}: {str(e)}")
            return []

    def get_activity_summary(self, student_id: int, days: int = 30) -> Dict[str, Any]:
        """
        指定期間の活動サマリーを取得
        
        Args:
            student_id: 学生ID
            days: 対象日数
            
        Returns:
            Dict: 活動サマリー
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 期間内の活動数
            activity_count = ActivityLog.query.filter_by(
                student_id=student_id
            ).filter(
                ActivityLog.created_at >= start_date,
                ActivityLog.created_at <= end_date
            ).count()

            # 活動タイプ別集計
            activity_types = (
                db.session.query(
                    ActivityLog.activity_type,
                    func.count(ActivityLog.id).label("count")
                )
                .filter_by(student_id=student_id)
                .filter(
                    ActivityLog.created_at >= start_date,
                    ActivityLog.created_at <= end_date
                )
                .group_by(ActivityLog.activity_type)
                .all()
            )

            type_breakdown = {}
            for activity_type, count in activity_types:
                type_breakdown[activity_type or "unknown"] = count

            # 1日平均活動数
            daily_average = activity_count / days if days > 0 else 0

            return {
                "period_days": days,
                "total_activities": activity_count,
                "daily_average": daily_average,
                "activity_breakdown": type_breakdown,
                "most_active_type": max(type_breakdown.items(), key=lambda x: x[1])[0] if type_breakdown else None
            }

        except Exception as e:
            logger.error(f"Activity summary error for student {student_id}: {str(e)}")
            return {
                "period_days": days,
                "total_activities": 0,
                "daily_average": 0,
                "activity_breakdown": {},
                "most_active_type": None
            }

    def _get_recent_activity_count(self, student_id: int, days: int = 7) -> int:
        """最近の活動数を取得"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            count = ActivityLog.query.filter_by(
                student_id=student_id
            ).filter(
                ActivityLog.created_at >= start_date,
                ActivityLog.created_at <= end_date
            ).count()

            return count

        except Exception as e:
            logger.error(f"Recent activity count error for student {student_id}: {str(e)}")
            return 0

    def _get_last_activity_date(self, student_id: int) -> Optional[datetime]:
        """最後の活動日時を取得"""
        try:
            last_activity = (
                ActivityLog.query.filter_by(student_id=student_id)
                .order_by(ActivityLog.created_at.desc())
                .first()
            )

            return last_activity.created_at if last_activity else None

        except Exception as e:
            logger.error(f"Last activity date error for student {student_id}: {str(e)}")
            return None

    def get_service_status(self) -> Dict[str, Any]:
        """サービス状態取得"""
        return {
            "service_name": "ActivityAnalyticsService",
            "status": "active",
            "version": "1.0.0",
            "capabilities": [
                "weekly_activity_statistics",
                "progress_statistics_generation",
                "todo_completion_tracking",
                "goal_completion_tracking",
                "recent_activities_retrieval"
            ]
        }