"""
エンドツーエンドテスト - ユーザーフロー

このファイルは、実際のユーザー操作をシミュレートした
エンドツーエンドテストを実装します。
"""

import pytest
import time
from unittest.mock import patch, Mock
from app import create_app, db
from app.models import User, Class, InquiryTheme, ActivityLog, Todo, Goal
import json


class TestStudentUserFlow:
    """学生ユーザーフローのE2Eテスト"""
    
    def test_complete_student_onboarding_flow(self, client, app):
        """学生の完全なオンボーディングフローテスト"""
        with app.app_context():
            # 1. 新規ユーザー登録
            registration_data = {
                'email': 'newstudent@test.com',
                'password': 'SecurePass123!',
                'confirm_password': 'SecurePass123!',
                'full_name': '新規学生',
                'role': 'student',
                'school_code': 'TEST001'
            }
            
            register_response = client.post('/auth/register', 
                                          data=registration_data,
                                          follow_redirects=True)
            assert register_response.status_code == 200
            
            # 2. メール検証（シミュレーション）
            user = User.query.filter_by(email='newstudent@test.com').first()
            assert user is not None
            user.email_verified = True
            user.is_approved = True
            db.session.commit()
            
            # 3. 初回ログイン
            login_response = client.post('/auth/login', data={
                'email': 'newstudent@test.com',
                'password': 'SecurePass123!'
            }, follow_redirects=True)
            assert login_response.status_code == 200
            
            # 4. 興味調査の完了
            interest_data = {
                'subjects': ['数学', '物理', 'プログラミング'],
                'hobbies': ['読書', 'ゲーム'],
                'career_interests': ['エンジニア']
            }
            
            survey_response = client.post('/student/interest_survey',
                                        data={'survey_data': json.dumps(interest_data)},
                                        follow_redirects=True)
            assert survey_response.status_code == 200
            
            # 5. 性格調査の完了
            personality_data = {
                'learning_style': 'visual',
                'personality_type': 'INTJ',
                'strengths': ['分析力', '集中力'],
                'challenges': ['コミュニケーション']
            }
            
            personality_response = client.post('/student/personality_survey',
                                             data={'survey_data': json.dumps(personality_data)},
                                             follow_redirects=True)
            assert personality_response.status_code == 200
            
            # 6. ダッシュボードアクセス
            dashboard_response = client.get('/student/dashboard')
            assert dashboard_response.status_code == 200
    
    def test_inquiry_theme_creation_and_activity_flow(self, student_client, app, sample_class):
        """探究テーマ作成と活動記録フローテスト"""
        with app.app_context():
            # 1. 探究テーマ作成
            theme_data = {
                'title': '持続可能なエネルギーの研究',
                'description': '再生可能エネルギーの効率性について調査する',
                'class_id': sample_class.id
            }
            
            theme_response = student_client.post('/student/create_theme',
                                               data=theme_data,
                                               follow_redirects=True)
            assert theme_response.status_code == 200
            
            # テーマが作成されたことを確認
            theme = InquiryTheme.query.filter_by(title='持続可能なエネルギーの研究').first()
            assert theme is not None
            
            # 2. 第1回活動記録
            activity1_data = {
                'title': '文献調査',
                'content': '太陽光発電に関する論文を5本読了しました。',
                'reflection': '技術の進歩が予想以上に早いことが分かりました。',
                'inquiry_theme_id': theme.id
            }
            
            activity1_response = student_client.post('/student/create_activity',
                                                   data=activity1_data,
                                                   follow_redirects=True)
            assert activity1_response.status_code == 200
            
            # 3. 第2回活動記録（画像付き）
            activity2_data = {
                'title': '実地調査',
                'content': '近隣の太陽光発電所を見学しました。',
                'reflection': '実際の設備を見ることで理解が深まりました。',
                'inquiry_theme_id': theme.id
            }
            
            # 画像ファイルのシミュレーション
            import io
            from werkzeug.datastructures import FileStorage
            
            test_image = FileStorage(
                stream=io.BytesIO(b'fake_image_data'),
                filename='solar_plant.jpg',
                content_type='image/jpeg'
            )
            activity2_data['image'] = test_image
            
            activity2_response = student_client.post('/student/create_activity',
                                                   data=activity2_data,
                                                   content_type='multipart/form-data',
                                                   follow_redirects=True)
            assert activity2_response.status_code == 200
            
            # 4. 活動履歴の確認
            activities_response = student_client.get('/student/activities')
            assert activities_response.status_code == 200
            
            # 活動が記録されていることを確認
            activities = ActivityLog.query.filter_by(inquiry_theme_id=theme.id).all()
            assert len(activities) == 2
    
    def test_todo_and_goal_management_flow(self, student_client, app):
        """Todo と目標管理フローテスト"""
        with app.app_context():
            # 1. 目標設定
            goal_data = {
                'title': 'TOEIC 700点獲得',
                'description': '英語力向上のため、3ヶ月以内にTOEIC 700点を目指す',
                'target_date': '2025-04-15'
            }
            
            goal_response = student_client.post('/student/create_goal',
                                              data=goal_data,
                                              follow_redirects=True)
            assert goal_response.status_code == 200
            
            # 目標が作成されたことを確認
            goal = Goal.query.filter_by(title='TOEIC 700点獲得').first()
            assert goal is not None
            
            # 2. 関連Todoの作成
            todo_items = [
                {
                    'title': '英単語1000個暗記',
                    'description': '頻出英単語集を使用',
                    'due_date': '2025-02-15'
                },
                {
                    'title': 'リスニング練習',
                    'description': '毎日30分のリスニング練習',
                    'due_date': '2025-03-15'
                },
                {
                    'title': '模擬試験受験',
                    'description': 'TOEIC模擬試験を2回受験',
                    'due_date': '2025-04-01'
                }
            ]
            
            created_todos = []
            for todo_data in todo_items:
                todo_response = student_client.post('/student/create_todo',
                                                  data=todo_data,
                                                  follow_redirects=True)
                assert todo_response.status_code == 200
                
                todo = Todo.query.filter_by(title=todo_data['title']).first()
                assert todo is not None
                created_todos.append(todo)
            
            # 3. Todoの進捗更新
            for i, todo in enumerate(created_todos):
                progress_data = {
                    'completed': i < 2  # 最初の2つを完了とする
                }
                
                update_response = student_client.post(f'/student/update_todo/{todo.id}',
                                                    data=progress_data,
                                                    follow_redirects=True)
                assert update_response.status_code == 200
            
            # 4. 目標の進捗更新
            goal_progress_data = {
                'progress': 65.0,
                'notes': '順調に学習が進んでいます。模擬試験では650点でした。'
            }
            
            goal_update_response = student_client.post(f'/student/update_goal/{goal.id}',
                                                     data=goal_progress_data,
                                                     follow_redirects=True)
            assert goal_update_response.status_code == 200
            
            # 5. 進捗確認
            goals_response = student_client.get('/student/goals')
            assert goals_response.status_code == 200
            
            todos_response = student_client.get('/student/todos')
            assert todos_response.status_code == 200


class TestTeacherUserFlow:
    """教師ユーザーフローのE2Eテスト"""
    
    def test_class_management_complete_flow(self, authenticated_client, app):
        """クラス管理完全フローテスト"""
        with app.app_context():
            # 1. 新しいクラス作成
            class_data = {
                'name': '高校2年A組',
                'description': '理系コース',
                'subject': '数学・物理'
            }
            
            class_response = authenticated_client.post('/teacher/create_class',
                                                     data=class_data,
                                                     follow_redirects=True)
            assert class_response.status_code == 200
            
            # クラスが作成されたことを確認
            new_class = Class.query.filter_by(name='高校2年A組').first()
            assert new_class is not None
            
            # 2. メインテーマ設定
            theme_data = {
                'title': '環境科学プロジェクト',
                'description': '地球環境問題の解決策を探る',
                'class_id': new_class.id
            }
            
            theme_response = authenticated_client.post('/teacher/create_main_theme',
                                                     data=theme_data,
                                                     follow_redirects=True)
            assert theme_response.status_code == 200
            
            # 3. カリキュラム作成
            curriculum_data = {
                'name': '環境科学カリキュラム',
                'description': '3ヶ月間の環境科学学習プログラム',
                'class_id': new_class.id,
                'curriculum_data': json.dumps({
                    'units': [
                        {'name': '地球温暖化', 'weeks': 4},
                        {'name': '再生可能エネルギー', 'weeks': 4},
                        {'name': '持続可能な社会', 'weeks': 4}
                    ],
                    'assessment': {
                        'research_project': 40,
                        'presentation': 30,
                        'report': 30
                    }
                })
            }
            
            curriculum_response = authenticated_client.post('/teacher/create_curriculum',
                                                          data=curriculum_data,
                                                          follow_redirects=True)
            assert curriculum_response.status_code == 200
            
            # 4. マイルストーン設定
            milestone_data = {
                'title': '中間発表',
                'description': '研究の中間成果を発表する',
                'due_date': '2025-03-15',
                'class_id': new_class.id
            }
            
            milestone_response = authenticated_client.post('/teacher/create_milestone',
                                                         data=milestone_data,
                                                         follow_redirects=True)
            assert milestone_response.status_code == 200
            
            # 5. 学生の進捗確認
            progress_response = authenticated_client.get(f'/teacher/class_progress/{new_class.id}')
            assert progress_response.status_code == 200
    
    @patch('app.ai.helpers.get_ai_response')
    def test_ai_assisted_curriculum_creation(self, mock_ai_response, authenticated_client, app):
        """AI支援カリキュラム作成フローテスト"""
        with app.app_context():
            # AIレスポンスのモック
            mock_ai_response.return_value = {
                'curriculum': {
                    'title': 'AI生成カリキュラム：現代社会と科学技術',
                    'description': '科学技術が現代社会に与える影響を学ぶ',
                    'units': [
                        {
                            'name': '人工知能の基礎',
                            'duration': '2週間',
                            'objectives': ['AIの歴史を理解する', '機械学習の基本概念を学ぶ']
                        },
                        {
                            'name': 'AIの社会実装',
                            'duration': '3週間',
                            'objectives': ['AIの社会での活用例を調査する', '倫理的課題を考察する']
                        }
                    ]
                }
            }
            
            # 1. AI支援リクエスト
            ai_request_data = {
                'subject': '情報科学',
                'grade': '高校2年',
                'duration': '5週間',
                'focus_areas': ['AI', '社会実装', '倫理']
            }
            
            ai_response = authenticated_client.post('/teacher/generate_curriculum_ai',
                                                  data=json.dumps(ai_request_data),
                                                  content_type='application/json')
            assert ai_response.status_code == 200
            
            # 2. AI生成カリキュラムの確認と編集
            ai_result = json.loads(ai_response.data)
            assert 'curriculum' in ai_result
            
            # 3. カリキュラムの保存
            save_data = {
                'name': ai_result['curriculum']['title'],
                'description': ai_result['curriculum']['description'],
                'curriculum_data': json.dumps(ai_result['curriculum']),
                'class_id': 1  # サンプルクラスID
            }
            
            save_response = authenticated_client.post('/teacher/save_curriculum',
                                                    data=save_data,
                                                    follow_redirects=True)
            assert save_response.status_code == 200
    
    def test_student_evaluation_flow(self, authenticated_client, app, sample_users):
        """学生評価フローテスト"""
        with app.app_context():
            student = sample_users[2]  # student user
            
            # 1. 評価ページアクセス
            eval_page_response = authenticated_client.get('/teacher/evaluate')
            assert eval_page_response.status_code == 200
            
            # 2. 学生評価実行
            evaluation_data = {
                'student_id': student.id,
                'subject': '探究学習',
                'score': 88,
                'comments': '研究テーマへの取り組みが素晴らしく、深い洞察を示しています。プレゼンテーション能力も向上しています。',
                'skills_assessment': json.dumps({
                    'research_skills': 9,
                    'critical_thinking': 8,
                    'presentation': 7,
                    'collaboration': 8
                })
            }
            
            eval_response = authenticated_client.post('/teacher/submit_evaluation',
                                                    data=evaluation_data,
                                                    follow_redirects=True)
            assert eval_response.status_code == 200
            
            # 3. 評価履歴確認
            history_response = authenticated_client.get('/teacher/evaluation_history')
            assert history_response.status_code == 200
            
            # 4. 学生へのフィードバック送信
            feedback_data = {
                'student_id': student.id,
                'message': '今期の探究学習での成長が素晴らしいです。次回は他の学生との協働も意識してみてください。',
                'suggestions': json.dumps([
                    '論文の構成をより論理的に',
                    'データ分析手法の向上',
                    'チームワークの強化'
                ])
            }
            
            feedback_response = authenticated_client.post('/teacher/send_feedback',
                                                        data=feedback_data,
                                                        follow_redirects=True)
            assert feedback_response.status_code == 200


class TestAdminUserFlow:
    """管理者ユーザーフローのE2Eテスト"""
    
    def test_school_and_user_management_flow(self, admin_client, app):
        """学校・ユーザー管理フローテスト"""
        with app.app_context():
            # 1. 新しい学校作成
            school_data = {
                'name': 'テスト高等学校',
                'school_code': 'TEST002',
                'address': '東京都新宿区テスト町1-2-3',
                'contact_email': 'contact@test-high.edu.jp',
                'phone': '03-1234-5678'
            }
            
            school_response = admin_client.post('/admin/create_school',
                                              data=school_data,
                                              follow_redirects=True)
            assert school_response.status_code == 200
            
            # 2. 学年作成
            year_data = {
                'year_name': '2025年度',
                'start_date': '2025-04-01',
                'end_date': '2026-03-31',
                'school_id': 2  # 新しく作成された学校のID
            }
            
            year_response = admin_client.post('/admin/create_school_year',
                                            data=year_data,
                                            follow_redirects=True)
            assert year_response.status_code == 200
            
            # 3. クラスグループ作成
            group_data = {
                'name': '1年A組',
                'description': '文系クラス',
                'school_year_id': 1,  # 作成された学年のID
                'capacity': 35
            }
            
            group_response = admin_client.post('/admin/create_class_group',
                                             data=group_data,
                                             follow_redirects=True)
            assert group_response.status_code == 200
            
            # 4. ユーザー一括インポート
            import_data = {
                'user_type': 'students',
                'csv_data': '''email,full_name,class_group_id
student1@test-high.edu.jp,テスト太郎,1
student2@test-high.edu.jp,テスト花子,1
student3@test-high.edu.jp,テスト次郎,1'''
            }
            
            import_response = admin_client.post('/admin/import_users',
                                              data=import_data,
                                              follow_redirects=True)
            assert import_response.status_code == 200
            
            # 5. ユーザー承認処理
            # 未承認ユーザーの確認
            pending_response = admin_client.get('/admin/pending_users')
            assert pending_response.status_code == 200
            
            # 全ユーザーの一括承認
            approve_response = admin_client.post('/admin/approve_all_users',
                                               follow_redirects=True)
            assert approve_response.status_code == 200
    
    def test_system_analytics_and_monitoring_flow(self, admin_client, app):
        """システム分析・監視フローテスト"""
        with app.app_context():
            # 1. ダッシュボード分析データ取得
            dashboard_response = admin_client.get('/admin/dashboard')
            assert dashboard_response.status_code == 200
            
            # 2. ユーザー統計レポート
            user_stats_response = admin_client.get('/admin/user_statistics')
            assert user_stats_response.status_code == 200
            
            # 3. 活動レポート生成
            activity_report_data = {
                'start_date': '2025-01-01',
                'end_date': '2025-01-31',
                'report_type': 'detailed'
            }
            
            report_response = admin_client.post('/admin/generate_activity_report',
                                              data=activity_report_data)
            assert report_response.status_code == 200
            
            # 4. システムヘルスチェック
            health_response = admin_client.get('/admin/system_health')
            assert health_response.status_code == 200
            
            # 5. セキュリティログ確認
            security_logs_response = admin_client.get('/admin/security_logs')
            assert security_logs_response.status_code == 200


@pytest.mark.e2e
class TestCrossRoleInteractions:
    """役割間相互作用のE2Eテスト"""
    
    def test_teacher_student_interaction_flow(self, client, app, sample_class):
        """教師-学生間相互作用フローテスト"""
        with app.app_context():
            # 教師としてログイン
            teacher_login = client.post('/auth/login', data={
                'email': 'teacher@test.com',
                'password': 'teacher123'
            }, follow_redirects=True)
            assert teacher_login.status_code == 200
            
            # 1. 教師がマイルストーンを作成
            milestone_data = {
                'title': '最終発表会',
                'description': '研究成果の最終発表',
                'due_date': '2025-03-20',
                'class_id': sample_class.id
            }
            
            milestone_response = client.post('/teacher/create_milestone',
                                           data=milestone_data,
                                           follow_redirects=True)
            assert milestone_response.status_code == 200
            
            # 教師ログアウト
            client.get('/auth/logout')
            
            # 学生としてログイン
            student_login = client.post('/auth/login', data={
                'email': 'student@test.com',
                'password': 'student123'
            }, follow_redirects=True)
            assert student_login.status_code == 200
            
            # 2. 学生がマイルストーンを確認
            milestones_response = client.get('/student/milestones')
            assert milestones_response.status_code == 200
            
            # 3. 学生がマイルストーンに提出
            submission_data = {
                'milestone_id': 1,  # 作成されたマイルストーンのID
                'submission_text': '研究の最終成果をまとめました。',
                'reflection': '多くのことを学ぶことができました。'
            }
            
            submission_response = client.post('/student/submit_milestone',
                                            data=submission_data,
                                            follow_redirects=True)
            assert submission_response.status_code == 200
            
            # 学生ログアウト
            client.get('/auth/logout')
            
            # 教師として再ログイン
            teacher_relogin = client.post('/auth/login', data={
                'email': 'teacher@test.com',
                'password': 'teacher123'
            }, follow_redirects=True)
            assert teacher_relogin.status_code == 200
            
            # 4. 教師が学生の提出物を確認・評価
            submissions_response = client.get('/teacher/review_submissions')
            assert submissions_response.status_code == 200
            
            evaluation_data = {
                'submission_id': 1,
                'score': 92,
                'feedback': '素晴らしい研究成果です。論理的な構成と深い考察が印象的でした。',
                'suggestions': '今後も継続的な研究を期待しています。'
            }
            
            eval_response = client.post('/teacher/evaluate_submission',
                                      data=evaluation_data,
                                      follow_redirects=True)
            assert eval_response.status_code == 200
    
    def test_admin_teacher_student_hierarchy_flow(self, client, app):
        """管理者-教師-学生階層フローテスト"""
        with app.app_context():
            # 1. 管理者がシステム設定
            admin_login = client.post('/auth/login', data={
                'email': 'admin@test.com',
                'password': 'admin123'
            })
            
            # システム設定
            system_config = {
                'max_students_per_class': 30,
                'milestone_notification_days': 7,
                'auto_backup_enabled': True
            }
            
            config_response = client.post('/admin/system_config',
                                        data=json.dumps(system_config),
                                        content_type='application/json')
            assert config_response.status_code == 200
            
            # 2. 教師権限でクラス作成
            client.get('/auth/logout')
            teacher_login = client.post('/auth/login', data={
                'email': 'teacher@test.com',
                'password': 'teacher123'
            })
            
            # 3. 学生の活動記録
            client.get('/auth/logout')
            student_login = client.post('/auth/login', data={
                'email': 'student@test.com',
                'password': 'student123'
            })
            
            # 4. システム全体での整合性確認
            client.get('/auth/logout')
            admin_relogin = client.post('/auth/login', data={
                'email': 'admin@test.com',
                'password': 'admin123'
            })
            
            # 全体統計の確認
            overall_stats = client.get('/admin/overall_statistics')
            assert overall_stats.status_code == 200


@pytest.mark.e2e 
@pytest.mark.slow
class TestPerformanceAndLoadE2E:
    """パフォーマンス・負荷のE2Eテスト"""
    
    def test_concurrent_user_simulation(self, app):
        """同時ユーザーアクセスシミュレーション"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def user_session(user_email, password, session_id):
            """ユーザーセッションをシミュレート"""
            with app.test_client() as client:
                try:
                    # ログイン
                    login_response = client.post('/auth/login', data={
                        'email': user_email,
                        'password': password
                    })
                    
                    if login_response.status_code == 200:
                        # ダッシュボードアクセス
                        dashboard_response = client.get('/student/dashboard')
                        
                        # 活動記録作成
                        activity_data = {
                            'title': f'同時テスト活動 {session_id}',
                            'content': f'セッション{session_id}のテスト内容',
                            'inquiry_theme_id': 1
                        }
                        activity_response = client.post('/student/create_activity',
                                                      data=activity_data)
                        
                        results.put({
                            'session_id': session_id,
                            'login_status': login_response.status_code,
                            'dashboard_status': dashboard_response.status_code,
                            'activity_status': activity_response.status_code
                        })
                    else:
                        results.put({
                            'session_id': session_id,
                            'login_status': login_response.status_code,
                            'error': 'Login failed'
                        })
                        
                except Exception as e:
                    results.put({
                        'session_id': session_id,
                        'error': str(e)
                    })
        
        # 複数の同時セッションを開始
        threads = []
        for i in range(5):  # 5つの同時セッション
            thread = threading.Thread(
                target=user_session,
                args=('student@test.com', 'student123', i)
            )
            threads.append(thread)
            thread.start()
        
        # すべてのスレッドの完了を待機
        for thread in threads:
            thread.join()
        
        # 結果の確認
        success_count = 0
        while not results.empty():
            result = results.get()
            if result.get('login_status') == 200:
                success_count += 1
        
        # 最低限の成功率を確認
        assert success_count >= 3  # 5回中3回以上成功