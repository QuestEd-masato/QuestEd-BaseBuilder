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
        
        if not classes:
            flash('履修しているクラスがありません。先生に連絡して、クラスに登録してもらってください。')
            return render_template('student_dashboard_no_classes.html')
        
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
            completed=False
        ).order_by(Todo.created_at.desc()).limit(5).all()
        student_info['pending_todos'] = pending_todos
        
        # アクティブな目標を取得（5件）
        active_goals = Goal.query.filter_by(
            student_id=current_user.id
        ).filter(Goal.status.in_(['not_started', 'in_progress'])).limit(5).all()
        student_info['active_goals'] = active_goals
        
        # Phase 2: 自由進度学習の進捗情報を取得
        learning_progress = _get_learning_progress_summary()
        
        # クラス別の詳細情報を取得
        class_details = []
        for class_obj in classes:
            # クラスのメインテーマを取得
            main_themes = MainTheme.query.filter_by(class_id=class_obj.id).all()
            
            # 最新のマイルストーンを取得
            from app.models import Milestone
            next_milestone = Milestone.query.filter_by(class_id=class_obj.id)\
                .filter(Milestone.due_date >= datetime.now().date())\
                .order_by(*mysql_nulls_last(Milestone.due_date, 'asc')).first()
            
            # 最新のチャット履歴を取得（1件）
            latest_chat = ChatHistory.query.filter_by(
                student_id=current_user.id,
                class_id=class_obj.id
            ).order_by(ChatHistory.created_at.desc()).first()
            
            class_detail = {
                'class': class_obj,
                'main_themes': main_themes,
                'next_milestone': next_milestone,
                'latest_chat': latest_chat
            }
            class_details.append(class_detail)
        
        # 週間活動統計を生成
        weekly_stats = _generate_weekly_activity_stats()
        
        # 学習進捗統計
        progress_stats = _generate_progress_stats()
        
        return render_template('student_dashboard.html',
                             student_info=student_info,
                             class_details=class_details,
                             weekly_stats=weekly_stats,
                             progress_stats=progress_stats,
                             learning_progress=learning_progress)
        
    except Exception as e:
        current_app.logger.error(f"Dashboard error for student {current_user.id}: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        flash('ダッシュボードの読み込み中にエラーが発生しました。')
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
            'todos_pending': Todo.query.filter_by(student_id=current_user.id, completed=False).count(),
            'goals_active': Goal.query.filter_by(student_id=current_user.id).filter(
                Goal.status.in_(['not_started', 'in_progress'])
            ).count(),
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
        completed_todos = Todo.query.filter_by(student_id=current_user.id, completed=True).count()
        
        # Goal統計
        total_goals = Goal.query.filter_by(student_id=current_user.id).count()
        completed_goals = Goal.query.filter_by(student_id=current_user.id, status='completed').count()
        
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