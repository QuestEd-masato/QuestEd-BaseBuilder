"""
Blueprint Registry
==================
Phase 5.3: Blueprint アーキテクチャ最適化

統合されたBlueprint管理システム:
- 動的Blueprint登録
- 依存関係管理
- 設定ベースの有効化/無効化
- パフォーマンス監視
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from flask import Blueprint, Flask


@dataclass
class BlueprintConfig:
    """Blueprint設定クラス"""

    name: str
    url_prefix: str
    enabled: bool = True
    dependencies: List[str] = None
    middleware: List[str] = None
    auth_required: bool = True
    rate_limit: Optional[str] = None


class BlueprintRegistry:
    """Blueprint統合管理クラス"""

    def __init__(self):
        self.blueprints: Dict[str, Blueprint] = {}
        self.configs: Dict[str, BlueprintConfig] = {}
        self.middleware_stack: Dict[str, List[Callable]] = {}
        self.logger = logging.getLogger(__name__)
        self.registration_order: List[str] = []

    def register_blueprint(
        self, app: Flask, blueprint: Blueprint, config: BlueprintConfig
    ) -> bool:
        """
        Blueprintの登録

        Args:
            app: Flaskアプリケーション
            blueprint: 登録するBlueprint
            config: Blueprint設定

        Returns:
            bool: 登録成功フラグ
        """
        try:
            # 有効性チェック
            if not config.enabled:
                self.logger.info(
                    f"Blueprint {config.name} is disabled, skipping registration"
                )
                return False

            # 依存関係チェック
            if not self._check_dependencies(config):
                self.logger.error(f"Dependencies not met for blueprint {config.name}")
                return False

            # 重複チェック
            if config.name in self.blueprints:
                self.logger.warning(f"Blueprint {config.name} already registered")
                return False

            # ミドルウェア適用
            self._apply_middleware(blueprint, config)

            # 認証設定
            if config.auth_required:
                self._apply_auth_middleware(blueprint)

            # レート制限設定
            if config.rate_limit:
                self._apply_rate_limiting(blueprint, config.rate_limit)

            # Blueprintを登録
            app.register_blueprint(blueprint, url_prefix=config.url_prefix)

            # 内部管理に追加
            self.blueprints[config.name] = blueprint
            self.configs[config.name] = config
            self.registration_order.append(config.name)

            self.logger.info(
                f"Blueprint {config.name} registered successfully at {config.url_prefix}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to register blueprint {config.name}: {str(e)}")
            return False

    def register_multiple_blueprints(
        self, app: Flask, blueprint_configs: List[tuple]
    ) -> Dict[str, bool]:
        """
        複数Blueprintの一括登録

        Args:
            app: Flaskアプリケーション
            blueprint_configs: (blueprint, config)のタプルリスト

        Returns:
            Dict[str, bool]: 登録結果
        """
        results = {}

        # 依存関係順でソート
        sorted_configs = self._sort_by_dependencies(blueprint_configs)

        for blueprint, config in sorted_configs:
            results[config.name] = self.register_blueprint(app, blueprint, config)

        return results

    def get_blueprint_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Blueprint状態の取得

        Returns:
            Dict: Blueprint状態情報
        """
        status = {}

        for name, config in self.configs.items():
            blueprint = self.blueprints.get(name)

            status[name] = {
                "enabled": config.enabled,
                "url_prefix": config.url_prefix,
                "registered": blueprint is not None,
                "route_count": len(blueprint.deferred_functions) if blueprint else 0,
                "dependencies": config.dependencies or [],
                "auth_required": config.auth_required,
                "rate_limit": config.rate_limit,
            }

        return status

    def get_route_map(self) -> Dict[str, List[str]]:
        """
        Blueprint別ルートマップの取得

        Returns:
            Dict: Blueprint別ルート一覧
        """
        route_map = {}

        for name, blueprint in self.blueprints.items():
            config = self.configs[name]
            routes = []

            # ルート情報を抽出
            for deferred in blueprint.deferred_functions:
                if hasattr(deferred, "func") and hasattr(deferred.func, "__name__"):
                    # ルール抽出の簡易実装
                    routes.append(f"{config.url_prefix}/<route>")

            route_map[name] = routes

        return route_map

    def disable_blueprint(self, name: str) -> bool:
        """
        Blueprintの無効化

        Args:
            name: Blueprint名

        Returns:
            bool: 無効化成功フラグ
        """
        if name in self.configs:
            self.configs[name].enabled = False
            self.logger.info(f"Blueprint {name} disabled")
            return True
        return False

    def enable_blueprint(self, name: str) -> bool:
        """
        Blueprintの有効化

        Args:
            name: Blueprint名

        Returns:
            bool: 有効化成功フラグ
        """
        if name in self.configs:
            self.configs[name].enabled = True
            self.logger.info(f"Blueprint {name} enabled")
            return True
        return False

    # プライベートメソッド

    def _check_dependencies(self, config: BlueprintConfig) -> bool:
        """依存関係チェック"""
        if not config.dependencies:
            return True

        for dependency in config.dependencies:
            if dependency not in self.blueprints:
                return False

        return True

    def _sort_by_dependencies(self, blueprint_configs: List[tuple]) -> List[tuple]:
        """依存関係に基づく並び替え"""
        # 簡易実装（実際にはトポロジカルソートを使用）
        return sorted(blueprint_configs, key=lambda x: len(x[1].dependencies or []))

    def _apply_middleware(self, blueprint: Blueprint, config: BlueprintConfig):
        """ミドルウェアの適用"""
        if not config.middleware:
            return

        for middleware_name in config.middleware:
            if middleware_name in self.middleware_stack:
                for middleware_func in self.middleware_stack[middleware_name]:
                    blueprint.before_request(middleware_func)

    def _apply_auth_middleware(self, blueprint: Blueprint):
        """認証ミドルウェアの適用"""
        from flask_login import login_required

        # すべてのルートに@login_requiredを適用する処理
        # 実際の実装では、デコレータを動的に適用
        pass

    def _apply_rate_limiting(self, blueprint: Blueprint, rate_limit: str):
        """レート制限の適用"""
        from app.utils.rate_limiting import api_limit

        # レート制限デコレータの動的適用
        # 実際の実装では、設定文字列を解析してデコレータを適用
        pass


class OptimizedBlueprintManager:
    """最適化されたBlueprint管理クラス"""

    def __init__(self):
        self.registry = BlueprintRegistry()
        self.performance_monitor = BlueprintPerformanceMonitor()

    def setup_application_blueprints(self, app: Flask) -> bool:
        """
        アプリケーション全体のBlueprint設定

        Args:
            app: Flaskアプリケーション

        Returns:
            bool: 設定成功フラグ
        """
        try:
            # Core Blueprint設定
            core_configs = self._get_core_blueprint_configs()

            # Feature Blueprint設定
            feature_configs = self._get_feature_blueprint_configs()

            # API Blueprint設定
            api_configs = self._get_api_blueprint_configs()

            # 全Blueprint登録
            all_configs = core_configs + feature_configs + api_configs
            results = self.registry.register_multiple_blueprints(app, all_configs)

            # 結果確認
            failed_registrations = [
                name for name, success in results.items() if not success
            ]

            if failed_registrations:
                app.logger.warning(
                    f"Failed to register blueprints: {failed_registrations}"
                )
                return False

            # パフォーマンス監視開始
            self.performance_monitor.start_monitoring(app)

            app.logger.info(f"Successfully registered {len(results)} blueprints")
            return True

        except Exception as e:
            app.logger.error(f"Blueprint setup failed: {str(e)}")
            return False

    def get_application_status(self) -> Dict[str, Any]:
        """アプリケーション状態の取得"""
        return {
            "blueprints": self.registry.get_blueprint_status(),
            "routes": self.registry.get_route_map(),
            "performance": self.performance_monitor.get_metrics(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _get_core_blueprint_configs(self) -> List[tuple]:
        """Core Blueprint設定を取得"""
        from app.admin import admin_bp
        from app.auth import auth_bp

        configs = [
            (
                auth_bp,
                BlueprintConfig(
                    name="auth",
                    url_prefix="/auth",
                    enabled=True,
                    auth_required=False,  # 認証Blueprint自体は認証不要
                    rate_limit="100/hour",
                ),
            ),
            (
                admin_bp,
                BlueprintConfig(
                    name="admin",
                    url_prefix="/admin",
                    enabled=True,
                    dependencies=["auth"],
                    rate_limit="1000/hour",
                ),
            ),
        ]

        return configs

    def _get_feature_blueprint_configs(self) -> List[tuple]:
        """Feature Blueprint設定を取得"""
        from app.student import student_bp
        from app.teacher import teacher_bp

        configs = [
            (
                teacher_bp,
                BlueprintConfig(
                    name="teacher",
                    url_prefix="/teacher",
                    enabled=True,
                    dependencies=["auth"],
                    rate_limit="2000/hour",
                ),
            ),
            (
                student_bp,
                BlueprintConfig(
                    name="student",
                    url_prefix="/student",
                    enabled=True,
                    dependencies=["auth"],
                    rate_limit="1500/hour",
                ),
            ),
        ]

        return configs

    def _get_api_blueprint_configs(self) -> List[tuple]:
        """API Blueprint設定を取得"""
        from app.api import api_bp
        from basebuilder.routes import register_basebuilder_routes

        configs = [
            (
                api_bp,
                BlueprintConfig(
                    name="api",
                    url_prefix="/api",
                    enabled=True,
                    dependencies=["auth"],
                    rate_limit="5000/hour",
                ),
            )
        ]

        return configs


class BlueprintPerformanceMonitor:
    """Blueprint パフォーマンス監視クラス"""

    def __init__(self):
        self.metrics = {"request_count": {}, "response_time": {}, "error_count": {}}

    def start_monitoring(self, app: Flask):
        """監視開始"""

        @app.before_request
        def before_request():
            # リクエスト開始時間を記録
            pass

        @app.after_request
        def after_request(response):
            # レスポンス時間を記録
            return response

        @app.errorhandler(Exception)
        def error_handler(error):
            # エラー発生を記録
            pass

    def get_metrics(self) -> Dict[str, Any]:
        """メトリクス取得"""
        return {
            "total_requests": sum(self.metrics["request_count"].values()),
            "average_response_time": 0.0,  # TODO: 実際の計算
            "error_rate": 0.0,  # TODO: 実際の計算
            "top_endpoints": [],  # TODO: 実際のランキング
        }
