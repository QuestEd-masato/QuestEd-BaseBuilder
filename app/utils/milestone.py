"""
マイルストーン関連のユーティリティ関数

マイルストーンの進捗計算、統計処理に関する共通機能を提供します。
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import current_app
from sqlalchemy import text

from extensions import db

logger = logging.getLogger(__name__)


def calculate_milestone_progress(milestones: List[Any]) -> Dict[str, Any]:
    """
    マイルストーン進捗を計算（テスト可能）

    Args:
        milestones: マイルストーンのリスト

    Returns:
        Dict: 進捗統計（総数、完了数、進捗率、次のマイルストーン）
    """
    if not milestones:
        return {
            "total_milestones": 0,
            "completed_milestones": 0,
            "progress_percentage": 0,
            "next_milestone": None,
        }

    total_milestones = len(milestones)
    completed_milestones = sum(
        1 for m in milestones if getattr(m, "is_completed", False)
    )
    progress_percentage = round(
        (completed_milestones / total_milestones * 100) if total_milestones > 0 else 0
    )

    # 次のマイルストーンを取得
    next_milestone = None
    for milestone in milestones:
        if not getattr(milestone, "is_completed", False):
            next_milestone = milestone
            break

    return {
        "total_milestones": total_milestones,
        "completed_milestones": completed_milestones,
        "progress_percentage": progress_percentage,
        "next_milestone": next_milestone,
    }


def get_milestones_for_student(class_id: int, student_id: int) -> List[Any]:
    """
    生徒のクラスマイルストーンを取得

    Args:
        class_id: クラスID
        student_id: 生徒ID

    Returns:
        List: マイルストーンのリスト（完了状況含む）
    """
    try:
        milestones = db.session.execute(
            text(
                """
            SELECT m.*, 
                   CASE WHEN sm.completed_at IS NOT NULL THEN 1 ELSE 0 END as is_completed,
                   sm.completed_at
            FROM milestones m
            LEFT JOIN student_milestones sm ON m.id = sm.milestone_id 
                AND sm.student_id = :student_id
            WHERE m.class_id = :class_id
            ORDER BY m.due_date
        """
            ),
            {"student_id": student_id, "class_id": class_id},
        ).fetchall()

        return milestones

    except Exception as e:
        logger.error(
            f"マイルストーン取得エラー: {str(e)} " f"(class_id={class_id}, student_id={student_id})"
        )
        return []


def get_milestone_statistics(milestones: List[Any]) -> Dict[str, Any]:
    """
    マイルストーン統計情報を取得

    Args:
        milestones: マイルストーンのリスト

    Returns:
        Dict: 統計情報
    """
    if not milestones:
        return {"total": 0, "completed": 0, "pending": 0, "overdue": 0, "upcoming": 0}

    from datetime import datetime

    now = datetime.utcnow()

    total = len(milestones)
    completed = 0
    pending = 0
    overdue = 0
    upcoming = 0

    for milestone in milestones:
        is_completed = getattr(milestone, "is_completed", False)
        due_date = getattr(milestone, "due_date", None)

        if is_completed:
            completed += 1
        else:
            pending += 1

            if due_date:
                if due_date < now.date():
                    overdue += 1
                elif due_date <= (now + timedelta(days=7)).date():
                    upcoming += 1

    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "overdue": overdue,
        "upcoming": upcoming,
    }
