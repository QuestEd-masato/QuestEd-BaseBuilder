"""
3状態管理システム（承認システム）

このモジュールは以下の機能を提供します：
- 学習完了申請の管理
- 教師による承認・却下処理
- 再申請機能
- 3状態管理（未完了・却下(再申請)・完了）
"""

from .services.approval_service import ApprovalService
from .services.workflow_service import WorkflowService
from .routes.approval_routes import approval_bp

__all__ = [
    'ApprovalService',
    'WorkflowService',
    'approval_bp'
]

__version__ = '1.0.0'