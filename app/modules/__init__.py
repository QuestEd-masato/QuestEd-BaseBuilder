"""
QuestEd モジュールシステム

各機能モジュールの統合管理
"""

from .lesson_system import lesson_bp
from .approval_system import approval_bp  
from .ranking_system import ranking_bp

# モジュール化されたBlueprint一覧
MODULAR_BLUEPRINTS = [
    lesson_bp,
    approval_bp,
    ranking_bp
]

__all__ = [
    'MODULAR_BLUEPRINTS',
    'lesson_bp',
    'approval_bp', 
    'ranking_bp'
]