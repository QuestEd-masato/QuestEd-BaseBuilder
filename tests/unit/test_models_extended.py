"""
モデルの拡張単体テスト

このファイルは、既存のtest_models.pyを拡張し、
より包括的なモデルテストを実装します。
"""

import pytest
from datetime import datetime, timedelta
from app.models import (
    User, School, Class, InquiryTheme, ActivityLog, 
    MainTheme, Curriculum, Milestone, Todo, Goal,
    InterestSurvey, PersonalitySurvey, StudentEvaluation
)
from basebuilder.models import (
    ProblemCategory, BasicKnowledgeItem, TextSet,
    LearningPath, AnswerRecord, ProficiencyRecord
)
from app import db
from werkzeug.exceptions import ValidationError
import json


class TestUserModelExtended:
    """ユーザーモデルの拡張テスト"""
    
    def test_user_email_verification_flow(self, app, sample_school):
        """メール検証フローのテスト"""
        with app.app_context():
            user = User(
                email='verify@test.com',
                role='student',
                school_id=sample_school.id,
                email_verified=False
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            
            # 検証トークン生成
            token = user.generate_verification_token()
            assert token is not None
            assert len(token) > 20
            
            # トークン検証
            assert user.verify_email_token(token) is True
            assert user.email_verified is True
            
            # 無効なトークンは拒否
            assert user.verify_email_token('invalid_token') is False
    
    def test_user_password_reset_flow(self, app, sample_school):
        """パスワードリセットフローのテスト"""
        with app.app_context():
            user = User(
                email='reset@test.com',
                role='teacher',
                school_id=sample_school.id
            )
            user.set_password('old_password')
            db.session.add(user)
            db.session.commit()
            
            # リセットトークン生成
            token = user.generate_reset_token()
            assert token is not None
            
            # 新しいパスワード設定
            new_password = 'new_secure_password'
            assert user.reset_password(token, new_password) is True
            
            # 新しいパスワードで認証確認
            assert user.check_password(new_password) is True
            assert user.check_password('old_password') is False
    
    def test_user_approval_workflow(self, app, sample_school):
        """ユーザー承認ワークフローのテスト"""
        with app.app_context():
            # 未承認学生
            student = User(
                email='pending@test.com',
                role='student',
                school_id=sample_school.id,
                is_approved=False
            )
            db.session.add(student)
            db.session.commit()
            
            assert student.is_approved is False
            assert student.needs_approval() is True
            
            # 承認処理
            student.approve_user()
            assert student.is_approved is True
            assert student.needs_approval() is False
    
    def test_user_permissions(self, app, sample_users):
        """ユーザー権限のテスト"""
        with app.app_context():
            admin, teacher, student = sample_users
            
            # 管理者権限
            assert admin.can_manage_users() is True
            assert admin.can_manage_schools() is True
            assert admin.can_view_all_data() is True
            
            # 教師権限
            assert teacher.can_manage_users() is False
            assert teacher.can_manage_classes() is True
            assert teacher.can_evaluate_students() is True
            
            # 学生権限
            assert student.can_manage_users() is False
            assert student.can_manage_classes() is False
            assert student.can_view_own_data() is True


class TestSchoolModelExtended:
    """学校モデルの拡張テスト"""
    
    def test_school_code_uniqueness(self, app):
        """学校コードの一意性テスト"""
        with app.app_context():
            school1 = School(name='学校1', school_code='UNIQUE001')
            school2 = School(name='学校2', school_code='UNIQUE001')  # 同じコード
            
            db.session.add(school1)
            db.session.commit()
            
            db.session.add(school2)
            with pytest.raises(Exception):  # IntegrityError
                db.session.commit()
    
    def test_school_user_statistics(self, app, sample_school, sample_users):
        """学校のユーザー統計テスト"""
        with app.app_context():
            stats = sample_school.get_user_statistics()
            
            assert stats['total_users'] == 3
            assert stats['admin_count'] == 1
            assert stats['teacher_count'] == 1
            assert stats['student_count'] == 1
            assert stats['approved_users'] == 3
    
    def test_school_activity_summary(self, app, sample_school):
        """学校の活動サマリーテスト"""
        with app.app_context():
            # テスト用活動データ作成
            summary = sample_school.get_activity_summary()
            
            assert 'total_classes' in summary
            assert 'total_themes' in summary
            assert 'total_activities' in summary


class TestClassModel:
    """クラスモデルのテスト"""
    
    def test_class_creation_and_relationships(self, app, sample_users):
        """クラス作成と関係性のテスト"""
        with app.app_context():
            teacher = sample_users[1]  # teacher
            
            test_class = Class(
                name='高校1年A組',
                description='数学重点クラス',
                teacher_id=teacher.id
            )
            db.session.add(test_class)
            db.session.commit()
            
            assert test_class.teacher.email == 'teacher@test.com'
            assert test_class.name == '高校1年A組'
    
    def test_class_student_enrollment(self, app, sample_class, sample_users):
        """クラスへの学生登録テスト"""
        with app.app_context():
            student = sample_users[2]  # student
            
            # 学生をクラスに追加
            sample_class.add_student(student)
            db.session.commit()
            
            assert student in sample_class.students
            assert sample_class in student.enrolled_classes


class TestInquiryThemeModel:
    """探究テーマモデルのテスト"""
    
    def test_inquiry_theme_creation(self, app, sample_users, sample_class):
        """探究テーマ作成のテスト"""
        with app.app_context():
            student = sample_users[2]
            
            theme = InquiryTheme(
                title='人工知能の教育への影響',
                description='AIが教育分野に与える影響を調査する',
                user_id=student.id,
                class_id=sample_class.id
            )
            db.session.add(theme)
            db.session.commit()
            
            assert theme.title == '人工知能の教育への影響'
            assert theme.user == student
            assert theme.class_obj == sample_class
    
    def test_inquiry_theme_status_tracking(self, app, sample_inquiry_theme):
        """探究テーマのステータス追跡テスト"""
        with app.app_context():
            # 初期状態
            assert sample_inquiry_theme.status == 'active'
            
            # ステータス変更
            sample_inquiry_theme.update_status('completed')
            assert sample_inquiry_theme.status == 'completed'
            
            # 完了日時の確認
            assert sample_inquiry_theme.completed_at is not None


class TestActivityLogModel:
    """活動ログモデルのテスト"""
    
    def test_activity_log_creation(self, app, sample_users, sample_inquiry_theme):
        """活動ログ作成のテスト"""
        with app.app_context():
            student = sample_users[2]
            
            activity = ActivityLog(
                title='第1回調査結果',
                content='図書館で関連書籍を調査しました。',
                reflection='もっと多角的な視点が必要だと感じました。',
                user_id=student.id,
                inquiry_theme_id=sample_inquiry_theme.id
            )
            db.session.add(activity)
            db.session.commit()
            
            assert activity.title == '第1回調査結果'
            assert activity.user == student
            assert activity.inquiry_theme == sample_inquiry_theme
    
    def test_activity_log_with_image(self, app, sample_activity_log, upload_file):
        """画像付き活動ログのテスト"""
        with app.app_context():
            # 画像ファイルの保存をシミュレート
            sample_activity_log.image_filename = 'test_image.png'
            db.session.commit()
            
            assert sample_activity_log.has_image() is True
            assert sample_activity_log.get_image_url().endswith('test_image.png')


class TestCurriculumModel:
    """カリキュラムモデルのテスト"""
    
    def test_curriculum_json_data(self, app, sample_class):
        """カリキュラムJSONデータのテスト"""
        with app.app_context():
            curriculum_data = {
                'subject': '数学',
                'units': [
                    {'name': '方程式', 'duration': 10},
                    {'name': '関数', 'duration': 15}
                ],
                'assessment': {
                    'midterm': 30,
                    'final': 50,
                    'assignments': 20
                }
            }
            
            curriculum = Curriculum(
                name='高校数学I',
                description='高校1年生向け数学カリキュラム',
                curriculum_data=json.dumps(curriculum_data),
                class_id=sample_class.id
            )
            db.session.add(curriculum)
            db.session.commit()
            
            # JSONデータの取得と検証
            parsed_data = curriculum.get_curriculum_data()
            assert parsed_data['subject'] == '数学'
            assert len(parsed_data['units']) == 2
            assert parsed_data['assessment']['midterm'] == 30


class TestTodoModel:
    """Todoモデルのテスト"""
    
    def test_todo_creation_and_completion(self, app, sample_users):
        """Todo作成と完了のテスト"""
        with app.app_context():
            student = sample_users[2]
            
            todo = Todo(
                title='資料収集',
                description='関連論文を5本以上読む',
                due_date=datetime.utcnow() + timedelta(days=7),
                user_id=student.id
            )
            db.session.add(todo)
            db.session.commit()
            
            assert todo.is_completed is False
            assert todo.is_overdue() is False
            
            # 完了処理
            todo.mark_completed()
            assert todo.is_completed is True
            assert todo.completed_at is not None
    
    def test_todo_overdue_detection(self, app, sample_users):
        """Todo期限切れ検出のテスト"""
        with app.app_context():
            student = sample_users[2]
            
            overdue_todo = Todo(
                title='期限切れタスク',
                due_date=datetime.utcnow() - timedelta(days=1),
                user_id=student.id
            )
            db.session.add(overdue_todo)
            db.session.commit()
            
            assert overdue_todo.is_overdue() is True


class TestGoalModel:
    """目標モデルのテスト"""
    
    def test_goal_progress_tracking(self, app, sample_users):
        """目標進捗追跡のテスト"""
        with app.app_context():
            student = sample_users[2]
            
            goal = Goal(
                title='英語力向上',
                description='TOEIC 600点を目指す',
                target_date=datetime.utcnow() + timedelta(days=90),
                user_id=student.id
            )
            db.session.add(goal)
            db.session.commit()
            
            # 進捗更新
            goal.update_progress(25.0, '基礎文法を復習中')
            assert goal.progress == 25.0
            assert goal.notes == '基礎文法を復習中'
            
            # 達成確認
            goal.update_progress(100.0, '目標達成！')
            assert goal.is_achieved() is True


class TestSurveyModels:
    """サーベイモデルのテスト"""
    
    def test_interest_survey(self, app, sample_users):
        """興味調査のテスト"""
        with app.app_context():
            student = sample_users[2]
            
            survey_data = {
                'subjects': ['数学', '物理', 'プログラミング'],
                'hobbies': ['読書', 'ゲーム', '映画鑑賞'],
                'career_interests': ['エンジニア', '研究者']
            }
            
            survey = InterestSurvey(
                survey_data=json.dumps(survey_data),
                user_id=student.id
            )
            db.session.add(survey)
            db.session.commit()
            
            parsed_data = survey.get_survey_data()
            assert 'プログラミング' in parsed_data['subjects']
            assert len(parsed_data['hobbies']) == 3
    
    def test_personality_survey(self, app, sample_users):
        """性格調査のテスト"""
        with app.app_context():
            student = sample_users[2]
            
            personality_data = {
                'learning_style': 'visual',
                'personality_type': 'INTJ',
                'strengths': ['分析力', '集中力'],
                'challenges': ['コミュニケーション', '時間管理']
            }
            
            survey = PersonalitySurvey(
                survey_data=json.dumps(personality_data),
                user_id=student.id
            )
            db.session.add(survey)
            db.session.commit()
            
            parsed_data = survey.get_survey_data()
            assert parsed_data['learning_style'] == 'visual'
            assert '分析力' in parsed_data['strengths']


class TestStudentEvaluationModel:
    """学生評価モデルのテスト"""
    
    def test_student_evaluation_creation(self, app, sample_users):
        """学生評価作成のテスト"""
        with app.app_context():
            teacher = sample_users[1]
            student = sample_users[2]
            
            evaluation = StudentEvaluation(
                student_id=student.id,
                teacher_id=teacher.id,
                subject='数学',
                score=85,
                comments='理解度が高く、応用問題もよく解けています。',
                evaluation_date=datetime.utcnow()
            )
            db.session.add(evaluation)
            db.session.commit()
            
            assert evaluation.student == student
            assert evaluation.teacher == teacher
            assert evaluation.score == 85
            assert evaluation.get_grade() == 'B'  # 85点はB評価


class TestBaseBuilderModels:
    """BaseBuilderモデルのテスト"""
    
    def test_problem_category_creation(self, app):
        """問題カテゴリ作成のテスト"""
        with app.app_context():
            category = ProblemCategory(
                name='代数',
                description='方程式と不等式',
                difficulty_level=2
            )
            db.session.add(category)
            db.session.commit()
            
            assert category.name == '代数'
            assert category.difficulty_level == 2
    
    def test_basic_knowledge_item(self, app):
        """基礎知識アイテムのテスト"""
        with app.app_context():
            category = ProblemCategory(name='幾何', difficulty_level=1)
            db.session.add(category)
            db.session.commit()
            
            problem = BasicKnowledgeItem(
                category_id=category.id,
                problem_text='正三角形の内角の和は何度ですか？',
                correct_answer='180度',
                explanation='三角形の内角の和は常に180度です。',
                difficulty=1
            )
            db.session.add(problem)
            db.session.commit()
            
            assert problem.category == category
            assert problem.problem_text == '正三角形の内角の和は何度ですか？'
    
    def test_learning_path_creation(self, app):
        """学習パス作成のテスト"""
        with app.app_context():
            path = LearningPath(
                name='基礎数学コース',
                description='中学数学から高校数学への橋渡し',
                difficulty_level=2
            )
            db.session.add(path)
            db.session.commit()
            
            assert path.name == '基礎数学コース'
            assert path.difficulty_level == 2
    
    def test_proficiency_record_tracking(self, app, sample_users):
        """熟練度記録追跡のテスト"""
        with app.app_context():
            student = sample_users[2]
            
            category = ProblemCategory(name='統計', difficulty_level=3)
            db.session.add(category)
            db.session.commit()
            
            record = ProficiencyRecord(
                user_id=student.id,
                category_id=category.id,
                mastery_level=0.75,
                total_attempts=10,
                correct_attempts=7
            )
            db.session.add(record)
            db.session.commit()
            
            assert record.user == student
            assert record.category == category
            assert record.mastery_level == 0.75
            assert record.get_accuracy() == 0.7


@pytest.mark.integration
class TestModelRelationships:
    """モデル間関係の統合テスト"""
    
    def test_complete_user_journey(self, app, sample_school):
        """完全なユーザージャーニーのテスト"""
        with app.app_context():
            # 1. 学生登録
            student = User(
                email='journey@test.com',
                role='student',
                full_name='テストジャーニー',
                school_id=sample_school.id,
                is_approved=True,
                email_verified=True
            )
            student.set_password('password123')
            db.session.add(student)
            
            # 2. 教師作成
            teacher = User(
                email='teacher.journey@test.com',
                role='teacher',
                full_name='テスト教師',
                school_id=sample_school.id,
                is_approved=True,
                email_verified=True
            )
            teacher.set_password('teacher123')
            db.session.add(teacher)
            db.session.commit()
            
            # 3. クラス作成
            test_class = Class(
                name='総合学習クラス',
                teacher_id=teacher.id
            )
            db.session.add(test_class)
            db.session.commit()
            
            # 4. 探究テーマ作成
            theme = InquiryTheme(
                title='環境問題の研究',
                description='地球温暖化対策を調査',
                user_id=student.id,
                class_id=test_class.id
            )
            db.session.add(theme)
            db.session.commit()
            
            # 5. 活動ログ作成
            activity = ActivityLog(
                title='文献調査',
                content='温暖化に関する論文を10本読了',
                user_id=student.id,
                inquiry_theme_id=theme.id
            )
            db.session.add(activity)
            db.session.commit()
            
            # 6. 評価作成
            evaluation = StudentEvaluation(
                student_id=student.id,
                teacher_id=teacher.id,
                subject='総合学習',
                score=90,
                comments='素晴らしい研究成果です'
            )
            db.session.add(evaluation)
            db.session.commit()
            
            # 関係性の確認
            assert student.inquiry_themes[0] == theme
            assert theme.activity_logs[0] == activity
            assert student.evaluations_received[0] == evaluation
            assert teacher.evaluations_given[0] == evaluation
            
            # データの整合性確認
            assert activity.inquiry_theme.user == student
            assert evaluation.student == student
            assert evaluation.teacher == teacher