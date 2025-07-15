"""
Data Access Layer
=================
データアクセス層の統合管理

機能:
- 安全なクエリ実行
- キャッシュ管理
- データ整合性チェック
- パフォーマンス監視
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import text
from sqlalchemy.orm import Query

from extensions import db

from .base_service import BaseService


class DataAccessLayer(BaseService):
    """データアクセス層統合クラス"""

    def __init__(self):
        super().__init__()
        self.query_cache = {}
        self.cache_ttl = 300  # 5分間のキャッシュ

    def get_service_name(self) -> str:
        return "DataAccessLayer"

    def safe_query(
        self,
        model_class,
        filters: Optional[Dict] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List:
        """
        安全なクエリ実行

        Args:
            model_class: モデルクラス
            filters: フィルター条件
            order_by: ソート条件
            limit: 件数制限

        Returns:
            List: クエリ結果
        """
        try:
            query = self._db.session.query(model_class)

            # フィルター適用
            if filters:
                for key, value in filters.items():
                    if hasattr(model_class, key):
                        attr = getattr(model_class, key)
                        if isinstance(value, list):
                            query = query.filter(attr.in_(value))
                        else:
                            query = query.filter(attr == value)

            # ソート適用
            if order_by:
                if hasattr(model_class, order_by):
                    query = query.order_by(getattr(model_class, order_by))

            # 件数制限
            if limit:
                query = query.limit(limit)

            result = query.all()
            self.log_info(
                f"Query executed: {model_class.__name__}, results: {len(result)}"
            )

            return result

        except Exception as e:
            self.log_error(f"Query error: {str(e)}")
            raise

    def safe_get_by_id(self, model_class, record_id: int):
        """
        IDによる安全な単一レコード取得

        Args:
            model_class: モデルクラス
            record_id: レコードID

        Returns:
            モデルインスタンス or None
        """
        try:
            result = self._db.session.query(model_class).get(record_id)
            self.log_info(
                f"Get by ID: {model_class.__name__}({record_id}) - {'Found' if result else 'Not found'}"
            )
            return result

        except Exception as e:
            self.log_error(f"Get by ID error: {str(e)}")
            raise

    def safe_create(self, model_instance) -> bool:
        """
        安全なレコード作成

        Args:
            model_instance: 作成するモデルインスタンス

        Returns:
            bool: 成功フラグ
        """
        try:
            self._db.session.add(model_instance)
            self._db.session.commit()

            self.log_info(f"Record created: {model_instance.__class__.__name__}")
            return True

        except Exception as e:
            self._db.session.rollback()
            self.log_error(f"Create error: {str(e)}")
            return False

    def safe_update(self, model_instance, updates: Dict[str, Any]) -> bool:
        """
        安全なレコード更新

        Args:
            model_instance: 更新するモデルインスタンス
            updates: 更新する値の辞書

        Returns:
            bool: 成功フラグ
        """
        try:
            for key, value in updates.items():
                if hasattr(model_instance, key):
                    setattr(model_instance, key, value)

            # 更新日時の自動設定
            if hasattr(model_instance, "updated_at"):
                model_instance.updated_at = datetime.utcnow()

            self._db.session.commit()

            self.log_info(f"Record updated: {model_instance.__class__.__name__}")
            return True

        except Exception as e:
            self._db.session.rollback()
            self.log_error(f"Update error: {str(e)}")
            return False

    def safe_delete(self, model_instance) -> bool:
        """
        安全なレコード削除

        Args:
            model_instance: 削除するモデルインスタンス

        Returns:
            bool: 成功フラグ
        """
        try:
            self._db.session.delete(model_instance)
            self._db.session.commit()

            self.log_info(f"Record deleted: {model_instance.__class__.__name__}")
            return True

        except Exception as e:
            self._db.session.rollback()
            self.log_error(f"Delete error: {str(e)}")
            return False

    def execute_raw_query(
        self, query: str, params: Optional[Dict] = None
    ) -> List[Dict]:
        """
        生SQLの安全な実行

        Args:
            query: SQL文
            params: パラメータ

        Returns:
            List[Dict]: 実行結果
        """
        try:
            result = self._db.session.execute(text(query), params or {})
            rows = result.fetchall()

            # 辞書形式に変換
            if rows:
                columns = result.keys()
                data = [dict(zip(columns, row)) for row in rows]
            else:
                data = []

            self.log_info(f"Raw query executed, results: {len(data)}")
            return data

        except Exception as e:
            self.log_error(f"Raw query error: {str(e)}")
            raise

    def get_cached_result(self, cache_key: str):
        """
        キャッシュから結果を取得

        Args:
            cache_key: キャッシュキー

        Returns:
            キャッシュされた結果 or None
        """
        if cache_key in self.query_cache:
            cached_item = self.query_cache[cache_key]

            # TTL チェック
            if datetime.now() - cached_item["timestamp"] < timedelta(
                seconds=self.cache_ttl
            ):
                self.log_info(f"Cache hit: {cache_key}")
                return cached_item["data"]
            else:
                # 期限切れキャッシュを削除
                del self.query_cache[cache_key]

        return None

    def set_cache_result(self, cache_key: str, data: Any):
        """
        結果をキャッシュに保存

        Args:
            cache_key: キャッシュキー
            data: 保存するデータ
        """
        self.query_cache[cache_key] = {"data": data, "timestamp": datetime.now()}

        # キャッシュサイズ制限（1000件）
        if len(self.query_cache) > 1000:
            # 最も古いアイテムを削除
            oldest_key = min(
                self.query_cache.keys(), key=lambda k: self.query_cache[k]["timestamp"]
            )
            del self.query_cache[oldest_key]

        self.log_info(f"Cache set: {cache_key}")

    def clear_cache(self, pattern: Optional[str] = None):
        """
        キャッシュをクリア

        Args:
            pattern: クリアするキーのパターン（省略時は全削除）
        """
        if pattern:
            keys_to_delete = [key for key in self.query_cache.keys() if pattern in key]
            for key in keys_to_delete:
                del self.query_cache[key]
            self.log_info(
                f"Cache cleared: pattern '{pattern}', {len(keys_to_delete)} items"
            )
        else:
            self.query_cache.clear()
            self.log_info("All cache cleared")

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        パフォーマンス統計の取得

        Returns:
            Dict: 統計情報
        """
        return {
            "cache_size": len(self.query_cache),
            "cache_hit_rate": 0,  # TODO: 実際の計算実装
            "active_connections": 0,  # TODO: DB接続数取得
            "query_count_today": 0,  # TODO: 今日のクエリ数取得
        }
