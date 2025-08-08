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
        """学生用ナビゲーション（完全版：17項目をドロップダウンで整理）"""
        return [
            NavigationItem(
                title="ダッシュボード",
                url="student_dashboard.dashboard",
                icon="fas fa-tachometer-alt"
            ),
            NavigationItem(
                title="学習活動",
                url="#",
                icon="fas fa-graduation-cap",
                submenu=[
                    NavigationItem("学習ポータル", "student_learning.learning_portal", "fas fa-book-open"),
                    NavigationItem("単元学習", "student_unit_learning.unit_dashboard", "fas fa-tasks"),
                    NavigationItem("進捗確認", "student_learning.progress", "fas fa-chart-line")
                ]
            ),
            NavigationItem(
                title="探究・活動",
                url="#",
                icon="fas fa-lightbulb",
                submenu=[
                    NavigationItem("探究テーマ", "student_themes.themes", "fas fa-search"),
                    NavigationItem("活動記録", "student_activities.activities", "fas fa-clipboard"),
                    NavigationItem("アンケート", "student_surveys.surveys", "fas fa-poll"),
                    NavigationItem("目標・TODO", "student_goals_todos.goals", "fas fa-flag-checkered")
                ]
            ),
            NavigationItem(
                title="成績・進捗",
                url="#",
                icon="fas fa-chart-line",
                submenu=[
                    NavigationItem("学習進捗", "student_learning.progress", "fas fa-tasks"),
                    NavigationItem("成績記録", "student_learning.grades", "fas fa-graduation-cap"),
                    NavigationItem("マイルストーン", "student_learning.milestones", "fas fa-flag"),
                    NavigationItem("達成状況", "student_learning.achievements", "fas fa-medal")
                ]
            ),
            NavigationItem(
                title="コミュニケーション",
                url="#",
                icon="fas fa-comments",
                submenu=[
                    NavigationItem("AIチャット", "student_chat.chat", "fas fa-robot"),
                    NavigationItem("クラス情報", "student_class_management.class_info", "fas fa-users"),
                    NavigationItem("ランキング", "ranking_system.student_ranking_dashboard", "fas fa-trophy"),
                    NavigationItem("通知", "student_notifications.notifications", "fas fa-bell")
                ]
            ),
            NavigationItem(
                title="BaseBuilder",
                url="basebuilder.index", 
                icon="fas fa-building"
            )
        ]
    
    @staticmethod
    def get_teacher_navigation() -> List[NavigationItem]:
        """教師用ナビゲーション（完全版：11項目を3グループに整理）"""
        return [
            NavigationItem(
                title="ダッシュボード",
                url="teacher_dashboard.dashboard",
                icon="fas fa-tachometer-alt"
            ),
            NavigationItem(
                title="クラス・カリキュラム管理",
                url="#",
                icon="fas fa-users",
                submenu=[
                    NavigationItem("クラス一覧", "teacher_class_management.classes", "fas fa-list"),
                    NavigationItem("カリキュラム管理", "teacher_curriculum_management.view_curriculums", "fas fa-book"),
                    NavigationItem("レッスン管理", "lesson_system.lesson_management", "fas fa-chalkboard-teacher"),
                    NavigationItem("タスク管理", "teacher_task_management.task_dashboard", "fas fa-tasks")
                ]
            ),
            NavigationItem(
                title="評価・承認システム",
                url="#",
                icon="fas fa-clipboard-check", 
                submenu=[
                    NavigationItem("承認待ち一覧", "approval_system.teacher_pending_approvals", "fas fa-clock"),
                    NavigationItem("学生評価", "teacher_student_evaluation.teacher_themes", "fas fa-star"),
                    NavigationItem("同期管理", "teacher_synchronization.sync_dashboard", "fas fa-sync")
                ]
            ),
            NavigationItem(
                title="分析・レポート",
                url="#",
                icon="fas fa-chart-bar",
                submenu=[
                    NavigationItem("クラス分析", "teacher_analytics.class_analytics", "fas fa-chart-line"),
                    NavigationItem("ランキング管理", "ranking_system.teacher_class_ranking", "fas fa-trophy")
                ]
            ),
            NavigationItem(
                title="BaseBuilder",
                url="basebuilder.index",
                icon="fas fa-building"
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