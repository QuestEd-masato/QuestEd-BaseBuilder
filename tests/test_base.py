"""
Base Test Classes
=================
Phase 6.1: テストフレームワーク構築

すべてのテストの基底クラス:
- データベースセットアップ
- テストユーザー作成
- 共通アサーション
- テストデータ生成
"""

import unittest
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Flask
from flask_login import login_user
from flask_testing import TestCase

from app import create_app
from extensions import db
from app.models import User, School, Class, Subject


class BaseTestCase(TestCase):
    """基本テストケースクラス"""
    
    def create_app(self):
        """テスト用アプリケーション作成"""
        app = create_app('testing')
        
        # テスト用設定
        app.config.update({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'test-secret-key'
        })
        
        return app
    
    def setUp(self):
        """テストセットアップ"""
        db.create_all()
        self._create_base_data()
        
    def tearDown(self):
        """テストクリーンアップ"""
        db.session.remove()
        db.drop_all()
    
    def _create_base_data(self):
        """基本テストデータ作成"""
        # テスト学校
        self.test_school = School(
            name='Test School',
            code='TEST001',
            created_at=datetime.utcnow()
        )
        db.session.add(self.test_school)
        
        # テスト科目
        self.test_subjects = []
        for i, subject_name in enumerate(['数学', '国語', '英語', '理科', '社会']):
            subject = Subject(
                name=subject_name,
                code=f'SUBJ{i+1:03d}',
                created_at=datetime.utcnow()
            )
            db.session.add(subject)
            self.test_subjects.append(subject)
        
        db.session.commit()
    
    def create_test_user(self, role: str = 'student', 
                        email: Optional[str] = None,
                        name: Optional[str] = None) -> User:
        """
        テストユーザー作成
        
        Args:
            role: ユーザーロール
            email: メールアドレス
            name: ユーザー名
            
        Returns:
            User: 作成されたユーザー
        """
        if not email:
            email = f"{role}_{datetime.now().timestamp()}@test.com"
        
        if not name:
            name = f"Test {role.capitalize()}"
        
        user = User(
            email=email,
            name=name,
            role=role,
            school_id=self.test_school.id,
            is_active=True,
            email_verified=True,
            created_at=datetime.utcnow()
        )
        user.set_password('password123')
        
        db.session.add(user)
        db.session.commit()
        
        return user
    
    def create_test_class(self, teacher: User, name: str = 'Test Class') -> Class:
        """
        テストクラス作成
        
        Args:
            teacher: 教師ユーザー
            name: クラス名
            
        Returns:
            Class: 作成されたクラス
        """
        test_class = Class(
            name=name,
            teacher_id=teacher.id,
            school_id=self.test_school.id,
            created_at=datetime.utcnow()
        )
        
        db.session.add(test_class)
        db.session.commit()
        
        return test_class
    
    def login_user(self, user: User):
        """テストユーザーでログイン"""
        with self.client:
            self.client.post('/auth/login', data={
                'email': user.email,
                'password': 'password123'
            })
    
    def assert_response_success(self, response, status_code: int = 200):
        """レスポンス成功アサーション"""
        self.assertEqual(response.status_code, status_code)
    
    def assert_json_success(self, response):
        """JSON成功レスポンスアサーション"""
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsNotNone(data)
        self.assertEqual(data.get('status'), 'success')
        return data


class APITestCase(BaseTestCase):
    """APIテスト用基底クラス"""
    
    def get_auth_headers(self, user: Optional[User] = None) -> Dict[str, str]:
        """
        認証ヘッダー取得
        
        Args:
            user: ユーザー（省略時は新規作成）
            
        Returns:
            Dict: 認証ヘッダー
        """
        if not user:
            user = self.create_test_user()
        
        # トークン生成（実際の実装に応じて調整）
        return {
            'Authorization': f'Bearer test-token-{user.id}',
            'Content-Type': 'application/json'
        }
    
    def make_request(self, method: str, endpoint: str, 
                    data: Optional[Dict] = None,
                    user: Optional[User] = None) -> Any:
        """
        APIリクエスト実行
        
        Args:
            method: HTTPメソッド
            endpoint: エンドポイント
            data: リクエストデータ
            user: 認証ユーザー
            
        Returns:
            Response: レスポンスオブジェクト
        """
        headers = self.get_auth_headers(user) if user else {}
        
        if method.upper() == 'GET':
            return self.client.get(endpoint, headers=headers)
        elif method.upper() == 'POST':
            return self.client.post(endpoint, json=data, headers=headers)
        elif method.upper() == 'PUT':
            return self.client.put(endpoint, json=data, headers=headers)
        elif method.upper() == 'DELETE':
            return self.client.delete(endpoint, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")


class IntegrationTestCase(BaseTestCase):
    """統合テスト用基底クラス"""
    
    def setUp(self):
        """統合テストセットアップ"""
        super().setUp()
        self._create_integration_test_data()
    
    def _create_integration_test_data(self):
        """統合テスト用データ作成"""
        # 教師作成
        self.teacher = self.create_test_user(role='teacher', 
                                           email='teacher@test.com')
        
        # クラス作成
        self.test_class = self.create_test_class(self.teacher)
        
        # 学生作成
        self.students = []
        for i in range(5):
            student = self.create_test_user(role='student',
                                          email=f'student{i}@test.com')
            self.students.append(student)
            
            # クラスに登録
            from app.models import ClassEnrollment
            enrollment = ClassEnrollment(
                student_id=student.id,
                class_id=self.test_class.id,
                enrolled_at=datetime.utcnow()
            )
            db.session.add(enrollment)
        
        db.session.commit()


class PerformanceTestCase(BaseTestCase):
    """パフォーマンステスト用基底クラス"""
    
    def measure_time(self, func, *args, **kwargs):
        """
        実行時間測定
        
        Args:
            func: 測定対象関数
            *args, **kwargs: 関数引数
            
        Returns:
            tuple: (結果, 実行時間)
        """
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        return result, execution_time
    
    def assert_performance(self, execution_time: float, 
                          max_time: float = 1.0):
        """
        パフォーマンスアサーション
        
        Args:
            execution_time: 実行時間
            max_time: 最大許容時間
        """
        self.assertLess(execution_time, max_time,
                       f"Execution time {execution_time:.3f}s exceeds maximum {max_time}s")