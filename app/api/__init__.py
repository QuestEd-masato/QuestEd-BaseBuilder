"""
API Module - Modular Architecture
================================
Phase 4.3: API分割実装

元のモノリシックAPI (1,710行) を6つの機能別モジュールに分割:

- unit_management.py   - 単元学習管理 (12ルート)
- chat_ai.py          - チャット・AI機能 (4ルート) 
- rankings.py         - ランキング・統計 (6ルート)
- review_system.py    - 復習システム (6ルート)
- student_tools.py    - 学生ツール (3ルート)
- admin_teacher.py    - 管理者・教師 (2ルート)

レガシーファイルは __init___legacy.py として保存。
"""

from flask import Blueprint

# 各機能モジュールのBlueprint をインポート
from .unit_management import unit_management_bp
from .chat_ai import chat_ai_bp
from .rankings import rankings_bp
from .review_system import review_system_bp
from .student_tools import student_tools_bp
from .admin_teacher import admin_teacher_bp

# メインAPIブループリント
api_bp = Blueprint('api', __name__, url_prefix='/api')


def register_api_routes(app):
    """
    全APIルートをアプリケーションに登録
    
    Args:
        app: Flaskアプリケーションインスタンス
    """
    
    # 各機能モジュールのBlueprintを登録
    api_bp.register_blueprint(unit_management_bp)
    api_bp.register_blueprint(chat_ai_bp)
    api_bp.register_blueprint(rankings_bp)
    api_bp.register_blueprint(review_system_bp)
    api_bp.register_blueprint(student_tools_bp)
    api_bp.register_blueprint(admin_teacher_bp)
    
    # メインAPIブループリントをアプリに登録
    app.register_blueprint(api_bp)


# 後方互換性のために元のblueprintも提供
def get_legacy_blueprint():
    """レガシー互換性のための関数"""
    return api_bp


# モジュール情報
__version__ = "2.0.0"
__description__ = "QuestEd API - Modular Architecture"

# 分割完了情報
REFACTORING_INFO = {
    'original_file_size': '1,710 lines',
    'new_modules': [
        'unit_management.py (12 routes)',
        'chat_ai.py (4 routes)',
        'rankings.py (6 routes)', 
        'review_system.py (6 routes)',
        'student_tools.py (3 routes)',
        'admin_teacher.py (2 routes)'
    ],
    'total_routes_migrated': 33,
    'completion_date': '2025-06-27',
    'legacy_backup': '__init___legacy.py'
}

# 利用可能なAPIモジュール
AVAILABLE_MODULES = [
    'unit_management',   # 単元学習管理
    'chat_ai',          # チャット・AI機能
    'rankings',         # ランキング・統計
    'review_system',    # 復習システム
    'student_tools',    # 学生ツール
    'admin_teacher'     # 管理者・教師機能
]

__all__ = [
    'api_bp',
    'register_api_routes',
    'get_legacy_blueprint',
    'REFACTORING_INFO',
    'AVAILABLE_MODULES'
]