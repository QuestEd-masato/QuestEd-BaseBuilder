"""
QuestEd ランキング機能テスト

ランキングサービス、API、テンプレートの基本機能をテストします。

Author: QuestEd Development Team
Created: 2025-01-15
Version: 1.0.0
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json

from app import create_app
from app.models import User, School, Class, Ranking, RankingCache
from app.services.ranking_service import RankingService
from extensions import db


class RankingServiceTestCase(unittest.TestCase):
    """ランキングサービステスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # テストデータベース作成
        db.create_all()
        
        # テストユーザー作成
        self.school = School(name='テスト学校', unique_code='TEST001')
        db.session.add(self.school)
        
        self.teacher = User(
            username='teacher1',
            email='teacher@test.com',
            role='teacher',
            school_id=1,
            is_active=True
        )
        db.session.add(self.teacher)
        
        self.students = []
        for i in range(5):
            student = User(
                username=f'student{i+1}',
                email=f'student{i+1}@test.com',
                role='student',
                school_id=1,
                is_active=True
            )
            self.students.append(student)
            db.session.add(student)
        
        self.class_obj = Class(
            name='テストクラス',
            teacher_id=1,
            school_id=1,
            is_active=True
        )
        db.session.add(self.class_obj)
        
        db.session.commit()
    
    def tearDown(self):
        """テストクリーンアップ"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_generate_cache_key(self):
        """キャッシュキー生成テスト"""
        key1 = RankingService._generate_cache_key('total_points', 'school', 1)
        key2 = RankingService._generate_cache_key('total_points', 'school', 1)
        key3 = RankingService._generate_cache_key('total_points', 'class', 1)
        
        self.assertEqual(key1, key2)  # 同じパラメータでは同じキー
        self.assertNotEqual(key1, key3)  # 異なるパラメータでは異なるキー
    
    def test_count_participants(self):
        """参加者数カウントテスト"""
        count_school = RankingService._count_participants('school', 1)
        count_class = RankingService._count_participants('class', 1)
        
        self.assertEqual(count_school, 5)  # 学生5人
        self.assertEqual(count_class, 0)   # クラス登録なし
    
    @patch('app.services.ranking_service.RankingService._calculate_ranking')
    def test_get_ranking_with_cache(self, mock_calculate):
        """キャッシュありランキング取得テスト"""
        # キャッシュデータを作成
        cache_data = {
            'rankings': [{'rank': 1, 'student_id': 1, 'score': 100}],
            'total_participants': 5,
            'last_updated': datetime.utcnow().isoformat()
        }
        
        cache = RankingCache(
            cache_key=RankingService._generate_cache_key('total_points', 'school', 1),
            ranking_type='total_points',
            scope='school',
            scope_id=1,
            ranking_data=cache_data,
            participant_count=5,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(cache)
        db.session.commit()
        
        # ランキング取得
        result = RankingService.get_ranking('total_points', 'school', 1)
        
        # キャッシュから取得されることを確認
        self.assertEqual(result['rankings'][0]['rank'], 1)
        mock_calculate.assert_not_called()
    
    def test_clear_cache(self):
        """キャッシュクリアテスト"""
        # テストキャッシュを作成
        cache = RankingCache(
            cache_key='test_key',
            ranking_type='total_points',
            scope='school',
            scope_id=1,
            ranking_data={'test': 'data'},
            participant_count=5,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(cache)
        db.session.commit()
        
        # キャッシュクリア
        RankingService.clear_cache('total_points')
        
        # キャッシュが削除されることを確認
        remaining = RankingCache.query.filter_by(ranking_type='total_points').count()
        self.assertEqual(remaining, 0)


class RankingAPITestCase(unittest.TestCase):
    """ランキングAPIテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # テストデータベース作成
        db.create_all()
        
        # テストユーザー作成
        self.school = School(name='テスト学校', unique_code='TEST001')
        db.session.add(self.school)
        
        self.student = User(
            username='teststudent',
            email='student@test.com',
            role='student',
            school_id=1,
            is_active=True
        )
        db.session.add(self.student)
        db.session.commit()
    
    def tearDown(self):
        """テストクリーンアップ"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def login_student(self):
        """学生としてログイン"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.student.id
            sess['_fresh'] = True
    
    @patch('app.services.ranking_service.RankingService.get_ranking')
    def test_get_ranking_api(self, mock_get_ranking):
        """ランキング取得APIテスト"""
        # モックデータ設定
        mock_get_ranking.return_value = {
            'rankings': [
                {'rank': 1, 'student_id': 1, 'student_name': 'テスト学生', 'score': 100}
            ],
            'total_participants': 1,
            'last_updated': datetime.utcnow().isoformat()
        }
        
        # ログイン
        self.login_student()
        
        # API呼び出し
        response = self.client.get('/api/ranking/total_points?scope=school')
        
        # レスポンス確認
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('rankings', data['data'])
    
    def test_get_ranking_api_unauthorized(self):
        """認証なしランキング取得APIテスト"""
        response = self.client.get('/api/ranking/total_points')
        self.assertEqual(response.status_code, 302)  # ログインページにリダイレクト
    
    @patch('app.services.ranking_service.RankingService.get_student_rank')
    def test_get_student_ranking_api(self, mock_get_student_rank):
        """学生ランキング取得APIテスト"""
        # モックデータ設定
        mock_get_student_rank.return_value = {
            'rank': 1,
            'score': 100,
            'total_participants': 10,
            'percentile': 90.0
        }
        
        # ログイン
        self.login_student()
        
        # API呼び出し
        response = self.client.get(f'/api/ranking/student/{self.student.id}')
        
        # レスポンス確認
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['rank'], 1)


class RankingRouteTestCase(unittest.TestCase):
    """ランキングルートテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # テストデータベース作成
        db.create_all()
        
        # テストユーザー作成
        self.school = School(name='テスト学校', unique_code='TEST001')
        db.session.add(self.school)
        
        self.student = User(
            username='teststudent',
            email='student@test.com',
            role='student',
            school_id=1,
            is_active=True
        )
        
        self.teacher = User(
            username='testteacher',
            email='teacher@test.com',
            role='teacher',
            school_id=1,
            is_active=True
        )
        
        db.session.add(self.student)
        db.session.add(self.teacher)
        db.session.commit()
    
    def tearDown(self):
        """テストクリーンアップ"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def login_student(self):
        """学生としてログイン"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.student.id
            sess['_fresh'] = True
    
    def login_teacher(self):
        """教師としてログイン"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.teacher.id
            sess['_fresh'] = True
    
    def test_student_ranking_page(self):
        """学生ランキングページテスト"""
        self.login_student()
        
        response = self.client.get('/student/ranking')
        self.assertEqual(response.status_code, 200)
        self.assertIn('<title>学習ランキング | QuestEd</title>'.encode('utf-8'), response.data)
    
    def test_teacher_ranking_analysis_page(self):
        """教師ランキング分析ページテスト"""
        self.login_teacher()
        
        response = self.client.get('/teacher/ranking_analysis')
        self.assertEqual(response.status_code, 200)
        self.assertIn('<title>ランキング分析 | QuestEd</title>'.encode('utf-8'), response.data)
    
    def test_student_access_teacher_page_denied(self):
        """学生が教師ページにアクセス拒否テスト"""
        self.login_student()
        
        response = self.client.get('/teacher/ranking_analysis')
        # 権限なしで適切にリダイレクトまたはエラーページが表示されることを確認
        self.assertIn(response.status_code, [403, 302])


class RankingIntegrationTestCase(unittest.TestCase):
    """ランキング統合テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # テストデータベース作成
        db.create_all()
        
        # テストデータ作成
        self.school = School(name='テスト学校', unique_code='TEST001')
        db.session.add(self.school)
        db.session.commit()
        
        # 複数学生のランキングデータを作成
        for i in range(3):
            student = User(
                username=f'student{i+1}',
                email=f'student{i+1}@test.com',
                role='student',
                school_id=1,
                is_active=True
            )
            db.session.add(student)
        
        db.session.commit()
    
    def tearDown(self):
        """テストクリーンアップ"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_full_ranking_workflow(self):
        """完全なランキングワークフローテスト"""
        # 1. ランキングデータの計算
        ranking_data = RankingService.get_ranking('total_points', 'school', 1)
        
        # 2. 結果の検証
        self.assertIn('rankings', ranking_data)
        self.assertIn('total_participants', ranking_data)
        self.assertIn('last_updated', ranking_data)
        
        # 3. キャッシュの確認
        cache = RankingCache.query.filter_by(ranking_type='total_points').first()
        self.assertIsNotNone(cache)
        
        # 4. キャッシュクリア
        RankingService.clear_cache()
        cache_after_clear = RankingCache.query.count()
        self.assertEqual(cache_after_clear, 0)


if __name__ == '__main__':
    # テスト実行
    unittest.main(verbosity=2)