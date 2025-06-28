"""
QuestEd Test Suite
==================
Phase 6.1: テストフレームワーク構築

統合テストフレームワーク:
- 単体テスト
- 統合テスト
- E2Eテスト
- パフォーマンステスト
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# テスト設定
TEST_DATABASE_URI = os.environ.get('TEST_DATABASE_URI', 'sqlite:///:memory:')
TEST_SECRET_KEY = 'test-secret-key-for-testing-only'

# テストカテゴリ
TEST_CATEGORIES = [
    'unit',        # 単体テスト
    'integration', # 統合テスト
    'api',         # APIテスト
    'security',    # セキュリティテスト
    'performance'  # パフォーマンステスト
]

__all__ = [
    'TEST_DATABASE_URI',
    'TEST_SECRET_KEY',
    'TEST_CATEGORIES'
]