# app/student/modules/class_management.py
"""学生クラス管理機能"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, desc

from app.models import db, Class, ClassEnrollment, MainTheme, Milestone, CurriculumUnit
from ..utils import student_required

class_management_bp = Blueprint('student_class_management', __name__)

@class_management_bp.route('/class/<int:class_id>')
@login_required
@student_required
def class_detail(class_id):
    """クラス詳細ページ（マイルストーン・カリキュラム表示）"""
    try:
        # クラス情報を取得
        class_obj = Class.query.get_or_404(class_id)
        
        # 学生がこのクラスに所属しているかチェック
        enrollment = ClassEnrollment.query.filter_by(
            student_id=current_user.id,
            class_id=class_id,
            is_active=True
        ).first()
        
        # 直接クラスIDでの所属もチェック
        if not enrollment and current_user.class_id == class_id:
            # 一時的な疑似enrollment作成
            enrollment = type('Enrollment', (), {
                'class_id': class_id,
                'student_id': current_user.id,
                'is_active': True
            })()
        
        if not enrollment:
            flash('このクラスにアクセスする権限がありません。', 'error')
            return redirect(url_for('student_dashboard.dashboard'))
        
        # メインテーマを取得
        try:
            from app.models import MainTheme, Milestone
            main_themes = MainTheme.query.filter_by(class_id=class_id).order_by(
                MainTheme.created_at.desc()
            ).all()
        except:
            main_themes = []
            current_app.logger.warning("MainTheme model not available")
        
        # マイルストーンを取得
        try:
            milestones = Milestone.query.filter_by(class_id=class_id).order_by(
                Milestone.due_date.asc()
            ).all()
        except:
            milestones = []
            current_app.logger.warning("Milestone model not available")
        
        # 今後のマイルストーンと過去のマイルストーンに分類
        today = datetime.now().date()
        upcoming_milestones = [m for m in milestones if m.due_date and m.due_date >= today]
        past_milestones = [m for m in milestones if m.due_date and m.due_date < today]
        
        # カリキュラム単元を取得（このクラス用）
        try:
            curriculum_units = CurriculumUnit.query.filter_by(
                is_active=True
            ).order_by(
                CurriculumUnit.subject, CurriculumUnit.order
            ).all()
        except:
            curriculum_units = []
            current_app.logger.warning("CurriculumUnit model query failed")
        
        # 科目別にカリキュラムを整理
        curriculum_by_subject = {}
        for unit in curriculum_units:
            subject = unit.subject or '未分類'
            if subject not in curriculum_by_subject:
                curriculum_by_subject[subject] = []
            curriculum_by_subject[subject].append(unit)
        
        # クラスの統計情報
        class_stats = _get_class_statistics(class_id)
        
        # Prepare milestones data to match template expectations
        all_milestones = upcoming_milestones + past_milestones
        
        # Calculate progress statistics
        completed_milestones = len([m for m in all_milestones if hasattr(m, 'is_completed') and m.is_completed])
        total_milestones = len(all_milestones)
        progress_percentage = (completed_milestones / total_milestones * 100) if total_milestones > 0 else 0
        
        # Next milestone
        next_milestone = upcoming_milestones[0] if upcoming_milestones else None
        
        # Curriculum data structure expected by template
        curriculum_data = []
        for subject, units in curriculum_by_subject.items():
            curriculum_data.append({
                'curriculum': {
                    'title': subject,
                    'description': f'{subject}の学習単元'
                },
                'items': units
            })
        
        return render_template('student/class_details.html',
                             class_obj=class_obj,
                             milestones=all_milestones,
                             next_milestone=next_milestone,
                             completed_milestones=completed_milestones,
                             total_milestones=total_milestones,
                             progress_percentage=progress_percentage,
                             curriculum_items=len(curriculum_units),
                             curriculum_data=curriculum_data)
        
    except Exception as e:
        current_app.logger.error(f"Class detail error: {str(e)}")
        flash('クラス詳細の読み込み中にエラーが発生しました。', 'error')
        return redirect(url_for('student_dashboard.dashboard'))

@class_management_bp.route('/milestone/<int:milestone_id>')
@login_required
@student_required
def milestone_detail(milestone_id):
    """マイルストーン詳細"""
    try:
        milestone = Milestone.query.get_or_404(milestone_id)
        
        # 学生がこのクラスに所属しているかチェック
        enrollment = ClassEnrollment.query.filter_by(
            student_id=current_user.id,
            class_id=milestone.class_id,
            is_active=True
        ).first()
        
        if not enrollment and current_user.class_id != milestone.class_id:
            flash('このマイルストーンにアクセスする権限がありません。', 'error')
            return redirect(url_for('student_dashboard.dashboard'))
        
        # このマイルストーンに関連する活動を取得
        from app.models import ActivityRecord
        related_activities = ActivityRecord.query.filter_by(
            student_id=current_user.id,
            class_id=milestone.class_id
        ).filter(
            ActivityRecord.created_at >= milestone.created_at
        ).order_by(ActivityRecord.created_at.desc()).limit(10).all()
        
        return render_template('student/milestone_detail.html',
                             milestone=milestone,
                             related_activities=related_activities)
        
    except Exception as e:
        current_app.logger.error(f"Milestone detail error: {str(e)}")
        flash('マイルストーン詳細の読み込み中にエラーが発生しました。', 'error')
        return redirect(url_for('student_dashboard.dashboard'))

def _get_class_statistics(class_id):
    """クラスの統計情報を取得"""
    try:
        # クラスの学生数
        student_count = ClassEnrollment.query.filter_by(
            class_id=class_id,
            is_active=True
        ).count()
        
        # メインテーマ数
        theme_count = MainTheme.query.filter_by(class_id=class_id).count()
        
        # マイルストーン数
        milestone_count = Milestone.query.filter_by(class_id=class_id).count()
        
        # 今後のマイルストーン数
        today = datetime.now().date()
        upcoming_milestone_count = Milestone.query.filter_by(class_id=class_id).filter(
            Milestone.due_date >= today
        ).count()
        
        return {
            'student_count': student_count,
            'theme_count': theme_count,
            'milestone_count': milestone_count,
            'upcoming_milestone_count': upcoming_milestone_count
        }
        
    except Exception as e:
        current_app.logger.error(f"Class statistics error: {str(e)}")
        return {
            'student_count': 0,
            'theme_count': 0,
            'milestone_count': 0,
            'upcoming_milestone_count': 0
        }