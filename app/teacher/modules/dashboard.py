# app/teacher/modules/dashboard.py
"""教師ダッシュボード機能"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from app.models import (
    db, User, Class, ClassEnrollment, InquiryTheme, Milestone, 
    Curriculum, CurriculumUnit, ChatHistory
)
from app.services.curriculum_bridge_service import CurriculumBridgeService
from app.utils.model_helpers import mysql_nulls_last
from ..common import teacher_required

dashboard_bp = Blueprint('teacher_dashboard', __name__)

@dashboard_bp.route('/teacher_dashboard')
@login_required
@teacher_required
def dashboard():
    """教師ダッシュボード（統合管理機能付き）"""
    from app.services.curriculum_bridge_service import CurriculumBridgeService
    
    # 教師が担当するクラスを取得
    classes = Class.query.filter_by(teacher_id=current_user.id).all()
    
    # 統合統計情報の初期化
    integrated_stats = {
        'total_curriculums': 0,
        'converted_curriculums': 0,
        'total_units': 0,
        'active_units': 0,
        'conversion_rate': 0
    }
    
    # 各クラスの生徒数と統計情報を計算
    class_info = []
    for class_obj in classes:
        # 生徒数を取得
        enrollments = ClassEnrollment.query.filter_by(class_id=class_obj.id).all()
        student_count = len(enrollments)
        
        # アンケート完了数を計算
        survey_completed = 0
        theme_selected = 0
        
        for enrollment in enrollments:
            student = enrollment.student
            # アンケート完了確認
            if student.has_completed_surveys():
                survey_completed += 1
            
            # テーマ選択確認
            selected_theme = InquiryTheme.query.filter_by(
                student_id=student.id,
                is_selected=True
            ).first()
            if selected_theme:
                theme_selected += 1
        
        # 次回のマイルストーンを取得
        next_milestone = Milestone.query.filter_by(class_id=class_obj.id)\
            .filter(Milestone.due_date >= datetime.utcnow().date())\
            .order_by(*mysql_nulls_last(Milestone.due_date, 'asc')).first()
        
        # カリキュラム・単元統合情報を取得
        curriculums = Curriculum.query.filter_by(
            class_id=class_obj.id,
            teacher_id=current_user.id
        ).all()
        
        curriculum_stats = {
            'total_curriculums': len(curriculums),
            'converted_count': 0,
            'total_units': 0,
            'recent_conversions': []
        }
        
        for curriculum in curriculums:
            # 変換状況をチェック
            conversion_status = CurriculumBridgeService.get_conversion_status(curriculum.id)
            if conversion_status.get('is_converted', False):
                curriculum_stats['converted_count'] += 1
                curriculum_stats['total_units'] += conversion_status.get('converted_units', 0)
                
                # 最近の変換履歴
                if conversion_status.get('conversion_date'):
                    curriculum_stats['recent_conversions'].append({
                        'curriculum_title': curriculum.title,
                        'conversion_date': conversion_status['conversion_date'],
                        'units_count': conversion_status.get('converted_units', 0)
                    })
        
        # 統合統計に加算
        integrated_stats['total_curriculums'] += curriculum_stats['total_curriculums']
        integrated_stats['converted_curriculums'] += curriculum_stats['converted_count']
        integrated_stats['total_units'] += curriculum_stats['total_units']
        
        class_info.append({
            'class': class_obj,
            'student_count': student_count,
            'survey_completed': survey_completed,
            'theme_selected': theme_selected,
            'next_milestone': next_milestone,
            'curriculum_stats': curriculum_stats
        })
    
    # アクティブな単元数を取得
    integrated_stats['active_units'] = CurriculumUnit.query.filter_by(
        created_by=current_user.id,
        is_active=True
    ).count()
    
    # 変換率計算
    if integrated_stats['total_curriculums'] > 0:
        integrated_stats['conversion_rate'] = round(
            (integrated_stats['converted_curriculums'] / integrated_stats['total_curriculums']) * 100, 1
        )
    
    # 承認待ちの学生数を取得
    pending_students_count = 0
    if current_user.school_id:
        pending_students_count = User.query.filter_by(
            role='student',
            school_id=current_user.school_id,
            email_confirmed=True,
            is_approved=False
        ).count()
    
    return render_template('teacher_dashboard.html', 
                         classes=class_info,
                         pending_students_count=pending_students_count,
                         integrated_stats=integrated_stats)

@dashboard_bp.route('/teacher/pending_users')
@login_required
@teacher_required
def pending_users():
    """承認待ちユーザー一覧"""
    # 同じ学校の承認待ち学生を取得
    pending_students = User.query.filter_by(
        role='student',
        school_id=current_user.school_id,
        email_confirmed=True,
        is_approved=False
    ).all()
    
    return render_template('teacher/pending_users.html', pending_students=pending_students)

@dashboard_bp.route('/teacher/approve_user/<int:user_id>', methods=['POST'])
@login_required
@teacher_required
def approve_user(user_id):
    """ユーザー承認"""
    user = User.query.get_or_404(user_id)
    
    # 同じ学校の学生のみ承認可能
    if user.school_id != current_user.school_id or user.role != 'student':
        flash('このユーザーを承認する権限がありません。')
        return redirect(url_for('teacher_dashboard.pending_users'))
    
    user.is_approved = True
    db.session.commit()
    
    flash(f'{user.username} を承認しました。')
    return redirect(url_for('teacher_dashboard.pending_users'))

@dashboard_bp.route('/api/teacher/first_class')
@login_required
@teacher_required
def api_teacher_first_class():
    """API: 教師の最初のクラス取得"""
    first_class = Class.query.filter_by(teacher_id=current_user.id).first()
    if first_class:
        return jsonify({
            'status': 'success',
            'class_id': first_class.id,
            'class_name': first_class.name
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'クラスが見つかりません'
        })

@dashboard_bp.route('/teacher/chat')
@login_required
@teacher_required
def chat_page():
    """教師チャット機能"""
    classes = Class.query.filter_by(teacher_id=current_user.id).all()
    recent_chats = ChatHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(ChatHistory.created_at.desc()).limit(10).all()
    
    return render_template('chat.html', 
                         classes=classes,
                         recent_chats=recent_chats)