# app/student/modules/dashboard.py
"""学生ダッシュボード機能"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import text, func, inspect
import logging
import traceback

from app.models import (
    db, User, Class, ClassEnrollment, MainTheme, InquiryTheme,
    InterestSurvey, PersonalitySurvey, ActivityLog, Todo, Goal,
    ChatHistory, CurriculumUnit, StudentUnitSelection
)
from app.utils.model_helpers import mysql_nulls_last
from ..utils import student_required, get_current_student_classes, get_student_theme_status, get_student_survey_status
from basebuilder.models import WordProficiency

dashboard_bp = Blueprint('student_dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    """学生ダッシュボード（Phase2承認ワークフロー対応済み）"""
    try:
        # 学生が履修しているクラスを取得
        enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
        classes = [enrollment.class_obj for enrollment in enrollments]
        
        # ClassEnrollmentが空の場合、User.class_idから取得を試行
        if not classes and current_user.class_id:
            direct_class = Class.query.get(current_user.class_id)
            if direct_class:
                classes = [direct_class]
                current_app.logger.info(f"[DASHBOARD] Student {current_user.id}: Using direct class_id {current_user.class_id}")
        
        # デバッグ情報をログに記録
        current_app.logger.info(f"[DASHBOARD] Student {current_user.id} ({current_user.username}): "
                               f"Found {len(enrollments)} enrollments, {len(classes)} classes, class_id={current_user.class_id}")
        
        if not classes:
            flash('履修しているクラスがありません。先生に連絡して、クラスに登録してもらってください。')
            return render_template('student/dashboard_minimal.html', 
                                 student_info={'class_count': 0},
                                 classes=[])
        
        # 学生の基本情報
        student_info = {
            'has_completed_surveys': False,
            'selected_theme': None,
            'recent_activities': [],
            'pending_todos': [],
            'active_goals': [],
            'class_count': len(classes)
        }
        
        # アンケート完了状況をチェック
        survey_status = get_student_survey_status()
        student_info['has_completed_surveys'] = survey_status['all_completed']
        
        # 選択中のテーマを取得
        theme_status = get_student_theme_status()
        student_info['selected_theme'] = theme_status['selected_theme']
        
        # 最近の活動記録を取得（5件）
        recent_activities = ActivityLog.query.filter_by(
            student_id=current_user.id
        ).order_by(ActivityLog.created_at.desc()).limit(5).all()
        student_info['recent_activities'] = recent_activities
        
        # 未完了のTodoを取得（5件）
        pending_todos = Todo.query.filter_by(
            student_id=current_user.id,
            is_completed=False
        ).order_by(Todo.created_at.desc()).limit(5).all()
        student_info['pending_todos'] = pending_todos
        
        # アクティブな目標を取得（5件）
        active_goals = Goal.query.filter_by(
            student_id=current_user.id,
            is_completed=False
        ).limit(5).all()
        student_info['active_goals'] = active_goals
        
        # Phase 2: 自由進度学習の進捗情報を取得
        try:
            learning_progress = _get_learning_progress_summary()
            current_app.logger.info(f"[DASHBOARD] Learning progress loaded for student {current_user.id}")
        except Exception as e:
            current_app.logger.error(f"[DASHBOARD] Learning progress error: {str(e)}")
            learning_progress = {'selected_units': [], 'stats': {'total_selected': 0}}
        
        # クラス別の詳細情報を取得
        class_details = []
        for class_obj in classes:
            try:
                # クラスのメインテーマを取得
                main_themes = MainTheme.query.filter_by(class_id=class_obj.id).all()
                current_app.logger.debug(f"[DASHBOARD] Main themes loaded for class {class_obj.id}")
                
                # 最新のマイルストーンを取得
                try:
                    from app.models import Milestone
                    next_milestone = Milestone.query.filter_by(class_id=class_obj.id)\
                        .filter(Milestone.due_date >= datetime.now().date())\
                        .order_by(*mysql_nulls_last(Milestone.due_date, 'asc')).first()
                except Exception as milestone_e:
                    current_app.logger.error(f"[DASHBOARD] Milestone query error: {str(milestone_e)}")
                    next_milestone = None
                
                # 最新のチャット履歴を取得（1件）
                try:
                    latest_chat = ChatHistory.query.filter_by(
                        user_id=current_user.id,
                        class_id=class_obj.id
                    ).order_by(ChatHistory.created_at.desc()).first()
                except Exception as chat_e:
                    current_app.logger.error(f"[DASHBOARD] Chat history error: {str(chat_e)}")
                    latest_chat = None
                
                class_detail = {
                    'class': class_obj,
                    'main_themes': main_themes,
                    'next_milestone': next_milestone,
                    'latest_chat': latest_chat
                }
                class_details.append(class_detail)
                
            except Exception as class_e:
                current_app.logger.error(f"[DASHBOARD] Class detail error for class {class_obj.id}: {str(class_e)}")
                # 基本的なクラス情報だけでも追加
                class_details.append({
                    'class': class_obj,
                    'main_themes': [],
                    'next_milestone': None,
                    'latest_chat': None
                })
        
        # 週間活動統計を生成
        try:
            weekly_stats = _generate_weekly_activity_stats()
            current_app.logger.info(f"[DASHBOARD] Weekly stats loaded for student {current_user.id}")
        except Exception as e:
            current_app.logger.error(f"[DASHBOARD] Weekly stats error: {str(e)}")
            weekly_stats = []
        
        # 学習進捗統計
        try:
            progress_stats = _generate_progress_stats()
            current_app.logger.info(f"[DASHBOARD] Progress stats loaded for student {current_user.id}")
        except Exception as e:
            current_app.logger.error(f"[DASHBOARD] Progress stats error: {str(e)}")
            progress_stats = {'todo_completion_rate': 0, 'goal_completion_rate': 0}
        
        # Phase 2: 不足している必須変数を追加
        # BaseBuilder統計変数 (最優先修正)
        try:
            basebuilder_stats = _generate_basebuilder_stats()
            current_app.logger.info(f"[DASHBOARD] BaseBuilder stats loaded for student {current_user.id}")
        except Exception as e:
            current_app.logger.error(f"[DASHBOARD] BaseBuilder stats error: {str(e)}")
            basebuilder_stats = {
                'total_words_attempted': 0,      # エラー発生源
                'total_mastered_words': 0,       # 定着度5の単語数  
                'weekly_words_learned': 0,       # 今週習得単語数
                'mastery_rate': 0,               # 達成率％
                'weekly_target': 20,             # 週間目標（設定値）
                'total_basic_words': 0           # 総基礎単語数
            }
        
        # 自由進度学習統計
        try:
            unit_stats = _generate_unit_stats()
            current_app.logger.info(f"[DASHBOARD] Unit stats loaded for student {current_user.id}")
        except Exception as e:
            current_app.logger.error(f"[DASHBOARD] Unit stats error: {str(e)}")
            unit_stats = {
                'total_units': 0,                # 総学習単元数
                'completed_units': 0,            # 完了単元数
                'in_progress_units': 0,          # 進行中単元数
                'completion_rate': 0,            # 完了率％
                'total_study_time': 0            # 総学習時間（分）
            }
        
        # アンケート情報を実際に取得
        try:
            from app.models import InterestSurvey, PersonalitySurvey
            interest_survey = InterestSurvey.query.filter_by(student_id=current_user.id).first()
            personality_survey = PersonalitySurvey.query.filter_by(student_id=current_user.id).first()
        except Exception as survey_e:
            current_app.logger.error(f"[DASHBOARD] Survey query error: {str(survey_e)}")
            interest_survey = None
            personality_survey = None
        
        survey_info = {
            'interest_survey': interest_survey,      # 興味関心アンケート
            'personality_survey': personality_survey # 性格診断アンケート
        }
        
        # クラス・活動情報を構築
        all_class_themes = []
        for class_detail in class_details:
            class_obj = class_detail['class']
            main_themes = class_detail['main_themes']
            
            # メインテーマがある場合は最初のテーマを使用、ない場合はデフォルト
            theme_title = None
            if main_themes:
                theme_title = main_themes[0].title
            
            class_theme = {
                'class_id': class_obj.id,
                'class_name': class_obj.name,
                'theme_title': theme_title
            }
            all_class_themes.append(class_theme)
        
        activity_info = {
            'all_class_themes': all_class_themes,   # 構築されたクラステーマ
            'class_info': {'class_count': len(classes)} if classes else {},  # クラス情報
            'class_todos': [],               # クラスTODO
            'class_goals': [],               # クラス目標
            'pending_todos_count': 0,        # 未完了TODO数
            'active_goals_count': 0,         # アクティブ目標数
            'recent_activities': [],         # 最近の活動
            'weekly_activities_count': 0,    # 週間活動数
            'monthly_chat_count': 0,         # 月間チャット数
            'class_top_learners': get_class_top_learners(classes),        # クラスランキング
            'weekly_top_learners': []        # 週間ランキング
        }
        
        # テンプレート用のスタイル変数を追加
        template_styles = {
            'btn_primary_style': 'display: inline-block; padding: 0.375rem 0.75rem; font-size: 0.875rem; border-radius: 0.25rem; text-decoration: none; background-color: #0056b3; color: white; border: 1px solid #0056b3;',
            'btn_outline_style': 'display: inline-block; padding: 0.375rem 0.75rem; font-size: 0.875rem; border-radius: 0.25rem; text-decoration: none; background-color: transparent; color: #0056b3; border: 1px solid #0056b3;'
        }
        
        current_app.logger.info(f"[DASHBOARD] Phase 2: Adding missing template variables for student {current_user.id}")
        current_app.logger.info(f"[DASHBOARD] Providing {len(all_class_themes)} class themes to template")
        
        return render_template('student/dashboard.html',
                             student_info=student_info,
                             class_details=class_details,
                             weekly_stats=weekly_stats,
                             progress_stats=progress_stats,
                             learning_progress=learning_progress,
                             # Phase 2: 新規追加変数
                             **basebuilder_stats,
                             **unit_stats,
                             **survey_info,
                             **activity_info,
                             **template_styles)
        
    except ImportError as e:
        current_app.logger.error(f"[DASHBOARD] Import error for student {current_user.id}: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        flash('システムモジュールの読み込みエラーが発生しました。')
        return dashboard_minimal()
    except AttributeError as e:
        current_app.logger.error(f"[DASHBOARD] Attribute error for student {current_user.id}: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        flash('データベースモデルのアクセスエラーが発生しました。')
        return dashboard_minimal()
    except KeyError as e:
        current_app.logger.error(f"[DASHBOARD] Missing context variable for student {current_user.id}: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        flash('テンプレート変数の不足エラーが発生しました。')
        return dashboard_minimal()
    except Exception as e:
        # 詳細なエラー情報をログに記録
        error_context = {
            'student_id': current_user.id,
            'error_type': type(e).__name__,
            'error_message': str(e),
            'function': 'dashboard()',
            'line_info': traceback.format_exc()
        }
        current_app.logger.error(f"[DASHBOARD] Unexpected error: {error_context}")
        
        # エラーの種類によって詳細なメッセージを設定
        if 'template' in str(e).lower():
            flash('テンプレートレンダリングでエラーが発生しました。')
        elif 'database' in str(e).lower() or 'sql' in str(e).lower():
            flash('データベース接続でエラーが発生しました。')
        elif 'permission' in str(e).lower() or 'access' in str(e).lower():
            flash('データアクセス権限でエラーが発生しました。')
        else:
            flash('予期しないエラーが発生しました。')
        
        return dashboard_minimal()

@dashboard_bp.route('/dashboard_minimal')
@login_required 
@student_required
def dashboard_minimal():
    """最小限のダッシュボード（エラー時のフォールバック）"""
    try:
        enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
        classes = [enrollment.class_obj for enrollment in enrollments]
        
        # Phase 2: 自由進度学習の基本情報
        learning_units = CurriculumUnit.query.filter_by(is_active=True).limit(10).all()
        selected_units = StudentUnitSelection.query.filter_by(
            student_id=current_user.id
        ).all()
        
        return render_template('student/dashboard_minimal.html',
                             classes=classes,
                             learning_units=learning_units,
                             selected_units=selected_units)
        
    except Exception as e:
        current_app.logger.error(f"Minimal dashboard error: {str(e)}")
        return render_template('errors/500.html')

@dashboard_bp.route('/debug/role')
@login_required
def debug_role():
    """ロール情報のデバッグ表示"""
    if not current_app.debug:
        return "Debug mode only", 404
    
    debug_info = {
        'user_id': current_user.id,
        'username': current_user.username,
        'role': current_user.role,
        'is_authenticated': current_user.is_authenticated,
        'is_active': current_user.is_active,
        'is_approved': current_user.is_approved
    }
    
    return jsonify(debug_info)

@dashboard_bp.route('/debug/routes')
@login_required
def debug_routes():
    """利用可能なルート一覧のデバッグ表示"""
    if not current_app.debug:
        return "Debug mode only", 404
    
    routes = []
    for rule in current_app.url_map.iter_rules():
        if 'student' in rule.rule:
            routes.append({
                'endpoint': rule.endpoint,
                'rule': rule.rule,
                'methods': list(rule.methods)
            })
    
    return jsonify(routes)

@dashboard_bp.route('/api/dashboard/quick-stats')
@login_required
@student_required
def api_quick_stats():
    """ダッシュボード用のクイック統計API"""
    try:
        # 基本統計
        stats = {
            'activities_count': ActivityLog.query.filter_by(student_id=current_user.id).count(),
            'todos_pending': Todo.query.filter_by(student_id=current_user.id, is_completed=False).count(),
            'goals_active': Goal.query.filter_by(student_id=current_user.id, is_completed=False).count(),
            'classes_enrolled': ClassEnrollment.query.filter_by(student_id=current_user.id).count()
        }
        
        # Phase 2: 学習進捗統計
        learning_stats = {
            'units_selected': StudentUnitSelection.query.filter_by(student_id=current_user.id).count(),
            'units_completed': StudentUnitSelection.query.filter_by(
                student_id=current_user.id, 
                status='completed'
            ).count(),
            'units_in_progress': StudentUnitSelection.query.filter_by(
                student_id=current_user.id,
                status='in_progress'
            ).count(),
            'pending_approvals': StudentUnitSelection.query.filter_by(
                student_id=current_user.id,
                approval_status='pending'
            ).count()
        }
        
        stats.update(learning_stats)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def _get_learning_progress_summary():
    """学習進捗サマリーを取得（Phase 2）"""
    try:
        # 選択中の単元
        selected_units = StudentUnitSelection.query.filter_by(
            student_id=current_user.id
        ).all()
        
        # 承認ワークフロー統計
        approval_stats = {
            'total_selected': len(selected_units),
            'completed': len([u for u in selected_units if u.status == 'completed']),
            'in_progress': len([u for u in selected_units if u.status == 'in_progress']),
            'pending_approval': len([u for u in selected_units if u.approval_status == 'pending']),
            'approved': len([u for u in selected_units if u.approval_status == 'approved']),
            'rejected': len([u for u in selected_units if u.approval_status == 'rejected'])
        }
        
        # 進捗率計算
        if approval_stats['total_selected'] > 0:
            approval_stats['completion_rate'] = round(
                (approval_stats['completed'] / approval_stats['total_selected']) * 100, 1
            )
            approval_stats['approval_rate'] = round(
                (approval_stats['approved'] / approval_stats['total_selected']) * 100, 1
            )
        else:
            approval_stats['completion_rate'] = 0
            approval_stats['approval_rate'] = 0
        
        return {
            'selected_units': selected_units[:5],  # 最新5件
            'stats': approval_stats
        }
        
    except Exception as e:
        current_app.logger.error(f"Learning progress summary error: {str(e)}")
        return {
            'selected_units': [],
            'stats': {
                'total_selected': 0,
                'completed': 0,
                'in_progress': 0,
                'pending_approval': 0,
                'approved': 0,
                'rejected': 0,
                'completion_rate': 0,
                'approval_rate': 0
            }
        }

def _generate_weekly_activity_stats():
    """週間活動統計を生成"""
    try:
        # 過去7日間の活動統計
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        daily_activities = db.session.query(
            func.date(ActivityLog.created_at).label('date'),
            func.count(ActivityLog.id).label('count')
        ).filter(
            ActivityLog.student_id == current_user.id,
            ActivityLog.created_at >= start_date,
            ActivityLog.created_at <= end_date
        ).group_by(
            func.date(ActivityLog.created_at)
        ).all()
        
        # 7日分のデータを準備（活動がない日は0）
        stats = []
        for i in range(7):
            date = (start_date + timedelta(days=i)).date()
            count = 0
            
            for activity in daily_activities:
                if activity.date == date:
                    count = activity.count
                    break
            
            stats.append({
                'date': date.strftime('%m/%d'),
                'count': count
            })
        
        return stats
        
    except Exception as e:
        current_app.logger.error(f"Weekly stats error: {str(e)}")
        return []

def _generate_progress_stats():
    """進捗統計を生成"""
    try:
        # Todo統計
        total_todos = Todo.query.filter_by(student_id=current_user.id).count()
        completed_todos = Todo.query.filter_by(student_id=current_user.id, is_completed=True).count()
        
        # Goal統計
        total_goals = Goal.query.filter_by(student_id=current_user.id).count()
        completed_goals = Goal.query.filter_by(student_id=current_user.id, is_completed=True).count()
        
        return {
            'todo_completion_rate': round((completed_todos / total_todos) * 100, 1) if total_todos > 0 else 0,
            'goal_completion_rate': round((completed_goals / total_goals) * 100, 1) if total_goals > 0 else 0,
            'total_todos': total_todos,
            'completed_todos': completed_todos,
            'total_goals': total_goals,
            'completed_goals': completed_goals
        }
        
    except Exception as e:
        current_app.logger.error(f"Progress stats error: {str(e)}")
        return {
            'todo_completion_rate': 0,
            'goal_completion_rate': 0,
            'total_todos': 0,
            'completed_todos': 0,
            'total_goals': 0,
            'completed_goals': 0
        }

def get_class_top_learners(classes):
    """クラスの上位学習者を取得（基礎学力マスターランキング）"""
    try:
        if not classes:
            return []
        
        # 全クラスのstudent_idを取得
        class_ids = [cls.id for cls in classes]
        
        # ClassEnrollmentから学生IDを取得
        student_ids = db.session.query(ClassEnrollment.student_id).filter(
            ClassEnrollment.class_id.in_(class_ids)
        ).distinct().all()
        
        if not student_ids:
            return []
        
        student_ids = [sid[0] for sid in student_ids]
        
        # 各学生の5/5レベル達成単語数を計算
        mastered_words_query = db.session.query(
            WordProficiency.student_id,
            func.count(WordProficiency.id).label('mastered_count')
        ).filter(
            WordProficiency.student_id.in_(student_ids),
            WordProficiency.level == 5
        ).group_by(WordProficiency.student_id).all()
        
        # 学生情報と結合して上位5名を取得
        top_learners = []
        for student_id, mastered_count in mastered_words_query:
            user = User.query.get(student_id)
            if user:
                top_learners.append({
                    'student_id': student_id,
                    'full_name': user.full_name or user.username,
                    'username': user.username,
                    'word_count': mastered_count
                })
        
        # 習得単語数で降順ソート、上位5名を取得
        top_learners.sort(key=lambda x: x['word_count'], reverse=True)
        
        return top_learners[:5]
        
    except Exception as e:
        current_app.logger.error(f"[DASHBOARD] get_class_top_learners error: {str(e)}")
        return []

def _generate_basebuilder_stats():
    """BaseBuilder統計を生成 - 実際のデータベース情報から計算"""
    try:
        from datetime import datetime, timedelta
        from basebuilder.models import BasicKnowledgeItem, AnswerRecord
        
        current_app.logger.info(f"[DASHBOARD] Generating BaseBuilder stats for student {current_user.id}")
        
        # AnswerRecordから学習履歴を取得
        answer_records = AnswerRecord.query.filter_by(
            student_id=current_user.id
        ).all()
        
        current_app.logger.info(f"[DASHBOARD] Found {len(answer_records)} answer records")
        
        # WordProficiencyから習熟度を取得
        word_proficiencies = WordProficiency.query.filter_by(
            student_id=current_user.id
        ).all()
        
        current_app.logger.info(f"[DASHBOARD] Found {len(word_proficiencies)} word proficiency records")
        
        # 基本統計を計算
        total_problems_attempted = len(set(record.problem_id for record in answer_records))
        total_correct_answers = sum(1 for record in answer_records if record.is_correct)
        
        # WordProficiencyベースの統計
        total_words_attempted = len(word_proficiencies)
        total_mastered_words = sum(1 for wp in word_proficiencies if wp.level >= 80)
        
        # データがない場合の代替計算
        if total_words_attempted == 0 and total_problems_attempted > 0:
            # 問題レベルでの習得計算
            problem_stats = {}
            for record in answer_records:
                if record.problem_id not in problem_stats:
                    problem_stats[record.problem_id] = {'correct': 0, 'total': 0}
                problem_stats[record.problem_id]['total'] += 1
                if record.is_correct:
                    problem_stats[record.problem_id]['correct'] += 1
            
            total_words_attempted = len(problem_stats)
            total_mastered_words = sum(1 for stats in problem_stats.values() 
                                     if stats['total'] >= 3 and stats['correct'] / stats['total'] >= 0.8)
        
        # 今週の学習統計
        week_start = datetime.now() - timedelta(days=7)
        weekly_answers = [record for record in answer_records if record.created_at >= week_start]
        weekly_words_learned = len(set(record.problem_id for record in weekly_answers if record.is_correct))
        
        # 習得率を計算
        if total_problems_attempted > 0:
            mastery_rate = round((total_correct_answers / len(answer_records)) * 100, 1)
        else:
            mastery_rate = round((total_mastered_words / total_words_attempted) * 100, 1) if total_words_attempted > 0 else 0
        
        # 総基礎単語数
        total_basic_words = BasicKnowledgeItem.query.count()
        
        stats = {
            'total_words_attempted': max(total_words_attempted, total_problems_attempted),
            'total_mastered_words': total_mastered_words,
            'weekly_words_learned': weekly_words_learned,
            'mastery_rate': mastery_rate,
            'weekly_target': 20,
            'total_basic_words': total_basic_words,
            'total_answers': len(answer_records),
            'correct_answers': total_correct_answers
        }
        
        current_app.logger.info(f"[DASHBOARD] BaseBuilder stats calculated: {stats}")
        return stats
        
    except Exception as e:
        current_app.logger.error(f"[DASHBOARD] BaseBuilder stats error: {str(e)}")
        import traceback
        current_app.logger.error(f"[DASHBOARD] Traceback: {traceback.format_exc()}")
        return {
            'total_words_attempted': 0,
            'total_mastered_words': 0,
            'weekly_words_learned': 0,
            'mastery_rate': 0,
            'weekly_target': 20,
            'total_basic_words': 0,
            'total_answers': 0,
            'correct_answers': 0
        }

def _generate_unit_stats():
    """自由進度学習統計を生成"""
    try:
        from app.models import CurriculumUnit, StudentUnitSelection
        from datetime import datetime, timedelta
        
        current_app.logger.info(f"[DASHBOARD] Generating unit stats for student {current_user.id}")
        
        # 学生の単元選択を取得
        unit_selections = StudentUnitSelection.query.filter_by(
            student_id=current_user.id
        ).all()
        
        current_app.logger.info(f"[DASHBOARD] Found {len(unit_selections)} unit selections")
        
        # 利用可能な総単元数
        total_available_units = CurriculumUnit.query.filter_by(is_active=True).count()
        
        # 統計計算
        total_units = len(unit_selections)
        completed_units = sum(1 for selection in unit_selections if selection.completion_rate >= 100)
        in_progress_units = sum(1 for selection in unit_selections if 0 < selection.completion_rate < 100)
        
        # 完了率計算
        completion_rate = round((completed_units / total_units) * 100, 1) if total_units > 0 else 0
        
        # 総学習時間（分）- 単元選択の更新日時から推定
        total_study_time = 0
        if unit_selections:
            # 最初の選択から最新の更新までの期間を基に推定学習時間を計算
            earliest_selection = min(selection.created_at for selection in unit_selections if selection.created_at)
            latest_update = max(selection.updated_at for selection in unit_selections if selection.updated_at)
            
            if earliest_selection and latest_update:
                study_period_days = (latest_update - earliest_selection).days
                # 単元数と完了率から学習時間を推定（1単元平均30分と仮定）
                estimated_time_per_unit = 30
                total_study_time = sum(
                    int(selection.completion_rate / 100 * estimated_time_per_unit) 
                    for selection in unit_selections
                )
        
        stats = {
            'total_units': total_units,
            'completed_units': completed_units,
            'in_progress_units': in_progress_units,
            'completion_rate': completion_rate,
            'total_study_time': total_study_time,
            'available_units': total_available_units
        }
        
        current_app.logger.info(f"[DASHBOARD] Unit stats calculated: {stats}")
        return stats
        
    except Exception as e:
        current_app.logger.error(f"[DASHBOARD] Unit stats error: {str(e)}")
        import traceback
        current_app.logger.error(f"[DASHBOARD] Traceback: {traceback.format_exc()}")
        return {
            'total_units': 0,
            'completed_units': 0,
            'in_progress_units': 0,
            'completion_rate': 0,
            'total_study_time': 0,
            'available_units': 0
        }