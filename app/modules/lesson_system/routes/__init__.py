"""レッスンシステム ルーティング"""

from .lesson_routes import lesson_bp
from .approval_routes import approval_bp

__all__ = ['lesson_bp', 'approval_bp']