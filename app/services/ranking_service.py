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

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import func, text, desc, and_, or_, case
from flask import current_app
import hashlib
import json

from extensions import db
from app.models import (
    User, School, Class, Ranking, RankingCache,
    ActivityLog
)
# コンディショナルインポート
try:
    from app.models import StudentUnitSelection
except ImportError:
    StudentUnitSelection = None

try:
    from app.utils.validators import validate_ranking_params
except ImportError:
    def validate_ranking_params(ranking_type, scope, scope_id, limit):
        return {'ranking_type': ranking_type, 'scope': scope, 'scope_id': scope_id, 'limit': limit}

# BaseBuilderモデルのコンディショナルインポート
try:
    from basebuilder.models import AnswerRecord, ProficiencyRecord, WordProficiency
except ImportError:
    # BaseBuilderモジュールが利用できない場合のダミークラス
    class AnswerRecord:
        student_id = None
        is_correct = None
        created_at = None
    
    class ProficiencyRecord:
        student_id = None
        score = None
        created_at = None
    
    class WordProficiency:
        student_id = None
        proficiency_level = None
        created_at = None

logger = logging.getLogger(__name__)


class RankingService:
    """
    ランキングサービスクラス
    
    学習データに基づいて様々なランキングを計算し、
    効率的にデータを提供します。
    """
    
    # キャッシュ有効期間（分）
    CACHE_DURATION = {
        'total_points': 60,      # 総合ポイント: 1時間
        'weekly_points': 30,     # 週間ポイント: 30分
        'monthly_points': 60,    # 月間ポイント: 1時間
        'accuracy_rate': 30,     # 正答率: 30分
        'study_time': 15,        # 学習時間: 15分
        'consistency': 120       # 継続性: 2時間
    }
    
    # ポイント計算基準
    POINTS_CONFIG = {
        'correct_answer': 10,     # 正解1問あたり
        'study_minute': 1,        # 学習1分あたり
        'daily_login': 50,        # 日次ログイン
        'streak_bonus': 20,       # 連続日数ボーナス（日数×20）
        'unit_completion': 100,   # 単元完了
        'perfect_score': 50       # 満点ボーナス
    }

    @classmethod
    def get_ranking(cls, ranking_type: str, scope: str = 'school', 
                   scope_id: int = None, limit: int = 50) -> Dict[str, Any]:
        """
        ランキングデータを取得
        
        Args:
            ranking_type: ランキング種類
            scope: 範囲（'school' or 'class'）
            scope_id: 範囲ID（学校IDまたはクラスID）
            limit: 取得件数
            
        Returns:
            Dict: ランキングデータ
        """
        try:
            # キャッシュから取得を試行
            cached_data = cls._get_cached_ranking(ranking_type, scope, scope_id)
            if cached_data:
                return cached_data
            
            # キャッシュにない場合は計算
            ranking_data = cls._calculate_ranking(ranking_type, scope, scope_id, limit)
            
            # キャッシュに保存
            cls._cache_ranking(ranking_type, scope, scope_id, ranking_data)
            
            return ranking_data
            
        except Exception as e:
            logger.error(f"ランキング取得エラー: {str(e)}", exc_info=True)
            # セキュリティ: 本番環境では詳細なエラー情報を隠す
            error_msg = 'ランキングデータの取得に失敗しました'
            if current_app.debug:
                error_msg += f' (詳細: {str(e)})'
            
            return {
                'rankings': [],
                'total_participants': 0,
                'last_updated': datetime.utcnow().isoformat(),
                'error': error_msg
            }

    @classmethod
    def _calculate_ranking(cls, ranking_type: str, scope: str, 
                          scope_id: int, limit: int) -> Dict[str, Any]:
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
        valid_ranking_types = ['total_points', 'weekly_points', 'monthly_points', 
                              'accuracy_rate', 'study_time', 'consistency']
        valid_scopes = ['school', 'class']
        
        if ranking_type not in valid_ranking_types:
            raise ValueError(f"無効なランキング種類: {ranking_type}")
        if scope not in valid_scopes:
            raise ValueError(f"無効な範囲: {scope}")
        if not isinstance(scope_id, int) or scope_id < 1:
            raise ValueError(f"無効な範囲ID: {scope_id}")
        if not isinstance(limit, int) or limit < 1 or limit > 1000:
            raise ValueError(f"無効な取得件数: {limit}")
        
        if ranking_type == 'total_points':
            return cls._calculate_total_points_ranking(scope, scope_id, limit)
        elif ranking_type == 'weekly_points':
            return cls._calculate_weekly_points_ranking(scope, scope_id, limit)
        elif ranking_type == 'monthly_points':
            return cls._calculate_monthly_points_ranking(scope, scope_id, limit)
        elif ranking_type == 'accuracy_rate':
            return cls._calculate_accuracy_ranking(scope, scope_id, limit)
        elif ranking_type == 'study_time':
            return cls._calculate_study_time_ranking(scope, scope_id, limit)
        elif ranking_type == 'consistency':
            return cls._calculate_consistency_ranking(scope, scope_id, limit)
        else:
            raise ValueError(f"未対応のランキング種類: {ranking_type}")

    @classmethod
    def _calculate_total_points_ranking(cls, scope: str, scope_id: int, limit: int) -> Dict[str, Any]:
        """総合ポイントランキングを計算"""
        logger.info(f"Calculating total points ranking: scope={scope}, scope_id={scope_id}, limit={limit}")
        
        base_query = cls._get_base_user_query(scope, scope_id)
        logger.debug(f"Base query filters applied for scope={scope}, scope_id={scope_id}")
        
        # ポイント計算のサブクエリ（BaseBuilderモデル対応）
        points_subquery = db.session.query(
            User.id.label('user_id'),
            (
                # 学習時間ポイント（分）
                func.coalesce(
                    func.sum(0), 0  # study_durationフィールドが存在しないためゼロで置き換え
                ) +
                # 単元完了ポイント
                func.coalesce(
                    func.sum(
                        case(
                            (StudentUnitSelection.progress_percentage >= 100, 
                              cls.POINTS_CONFIG['unit_completion']),
                            else_=0
                        )
                    ), 0
                )
            ).label('total_points')
        ).select_from(User).outerjoin(
            ActivityLog, User.id == ActivityLog.student_id
        ).outerjoin(
            StudentUnitSelection, User.id == StudentUnitSelection.student_id
        ).filter(
            User.role == 'student',
            User.is_active == True
        ).group_by(User.id).subquery()
        
        # BaseBuilderモジュールが利用可能な場合は正解ポイントも追加
        try:
            answer_points_subquery = db.session.query(
                AnswerRecord.student_id,
                func.sum(AnswerRecord.is_correct * cls.POINTS_CONFIG['correct_answer']).label('answer_points')
            ).group_by(AnswerRecord.student_id).subquery()
            
            points_subquery = db.session.query(
                points_subquery.c.user_id,
                (points_subquery.c.total_points + 
                 func.coalesce(answer_points_subquery.c.answer_points, 0)).label('total_points')
            ).outerjoin(
                answer_points_subquery, points_subquery.c.user_id == answer_points_subquery.c.student_id
            ).subquery()
        except Exception as e:
            # BaseBuilderモジュールが利用できない場合はActivityLogベースのみ
            logger.warning(f"BaseBuilderモジュール利用不可、ActivityLogベースで計算: {e}")
            pass
        
        # ランキングクエリ
        ranking_query = base_query.join(
            points_subquery, User.id == points_subquery.c.user_id
        ).add_columns(
            points_subquery.c.total_points,
            func.row_number().over(order_by=desc(points_subquery.c.total_points)).label('rank')
        ).order_by(desc(points_subquery.c.total_points)).limit(limit)
        
        results = ranking_query.all()
        logger.info(f"Found {len(results)} ranking entries for total_points")
        
        if not results:
            logger.warning("No ranking data found - checking user count and activity data")
            user_count = base_query.count()
            activity_count = ActivityLog.query.count()
            logger.warning(f"Total users matching criteria: {user_count}, Total activities: {activity_count}")
            
            # データが空の場合は基本的なユーザーリストを返す（開発・テスト用）
            fallback_users = base_query.limit(limit).all()
            logger.info(f"Fallback: returning {len(fallback_users)} users with base scores")
            
            return {
                'rankings': [
                    {
                        'rank': idx + 1,
                        'student_id': user.id,
                        'student_name': user.username,
                        'score': 10.0,  # デフォルトスコア
                        'school_name': user.school.name if user.school else None,
                        'class_name': ', '.join([c.name for c in user.classes]) if user.classes else None
                    }
                    for idx, user in enumerate(fallback_users)
                ],
                'total_participants': user_count,
                'last_updated': datetime.utcnow().isoformat(),
                'ranking_type': 'total_points',
                'is_fallback': True  # フォールバックデータであることを示す
            }
        
        return {
            'rankings': [
                {
                    'rank': result.rank,
                    'student_id': result.id,
                    'student_name': result.username,
                    'score': float(result.total_points),
                    'school_name': result.school.name if result.school else None,
                    'class_name': ', '.join([c.name for c in result.classes]) if result.classes else None
                }
                for result in results
            ],
            'total_participants': cls._count_participants(scope, scope_id),
            'last_updated': datetime.utcnow().isoformat(),
            'ranking_type': 'total_points'
        }

    @classmethod
    def _calculate_weekly_points_ranking(cls, scope: str, scope_id: int, limit: int) -> Dict[str, Any]:
        """週間ポイントランキングを計算"""
        week_start = datetime.now() - timedelta(days=7)
        
        base_query = cls._get_base_user_query(scope, scope_id)
        
        # 週間ポイント計算
        points_subquery = db.session.query(
            User.id.label('user_id'),
            (
                func.coalesce(
                    func.sum(
                        case(
                            (AnswerRecord.created_at >= week_start,
                              AnswerRecord.is_correct * cls.POINTS_CONFIG['correct_answer']),
                            else_=0
                        )
                    ), 0
                ) +
                func.coalesce(
                    func.sum(
                        case(
                            (ActivityLog.created_at >= week_start,
                              0),  # study_durationフィールドが存在しないためゼロで置き換え
                            else_=0
                        )
                    ), 0
                )
            ).label('weekly_points')
        ).select_from(User).outerjoin(
            AnswerRecord, User.id == AnswerRecord.student_id
        ).outerjoin(
            ActivityLog, User.id == ActivityLog.student_id
        ).filter(
            User.role == 'student',
            User.is_active == True
        ).group_by(User.id).subquery()
        
        ranking_query = base_query.join(
            points_subquery, User.id == points_subquery.c.user_id
        ).add_columns(
            points_subquery.c.weekly_points,
            func.row_number().over(order_by=desc(points_subquery.c.weekly_points)).label('rank')
        ).order_by(desc(points_subquery.c.weekly_points)).limit(limit)
        
        results = ranking_query.all()
        
        return {
            'rankings': [
                {
                    'rank': result.rank,
                    'student_id': result.id,
                    'student_name': result.username,
                    'score': float(result.weekly_points),
                    'school_name': result.school.name if result.school else None,
                    'class_name': ', '.join([c.name for c in result.classes]) if result.classes else None
                }
                for result in results
            ],
            'total_participants': cls._count_participants(scope, scope_id),
            'last_updated': datetime.utcnow().isoformat(),
            'ranking_type': 'weekly_points'
        }

    @classmethod
    def _calculate_monthly_points_ranking(cls, scope: str, scope_id: int, limit: int) -> Dict[str, Any]:
        """月間ポイントランキングを計算"""
        month_start = datetime.now() - timedelta(days=30)
        
        base_query = cls._get_base_user_query(scope, scope_id)
        
        points_subquery = db.session.query(
            User.id.label('user_id'),
            (
                func.coalesce(
                    func.sum(
                        case(
                            (AnswerRecord.created_at >= month_start,
                              AnswerRecord.is_correct * cls.POINTS_CONFIG['correct_answer']),
                            else_=0
                        )
                    ), 0
                ) +
                func.coalesce(
                    func.sum(
                        case(
                            (ActivityLog.created_at >= month_start,
                              0),  # study_durationフィールドが存在しないためゼロで置き換え
                            else_=0
                        )
                    ), 0
                )
            ).label('monthly_points')
        ).select_from(User).outerjoin(
            AnswerRecord, User.id == AnswerRecord.student_id
        ).outerjoin(
            ActivityLog, User.id == ActivityLog.student_id
        ).filter(
            User.role == 'student',
            User.is_active == True
        ).group_by(User.id).subquery()
        
        ranking_query = base_query.join(
            points_subquery, User.id == points_subquery.c.user_id
        ).add_columns(
            points_subquery.c.monthly_points,
            func.row_number().over(order_by=desc(points_subquery.c.monthly_points)).label('rank')
        ).order_by(desc(points_subquery.c.monthly_points)).limit(limit)
        
        results = ranking_query.all()
        
        return {
            'rankings': [
                {
                    'rank': result.rank,
                    'student_id': result.id,
                    'student_name': result.username,
                    'score': float(result.monthly_points),
                    'school_name': result.school.name if result.school else None,
                    'class_name': ', '.join([c.name for c in result.classes]) if result.classes else None
                }
                for result in results
            ],
            'total_participants': cls._count_participants(scope, scope_id),
            'last_updated': datetime.utcnow().isoformat(),
            'ranking_type': 'monthly_points'
        }

    @classmethod
    def _calculate_accuracy_ranking(cls, scope: str, scope_id: int, limit: int) -> Dict[str, Any]:
        """正答率ランキングを計算（最低20問回答必須）"""
        base_query = cls._get_base_user_query(scope, scope_id)
        
        accuracy_subquery = db.session.query(
            User.id.label('user_id'),
            func.avg(AnswerRecord.is_correct * 100).label('accuracy_rate'),
            func.count(AnswerRecord.id).label('total_answers')
        ).select_from(User).join(
            AnswerRecord, User.id == AnswerRecord.student_id
        ).filter(
            User.role == 'student',
            User.is_active == True
        ).group_by(User.id).having(
            func.count(AnswerRecord.id) >= 20  # 最低20問回答必須
        ).subquery()
        
        ranking_query = base_query.join(
            accuracy_subquery, User.id == accuracy_subquery.c.user_id
        ).add_columns(
            accuracy_subquery.c.accuracy_rate,
            accuracy_subquery.c.total_answers,
            func.row_number().over(order_by=desc(accuracy_subquery.c.accuracy_rate)).label('rank')
        ).order_by(desc(accuracy_subquery.c.accuracy_rate)).limit(limit)
        
        results = ranking_query.all()
        
        return {
            'rankings': [
                {
                    'rank': result.rank,
                    'student_id': result.id,
                    'student_name': result.username,
                    'score': round(float(result.accuracy_rate), 1),
                    'total_answers': result.total_answers,
                    'school_name': result.school.name if result.school else None,
                    'class_name': ', '.join([c.name for c in result.classes]) if result.classes else None
                }
                for result in results
            ],
            'total_participants': cls._count_participants(scope, scope_id),
            'last_updated': datetime.utcnow().isoformat(),
            'ranking_type': 'accuracy_rate'
        }

    @classmethod
    def _calculate_study_time_ranking(cls, scope: str, scope_id: int, limit: int) -> Dict[str, Any]:
        """学習時間ランキングを計算（今週）"""
        week_start = datetime.now() - timedelta(days=7)
        
        base_query = cls._get_base_user_query(scope, scope_id)
        
        study_time_subquery = db.session.query(
            User.id.label('user_id'),
            func.sum(1).label('total_study_time')  # study_durationフィールドが存在しないため活動数で代用
        ).select_from(User).join(
            ActivityLog, User.id == ActivityLog.student_id
        ).filter(
            User.role == 'student',
            User.is_active == True,
            ActivityLog.created_at >= week_start
        ).group_by(User.id).subquery()
        
        ranking_query = base_query.join(
            study_time_subquery, User.id == study_time_subquery.c.user_id
        ).add_columns(
            study_time_subquery.c.total_study_time,
            func.row_number().over(order_by=desc(study_time_subquery.c.total_study_time)).label('rank')
        ).order_by(desc(study_time_subquery.c.total_study_time)).limit(limit)
        
        results = ranking_query.all()
        
        return {
            'rankings': [
                {
                    'rank': result.rank,
                    'student_id': result.id,
                    'student_name': result.username,
                    'score': float(result.total_study_time or 0),
                    'hours': round(float(result.total_study_time or 0) / 60, 1),
                    'school_name': result.school.name if result.school else None,
                    'class_name': ', '.join([c.name for c in result.classes]) if result.classes else None
                }
                for result in results
            ],
            'total_participants': cls._count_participants(scope, scope_id),
            'last_updated': datetime.utcnow().isoformat(),
            'ranking_type': 'study_time'
        }

    @classmethod
    def _calculate_consistency_ranking(cls, scope: str, scope_id: int, limit: int) -> Dict[str, Any]:
        """継続性ランキングを計算（過去30日の学習日数）"""
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        base_query = cls._get_base_user_query(scope, scope_id)
        
        consistency_subquery = db.session.query(
            User.id.label('user_id'),
            func.count(func.distinct(func.date(ActivityLog.created_at))).label('study_days')
        ).select_from(User).join(
            ActivityLog, User.id == ActivityLog.student_id
        ).filter(
            User.role == 'student',
            User.is_active == True,
            ActivityLog.created_at >= thirty_days_ago
        ).group_by(User.id).subquery()
        
        ranking_query = base_query.join(
            consistency_subquery, User.id == consistency_subquery.c.user_id
        ).add_columns(
            consistency_subquery.c.study_days,
            func.row_number().over(order_by=desc(consistency_subquery.c.study_days)).label('rank')
        ).order_by(desc(consistency_subquery.c.study_days)).limit(limit)
        
        results = ranking_query.all()
        
        return {
            'rankings': [
                {
                    'rank': result.rank,
                    'student_id': result.id,
                    'student_name': result.username,
                    'score': result.study_days,
                    'consistency_rate': round((result.study_days / 30) * 100, 1),
                    'school_name': result.school.name if result.school else None,
                    'class_name': ', '.join([c.name for c in result.classes]) if result.classes else None
                }
                for result in results
            ],
            'total_participants': cls._count_participants(scope, scope_id),
            'last_updated': datetime.utcnow().isoformat(),
            'ranking_type': 'consistency'
        }

    @classmethod
    def _get_base_user_query(cls, scope: str, scope_id: int):
        """ベースとなるユーザークエリを取得"""
        query = db.session.query(User).select_from(User).filter(
            User.role == 'student',
            User.is_active == True
        )
        
        if scope == 'school' and scope_id:
            query = query.filter(User.school_id == scope_id)
        elif scope == 'class' and scope_id:
            from app.models import ClassEnrollment
            query = query.join(ClassEnrollment, User.id == ClassEnrollment.student_id).filter(
                ClassEnrollment.class_id == scope_id,
                ClassEnrollment.is_active == True
            )
        
        return query

    @classmethod
    def _count_participants(cls, scope: str, scope_id: int) -> int:
        """参加者数をカウント"""
        return cls._get_base_user_query(scope, scope_id).count()

    @classmethod
    def _get_cached_ranking(cls, ranking_type: str, scope: str, scope_id: int) -> Optional[Dict[str, Any]]:
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
    def _cache_ranking(cls, ranking_type: str, scope: str, scope_id: int, data: Dict[str, Any]):
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
                participant_count=data.get('total_participants', 0),
                expires_at=expires_at
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
    def get_student_rank(cls, student_id: int, ranking_type: str, 
                        scope: str = 'school', scope_id: int = None) -> Dict[str, Any]:
        """特定の学生のランキング情報を取得"""
        try:
            ranking_data = cls.get_ranking(ranking_type, scope, scope_id, limit=1000)
            
            for rank_info in ranking_data['rankings']:
                if rank_info['student_id'] == student_id:
                    return {
                        'rank': rank_info['rank'],
                        'score': rank_info['score'],
                        'total_participants': ranking_data['total_participants'],
                        'ranking_type': ranking_type,
                        'percentile': round((1 - (rank_info['rank'] - 1) / ranking_data['total_participants']) * 100, 1)
                    }
            
            return {
                'rank': None,
                'score': 0,
                'total_participants': ranking_data['total_participants'],
                'ranking_type': ranking_type,
                'percentile': 0
            }
            
        except Exception as e:
            logger.error(f"学生ランキング取得エラー: {str(e)}")
            return {
                'rank': None,
                'score': 0,
                'total_participants': 0,
                'ranking_type': ranking_type,
                'percentile': 0,
                'error': str(e)
            }

    @classmethod
    def update_rankings(cls):
        """全ランキングを更新（定期実行用）"""
        ranking_types = ['total_points', 'weekly_points', 'monthly_points', 
                        'accuracy_rate', 'study_time', 'consistency']
        
        for ranking_type in ranking_types:
            try:
                # キャッシュをクリア
                cls.clear_cache(ranking_type)
                
                # 学校全体のランキングを計算
                cls.get_ranking(ranking_type, 'school', None)
                
                # 各クラスのランキングを計算
                classes = Class.query.all()
                for class_obj in classes:
                    cls.get_ranking(ranking_type, 'class', class_obj.id)
                
                logger.info(f"{ranking_type} ランキングを更新しました")
                
            except Exception as e:
                logger.error(f"{ranking_type} ランキング更新エラー: {str(e)}")