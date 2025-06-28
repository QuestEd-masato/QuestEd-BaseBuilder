"""
Service Unit Tests
==================
Phase 6.1: サービス層の単体テスト

統合されたサービスのテスト:
- UnifiedCurriculumService
- UnifiedProgressServiceV2
- LearningProgressManager
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from tests.test_base import BaseTestCase
from app.services.unified_curriculum_service import UnifiedCurriculumService
from app.services.unified_progress_service_v2 import UnifiedProgressServiceV2
from app.features.learning.progress_manager import LearningProgressManager


class TestUnifiedCurriculumService(BaseTestCase):
    """統合カリキュラムサービスのテスト"""
    
    def setUp(self):
        super().setUp()
        self.service = UnifiedCurriculumService()
        self.teacher = self.create_test_user(role='teacher')
    
    def test_create_curriculum_success(self):
        """カリキュラム作成成功テスト"""
        with patch.object(self.service, 'get_current_user_id', return_value=self.teacher.id):
            with patch.object(self.service, 'check_permission', return_value=True):
                data = {
                    'title': 'Test Curriculum',
                    'description': 'Test Description',
                    'subject_id': self.test_subjects[0].id,
                    'curriculum_data': {'units': []}
                }
                
                result = self.service.create_curriculum(data)
                
                self.assertTrue(result['success'])
                self.assertEqual(result['message'], 'カリキュラムを作成しました')
                self.assertIn('curriculum_id', result)
    
    def test_create_curriculum_validation_error(self):
        """カリキュラム作成バリデーションエラーテスト"""
        with patch.object(self.service, 'get_current_user_id', return_value=self.teacher.id):
            with patch.object(self.service, 'check_permission', return_value=True):
                data = {
                    'description': 'Missing title'
                }
                
                result = self.service.create_curriculum(data)
                
                self.assertFalse(result['success'])
                self.assertEqual(result['message'], 'バリデーションエラー')
                self.assertIn('errors', result)
    
    def test_update_curriculum_success(self):
        """カリキュラム更新成功テスト"""
        # まずカリキュラムを作成
        with patch.object(self.service, 'get_current_user_id', return_value=self.teacher.id):
            with patch.object(self.service, 'check_permission', return_value=True):
                create_data = {
                    'title': 'Original Title',
                    'subject_id': self.test_subjects[0].id
                }
                create_result = self.service.create_curriculum(create_data)
                curriculum_id = create_result['curriculum_id']
                
                # 更新実行
                update_data = {
                    'title': 'Updated Title',
                    'description': 'Updated Description'
                }
                
                with patch.object(self.service, '_can_modify_curriculum', return_value=True):
                    result = self.service.update_curriculum(curriculum_id, update_data)
                    
                    self.assertTrue(result['success'])
                    self.assertEqual(result['message'], 'カリキュラムを更新しました')
    
    def test_convert_to_units(self):
        """単元変換テスト"""
        with patch.object(self.service, 'get_current_user_id', return_value=self.teacher.id):
            with patch.object(self.service, 'check_permission', return_value=True):
                # カリキュラム作成
                create_data = {
                    'title': 'Test Curriculum',
                    'subject_id': self.test_subjects[0].id,
                    'curriculum_data': {
                        'units': [
                            {'title': 'Unit 1', 'description': 'First unit'},
                            {'title': 'Unit 2', 'description': 'Second unit'}
                        ]
                    }
                }
                create_result = self.service.create_curriculum(create_data)
                curriculum_id = create_result['curriculum_id']
                
                # 単元変換
                with patch.object(self.service, '_can_modify_curriculum', return_value=True):
                    result = self.service.convert_to_units(curriculum_id)
                    
                    self.assertTrue(result['success'])
                    self.assertIn('created_units', result)


class TestUnifiedProgressServiceV2(BaseTestCase):
    """統合進捗サービスV2のテスト"""
    
    def setUp(self):
        super().setUp()
        self.service = UnifiedProgressServiceV2()
        self.student = self.create_test_user(role='student')
    
    @patch('app.features.learning.progress_manager.LearningProgressManager.get_student_progress')
    def test_get_comprehensive_progress(self, mock_get_progress):
        """包括的進捗取得テスト"""
        mock_get_progress.return_value = {
            'student_id': self.student.id,
            'total_units': 10,
            'completed_units': 5,
            'in_progress_units': 3,
            'completion_rate': 0.5,
            'units': []
        }
        
        with patch.object(self.service, '_get_recent_activities', return_value=[]):
            with patch.object(self.service, '_get_goals_todos_status', return_value={}):
                result = self.service.get_comprehensive_progress(self.student.id)
                
                self.assertIn('student_id', result)
                self.assertEqual(result['student_id'], self.student.id)
                self.assertIn('basic_progress', result)
                self.assertIn('learning_analytics', result)
                self.assertIn('statistics', result)
    
    def test_get_progress_summary(self):
        """進捗サマリー取得テスト"""
        with patch.object(self.service.learning_manager, 'get_student_progress') as mock_get:
            mock_get.return_value = {
                'total_units': 10,
                'completed_units': 5,
                'in_progress_units': 3,
                'completion_rate': 0.5
            }
            
            with patch.object(self.service.progress_calculator, 'calculate_average_progress', return_value=0.65):
                summary = self.service.get_progress_summary(self.student.id)
                
                self.assertEqual(summary.total_units, 10)
                self.assertEqual(summary.completed_units, 5)
                self.assertEqual(summary.completion_rate, 0.5)
                self.assertEqual(summary.average_progress, 0.65)


class TestLearningProgressManager(BaseTestCase):
    """学習進捗管理のテスト"""
    
    def setUp(self):
        super().setUp()
        self.manager = LearningProgressManager()
        self.student = self.create_test_user(role='student')
        self.teacher = self.create_test_user(role='teacher')
    
    def test_update_unit_progress_new_selection(self):
        """新規単元進捗更新テスト"""
        with patch.object(self.manager, 'get_current_user_id', return_value=self.student.id):
            with patch.object(self.manager, 'check_permission', return_value=True):
                result = self.manager.update_unit_progress(
                    self.student.id, 
                    unit_id=1,
                    progress_percentage=50.0
                )
                
                self.assertTrue(result)
    
    def test_request_completion_insufficient_progress(self):
        """進捗不足での完了申請テスト"""
        with patch.object(self.manager, 'get_current_user_id', return_value=self.student.id):
            with patch.object(self.manager, 'check_permission', return_value=True):
                # 進捗50%で完了申請（80%必要）
                from app.models import StudentUnitSelection
                selection = StudentUnitSelection(
                    student_id=self.student.id,
                    unit_id=1,
                    status='in_progress',
                    progress_percentage=50.0
                )
                
                with patch.object(self.manager.dal, 'safe_query', return_value=[selection]):
                    result = self.manager.request_completion(
                        self.student.id, 
                        unit_id=1,
                        comment='Please approve'
                    )
                    
                    self.assertFalse(result['success'])
                    self.assertIn('80%以上', result['message'])
    
    def test_approve_completion_success(self):
        """完了承認成功テスト"""
        with patch.object(self.manager, 'get_current_user_id', return_value=self.teacher.id):
            with patch.object(self.manager, 'check_permission', return_value=True):
                from app.models import StudentUnitSelection
                selection = StudentUnitSelection(
                    id=1,
                    student_id=self.student.id,
                    unit_id=1,
                    status='in_progress',
                    progress_percentage=90.0,
                    approval_status='pending'
                )
                
                with patch.object(self.manager.dal, 'safe_get_by_id', return_value=selection):
                    with patch.object(self.manager, '_can_approve_student', return_value=True):
                        with patch.object(self.manager.dal, 'safe_update', return_value=True):
                            result = self.manager.approve_completion(
                                selection_id=1,
                                teacher_id=self.teacher.id,
                                comment='Good work!'
                            )
                            
                            self.assertTrue(result['success'])
                            self.assertEqual(result['message'], '完了を承認しました')


if __name__ == '__main__':
    unittest.main()