"""
QuestEd ランキングサービス

学習成果に基づくランキング機能を提供します。
様々な指標（総合ポイント、正答率、学習時間等）でランキングを計算し、
キャッシュ機能により高速な表示を実現します。

機能:
- 総合ポイントランキング
- 週間・月間ポイントランキング
- 正答率ランキング
- 学習時間ランキング
- 継続性ランキング
- 学校・クラス別ランキング
- キャッシュ機能

Author: QuestEd Development Team
Created: 2025-01-15
Version: 1.0.0
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app
from sqlalchemy import and_, case, desc, func, or_, text

from app.models import Class, Ranking, RankingCache, School, User
from extensions import db

# コンディショナルインポート
try:
    from app.models import StudentUnitSelection
except ImportError:
    StudentUnitSelection = None

try:
    from app.utils.validators import validate_ranking_params
except ImportError:

    def validate_ranking_params(ranking_type, scope, scope_id, limit):
        return {
            "ranking_type": ranking_type,
            "scope": scope,
            "scope_id": scope_id,
            "limit": limit,
        }


# BaseBuilderモデルのインポート
from basebuilder.models import AnswerRecord, WordProficiency

logger = logging.getLogger(__name__)


class RankingService:
    """
    ランキングサービスクラス

    学習データに基づいて様々なランキングを計算し、
    効率的にデータを提供します。
    """

    # キャッシュ有効期間（分）
    CACHE_DURATION = {
        "total_points": 60,  # 総合ポイント: 1時間
        "weekly_points": 30,  # 週間ポイント: 30分
        "monthly_points": 60,  # 月間ポイント: 1時間
        "accuracy_rate": 30,  # 正答率: 30分
        "study_time": 15,  # 学習時間: 15分
        "consistency": 120,  # 継続性: 2時間
    }

    # ポイント計算基準（改良版）
    POINTS_CONFIG = {
        "correct_answer": 10,  # BaseBuilder正答×10点
        "chat_usage": 5,  # チャット利用×5点
        "activity_log": 15,  # 学習記録×15点
        "daily_login": 30,  # 日次ログイン×30点
        "study_minute": 1,  # 学習1分あたり
        "streak_bonus": 20,  # 連続日数ボーナス（日数×20）
        "unit_completion": 100,  # 単元完了
        "perfect_score": 50,  # 満点ボーナス
    }

    @classmethod
    def get_ranking(
        cls,
        ranking_type: str,
        scope: str = "school",
        scope_id: int = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        ランキングデータを取得（簡素化版）

        Args:
            ranking_type: ランキング種類
            scope: 範囲（'school' or 'class'）
            scope_id: 範囲ID（学校IDまたはクラスID）
            limit: 取得件数

        Returns:
            Dict: ランキングデータ
        """
        try:
            # キャッシュ機能を一時的に無効化
            ranking_data = cls._calculate_ranking(ranking_type, scope, scope_id, limit)
            return ranking_data

        except Exception as e:
            logger.error(f"ランキング取得エラー: {str(e)}", exc_info=True)
            return {
                "rankings": [],
                "total_participants": 0,
                "last_updated": datetime.utcnow().isoformat(),
                "error": "ランキングデータの取得に失敗しました",
            }

    @classmethod
    def _calculate_ranking(
        cls, ranking_type: str, scope: str, scope_id: int, limit: int
    ) -> Dict[str, Any]:
        """
        ランキングを計算

        Args:
            ranking_type: ランキング種類
            scope: 範囲
            scope_id: 範囲ID
            limit: 取得件数

        Returns:
            Dict: 計算されたランキングデータ
        """
        # セキュリティ：入力値検証
        valid_ranking_types = [
            "total_points",
            "weekly_points",
            "monthly_points",
            "accuracy_rate",
            "study_time",
            "consistency",
        ]
        valid_scopes = ["school", "class"]

        if ranking_type not in valid_ranking_types:
            raise ValueError(f"無効なランキング種類: {ranking_type}")
        if scope not in valid_scopes:
            raise ValueError(f"無効な範囲: {scope}")
        if scope == "class" and (not isinstance(scope_id, int) or scope_id < 1):
            raise ValueError(f"無効な範囲ID: {scope_id}")
        if not isinstance(limit, int) or limit < 1 or limit > 1000:
            raise ValueError(f"無効な取得件数: {limit}")

        if ranking_type == "total_points":
            return cls._calculate_total_points_ranking(scope, scope_id, limit)
        elif ranking_type == "weekly_points":
            return cls._calculate_weekly_points_ranking(scope, scope_id, limit)
        elif ranking_type == "monthly_points":
            return cls._calculate_monthly_points_ranking(scope, scope_id, limit)
        elif ranking_type == "accuracy_rate":
            return cls._calculate_accuracy_ranking(scope, scope_id, limit)
        elif ranking_type == "study_time":
            return cls._calculate_study_time_ranking(scope, scope_id, limit)
        elif ranking_type == "consistency":
            return cls._calculate_consistency_ranking(scope, scope_id, limit)
        else:
            raise ValueError(f"未対応のランキング種類: {ranking_type}")

    @classmethod
    def _calculate_total_points_ranking(
        cls, scope: str, scope_id: int, limit: int
    ) -> Dict[str, Any]:
        """総合ポイントランキングを計算（改良版：シンプル化でユーザー名取得を修正）"""
        logger.info(
            f"Calculating total points ranking: scope={scope}, scope_id={scope_id}, limit={limit}"
        )

        try:
            # 段階的計算：各テーブルを個別に集計してからPythonで統合
            from app.models import ActivityLog, ChatHistory

            # 1. 基本ユーザーリストを取得（スコープフィルタリング適用）
            user_query = db.session.query(
                User.id, func.coalesce(User.full_name, User.username).label("name")
            ).filter(User.role == "student", User.is_active == True)

            # スコープフィルタリング
            if scope == "school" and scope_id:
                user_query = user_query.filter(User.school_id == scope_id)
            elif scope == "class" and scope_id:
                from app.models import ClassEnrollment

                user_query = user_query.join(
                    ClassEnrollment, User.id == ClassEnrollment.student_id
                ).filter(
                    ClassEnrollment.class_id == scope_id,
                    ClassEnrollment.is_active == True,
                )

            users = user_query.all()
            logger.info(f"Found {len(users)} eligible students for ranking")

            if not users:
                return {
                    "rankings": [],
                    "total_participants": 0,
                    "last_updated": datetime.utcnow().isoformat(),
                    "ranking_type": "total_points",
                }

            user_ids = [user.id for user in users]

            # 2. BaseBuilder統計を個別に取得（型変換を修正）
            basebuilder_stats = {}
            bb_results = (
                db.session.query(
                    AnswerRecord.student_id,
                    func.count(AnswerRecord.id).label("total_answers"),
                    func.sum(func.cast(AnswerRecord.is_correct, db.Integer)).label(
                        "correct_answers"
                    ),  # 明示的な型変換
                )
                .filter(AnswerRecord.student_id.in_(user_ids))
                .group_by(AnswerRecord.student_id)
                .all()
            )

            for result in bb_results:
                # Noneチェックと型変換を強化
                total_answers = (
                    result.total_answers if result.total_answers is not None else 0
                )
                correct_answers = (
                    result.correct_answers if result.correct_answers is not None else 0
                )

                basebuilder_stats[result.student_id] = {
                    "total_answers": int(total_answers),
                    "correct_answers": int(correct_answers),
                }

                logger.debug(
                    f"BaseBuilder stats for student {result.student_id}: total={total_answers}, correct={correct_answers}"
                )

            # 3. チャット統計を個別に取得
            chat_stats = {}
            chat_results = (
                db.session.query(
                    ChatHistory.user_id, func.count(ChatHistory.id).label("chat_count")
                )
                .filter(ChatHistory.user_id.in_(user_ids))
                .group_by(ChatHistory.user_id)
                .all()
            )

            for result in chat_results:
                chat_stats[result.user_id] = int(result.chat_count or 0)

            # 4. 学習記録統計を個別に取得
            activity_stats = {}
            activity_results = (
                db.session.query(
                    ActivityLog.student_id,
                    func.count(ActivityLog.id).label("activity_count"),
                )
                .filter(ActivityLog.student_id.in_(user_ids))
                .group_by(ActivityLog.student_id)
                .all()
            )

            for result in activity_results:
                activity_stats[result.student_id] = int(result.activity_count or 0)

            # 5. Pythonでポイント計算と統合
            ranking_data = []
            for user in users:
                # 各統計を取得（デフォルト値付き）
                bb_data = basebuilder_stats.get(
                    user.id, {"total_answers": 0, "correct_answers": 0}
                )
                chat_count = chat_stats.get(user.id, 0)
                activity_count = activity_stats.get(user.id, 0)

                # ポイント計算
                total_points = (
                    bb_data["correct_answers"] * cls.POINTS_CONFIG["correct_answer"]
                    + chat_count * cls.POINTS_CONFIG["chat_usage"]
                    + activity_count * cls.POINTS_CONFIG["activity_log"]
                )

                ranking_data.append(
                    {
                        "student_id": user.id,
                        "student_name": user.name,
                        "total_points": total_points,
                        "total_answers": bb_data["total_answers"],
                        "correct_answers": bb_data["correct_answers"],
                        "chat_count": chat_count,
                        "activity_count": activity_count,
                    }
                )

            # 6. ポイント順でソート
            ranking_data.sort(key=lambda x: x["total_points"], reverse=True)

            # 7. 制限適用
            if limit:
                ranking_data = ranking_data[:limit]

            logger.info(
                f"Found {len(ranking_data)} ranking entries with corrected point system"
            )

            # デバッグ：最初の3件の詳細をログ出力
            for i, result in enumerate(ranking_data[:3]):
                logger.info(
                    f"Rank {i+1}: ID={result['student_id']}, Name={result['student_name']}, Points={result['total_points']}, Correct={result['correct_answers']}"
                )

            return {
                "rankings": [
                    {
                        "rank": idx + 1,
                        "student_id": result["student_id"],
                        "student_name": result["student_name"],
                        "full_name": result["student_name"],  # テンプレート互換性のため
                        "username": result["student_name"],  # フォールバック用
                        "score": float(result["total_points"]),
                        "total_answers": result["total_answers"],
                        "correct_answers": result["correct_answers"],
                        "chat_count": result["chat_count"],
                        "activity_count": result["activity_count"],
                        "accuracy_rate": round(
                            (result["correct_answers"] / result["total_answers"]) * 100,
                            1,
                        )
                        if result["total_answers"] > 0
                        else 0,
                        "school_name": None,  # 簡素化のため一時的にNone
                        "class_name": None,
                    }
                    for idx, result in enumerate(ranking_data)
                ],
                "total_participants": len(ranking_data),
                "last_updated": datetime.utcnow().isoformat(),
                "ranking_type": "total_points",
            }

        except Exception as e:
            logger.error(f"Total points ranking calculation error: {str(e)}")
            return {
                "rankings": [],
                "total_participants": 0,
                "last_updated": datetime.utcnow().isoformat(),
                "ranking_type": "total_points",
                "error": str(e),
            }

    @classmethod
    def _calculate_weekly_points_ranking(
        cls, scope: str, scope_id: int, limit: int
    ) -> Dict[str, Any]:
        """週間ポイントランキングを計算（修正版）"""
        logger.info(
            f"Calculating weekly points ranking: scope={scope}, scope_id={scope_id}, limit={limit}"
        )
        week_start = datetime.now() - timedelta(days=7)

        try:
            from app.models import ActivityLog, ChatHistory

            # 1. 基本ユーザーリストを取得（総合ポイントと同じロジック）
            user_query = db.session.query(
                User.id, func.coalesce(User.full_name, User.username).label("name")
            ).filter(User.role == "student", User.is_active == True)

            # スコープフィルタリング（修正：school の場合 scope_id がなくても処理続行）
            if scope == "school" and scope_id:
                user_query = user_query.filter(User.school_id == scope_id)
            elif scope == "class" and scope_id:
                from app.models import ClassEnrollment

                user_query = user_query.join(
                    ClassEnrollment, User.id == ClassEnrollment.student_id
                ).filter(
                    ClassEnrollment.class_id == scope_id,
                    ClassEnrollment.is_active == True,
                )

            users = user_query.all()
            logger.info(f"Found {len(users)} eligible students for weekly ranking")

            if not users:
                return {
                    "rankings": [],
                    "total_participants": 0,
                    "last_updated": datetime.utcnow().isoformat(),
                    "ranking_type": "weekly_points",
                }

            user_ids = [user.id for user in users]

            # 2. 週間BaseBuilder統計を個別に取得
            basebuilder_stats = {}
            bb_results = (
                db.session.query(
                    AnswerRecord.student_id,
                    func.count(AnswerRecord.id).label("total_answers"),
                    func.sum(func.cast(AnswerRecord.is_correct, db.Integer)).label(
                        "correct_answers"
                    ),
                )
                .filter(
                    AnswerRecord.student_id.in_(user_ids),
                    AnswerRecord.created_at >= week_start,
                )
                .group_by(AnswerRecord.student_id)
                .all()
            )

            for result in bb_results:
                total_answers = (
                    result.total_answers if result.total_answers is not None else 0
                )
                correct_answers = (
                    result.correct_answers if result.correct_answers is not None else 0
                )

                basebuilder_stats[result.student_id] = {
                    "total_answers": int(total_answers),
                    "correct_answers": int(correct_answers),
                }

            # 3. 週間チャット統計を個別に取得
            chat_stats = {}
            chat_results = (
                db.session.query(
                    ChatHistory.user_id, func.count(ChatHistory.id).label("chat_count")
                )
                .filter(
                    ChatHistory.user_id.in_(user_ids),
                    ChatHistory.created_at >= week_start,
                )
                .group_by(ChatHistory.user_id)
                .all()
            )

            for result in chat_results:
                chat_stats[result.user_id] = int(result.chat_count or 0)

            # 4. 週間学習記録統計を個別に取得
            activity_stats = {}
            activity_results = (
                db.session.query(
                    ActivityLog.student_id,
                    func.count(ActivityLog.id).label("activity_count"),
                )
                .filter(
                    ActivityLog.student_id.in_(user_ids),
                    ActivityLog.created_at >= week_start,
                )
                .group_by(ActivityLog.student_id)
                .all()
            )

            for result in activity_results:
                activity_stats[result.student_id] = int(result.activity_count or 0)

            # 5. 週間ポイント計算と統合
            ranking_data = []
            for user in users:
                bb_data = basebuilder_stats.get(
                    user.id, {"total_answers": 0, "correct_answers": 0}
                )
                chat_count = chat_stats.get(user.id, 0)
                activity_count = activity_stats.get(user.id, 0)

                weekly_points = (
                    bb_data["correct_answers"] * cls.POINTS_CONFIG["correct_answer"]
                    + chat_count * cls.POINTS_CONFIG["chat_usage"]
                    + activity_count * cls.POINTS_CONFIG["activity_log"]
                )

                ranking_data.append(
                    {
                        "student_id": user.id,
                        "student_name": user.name,
                        "weekly_points": weekly_points,
                        "total_answers": bb_data["total_answers"],
                        "correct_answers": bb_data["correct_answers"],
                        "chat_count": chat_count,
                        "activity_count": activity_count,
                    }
                )

            # 6. ポイント順でソート
            ranking_data.sort(key=lambda x: x["weekly_points"], reverse=True)

            # 7. 制限適用
            if limit:
                ranking_data = ranking_data[:limit]

            logger.info(f"Found {len(ranking_data)} weekly ranking entries")

            return {
                "rankings": [
                    {
                        "rank": idx + 1,
                        "student_id": result["student_id"],
                        "student_name": result["student_name"],
                        "full_name": result["student_name"],
                        "username": result["student_name"],
                        "score": float(result["weekly_points"]),
                        "total_answers": result["total_answers"],
                        "correct_answers": result["correct_answers"],
                        "chat_count": result["chat_count"],
                        "activity_count": result["activity_count"],
                        "school_name": None,
                        "class_name": None,
                    }
                    for idx, result in enumerate(ranking_data)
                ],
                "total_participants": len(ranking_data),
                "last_updated": datetime.utcnow().isoformat(),
                "ranking_type": "weekly_points",
            }

        except Exception as e:
            logger.error(f"Weekly points ranking calculation error: {str(e)}")
            return {
                "rankings": [],
                "total_participants": 0,
                "last_updated": datetime.utcnow().isoformat(),
                "ranking_type": "weekly_points",
                "error": str(e),
            }

    @classmethod
    def _calculate_monthly_points_ranking(
        cls, scope: str, scope_id: int, limit: int
    ) -> Dict[str, Any]:
        """月間ポイントランキングを計算（修正版）"""
        logger.info(
            f"Calculating monthly points ranking: scope={scope}, scope_id={scope_id}, limit={limit}"
        )
        month_start = datetime.now() - timedelta(days=30)

        try:
            from app.models import ActivityLog, ChatHistory

            # 1. 基本ユーザーリストを取得（総合ポイントと同じロジック）
            user_query = db.session.query(
                User.id, func.coalesce(User.full_name, User.username).label("name")
            ).filter(User.role == "student", User.is_active == True)

            # スコープフィルタリング（修正：school の場合 scope_id がなくても処理続行）
            if scope == "school" and scope_id:
                user_query = user_query.filter(User.school_id == scope_id)
            elif scope == "class" and scope_id:
                from app.models import ClassEnrollment

                user_query = user_query.join(
                    ClassEnrollment, User.id == ClassEnrollment.student_id
                ).filter(
                    ClassEnrollment.class_id == scope_id,
                    ClassEnrollment.is_active == True,
                )

            users = user_query.all()
            logger.info(f"Found {len(users)} eligible students for monthly ranking")

            if not users:
                return {
                    "rankings": [],
                    "total_participants": 0,
                    "last_updated": datetime.utcnow().isoformat(),
                    "ranking_type": "monthly_points",
                }

            user_ids = [user.id for user in users]

            # 2. 月間BaseBuilder統計を個別に取得
            basebuilder_stats = {}
            bb_results = (
                db.session.query(
                    AnswerRecord.student_id,
                    func.count(AnswerRecord.id).label("total_answers"),
                    func.sum(func.cast(AnswerRecord.is_correct, db.Integer)).label(
                        "correct_answers"
                    ),
                )
                .filter(
                    AnswerRecord.student_id.in_(user_ids),
                    AnswerRecord.created_at >= month_start,
                )
                .group_by(AnswerRecord.student_id)
                .all()
            )

            for result in bb_results:
                total_answers = (
                    result.total_answers if result.total_answers is not None else 0
                )
                correct_answers = (
                    result.correct_answers if result.correct_answers is not None else 0
                )

                basebuilder_stats[result.student_id] = {
                    "total_answers": int(total_answers),
                    "correct_answers": int(correct_answers),
                }

            # 3. 月間チャット統計を個別に取得
            chat_stats = {}
            chat_results = (
                db.session.query(
                    ChatHistory.user_id, func.count(ChatHistory.id).label("chat_count")
                )
                .filter(
                    ChatHistory.user_id.in_(user_ids),
                    ChatHistory.created_at >= month_start,
                )
                .group_by(ChatHistory.user_id)
                .all()
            )

            for result in chat_results:
                chat_stats[result.user_id] = int(result.chat_count or 0)

            # 4. 月間学習記録統計を個別に取得
            activity_stats = {}
            activity_results = (
                db.session.query(
                    ActivityLog.student_id,
                    func.count(ActivityLog.id).label("activity_count"),
                )
                .filter(
                    ActivityLog.student_id.in_(user_ids),
                    ActivityLog.created_at >= month_start,
                )
                .group_by(ActivityLog.student_id)
                .all()
            )

            for result in activity_results:
                activity_stats[result.student_id] = int(result.activity_count or 0)

            # 5. 月間ポイント計算と統合
            ranking_data = []
            for user in users:
                bb_data = basebuilder_stats.get(
                    user.id, {"total_answers": 0, "correct_answers": 0}
                )
                chat_count = chat_stats.get(user.id, 0)
                activity_count = activity_stats.get(user.id, 0)

                monthly_points = (
                    bb_data["correct_answers"] * cls.POINTS_CONFIG["correct_answer"]
                    + chat_count * cls.POINTS_CONFIG["chat_usage"]
                    + activity_count * cls.POINTS_CONFIG["activity_log"]
                )

                ranking_data.append(
                    {
                        "student_id": user.id,
                        "student_name": user.name,
                        "monthly_points": monthly_points,
                        "total_answers": bb_data["total_answers"],
                        "correct_answers": bb_data["correct_answers"],
                        "chat_count": chat_count,
                        "activity_count": activity_count,
                    }
                )

            # 6. ポイント順でソート
            ranking_data.sort(key=lambda x: x["monthly_points"], reverse=True)

            # 7. 制限適用
            if limit:
                ranking_data = ranking_data[:limit]

            logger.info(f"Found {len(ranking_data)} monthly ranking entries")

            return {
                "rankings": [
                    {
                        "rank": idx + 1,
                        "student_id": result["student_id"],
                        "student_name": result["student_name"],
                        "full_name": result["student_name"],
                        "username": result["student_name"],
                        "score": float(result["monthly_points"]),
                        "total_answers": result["total_answers"],
                        "correct_answers": result["correct_answers"],
                        "chat_count": result["chat_count"],
                        "activity_count": result["activity_count"],
                        "school_name": None,
                        "class_name": None,
                    }
                    for idx, result in enumerate(ranking_data)
                ],
                "total_participants": len(ranking_data),
                "last_updated": datetime.utcnow().isoformat(),
                "ranking_type": "monthly_points",
            }

        except Exception as e:
            logger.error(f"Monthly points ranking calculation error: {str(e)}")
            return {
                "rankings": [],
                "total_participants": 0,
                "last_updated": datetime.utcnow().isoformat(),
                "ranking_type": "monthly_points",
                "error": str(e),
            }

    @classmethod
    def _calculate_accuracy_ranking(
        cls, scope: str, scope_id: int, limit: int
    ) -> Dict[str, Any]:
        """正答率ランキングを計算（最低20問回答必須）（修正版）"""
        logger.info(
            f"Calculating accuracy ranking: scope={scope}, scope_id={scope_id}, limit={limit}"
        )

        try:
            # シンプルな直接結合クエリで正確なユーザー情報を取得
            ranking_query = (
                db.session.query(
                    User.id.label("student_id"),
                    User.username.label("student_name"),
                    (
                        func.sum(AnswerRecord.is_correct)
                        / func.count(AnswerRecord.id)
                        * 100
                    ).label("accuracy_rate"),
                    func.count(AnswerRecord.id).label("total_answers"),
                    func.sum(AnswerRecord.is_correct).label("correct_answers"),
                )
                .select_from(User)
                .join(AnswerRecord, User.id == AnswerRecord.student_id)
                .filter(User.role == "student", User.is_active == True)
            )

            # スコープフィルタリング
            if scope == "school" and scope_id:
                ranking_query = ranking_query.filter(User.school_id == scope_id)
            elif scope == "class" and scope_id:
                from app.models import ClassEnrollment

                ranking_query = ranking_query.join(
                    ClassEnrollment, User.id == ClassEnrollment.student_id
                ).filter(
                    ClassEnrollment.class_id == scope_id,
                    ClassEnrollment.is_active == True,
                )

            ranking_query = (
                ranking_query.group_by(User.id, User.username)
                .having(func.count(AnswerRecord.id) >= 20)  # 最低20問回答必須
                .order_by(desc("accuracy_rate"))
                .limit(limit)
            )

            results = ranking_query.all()
            logger.info(
                f"Found {len(results)} accuracy ranking entries with correct user joins"
            )

            return {
                "rankings": [
                    {
                        "rank": idx + 1,
                        "student_id": result.student_id,
                        "student_name": result.student_name,
                        "score": round(float(result.accuracy_rate), 1),
                        "total_answers": result.total_answers,
                        "correct_answers": result.correct_answers,
                        "school_name": None,  # 簡素化のため一時的にNone
                        "class_name": None,
                    }
                    for idx, result in enumerate(results)
                ],
                "total_participants": len(results),
                "last_updated": datetime.utcnow().isoformat(),
                "ranking_type": "accuracy_rate",
            }

        except Exception as e:
            logger.error(f"Accuracy ranking calculation error: {str(e)}")
            return {
                "rankings": [],
                "total_participants": 0,
                "last_updated": datetime.utcnow().isoformat(),
                "ranking_type": "accuracy_rate",
                "error": str(e),
            }

    @classmethod
    def _calculate_study_time_ranking(
        cls, scope: str, scope_id: int, limit: int
    ) -> Dict[str, Any]:
        """学習時間ランキングを計算（BaseBuilder回答数ベース）"""
        week_start = datetime.now() - timedelta(days=7)

        try:
            # BaseBuilderの回答数を学習時間の代理指標として使用
            ranking_query = (
                db.session.query(
                    User.id.label("student_id"),
                    User.username.label("student_name"),
                    func.count(AnswerRecord.id).label("study_activities"),
                    func.sum(AnswerRecord.is_correct).label("correct_answers"),
                )
                .select_from(User)
                .outerjoin(AnswerRecord, User.id == AnswerRecord.student_id)
                .filter(
                    User.role == "student",
                    User.is_active == True,
                    AnswerRecord.created_at >= week_start,
                )
            )

            # スコープフィルタリング
            if scope == "school" and scope_id:
                ranking_query = ranking_query.filter(User.school_id == scope_id)
            elif scope == "class" and scope_id:
                from app.models import ClassEnrollment

                ranking_query = ranking_query.join(
                    ClassEnrollment, User.id == ClassEnrollment.student_id
                ).filter(
                    ClassEnrollment.class_id == scope_id,
                    ClassEnrollment.is_active == True,
                )

            results = (
                ranking_query.group_by(User.id, User.username)
                .order_by(desc("study_activities"))
                .limit(limit)
                .all()
            )

            return {
                "rankings": [
                    {
                        "rank": idx + 1,
                        "student_id": result.student_id,
                        "student_name": result.student_name,
                        "score": float(result.study_activities or 0),
                        "hours": round(
                            float(result.study_activities or 0) / 60, 1
                        ),  # 1問題=1分と仮定
                        "correct_answers": result.correct_answers,
                        "school_name": None,
                        "class_name": None,
                    }
                    for idx, result in enumerate(results)
                ],
                "total_participants": len(results),
                "last_updated": datetime.utcnow().isoformat(),
                "ranking_type": "study_time",
            }

        except Exception as e:
            logger.error(f"Study time ranking calculation error: {str(e)}")
            return {
                "rankings": [],
                "total_participants": 0,
                "last_updated": datetime.utcnow().isoformat(),
                "ranking_type": "study_time",
                "error": str(e),
            }

    @classmethod
    def _calculate_consistency_ranking(
        cls, scope: str, scope_id: int, limit: int
    ) -> Dict[str, Any]:
        """継続性ランキングを計算（学習日数＋ログイン日数ベース）"""
        thirty_days_ago = datetime.now() - timedelta(days=30)

        try:
            from app.models import ActivityLog, ChatHistory

            # 学習活動日数（BaseBuilder + チャット + 学習記録）を計算
            activity_dates_subquery = (
                db.session.query(
                    AnswerRecord.student_id.label("user_id"),
                    func.date(AnswerRecord.created_at).label("activity_date"),
                )
                .filter(AnswerRecord.created_at >= thirty_days_ago)
                .union_all(
                    db.session.query(
                        ChatHistory.user_id.label("user_id"),
                        func.date(ChatHistory.created_at).label("activity_date"),
                    ).filter(ChatHistory.created_at >= thirty_days_ago)
                )
                .union_all(
                    db.session.query(
                        ActivityLog.student_id.label("user_id"),
                        func.date(ActivityLog.created_at).label("activity_date"),
                    ).filter(ActivityLog.created_at >= thirty_days_ago)
                )
                .subquery()
            )

            # ユニークな活動日数を計算
            consistency_subquery = (
                db.session.query(
                    activity_dates_subquery.c.user_id,
                    func.count(
                        func.distinct(activity_dates_subquery.c.activity_date)
                    ).label("activity_days"),
                )
                .group_by(activity_dates_subquery.c.user_id)
                .subquery()
            )

            ranking_query = (
                db.session.query(
                    User.id.label("student_id"),
                    User.username.label("student_name"),
                    func.coalesce(consistency_subquery.c.activity_days, 0).label(
                        "study_days"
                    ),
                    (
                        func.coalesce(consistency_subquery.c.activity_days, 0)
                        * cls.POINTS_CONFIG["daily_login"]
                    ).label("consistency_points"),
                )
                .select_from(User)
                .outerjoin(
                    consistency_subquery, User.id == consistency_subquery.c.user_id
                )
                .filter(User.role == "student", User.is_active == True)
            )

            # スコープフィルタリング
            if scope == "school" and scope_id:
                ranking_query = ranking_query.filter(User.school_id == scope_id)
            elif scope == "class" and scope_id:
                from app.models import ClassEnrollment

                ranking_query = ranking_query.join(
                    ClassEnrollment, User.id == ClassEnrollment.student_id
                ).filter(
                    ClassEnrollment.class_id == scope_id,
                    ClassEnrollment.is_active == True,
                )

            results = (
                ranking_query.group_by(User.id, User.username)
                .order_by(desc("study_days"))
                .limit(limit)
                .all()
            )

            return {
                "rankings": [
                    {
                        "rank": idx + 1,
                        "student_id": result.student_id,
                        "student_name": result.student_name,
                        "score": result.study_days,
                        "consistency_rate": round((result.study_days / 30) * 100, 1),
                        "total_answers": result.total_answers,
                        "school_name": None,
                        "class_name": None,
                    }
                    for idx, result in enumerate(results)
                ],
                "total_participants": len(results),
                "last_updated": datetime.utcnow().isoformat(),
                "ranking_type": "consistency",
            }

        except Exception as e:
            logger.error(f"Consistency ranking calculation error: {str(e)}")
            return {
                "rankings": [],
                "total_participants": 0,
                "last_updated": datetime.utcnow().isoformat(),
                "ranking_type": "consistency",
                "error": str(e),
            }

    @classmethod
    def _get_base_user_query(cls, scope: str, scope_id: int):
        """ベースとなるユーザークエリを取得"""
        query = (
            db.session.query(User)
            .select_from(User)
            .filter(User.role == "student", User.is_active == True)
        )

        if scope == "school" and scope_id:
            # 学校フィルタ: users.school_id または class_enrollments経由
            from app.models import Class, ClassEnrollment

            query = (
                query.outerjoin(ClassEnrollment, User.id == ClassEnrollment.student_id)
                .outerjoin(Class, ClassEnrollment.class_id == Class.id)
                .filter(
                    or_(
                        User.school_id == scope_id,
                        and_(
                            ClassEnrollment.is_active == True,
                            Class.school_id == scope_id,
                        ),
                    )
                )
            )
        elif scope == "class" and scope_id:
            from app.models import ClassEnrollment

            query = query.join(
                ClassEnrollment, User.id == ClassEnrollment.student_id
            ).filter(
                ClassEnrollment.class_id == scope_id, ClassEnrollment.is_active == True
            )
        else:
            # グローバルランキング: BaseBuilderで学習データがある生徒のみ
            query = query.filter(
                User.id.in_(db.session.query(AnswerRecord.student_id).distinct())
            )

        return query

    @classmethod
    def _count_participants(cls, scope: str, scope_id: int) -> int:
        """参加者数をカウント"""
        return cls._get_base_user_query(scope, scope_id).count()

    @classmethod
    def _get_cached_ranking(
        cls, ranking_type: str, scope: str, scope_id: int
    ) -> Optional[Dict[str, Any]]:
        """キャッシュからランキングデータを取得"""
        cache_key = cls._generate_cache_key(ranking_type, scope, scope_id)

        cached = RankingCache.query.filter_by(cache_key=cache_key).first()

        if cached and cached.expires_at > datetime.utcnow():
            return cached.ranking_data

        # 期限切れのキャッシュを削除
        if cached:
            db.session.delete(cached)
            db.session.commit()

        return None

    @classmethod
    def _cache_ranking(
        cls, ranking_type: str, scope: str, scope_id: int, data: Dict[str, Any]
    ):
        """ランキングデータをキャッシュ"""
        try:
            cache_key = cls._generate_cache_key(ranking_type, scope, scope_id)
            cache_duration = cls.CACHE_DURATION.get(ranking_type, 30)
            expires_at = datetime.utcnow() + timedelta(minutes=cache_duration)

            # 既存のキャッシュを削除
            existing = RankingCache.query.filter_by(cache_key=cache_key).first()
            if existing:
                db.session.delete(existing)

            # 新しいキャッシュを作成
            cache = RankingCache(
                cache_key=cache_key,
                ranking_type=ranking_type,
                scope=scope,
                scope_id=scope_id or 0,
                ranking_data=data,
                participant_count=data.get("total_participants", 0),
                expires_at=expires_at,
            )

            db.session.add(cache)
            db.session.commit()

        except Exception as e:
            logger.error(f"キャッシュ保存エラー: {str(e)}")
            db.session.rollback()

    @classmethod
    def _generate_cache_key(cls, ranking_type: str, scope: str, scope_id: int) -> str:
        """キャッシュキーを生成"""
        key_data = f"{ranking_type}:{scope}:{scope_id or 'all'}"
        return hashlib.md5(key_data.encode()).hexdigest()

    @classmethod
    def clear_cache(cls, ranking_type: str = None):
        """キャッシュをクリア"""
        try:
            query = RankingCache.query
            if ranking_type:
                query = query.filter_by(ranking_type=ranking_type)

            query.delete()
            db.session.commit()
            logger.info(f"ランキングキャッシュをクリアしました: {ranking_type or 'all'}")

        except Exception as e:
            logger.error(f"キャッシュクリアエラー: {str(e)}")
            db.session.rollback()

    @classmethod
    def get_student_rank(
        cls,
        student_id: int,
        ranking_type: str,
        scope: str = "school",
        scope_id: int = None,
    ) -> Dict[str, Any]:
        """特定の学生のランキング情報を取得"""
        try:
            ranking_data = cls.get_ranking(ranking_type, scope, scope_id, limit=1000)

            for rank_info in ranking_data["rankings"]:
                if rank_info["student_id"] == student_id:
                    return {
                        "rank": rank_info["rank"],
                        "score": rank_info["score"],
                        "total_participants": ranking_data["total_participants"],
                        "ranking_type": ranking_type,
                        "percentile": round(
                            (
                                1
                                - (rank_info["rank"] - 1)
                                / ranking_data["total_participants"]
                            )
                            * 100,
                            1,
                        ),
                    }

            return {
                "rank": None,
                "score": 0,
                "total_participants": ranking_data["total_participants"],
                "ranking_type": ranking_type,
                "percentile": 0,
            }

        except Exception as e:
            logger.error(f"学生ランキング取得エラー: {str(e)}")
            return {
                "rank": None,
                "score": 0,
                "total_participants": 0,
                "ranking_type": ranking_type,
                "percentile": 0,
                "error": str(e),
            }

    @classmethod
    def update_rankings(cls):
        """全ランキングを更新（定期実行用）"""
        ranking_types = [
            "total_points",
            "weekly_points",
            "monthly_points",
            "accuracy_rate",
            "study_time",
            "consistency",
        ]

        for ranking_type in ranking_types:
            try:
                # キャッシュをクリア
                cls.clear_cache(ranking_type)

                # 学校全体のランキングを計算
                cls.get_ranking(ranking_type, "school", None)

                # 各クラスのランキングを計算
                classes = Class.query.all()
                for class_obj in classes:
                    cls.get_ranking(ranking_type, "class", class_obj.id)

                logger.info(f"{ranking_type} ランキングを更新しました")

            except Exception as e:
                logger.error(f"{ranking_type} ランキング更新エラー: {str(e)}")

    @classmethod
    def _format_ranking_entry(cls, result, rank, ranking_type):
        """ランキングエントリーのフォーマット（簡素化版）"""
        try:
            # 基本的なオブジェクト属性アクセスのみ
            user_id = getattr(result, "id", 0)
            username = getattr(result, "username", "Unknown")

            # スコア取得を簡素化
            if ranking_type == "total_points":
                score = getattr(result, "total_points", 0)
            elif ranking_type == "weekly_points":
                score = getattr(result, "weekly_points", 0)
            elif ranking_type == "monthly_points":
                score = getattr(result, "monthly_points", 0)
            else:
                score = 0

            return {
                "rank": rank or 0,
                "student_id": user_id or 0,
                "student_name": username or "Unknown",
                "score": float(score) if score is not None else 0.0,
                "school_name": None,
                "class_name": None,
            }
        except Exception:
            return {
                "rank": rank or 0,
                "student_id": 0,
                "student_name": "Error",
                "score": 0.0,
                "school_name": None,
                "class_name": None,
            }
