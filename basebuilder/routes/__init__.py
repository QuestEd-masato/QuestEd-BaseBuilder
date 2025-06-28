"""
BaseBuilder Routes Module
========================
Phase 4.1: basebuilder/routes.py の分割実装

元の巨大ファイル(3,415行)を機能別に分割し、保守性を向上させる。
元のファイルは basebuilder/routes_legacy.py として保持し、
段階的に新しい構造に移行する。
"""

from flask import Blueprint
from .categories import categories_bp
from .problems import problems_bp
from .sessions import sessions_bp
from .progress import progress_bp
from .analytics import analytics_bp
from .admin import admin_bp


def register_basebuilder_routes(app):
    """BaseBuilder関連の全ルートを登録"""
    
    # 各モジュールのBlueprintを登録
    app.register_blueprint(categories_bp, url_prefix='/basebuilder')
    app.register_blueprint(problems_bp, url_prefix='/basebuilder')
    app.register_blueprint(sessions_bp, url_prefix='/basebuilder')
    app.register_blueprint(progress_bp, url_prefix='/basebuilder')
    app.register_blueprint(analytics_bp, url_prefix='/basebuilder')
    app.register_blueprint(admin_bp, url_prefix='/basebuilder')


# モジュール情報
__version__ = "2.0.0"
__description__ = "BaseBuilder Routes - Refactored for better maintainability"

# 利用可能な機能モジュールリスト
AVAILABLE_MODULES = [
    'categories',    # カテゴリ管理
    'problems',      # 問題管理
    'sessions',      # セッション管理
    'progress',      # 進捗管理
    'analytics',     # 分析・統計
    'admin'          # 管理機能
]

# リファクタリング情報
REFACTORING_INFO = {
    'original_file_size': '3,415 lines',
    'refactored_modules': len(AVAILABLE_MODULES),
    'total_routes': 47,
    'refactoring_date': '2025-06-27',
    'migration_strategy': 'gradual_with_legacy_fallback'
}