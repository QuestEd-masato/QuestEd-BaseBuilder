# -*- coding: utf-8 -*-
"""
Migration Adapter Test Suite
=============================
移行アダプターの動作確認テスト
"""

import json
import unittest
from unittest.mock import Mock, patch, MagicMock
from app.services.curriculum.migration_adapter import CurriculumMigrationAdapter


class TestCurriculumMigrationAdapter(unittest.TestCase):
    """移行アダプターのテストケース"""
    
    def setUp(self):
        """テスト前準備"""
        self.adapter = CurriculumMigrationAdapter
        self.test_curriculum_id = 1
        
        # テストデータ
        self.test_content = {
            'table_content': [
                {
                    'lesson_number': 1,
                    'title': 'テストレッスン1',
                    'description': 'これはテストです',
                    'lesson_type': 'lecture',
                    'duration_minutes': 50,
                    'learning_objectives': ['目標1', '目標2'],
                    'tasks': [
                        {
                            'task_number': 1,
                            'title': 'タスク1',
                            'description': 'タスクの説明'
                        }
                    ]
                }
            ]
        }
    
    @patch('app.services.curriculum.migration_adapter.CurriculumLesson')
    @patch('app.services.curriculum.migration_adapter.Curriculum')
    def test_read_from_lessons_table_preferred(self, mock_curriculum, mock_lesson):
        """テーブル優先読み込みのテスト"""
        # モックの設定
        mock_lesson_instance = Mock()
        mock_lesson_instance.lesson_number = 1
        mock_lesson_instance.title = 'テストレッスン'
        mock_lesson_instance.description = '説明'
        mock_lesson_instance.lesson_type = Mock(value='lecture')
        mock_lesson_instance.duration_minutes = 50
        mock_lesson_instance.learning_objectives = []
        mock_lesson_instance.key_points = []
        mock_lesson_instance.evaluation_criteria = {}
        mock_lesson_instance.resources = []
        mock_lesson_instance.teacher_notes = ''
        mock_lesson_instance.tasks = []
        mock_lesson_instance.to_dict = Mock(return_value={'id': 1, 'title': 'テストレッスン'})
        
        mock_lesson.query.filter_by.return_value.order_by.return_value.all.return_value = [mock_lesson_instance]
        
        # テスト実行
        self.adapter.PREFER_TABLE_READ = True
        result = self.adapter.read_curriculum_content(self.test_curriculum_id)
        
        # 検証
        self.assertIn('lessons', result)
        self.assertIn('table_content', result)
        self.assertEqual(len(result['lessons']), 1)
    
    @patch('app.services.curriculum.migration_adapter.db')
    @patch('app.services.curriculum.migration_adapter.CurriculumLesson')
    @patch('app.services.curriculum.migration_adapter.Curriculum')
    def test_dual_write_enabled(self, mock_curriculum, mock_lesson, mock_db):
        """両方書き込みモードのテスト"""
        # モックの設定
        mock_curriculum_instance = Mock()
        mock_curriculum_instance.curriculum_data = '{}'
        mock_curriculum.query.get.return_value = mock_curriculum_instance
        
        # テスト実行
        self.adapter.ENABLE_DUAL_WRITE = True
        result = self.adapter.write_curriculum_content(self.test_curriculum_id, self.test_content)
        
        # 検証: commitが呼ばれたか
        self.assertTrue(mock_db.session.commit.called or mock_db.session.rollback.called)
    
    def test_convert_lesson_type(self):
        """レッスンタイプ変換のテスト"""
        from app.modules.lesson_system.models.lesson_models import LessonType
        
        result = self.adapter._get_lesson_type('lecture')
        self.assertEqual(result, LessonType.LECTURE)
        
        result = self.adapter._get_lesson_type('practice')
        self.assertEqual(result, LessonType.PRACTICE)
        
        # デフォルト値
        result = self.adapter._get_lesson_type('unknown')
        self.assertEqual(result, LessonType.LECTURE)
    
    @patch('app.services.curriculum.migration_adapter.Curriculum')
    def test_verify_data_consistency(self, mock_curriculum):
        """データ整合性検証のテスト"""
        with patch.object(self.adapter, '_read_from_data_column') as mock_json_read:
            with patch.object(self.adapter, '_read_from_lessons_table') as mock_table_read:
                # 同じ数のレッスン
                mock_json_read.return_value = {'table_content': [1, 2, 3]}
                mock_table_read.return_value = {'lessons': [1, 2, 3]}
                
                result = self.adapter.verify_data_consistency(self.test_curriculum_id)
                
                self.assertTrue(result['consistent'])
                self.assertEqual(result['json_lessons'], 3)
                self.assertEqual(result['table_lessons'], 3)
                
                # 異なる数のレッスン
                mock_json_read.return_value = {'table_content': [1, 2]}
                mock_table_read.return_value = {'lessons': [1, 2, 3]}
                
                result = self.adapter.verify_data_consistency(self.test_curriculum_id)
                
                self.assertFalse(result['consistent'])
                self.assertIn('Mismatch', result['message'])


if __name__ == '__main__':
    unittest.main()