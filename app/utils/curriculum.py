"""
カリキュラム関連のユーティリティ関数

カリキュラムデータの取得、変換、処理に関する共通機能を提供します。
"""

import json
import logging
from typing import Any, Dict, List, Optional

from flask import current_app
from sqlalchemy import text

from app.models import Curriculum
from extensions import db

logger = logging.getLogger(__name__)


def get_curriculum_items(curriculum: Curriculum) -> List[Any]:
    """
    カリキュラムから項目リストを取得（json/table形式対応）

    Args:
        curriculum: Curriculumオブジェクト

    Returns:
        List: カリキュラム項目のリスト
    """
    items = []

    try:
        if hasattr(curriculum, "format") and curriculum.format == "table":
            # 新形式のカリキュラム（正規化テーブル）
            items = db.session.execute(
                text(
                    """
                SELECT phase, week, hours, category, activity, 
                       teacher_support, evaluation_method
                FROM curriculum_items
                WHERE curriculum_id = :curriculum_id
                ORDER BY order_index
            """
                ),
                {"curriculum_id": curriculum.id},
            ).fetchall()

        elif hasattr(curriculum, "format") and curriculum.format == "json":
            # レガシー形式のカリキュラム（JSON）
            items = _convert_json_to_items(curriculum)

        else:
            # format属性がない場合のデフォルト処理
            logger.info(f"カリキュラム形式未指定: curriculum_id={curriculum.id}")
            items = []

    except Exception as e:
        logger.error(f"カリキュラム項目取得エラー: {str(e)} (curriculum_id={curriculum.id})")
        items = []

    return items


def _convert_json_to_items(curriculum: Curriculum) -> List[Any]:
    """
    JSON形式のカリキュラムを標準的な項目形式に変換

    Args:
        curriculum: Curriculumオブジェクト（JSON形式）

    Returns:
        List: 変換された項目リスト
    """
    items = []

    if not hasattr(curriculum, "content") or not curriculum.content:
        return items

    try:
        json_data = (
            json.loads(curriculum.content)
            if isinstance(curriculum.content, str)
            else curriculum.content
        )

        # JSON形式から items 形式に変換
        if isinstance(json_data, list):
            for idx, item in enumerate(json_data):
                # JSON項目を標準的な形式に変換
                converted_item = type(
                    "Item",
                    (),
                    {
                        "phase": item.get("phase", f"Phase {idx + 1}"),
                        "week": item.get("week", idx + 1),
                        "hours": item.get("hours", 0),
                        "category": item.get("category", ""),
                        "activity": item.get("activity", item.get("title", "")),
                        "teacher_support": item.get(
                            "teacher_support", item.get("description", "")
                        ),
                        "evaluation_method": item.get("evaluation_method", ""),
                    },
                )()
                items.append(converted_item)

    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning(f"JSON解析エラー: {str(e)} (curriculum_id={curriculum.id})")
        items = []

    return items


def get_curriculum_data_for_class(class_id: int) -> List[Dict[str, Any]]:
    """
    クラスのカリキュラムデータを取得

    Args:
        class_id: クラスID

    Returns:
        List: カリキュラムデータのリスト（curriculum, items含む）
    """
    curriculum_data = []

    try:
        curriculums = Curriculum.query.filter_by(class_id=class_id).all()

        for curriculum in curriculums:
            items = get_curriculum_items(curriculum)
            curriculum_data.append({"curriculum": curriculum, "items": items})

    except Exception as e:
        logger.error(f"クラスカリキュラムデータ取得エラー: {str(e)} (class_id={class_id})")

    return curriculum_data


def calculate_curriculum_statistics(
    curriculum_data: List[Dict[str, Any]]
) -> Dict[str, int]:
    """
    カリキュラム統計を計算

    Args:
        curriculum_data: カリキュラムデータのリスト

    Returns:
        Dict: 統計データ（総項目数、総時間数等）
    """
    total_items = sum(len(data["items"]) for data in curriculum_data)
    total_hours = 0
    categories_set = set()

    for data in curriculum_data:
        for item in data["items"]:
            if hasattr(item, "hours") and item.hours:
                try:
                    total_hours += int(item.hours)
                except (ValueError, TypeError):
                    pass

            if hasattr(item, "category") and item.category:
                categories_set.add(item.category)

    return {
        "total_items": total_items,
        "total_hours": total_hours,
        "categories_with_content": len(categories_set),
        "total_curriculums": len(curriculum_data),
    }
