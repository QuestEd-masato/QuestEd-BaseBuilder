"""
Unit Management API Tests
=========================
Phase 6.1: 単元管理APIのテスト

APIエンドポイントのテスト:
- 単元選択
- 進捗更新
- 完了申請
- 承認ワークフロー
"""

import json
from datetime import datetime

from tests.test_base import APITestCase
from app.models import CurriculumUnit, StudentUnitSelection


class TestUnitManagementAPI(APITestCase):
    """単元管理APIテスト"""
    
    def setUp(self):
        super().setUp()
        self.student = self.create_test_user(role='student')
        self.teacher = self.create_test_user(role='teacher')
        self.test_class = self.create_test_class(self.teacher)
        
        # テスト単元作成
        self.unit = CurriculumUnit(
            title='Test Unit',
            description='Test unit for API testing',
            subject_id=self.test_subjects[0].id,
            school_id=self.test_school.id,
            created_by=self.teacher.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.session.add(self.unit)
        db.session.commit()
    
    def test_select_unit_success(self):
        """単元選択成功テスト"""
        response = self.make_request(
            'POST',
            '/api/units/select',
            data={'unit_id': self.unit.id},
            user=self.student
        )
        
        data = self.assert_json_success(response)
        self.assertIn('unit_title', data)
        self.assertEqual(data['unit_title'], 'Test Unit')
    
    def test_select_unit_without_permission(self):
        """権限なし単元選択テスト"""
        # 別の学校の単元
        other_school_unit = CurriculumUnit(
            title='Other School Unit',
            school_id=999,  # 存在しない学校ID
            created_by=self.teacher.id,
            is_active=True
        )
        db.session.add(other_school_unit)
        db.session.commit()
        
        response = self.make_request(
            'POST',
            '/api/units/select',
            data={'unit_id': other_school_unit.id},
            user=self.student
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertEqual(data['status'], 'error')
    
    def test_get_units_with_progress(self):
        """進捗付き単元一覧取得テスト"""
        # 進捗データ作成
        selection = StudentUnitSelection(
            student_id=self.student.id,
            unit_id=self.unit.id,
            status='in_progress',
            progress_percentage=75.0,
            started_at=datetime.utcnow()
        )
        db.session.add(selection)
        db.session.commit()
        
        response = self.make_request(
            'GET',
            '/api/units?include_progress=true',
            user=self.student
        )
        
        data = self.assert_json_success(response)
        self.assertIn('units', data)
        self.assertGreater(len(data['units']), 0)
        
        # 進捗情報確認
        unit_data = next((u for u in data['units'] if u['id'] == self.unit.id), None)
        self.assertIsNotNone(unit_data)
        self.assertIn('progress', unit_data)
        self.assertEqual(unit_data['progress']['status'], 'in_progress')
        self.assertEqual(unit_data['progress']['progress_percentage'], 75.0)
    
    def test_update_unit_progress(self):
        """単元進捗更新テスト"""
        # まず単元を選択
        self.make_request(
            'POST',
            '/api/units/select',
            data={'unit_id': self.unit.id},
            user=self.student
        )
        
        # 進捗更新
        response = self.make_request(
            'POST',
            f'/api/units/{self.unit.id}/progress',
            data={
                'progress_percentage': 85.0,
                'completed_item_ids': [1, 2, 3]
            },
            user=self.student
        )
        
        data = self.assert_json_success(response)
        self.assertEqual(data['current_progress'], 85.0)
        self.assertEqual(data['current_status'], 'in_progress')
    
    def test_request_completion(self):
        """完了申請テスト"""
        # 進捗を80%以上に設定
        selection = StudentUnitSelection(
            student_id=self.student.id,
            unit_id=self.unit.id,
            status='in_progress',
            progress_percentage=90.0
        )
        db.session.add(selection)
        db.session.commit()
        
        response = self.make_request(
            'POST',
            f'/api/units/{self.unit.id}/request-completion',
            data={'completion_comment': 'I have completed all tasks'},
            user=self.student
        )
        
        data = self.assert_json_success(response)
        self.assertIn('approval_required', data)
    
    def test_teacher_get_pending_approvals(self):
        """教師の承認待ち一覧取得テスト"""
        # 学生をクラスに登録
        from app.models import ClassEnrollment
        enrollment = ClassEnrollment(
            student_id=self.student.id,
            class_id=self.test_class.id
        )
        db.session.add(enrollment)
        
        # 承認待ち申請作成
        selection = StudentUnitSelection(
            student_id=self.student.id,
            unit_id=self.unit.id,
            status='in_progress',
            progress_percentage=95.0,
            approval_status='pending',
            completion_request_date=datetime.utcnow()
        )
        db.session.add(selection)
        db.session.commit()
        
        response = self.make_request(
            'GET',
            '/api/approvals/pending',
            user=self.teacher
        )
        
        data = self.assert_json_success(response)
        self.assertIn('pending_approvals', data)
        self.assertGreater(len(data['pending_approvals']), 0)
    
    def test_approve_completion(self):
        """完了承認テスト"""
        # 承認対象作成
        selection = StudentUnitSelection(
            student_id=self.student.id,
            unit_id=self.unit.id,
            status='in_progress',
            progress_percentage=100.0,
            approval_status='pending'
        )
        db.session.add(selection)
        db.session.commit()
        
        response = self.make_request(
            'POST',
            f'/api/approvals/{selection.id}/approve',
            data={'teacher_comments': 'Well done!'},
            user=self.teacher
        )
        
        data = self.assert_json_success(response)
        self.assertEqual(data['message'], '単元完了を承認しました')
    
    def test_batch_approve_completions(self):
        """一括承認テスト"""
        # 複数の承認待ち作成
        selection_ids = []
        for i in range(3):
            selection = StudentUnitSelection(
                student_id=self.student.id,
                unit_id=self.unit.id,
                status='in_progress',
                progress_percentage=100.0,
                approval_status='pending'
            )
            db.session.add(selection)
            db.session.flush()
            selection_ids.append(selection.id)
        
        db.session.commit()
        
        response = self.make_request(
            'POST',
            '/api/approvals/batch-approve',
            data={
                'selection_ids': selection_ids,
                'teacher_comments': 'Batch approved'
            },
            user=self.teacher
        )
        
        data = self.assert_json_success(response)
        self.assertEqual(data['success_count'], 3)
    
    def test_get_approval_statistics(self):
        """承認統計取得テスト"""
        response = self.make_request(
            'GET',
            '/api/approvals/statistics',
            user=self.teacher
        )
        
        data = self.assert_json_success(response)
        self.assertIn('statistics', data)
        self.assertIn('pending_approvals', data['statistics'])
        self.assertIn('approved_count', data['statistics'])


if __name__ == '__main__':
    unittest.main()