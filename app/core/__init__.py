"""
Core Module
===========
Phase 5.1: 構造最適化 - コア機能の統合

システム全体で共有される核となる機能をここに集約:
- 基盤サービス
- 共通ユーティリティ
- データアクセス層
- セキュリティ機能
"""

from .base_service import BaseService
from .data_access import DataAccessLayer
from .security_manager import SecurityManager

__all__ = ["BaseService", "SecurityManager", "DataAccessLayer"]
