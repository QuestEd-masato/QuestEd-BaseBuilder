"""
リファクタリング後の動作確認テスト
====================================
Phase 1, 2でリファクタリングした機能が正しく動作することを確認
"""

import pytest
from flask import url_for
from app.models import db, User, Class, Curriculum, CurriculumUnit, StudentUnitSelection


class TestTeacherRefactoring:
    """教師機能のリファクタリングテスト"""
    
    def test_teacher_dashboard_route(self, client, teacher_user):
        """教師ダッシュボードルートのテスト"""
        client.post('/login', data={
            'email': teacher_user.email,
            'password': 'password123'
        })
        
        # 新しいルート名でアクセス
        response = client.get('/teacher/teacher_dashboard')
        assert response.status_code == 200
        
        # url_forも動作確認
        with client.application.app_context():
            assert url_for('teacher_dashboard.dashboard') == '/teacher/teacher_dashboard'
    
    def test_class_management_routes(self, client, teacher_user):
        """クラス管理ルートのテスト"""
        client.post('/login', data={
            'email': teacher_user.email,
            'password': 'password123'
        })
        
        # クラス一覧
        response = client.get('/teacher/classes')
        assert response.status_code == 200
        
        # url_forテスト
        with client.application.app_context():
            assert url_for('teacher_class_management.classes') == '/teacher/classes'
            assert url_for('teacher_class_management.create_class') == '/teacher/create_class'
    
    def test_curriculum_management_import(self, app):
        """カリキュラム管理関数のインポートテスト"""
        with app.app_context():
            # モジュールからの正しいインポート
            from app.teacher.modules.curriculum_management import view_curriculums
            assert callable(view_curriculums)
            
            # 後方互換性（__init__.pyからのインポート）
            from app.teacher import view_curriculums as view_curriculums_compat
            assert callable(view_curriculums_compat)


class TestStudentRefactoring:
    """学生機能のリファクタリングテスト"""
    
    def test_student_dashboard_route(self, client, student_user):
        """学生ダッシュボードルートのテスト"""
        client.post('/login', data={
            'email': student_user.email,
            'password': 'password123'
        })
        
        # 新しいルート名でアクセス
        response = client.get('/student/dashboard')
        assert response.status_code == 200
        
        # url_forテスト
        with client.application.app_context():
            assert url_for('student_dashboard.dashboard') == '/student/dashboard'
    
    def test_activities_routes(self, client, student_user):
        """活動記録ルートのテスト"""
        client.post('/login', data={
            'email': student_user.email,
            'password': 'password123'
        })
        
        # 活動一覧
        response = client.get('/student/activities')
        assert response.status_code == 200
        
        # url_forテスト
        with client.application.app_context():
            assert url_for('student_activities.activities') == '/student/activities'
            assert url_for('student_activities.new_activity') == '/student/new_activity'
    
    def test_goals_todos_import(self, app):
        """目標・TODO管理関数のインポートテスト"""
        with app.app_context():
            # モジュールからの正しいインポート
            from app.student.modules.goals_todos import goals, todos
            assert callable(goals)
            assert callable(todos)
            
            # 後方互換性
            from app.student import goals as goals_compat, todos as todos_compat
            assert callable(goals_compat)
            assert callable(todos_compat)


class TestAPIRefactoring:
    """API機能のリファクタリングテスト"""
    
    def test_unit_progress_api(self, client, student_user, sample_unit):
        """単元進捗APIのテスト"""
        client.post('/login', data={
            'email': student_user.email,
            'password': 'password123'
        })
        
        # 単元選択
        StudentUnitSelection.query.filter_by(
            student_id=student_user.id,
            unit_id=sample_unit.id
        ).delete()
        db.session.commit()
        
        response = client.post('/api/units/select', json={
            'unit_id': sample_unit.id
        })
        assert response.status_code == 200
        
        # 進捗更新（重複削除確認）
        response = client.post(f'/api/units/{sample_unit.id}/progress')
        assert response.status_code == 200
        data = response.get_json()
        assert 'progress' in data
    
    def test_approval_workflow_api(self, client, student_user, teacher_user, sample_unit):
        """承認ワークフローAPIのテスト"""
        # 学生としてログイン
        client.post('/login', data={
            'email': student_user.email,
            'password': 'password123'
        })
        
        # 単元完了申請
        response = client.post(f'/api/units/{sample_unit.id}/request-completion', json={
            'notes': 'テスト完了申請'
        })
        assert response.status_code in [200, 400]  # 既存データによる
        
        # 教師としてログイン
        client.get('/logout')
        client.post('/login', data={
            'email': teacher_user.email,
            'password': 'password123'
        })
        
        # 承認待ち一覧取得
        response = client.get('/api/approvals/pending')
        assert response.status_code == 200
        data = response.get_json()
        assert 'pending_approvals' in data


class TestPhase3DataIntegrity:
    """Phase 3 データ整合性機能のテスト"""
    
    def test_data_integrity_api_access(self, client, admin_user):
        """データ整合性API権限テスト"""
        # 管理者としてログイン
        client.post('/login', data={
            'email': admin_user.email,
            'password': 'password123'
        })
        
        # 検証API
        response = client.get('/api/data-integrity/verify')
        assert response.status_code == 200
        data = response.get_json()
        assert 'checks' in data
    
    def test_unit_mapping_service(self, app, sample_unit):
        """単元マッピングサービスのテスト"""
        with app.app_context():
            from app.services.unit_item_mapping_service import UnitItemMappingService
            
            # 単元の問題取得（マッピングなしでもフォールバック動作）
            problems = UnitItemMappingService.get_unit_problems(sample_unit.id)
            assert isinstance(problems, list)
            
            # 進捗計算
            progress, correct, total = UnitItemMappingService.calculate_unit_progress(
                student_id=1,
                unit_id=sample_unit.id
            )
            assert isinstance(progress, float)
            assert 0 <= progress <= 100


class TestImportCompatibility:
    """インポート互換性のテスト"""
    
    def test_teacher_imports(self, app):
        """教師モジュールのインポート互換性"""
        with app.app_context():
            # 分析関数の修正されたインポート
            from app.teacher.modules.analytics import _generate_class_analytics
            assert callable(_generate_class_analytics)
    
    def test_student_imports(self, app):
        """学生モジュールのインポート互換性"""
        with app.app_context():
            # Blueprint登録
            from app.student import student_bp
            assert student_bp is not None
            
            # 各モジュールのBlueprint
            from app.student.modules.dashboard import dashboard_bp
            assert dashboard_bp.name == 'student_dashboard'
            
            from app.student.modules.activities import activities_bp
            assert activities_bp.name == 'student_activities'
    
    def test_no_duplicate_routes(self, app):
        """ルート重複がないことを確認"""
        with app.app_context():
            routes = {}
            for rule in app.url_map.iter_rules():
                key = (str(rule.rule), tuple(sorted(rule.methods - {'HEAD', 'OPTIONS'})))
                if key in routes:
                    # 同じパスとメソッドの組み合わせが複数存在
                    pytest.fail(f"Duplicate route found: {rule.rule} ({rule.endpoint})")
                routes[key] = rule.endpoint