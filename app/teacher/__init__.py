# app/teacher/__init__.py
"""Teacher Blueprint - モジュール化されたティーチャー機能の統合"""

from flask import Blueprint

# 共通機能をインポート
from .common import teacher_required
from .modules.analytics import analytics_bp
from .modules.approval_workflow import approval_workflow_bp
from .modules.class_management import class_management_bp
from .modules.curriculum_management import curriculum_management_bp

# 各機能モジュールをインポート
from .modules.dashboard import dashboard_bp
from .modules.student_evaluation import student_evaluation_bp
from .modules.synchronization import synchronization_bp
from .modules.task_management import task_management_bp

# メインのBlueprintを作成
teacher_bp = Blueprint("teacher", __name__)


def register_teacher_blueprints(app):
    """Teacher関連のすべてのBlueprintを登録"""

    # 各モジュールのBlueprintを登録
    app.register_blueprint(dashboard_bp, url_prefix="/teacher")
    app.register_blueprint(class_management_bp, url_prefix="/teacher")
    app.register_blueprint(curriculum_management_bp, url_prefix="/teacher")
    app.register_blueprint(student_evaluation_bp, url_prefix="/teacher")
    app.register_blueprint(analytics_bp, url_prefix="/teacher")
    app.register_blueprint(approval_workflow_bp, url_prefix="/teacher")
    app.register_blueprint(synchronization_bp, url_prefix="/teacher")
    app.register_blueprint(task_management_bp, url_prefix="/teacher")


# 後方互換性のため、主要な関数をこのモジュールレベルで公開
# これにより、既存のテンプレートやインポートが引き続き動作する

# 分析・統計関数
from .modules.analytics import api_class_ranking, class_analytics, ranking_analysis

# 承認ワークフロー関数
from .modules.approval_workflow import (
    approve_completion,
    pending_unit_approvals,
    reject_completion,
)

# クラス管理関数
from .modules.class_management import (
    add_students,
    class_details,
    classes,
    create_class,
    create_milestone,
    delete_class,
    delete_milestone,
    edit_class,
    edit_milestone,
    import_students,
    remove_student,
    view_class,
    view_milestone,
)

# カリキュラム管理関数
from .modules.curriculum_management import (
    create_curriculum_form,
    delete_curriculum,
    edit_curriculum,
    export_curriculum,
    generate_curriculum,
    import_curriculum,
    view_curriculum,
    view_curriculums,
)

# ダッシュボード関数
from .modules.dashboard import dashboard

# 学生評価関数
from .modules.student_evaluation import (
    generate_evaluations,
    generate_student_report,
    teacher_themes,
)

# 同期管理関数
from .modules.synchronization import (
    auto_sync_settings,
    integrated_management,
    manual_sync_curriculum,
    sync_all_curriculums,
)

# ルート重複を回避するため、リダイレクトルートは削除
# 既存のテンプレートは新しいURL名前空間を使用：
# - teacher_dashboard.dashboard
# - teacher_class_management.classes


# このファイルをインポートした際の初期化
def init_teacher_module(app):
    """Teacher モジュールの初期化"""
    register_teacher_blueprints(app)


# モジュール情報
__version__ = "2.0.0"
__description__ = (
    "QuestEd Teacher Management Module - Refactored for better maintainability"
)

# 利用可能な機能モジュールリスト
AVAILABLE_MODULES = [
    "dashboard",  # ダッシュボード機能
    "class_management",  # クラス管理
    "curriculum_management",  # カリキュラム管理
    "student_evaluation",  # 学生評価
    "analytics",  # 分析・統計
    "approval_workflow",  # 承認ワークフロー
    "synchronization",  # 同期管理
    "task_management",  # 課題管理・承認システム
]

# リファクタリング情報
REFACTORING_INFO = {
    "original_file_size": "2,971 lines",
    "refactored_modules": len(AVAILABLE_MODULES),
    "refactoring_date": "2025-06-26",
    "benefits": ["保守性の向上", "コードの可読性向上", "機能分離の明確化", "テストの容易性向上", "開発効率の向上"],
}
