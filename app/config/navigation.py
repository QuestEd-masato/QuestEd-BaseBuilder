"""
統合ナビゲーション設定

全モジュールの統合ナビゲーションを管理
"""

from typing import Dict, List, Optional
from flask_login import current_user

class NavigationItem:
    """ナビゲーション項目クラス"""
    
    def __init__(self, title: str, url: str, icon: str = None, 
                 permission: str = None, submenu: List = None):
        self.title = title
        self.url = url
        self.icon = icon
        self.permission = permission
        self.submenu = submenu or []
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'title': self.title,
            'url': self.url,
            'icon': self.icon,
            'permission': self.permission,
            'submenu': [item.to_dict() for item in self.submenu]
        }

class NavigationConfig:
    """ナビゲーション設定管理"""
    
    @staticmethod
    def get_student_navigation() -> List[NavigationItem]:
        """学生用ナビゲーション"""
        return [
            NavigationItem(
                title="ダッシュボード",
                url="student_dashboard.dashboard",
                icon="fas fa-tachometer-alt"
            ),
            NavigationItem(
                title="学習システム",
                url="#",
                icon="fas fa-book-open",
                submenu=[
                    NavigationItem(
                        title="レッスン",
                        url="student_learning.learning_portal",
                        icon="fas fa-tasks"
                    ),
                    NavigationItem(
                        title="進捗確認",
                        url="student_ranking.ranking",
                        icon="fas fa-chart-line"
                    ),
                    NavigationItem(
                        title="ランキング",
                        url="ranking_system.student_ranking_dashboard",
                        icon="fas fa-trophy"
                    )
                ]
            ),
            NavigationItem(
                title="探究活動",
                url="#",
                icon="fas fa-search",
                submenu=[
                    NavigationItem(
                        title="探究テーマ",
                        url="student_themes.themes",
                        icon="fas fa-lightbulb"
                    ),
                    NavigationItem(
                        title="活動記録",
                        url="student_activities.activities",
                        icon="fas fa-journal-whills"
                    )
                ]
            ),
            NavigationItem(
                title="基礎学力",
                url="#",
                icon="fas fa-graduation-cap",
                submenu=[
                    NavigationItem(
                        title="テキスト一覧",
                        url="texts.my_texts",
                        icon="fas fa-book"
                    ),
                    NavigationItem(
                        title="問題に挑戦",
                        url="problems.problems",
                        icon="fas fa-puzzle-piece"
                    ),
                    NavigationItem(
                        title="熟練度確認",
                        url="progress.view_proficiency",
                        icon="fas fa-chart-bar"
                    ),
                    NavigationItem(
                        title="理解度分析",
                        url="analytics.analytics",
                        icon="fas fa-analytics"
                    )
                ]
            ),
            NavigationItem(
                title="ツール",
                url="#",
                icon="fas fa-tools",
                submenu=[
                    NavigationItem(
                        title="AIチャット",
                        url="student_chat.select_class",
                        icon="fas fa-comments"
                    ),
                    NavigationItem(
                        title="アンケート",
                        url="student_surveys.surveys",
                        icon="fas fa-poll"
                    ),
                    NavigationItem(
                        title="To Doリスト",
                        url="student_goals_todos_secure.todos",
                        icon="fas fa-check-square"
                    ),
                    NavigationItem(
                        title="目標管理",
                        url="student_goals_todos_secure.goals",
                        icon="fas fa-bullseye"
                    )
                ]
            ),
            NavigationItem(
                title="クラス",
                url="teacher_class_management.classes",
                icon="fas fa-users"
            )
        ]
    
    @staticmethod
    def get_teacher_navigation() -> List[NavigationItem]:
        """教師用ナビゲーション"""
        return [
            NavigationItem(
                title="ダッシュボード",
                url="teacher_dashboard.dashboard",
                icon="fas fa-tachometer-alt"
            ),
            NavigationItem(
                title="教育システム",
                url="#",
                icon="fas fa-chalkboard-teacher",
                submenu=[
                    NavigationItem(
                        title="承認管理",
                        url="approval_system.teacher_pending_approvals",
                        icon="fas fa-clipboard-check"
                    ),
                    NavigationItem(
                        title="クラスランキング",
                        url="ranking_system.teacher_class_ranking",
                        icon="fas fa-trophy"
                    )
                ]
            ),
            NavigationItem(
                title="探究活動",
                url="#",
                icon="fas fa-search",
                submenu=[
                    NavigationItem(
                        title="テーマ管理",
                        url="teacher_student_evaluation.teacher_themes",
                        icon="fas fa-lightbulb"
                    ),
                    NavigationItem(
                        title="クラス管理",
                        url="teacher_class_management.classes",
                        icon="fas fa-users"
                    )
                ]
            ),
            NavigationItem(
                title="基礎学力",
                url="#",
                icon="fas fa-graduation-cap",
                submenu=[
                    NavigationItem(
                        title="基礎学力ホーム",
                        url="texts.dashboard",
                        icon="fas fa-home"
                    ),
                    NavigationItem(
                        title="問題管理",
                        url="problems.problems",
                        icon="fas fa-puzzle-piece"
                    ),
                    NavigationItem(
                        title="テキスト一覧",
                        url="texts.text_sets",
                        icon="fas fa-book"
                    ),
                    NavigationItem(
                        title="理解度分析",
                        url="analytics.analytics",
                        icon="fas fa-analytics"
                    )
                ]
            ),
            NavigationItem(
                title="ツール",
                url="#",
                icon="fas fa-tools",
                submenu=[
                    NavigationItem(
                        title="AIチャット",
                        url="teacher_dashboard.chat_page",
                        icon="fas fa-comments"
                    )
                ]
            )
        ]
    
    @staticmethod
    def get_admin_navigation() -> List[NavigationItem]:
        """管理者用ナビゲーション"""
        return [
            NavigationItem(
                title="ダッシュボード",
                url="admin_panel.dashboard",
                icon="fas fa-tachometer-alt"
            ),
            NavigationItem(
                title="学校管理",
                url="#",
                icon="fas fa-school",
                submenu=[
                    NavigationItem(
                        title="学校一覧",
                        url="admin_panel.admin_schools",
                        icon="fas fa-list"
                    ),
                    NavigationItem(
                        title="学校登録",
                        url="admin_panel.create_school",
                        icon="fas fa-plus"
                    )
                ]
            ),
            NavigationItem(
                title="ユーザー管理",
                url="#",
                icon="fas fa-users",
                submenu=[
                    NavigationItem(
                        title="ユーザー一覧",
                        url="admin_panel.users",
                        icon="fas fa-list"
                    ),
                    NavigationItem(
                        title="一括インポート",
                        url="admin_panel.import_users",
                        icon="fas fa-upload"
                    )
                ]
            ),
            NavigationItem(
                title="システム設定",
                url="#",
                icon="fas fa-cogs",
                submenu=[
                    NavigationItem(
                        title="基本設定",
                        url="#",
                        icon="fas fa-sliders-h"
                    ),
                    NavigationItem(
                        title="バックアップ",
                        url="#",
                        icon="fas fa-save"
                    ),
                    NavigationItem(
                        title="メンテナンス",
                        url="#",
                        icon="fas fa-wrench"
                    )
                ]
            )
        ]

class NavigationManager:
    """ナビゲーション管理クラス"""
    
    @staticmethod
    def get_navigation_for_user(user=None) -> List[Dict]:
        """ユーザー役割に応じたナビゲーション取得"""
        if not user:
            return []
        
        if user.role == 'student':
            nav_items = NavigationConfig.get_student_navigation()
        elif user.role == 'teacher':
            nav_items = NavigationConfig.get_teacher_navigation()
        elif user.role == 'admin':
            nav_items = NavigationConfig.get_admin_navigation()
        else:
            return []
        
        return [item.to_dict() for item in nav_items]
    
    @staticmethod
    def get_breadcrumb_for_path(path: str, user=None) -> List[Dict]:
        """パスに基づいてパンくずリストを生成"""
        breadcrumbs = [{'title': 'ホーム', 'url': '/'}]
        
        # パスベースのパンくずリスト生成ロジック
        if '/lesson-system/' in path:
            breadcrumbs.append({'title': '学習システム', 'url': '/lesson-system/'})
        elif '/ranking-system/' in path:
            breadcrumbs.append({'title': 'ランキング', 'url': '/ranking-system/'})
        elif '/approval-system/' in path:
            breadcrumbs.append({'title': '承認管理', 'url': '/approval-system/'})
        elif '/admin/' in path:
            breadcrumbs.append({'title': '管理画面', 'url': '/admin/'})
        
        return breadcrumbs
    
    @staticmethod
    def get_current_module(path: str) -> Optional[str]:
        """現在のモジュールを特定"""
        if '/ranking-system/' in path:
            return 'ranking_system'
        elif '/approval-system/' in path:
            return 'approval_system'
        elif '/admin/' in path:
            return 'admin'
        elif '/student/' in path:
            return 'student'
        elif '/teacher/' in path:
            return 'teacher'
        else:
            return None

# テンプレートでの使用例
def register_navigation_functions(app):
    """Flaskアプリケーションにナビゲーション関数を登録"""
    
    @app.context_processor
    def inject_navigation():
        """テンプレートでのナビゲーション機能提供"""
        return {
            'get_navigation': NavigationManager.get_navigation_for_user,
            'get_breadcrumb': NavigationManager.get_breadcrumb_for_path,
            'get_current_module': NavigationManager.get_current_module
        }