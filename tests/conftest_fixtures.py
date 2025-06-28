"""
テスト用フィクスチャの追加定義
==============================
リファクタリングテストに必要なフィクスチャを定義
"""

import pytest
from app.models import db, User, School, Class, Subject, CurriculumUnit


@pytest.fixture
def admin_user(app, sample_school):
    """管理者ユーザーのフィクスチャ"""
    with app.app_context():
        admin = User(
            email='admin@test.com',
            username='admin_test',
            full_name='管理者テスト',
            role='admin',
            school_id=sample_school.id,
            email_confirmed=True,
            is_approved=True,
            is_active=True
        )
        admin.set_password('password123')
        db.session.add(admin)
        db.session.commit()
        return admin


@pytest.fixture
def teacher_user(app, sample_school):
    """教師ユーザーのフィクスチャ"""
    with app.app_context():
        teacher = User(
            email='teacher@test.com',
            username='teacher_test',
            full_name='教師テスト',
            role='teacher',
            school_id=sample_school.id,
            email_confirmed=True,
            is_approved=True,
            is_active=True
        )
        teacher.set_password('password123')
        db.session.add(teacher)
        db.session.commit()
        return teacher


@pytest.fixture
def student_user(app, sample_school):
    """学生ユーザーのフィクスチャ"""
    with app.app_context():
        student = User(
            email='student@test.com',
            username='student_test',
            full_name='学生テスト',
            role='student',
            school_id=sample_school.id,
            email_confirmed=True,
            is_approved=True,
            is_active=True
        )
        student.set_password('password123')
        db.session.add(student)
        db.session.commit()
        return student


@pytest.fixture
def sample_subject(app):
    """教科のフィクスチャ"""
    with app.app_context():
        subject = Subject(
            name='数学',
            description='数学の教科'
        )
        db.session.add(subject)
        db.session.commit()
        return subject


@pytest.fixture
def sample_unit(app, sample_school, sample_subject, teacher_user):
    """カリキュラム単元のフィクスチャ"""
    with app.app_context():
        unit = CurriculumUnit(
            title='テスト単元',
            description='テスト用の単元です',
            unit_code='TEST001',
            difficulty_level=2,
            estimated_minutes=60,
            order_index=1,
            school_id=sample_school.id,
            created_by=teacher_user.id,
            subject_id=sample_subject.id,
            is_active=True,
            tags='["テスト", "サンプル"]',
            learning_objectives='テスト目標'
        )
        db.session.add(unit)
        db.session.commit()
        return unit


@pytest.fixture
def sample_class(app, teacher_user, sample_school, sample_subject):
    """クラスのフィクスチャ"""
    with app.app_context():
        class_obj = Class(
            name='テストクラス',
            description='テスト用クラス',
            teacher_id=teacher_user.id,
            school_id=sample_school.id,
            subject_id=sample_subject.id,
            is_active=True
        )
        db.session.add(class_obj)
        db.session.commit()
        return class_obj