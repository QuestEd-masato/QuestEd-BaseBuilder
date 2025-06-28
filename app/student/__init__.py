# app/student/__init__.py
"""Student Blueprint - モジュール化された学生機能の統合"""

from flask import Blueprint

# 既存の実装したモジュールをインポート
from .modules.dashboard import dashboard_bp
from .modules.activities import activities_bp
from .modules.surveys import surveys_bp
from .modules.goals_todos import goals_todos_bp

# 共通機能をインポート
from .utils import student_required

# メインのBlueprintを作成
student_bp = Blueprint('student', __name__)

def register_student_blueprints(app):
    """Student関連のすべてのBlueprintを登録"""
    
    # 実装済みモジュールのBlueprintを登録
    app.register_blueprint(dashboard_bp, url_prefix='/student')
    app.register_blueprint(activities_bp, url_prefix='/student')
    app.register_blueprint(surveys_bp, url_prefix='/student')
    app.register_blueprint(goals_todos_bp, url_prefix='/student')

# 後方互換性のため、主要な関数をこのモジュールレベルで公開
from .modules.dashboard import dashboard
from .modules.activities import activities, new_activity, edit_activity, delete_activity, view_activity, export_activities
from .modules.surveys import surveys, interest_survey, personality_survey
from .modules.goals_todos import (
    todos, new_todo, edit_todo, delete_todo, toggle_todo,
    goals, new_goal, edit_goal, delete_goal, update_goal_progress
)

# TODO: 残りのモジュールを実装する必要があります
# - themes.py (テーマ選択)
# - learning_progress.py (学習進捗)
# - unit_completion.py (単元完了申請)

# 一時的に元のファイルから必要な関数をインポート（実装されるまで）
# 注意: 元のファイルが __init___backup_original.py.disabled にリネームされているため、
# これらの関数は一時的に利用できません。順次新しいモジュールに実装する必要があります。

# このファイルをインポートした際の初期化
def init_student_module(app):
    """Student モジュールの初期化"""
    register_student_blueprints(app)

# モジュール情報
__version__ = "1.0.0"
__description__ = "QuestEd Student Management Module - Partially refactored"

# 実装済み機能モジュールリスト
IMPLEMENTED_MODULES = [
    'dashboard',     # ダッシュボード機能
    'activities',    # 活動記録
    'surveys',       # アンケート機能
    'goals_todos'    # 目標・TODO管理
]

# 未実装機能モジュールリスト（今後実装予定）
PENDING_MODULES = [
    'themes',           # テーマ選択
    'learning_progress', # 学習進捗
    'unit_completion'   # 単元完了申請
]

# リファクタリング情報
REFACTORING_INFO = {
    'original_file_size': '2,950 lines',
    'implemented_modules': len(IMPLEMENTED_MODULES),
    'pending_modules': len(PENDING_MODULES),
    'refactoring_progress': f'{len(IMPLEMENTED_MODULES)}/{len(IMPLEMENTED_MODULES) + len(PENDING_MODULES)} modules',
    'refactoring_date': '2025-06-26',
    'status': 'Partial implementation - Core functionality available'
}